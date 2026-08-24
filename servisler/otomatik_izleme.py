"""Otomatik izleme motoru.

Her kategori için bir durum makinesi işletilir::

    YOK ──(algılandı)──> CALISIYOR
    CALISIYOR ──(boşta eşiği)──> BOSTA          # süre birikmez
    BOSTA ──(girdi)──> CALISIYOR                # kesintisiz devam
    CALISIYOR/BOSTA ──(algılanmıyor)──> KAYIP   # grace başlar
    KAYIP ──(tekrar algılandı)──> CALISIYOR
    KAYIP ──(grace doldu)──> YOK                # oturum kapanır

Boştayken oturum kapanmaz, yalnızca duraklar; böylece kısa molalar geçmişi
onlarca parçaya bölmez ama açık unutulan editör saat yazmaz.
"""

import datetime as dt
import logging
import threading

import config
from depo import json_deposu
from platform_katmani import bosta, surecler
from servisler import zaman_takibi

logger = logging.getLogger(__name__)

# Tarayıcı eklentisinden gelen son "açık" kalp atışı (kategori -> datetime).
# Yalnızca RAM'de tutulur; kaybolursa eklenti 15 saniye içinde yeniler.
_site_kalp_atislari = {}
_kalp_kilidi = threading.Lock()

_durdur_bayragi = threading.Event()
_thread = None
_duraklatildi = threading.Event()

# Bir önceki turun duvar saati; uyku/askıya alma tespiti için.
_onceki_tur_zamani = None


# --- Tarayıcı eklentisi arayüzü --------------------------------------------

def site_durumu_bildir(kategori, durum):
    with _kalp_kilidi:
        if durum == "acik":
            _site_kalp_atislari[kategori] = zaman_takibi.simdi()
        elif durum == "kapandi":
            _site_kalp_atislari.pop(kategori, None)


def _site_aktif_mi(kategori, su_an):
    with _kalp_kilidi:
        son = _site_kalp_atislari.get(kategori)
    if son is None:
        return False
    return (su_an - son).total_seconds() < config.IZLEME_SITE_KALP_ATISI_ZAMAN_ASIMI_SANIYE


# --- Duraklatma (tepsi menüsünden) -----------------------------------------

def duraklat():
    _duraklatildi.set()


def devam_et():
    _duraklatildi.clear()


def duraklatildi_mi():
    return _duraklatildi.is_set()


# --- Yardımcılar ------------------------------------------------------------

def _kategori_eslemeleri(veri):
    """kategori -> izlenen işlem adları / alan adları.

    Bir işlem yalnızca ilk eşleştiği kategoriye bağlanır; aynı işlemin iki
    kategoriye eşlenmesi süreyi çift saydırırdı.
    """
    editorler = {}
    gorulen_islemler = set()
    for kayit in veri["izleme"]["editorler"]:
        islem = (kayit.get("islem_adi") or "").strip().lower()
        kategori = kayit.get("kategori")
        if not islem or not kategori or islem in gorulen_islemler:
            continue
        gorulen_islemler.add(islem)
        editorler.setdefault(kategori, []).append(islem)

    siteler = {}
    gorulen_alanlar = set()
    for kayit in veri["izleme"]["siteler"]:
        alan = (kayit.get("alan_adi") or "").strip().lower()
        kategori = kayit.get("kategori")
        if not alan or not kategori or alan in gorulen_alanlar:
            continue
        gorulen_alanlar.add(alan)
        siteler.setdefault(kategori, []).append(alan)

    return editorler, siteler


def _ertelendi_mi(veri, kategori, su_an):
    damga = veri["izleme"]["ertelemeler"].get(kategori)
    if not damga:
        return False
    bitis = zaman_takibi.zaman_coz(damga)
    if bitis is None or su_an >= bitis:
        veri["izleme"]["ertelemeler"].pop(kategori, None)
        return False
    return True


def _uyku_oldu_mu(su_an):
    """İki tarama arasında duvar saati beklenenden çok ilerlediyse True.

    GetLastInputInfo uyku sırasında ilerlemediği için dizüstünün kapağının
    kapatıldığı süre boşta olarak görünmez; bunu duvar saatiyle yakalarız.
    """
    global _onceki_tur_zamani
    onceki = _onceki_tur_zamani
    _onceki_tur_zamani = su_an
    if onceki is None:
        return False
    return (su_an - onceki).total_seconds() > config.UYKU_TESPIT_TOLERANSI_SANIYE


# --- Ana tarama -------------------------------------------------------------

def tara_bir_kez(su_an=None, bosta_saniye=None, calisan_islemler=None):
    """Tek bir tarama turu. Test edilebilir olması için parametreli."""
    su_an = su_an or zaman_takibi.simdi()
    uyku_oldu = _uyku_oldu_mu(su_an)

    if bosta_saniye is None:
        bosta_saniye = bosta.bosta_gecen_saniye()

    with json_deposu.belki_guncelle() as (veri, degisti_isaretle):
        editorler, siteler = _kategori_eslemeleri(veri)
        esik_saniye = (veri["ayarlar"]["bosta_esigi_dakika"] or 0) * 60
        kullanici_bosta = uyku_oldu or (esik_saniye > 0 and bosta_saniye >= esik_saniye)

        if calisan_islemler is None:
            aranan = {ad for adlar in editorler.values() for ad in adlar}
            calisan_islemler = surecler.aranan_islemler_calisiyor_mu(aranan)

        kategoriler = set(editorler) | set(siteler) | set(veri["aktif_oturumlar"])

        for kategori in kategoriler:
            if _islem_gor(
                veri, kategori, editorler, siteler, calisan_islemler,
                su_an, kullanici_bosta, uyku_oldu,
            ):
                degisti_isaretle()


def _algilaniyor_mu(kategori, editorler, siteler, calisan_islemler, su_an):
    for islem in editorler.get(kategori, []):
        if islem in calisan_islemler:
            return True
    if kategori in siteler and _site_aktif_mi(kategori, su_an):
        return True
    return False


def _islem_gor(veri, kategori, editorler, siteler, calisan_islemler,
               su_an, kullanici_bosta, uyku_oldu):
    """Tek bir kategori için durum makinesini ilerletir. Değişiklik varsa True."""
    aktif = veri["aktif_oturumlar"].get(kategori)
    izleniyor = kategori in editorler or kategori in siteler
    algilaniyor = izleniyor and _algilaniyor_mu(
        kategori, editorler, siteler, calisan_islemler, su_an
    )

    # --- Aktif oturum yok ---
    if aktif is None:
        if algilaniyor and not _ertelendi_mi(veri, kategori, su_an) and not duraklatildi_mi():
            veri["aktif_oturumlar"][kategori] = zaman_takibi.yeni_aktif_oturum(
                "otomatik", su_an
            )
            logger.info("Otomatik oturum başladı: %s", kategori)
            return True
        return False

    # --- Manuel oturumlar: yalnızca süreyi işaretle ---
    if aktif.get("kaynak") != "otomatik":
        return _sureyi_isaretle(aktif, su_an, kullanici_bosta or uyku_oldu)

    # --- Otomatik oturum, hâlâ algılanıyor ---
    if algilaniyor and not duraklatildi_mi():
        aktif.pop("kayip_zamani", None)
        return _sureyi_isaretle(aktif, su_an, kullanici_bosta or uyku_oldu)

    # --- Algılanmıyor: grace süresi ---
    # Süre birikmez ama "boşta" işareti kullanıcının gerçek durumunu yansıtır;
    # program kapandığı için duran bir oturum "hareket bekleniyor" demez.
    _sureyi_isaretle(
        aktif, su_an, kullanici_bosta or uyku_oldu, biriksin=False
    )
    kayip_damgasi = aktif.get("kayip_zamani")
    if not kayip_damgasi:
        aktif["kayip_zamani"] = su_an.isoformat()
        return True

    kayip_zamani = zaman_takibi.zaman_coz(kayip_damgasi) or su_an
    if (su_an - kayip_zamani).total_seconds() < config.IZLEME_KAYIP_GRACE_SANIYE:
        return True

    zaman_takibi.aktif_oturumu_kapat(veri, kategori, bitis=kayip_zamani)
    logger.info("Otomatik oturum kapandı: %s", kategori)
    return True


def _sureyi_isaretle(aktif, su_an, bosta_mi, biriksin=True):
    """``birikmis_saniye`` ve ``son_gorulme`` alanlarını günceller.

    Boşta geçen turlar süreye eklenmez; ``son_gorulme`` yine ilerletilir ki
    çökme kurtarması oturumu doğru anda kapatabilsin. ``biriksin=False``,
    kayıp (grace) durumunda süre işlemesin diye kullanılır.
    """
    son_gorulme = zaman_takibi.zaman_coz(aktif.get("son_gorulme"))
    onceki_bosta = bool(aktif.get("bosta_mi"))

    if biriksin and son_gorulme and not onceki_bosta and not bosta_mi:
        gecen = max((su_an - son_gorulme).total_seconds(), 0)
        aktif["birikmis_saniye"] = (aktif.get("birikmis_saniye") or 0) + gecen

    # Tam hassasiyet: saniyeye yuvarlamak her turda kesir kadar fazla saydırır.
    aktif["son_gorulme"] = su_an.isoformat()
    aktif["bosta_mi"] = bool(bosta_mi)
    return True


# --- Açılışta çökme kurtarma -----------------------------------------------

def acilis_kurtarmasi():
    """Önceki çalışmadan kalan aktif oturumları kapatır.

    Uygulama çökerse veya bilgisayar kapanırsa ``aktif_oturumlar`` diskte
    kalır. Kurtarma olmadan bu oturumlar bir sonraki açılışta "hâlâ devam
    ediyor" sayılır ve günlerce süren sahte kayıtlar üretir.
    """
    with json_deposu.belki_guncelle() as (veri, degisti_isaretle):
        su_an = zaman_takibi.simdi()
        for kategori in list(veri["aktif_oturumlar"].keys()):
            aktif = veri["aktif_oturumlar"][kategori]
            son_gorulme = zaman_takibi.zaman_coz(aktif.get("son_gorulme"))
            if son_gorulme is None:
                veri["aktif_oturumlar"].pop(kategori, None)
                degisti_isaretle()
                continue
            bosluk = (su_an - son_gorulme).total_seconds()
            if bosluk > config.IZLEME_TARAMA_ARALIGI_SANIYE * 3:
                kayitlar = zaman_takibi.aktif_oturumu_kapat(
                    veri, kategori, bitis=son_gorulme
                )
                toplam = sum(k["sure_dakika"] for k in kayitlar)
                logger.info(
                    "Çökme kurtarma: '%s' oturumu %s dakika olarak kapatıldı",
                    kategori, toplam,
                )
                degisti_isaretle()


# --- Thread yönetimi --------------------------------------------------------

def _dongu():
    while not _durdur_bayragi.is_set():
        try:
            tara_bir_kez()
        except Exception:
            logger.exception("Otomatik izleme taramasında hata")
        _durdur_bayragi.wait(config.IZLEME_TARAMA_ARALIGI_SANIYE)


def baslat():
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    try:
        acilis_kurtarmasi()
    except Exception:
        logger.exception("Açılış kurtarması başarısız")
    _durdur_bayragi.clear()
    _thread = threading.Thread(target=_dongu, daemon=True, name="otomatik-izleme")
    _thread.start()
    logger.info("İzleme motoru başladı")


def durdur():
    global _thread
    _durdur_bayragi.set()
    thread = _thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=2)
    _thread = None
    logger.info("İzleme motoru durdu")
