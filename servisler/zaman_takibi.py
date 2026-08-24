"""Oturum kayıtları: başlatma, durdurma, düzenleme.

Aktif oturumlar "checkpoint" modeliyle tutulur: her tarama turunda
``son_gorulme`` ve ``birikmis_saniye`` diske işaretlenir. Böylece çökmede
tüm oturum değil, en fazla bir tur kaybedilir ve açılışta hayalet oturumlar
``son_gorulme`` anında kapatılabilir.
"""

import datetime as dt
import logging
import uuid

import config
from depo import json_deposu

logger = logging.getLogger(__name__)


def simdi():
    """Zaman dilimi bilgisi taşıyan şimdiki zaman.

    Naive damgalar DST geçişinde süreyi bir saat kaydırdığı için her yerde
    offset'li damga kullanılır.
    """
    return dt.datetime.now().astimezone()


def zaman_coz(metin):
    """ISO metni datetime'a çevirir; naive gelirse yerel dilime bağlar."""
    if not metin:
        return None
    try:
        an = dt.datetime.fromisoformat(metin)
    except (TypeError, ValueError):
        return None
    if an.tzinfo is None:
        an = an.astimezone()
    return an


def yeni_aktif_oturum(kaynak, baslangic=None):
    an = baslangic or simdi()
    return {
        "baslangic": an.isoformat(timespec="seconds"),
        # son_gorulme aritmetikte kullanılır: saniyeye yuvarlanırsa her turda
        # kesir kadar fazla sayılır ve uzun günlerde süre belirgin şişer.
        "son_gorulme": an.isoformat(),
        "birikmis_saniye": 0,
        "bosta_mi": False,
        "kaynak": kaynak,
    }


def _oturum_kaydi(kategori, baslangic, bitis, saniye, kaynak, notu=""):
    return {
        "id": uuid.uuid4().hex,
        "tarih": baslangic.date().isoformat(),
        "kategori": kategori,
        "baslangic": baslangic.strftime("%H:%M:%S"),
        "bitis": bitis.strftime("%H:%M:%S"),
        "sure_dakika": round(saniye / 60, 1),
        "kaynak": kaynak,
        "not": notu,
        "duzenlendi": False,
    }


def oturumlari_uret(kategori, baslangic, bitis, toplam_saniye, kaynak, notu=""):
    """Bir çalışmayı gün sınırlarına bölerek oturum kayıtlarına çevirir.

    23:00–01:00 arası bir çalışma tek güne yazılırsa gece çalışanların
    heatmap'i kayar ve Pazar gecesi çalışması önceki haftaya düşer. Bu
    yüzden kayıt gün sınırında bölünür.

    ``toplam_saniye`` boşta geçen süre çıkarılmış gerçek süredir; gün
    sınırına bölünürken duvar saati süresine oranlanarak dağıtılır.
    """
    if bitis <= baslangic:
        return []

    tavan = config.OTURUM_TAVANI_SAAT * 3600
    if toplam_saniye > tavan:
        logger.warning(
            "'%s' oturumu tavanı aştı (%.0f sn), %s saate kırpıldı",
            kategori, toplam_saniye, config.OTURUM_TAVANI_SAAT,
        )
        toplam_saniye = tavan

    duvar_saniye = (bitis - baslangic).total_seconds()
    oran = (toplam_saniye / duvar_saniye) if duvar_saniye > 0 else 0

    kayitlar = []
    parca_baslangic = baslangic
    while parca_baslangic < bitis:
        gun_sonu = dt.datetime.combine(
            parca_baslangic.date() + dt.timedelta(days=1),
            dt.time.min,
            tzinfo=parca_baslangic.tzinfo,
        )
        parca_bitis = min(gun_sonu, bitis)
        parca_duvar = (parca_bitis - parca_baslangic).total_seconds()
        parca_saniye = parca_duvar * oran
        if parca_saniye >= 1:
            gosterilen_bitis = parca_bitis - dt.timedelta(seconds=1) if parca_bitis == gun_sonu else parca_bitis
            kayitlar.append(
                _oturum_kaydi(
                    kategori, parca_baslangic, gosterilen_bitis, parca_saniye, kaynak, notu
                )
            )
        parca_baslangic = parca_bitis
    return kayitlar


def aktif_oturumu_kapat(veri, kategori, bitis=None):
    """Aktif oturumu kapatıp ``oturumlar`` listesine yazar.

    ``bitis`` verilmezse ``son_gorulme`` kullanılır — çökme kurtarmasında
    doğru davranış budur.
    """
    aktif = veri["aktif_oturumlar"].pop(kategori, None)
    if not aktif:
        return []

    baslangic = zaman_coz(aktif.get("baslangic"))
    son_gorulme = zaman_coz(aktif.get("son_gorulme")) or baslangic
    if baslangic is None:
        return []

    gercek_bitis = bitis or son_gorulme or baslangic
    saniye = aktif.get("birikmis_saniye") or 0
    if saniye <= 0:
        saniye = max((gercek_bitis - baslangic).total_seconds(), 0)

    kayitlar = oturumlari_uret(
        kategori, baslangic, gercek_bitis, saniye, aktif.get("kaynak", "manuel")
    )
    veri["oturumlar"].extend(kayitlar)
    return kayitlar


def oturum_baslat(kategori, kaynak="manuel"):
    with json_deposu.guncelle() as veri:
        if kategori in veri["aktif_oturumlar"]:
            raise ValueError(f"'{kategori}' için zaten aktif bir oturum var.")
        veri["aktif_oturumlar"][kategori] = yeni_aktif_oturum(kaynak)
        return veri["aktif_oturumlar"][kategori]


def oturum_durdur(kategori, ertele=True):
    """Oturumu şimdi kapatır.

    Otomatik bir oturum elle durdurulduğunda kategori bir süre ertelenir;
    aksi hâlde program hâlâ açık olduğu için izleme motoru oturumu anında
    yeniden başlatır ve "Durdur" işe yaramamış görünür. Erteleme aynı kilit
    altında yazılır, böylece araya tarama giremez.
    """
    with json_deposu.guncelle() as veri:
        aktif = veri["aktif_oturumlar"].get(kategori)
        if aktif is None:
            raise ValueError(f"'{kategori}' için aktif oturum yok.")
        kaynak = aktif.get("kaynak", "manuel")
        kayitlar = aktif_oturumu_kapat(veri, kategori, bitis=simdi())
        if ertele and kaynak == "otomatik":
            bitis = simdi() + dt.timedelta(seconds=config.IZLEME_ERTELEME_SANIYE)
            veri["izleme"]["ertelemeler"][kategori] = bitis.isoformat(timespec="seconds")
        return kayitlar


def tum_oturumlari_durdur():
    """Uygulama kapanırken açık kalan tüm oturumları kapatır."""
    with json_deposu.guncelle() as veri:
        kategoriler = list(veri["aktif_oturumlar"].keys())
        for kategori in kategoriler:
            aktif_oturumu_kapat(veri, kategori, bitis=simdi())
        return kategoriler


def aktif_oturumlari_getir():
    return json_deposu.oku()["aktif_oturumlar"]


def gecen_saniye(aktif):
    """Aktif bir oturumun o ana kadarki gerçek (boşta hariç) süresi."""
    saniye = aktif.get("birikmis_saniye") or 0
    # Boşta ya da kayıp (program kapalı, grace bekleniyor) ise sunucu da süre
    # işletmiyor; ekran da ilerlememeli.
    if not aktif.get("bosta_mi") and not aktif.get("kayip_zamani"):
        son_gorulme = zaman_coz(aktif.get("son_gorulme"))
        if son_gorulme:
            saniye += max((simdi() - son_gorulme).total_seconds(), 0)
    return saniye


def oturum_durumu(aktif):
    """Arayüzde gösterilecek durum: calisiyor | bosta | kayip."""
    if aktif.get("kayip_zamani"):
        return "kayip"
    if aktif.get("bosta_mi"):
        return "bosta"
    return "calisiyor"


# --- Oturum düzenleme -------------------------------------------------------

def oturum_guncelle(oturum_id, **alanlar):
    """Kayıtlı bir oturumun alanlarını değiştirir."""
    with json_deposu.guncelle() as veri:
        for oturum in veri["oturumlar"]:
            if oturum.get("id") == oturum_id:
                for anahtar in ("tarih", "kategori", "sure_dakika", "not"):
                    if anahtar in alanlar and alanlar[anahtar] is not None:
                        oturum[anahtar] = alanlar[anahtar]
                oturum["duzenlendi"] = True
                return oturum
        raise ValueError("Oturum bulunamadı.")


def oturum_sil(oturum_id):
    with json_deposu.guncelle() as veri:
        onceki = len(veri["oturumlar"])
        veri["oturumlar"] = [o for o in veri["oturumlar"] if o.get("id") != oturum_id]
        if len(veri["oturumlar"]) == onceki:
            raise ValueError("Oturum bulunamadı.")


def oturum_ekle(tarih, kategori, sure_dakika, notu=""):
    """Elle geçmişe oturum ekler."""
    with json_deposu.guncelle() as veri:
        oturum = {
            "id": uuid.uuid4().hex,
            "tarih": tarih,
            "kategori": kategori,
            "baslangic": "",
            "bitis": "",
            "sure_dakika": sure_dakika,
            "kaynak": "manuel",
            "not": notu,
            "duzenlendi": True,
        }
        veri["oturumlar"].append(oturum)
        return oturum
