"""JSON dosya deposu: atomik yazma, yedekleme ve bozuk dosyadan kurtarma."""

import contextlib
import datetime as dt
import glob
import json
import logging
import os
import shutil
import threading

from depo import goc
from depo.varsayilan import normallestir, varsayilan_veri
from platform_katmani import yollar

logger = logging.getLogger(__name__)

_kilit = threading.RLock()

TUTULACAK_YEDEK_SAYISI = 10

# Bozuk dosyadan kurtarma yaşandıysa arayüzde uyarı gösterebilmek için.
son_kurtarma_mesaji = None


def _yaz_atomik(veri, hedef):
    """Geçici dosyaya yazıp atomik olarak taşır.

    ``open(..., "w")`` dosyayı önce sıfırladığı için çökme yarım dosya
    bırakırdı; ``os.replace`` hem Windows hem POSIX'te atomiktir.
    """
    yollar.dizini_hazirla(os.path.dirname(hedef))
    gecici = hedef + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(gecici, hedef)


def _yedekleri_buda():
    dizin = yollar.yedek_dizini()
    yedekler = sorted(glob.glob(os.path.join(dizin, "veri-*.json")))
    for eski in yedekler[:-TUTULACAK_YEDEK_SAYISI]:
        try:
            os.remove(eski)
        except OSError:
            pass


def _gunluk_yedek_al(kaynak):
    """Gün başına bir yedek alır."""
    if not os.path.exists(kaynak):
        return
    dizin = yollar.dizini_hazirla(yollar.yedek_dizini())
    bugun = dt.date.today().isoformat().replace("-", "")
    if glob.glob(os.path.join(dizin, f"veri-{bugun}-*.json")):
        return
    damga = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        shutil.copy2(kaynak, os.path.join(dizin, f"veri-{damga}.json"))
        _yedekleri_buda()
    except OSError as hata:
        logger.warning("Yedek alınamadı: %s", hata)


def _en_yeni_yedegi_oku():
    dizin = yollar.yedek_dizini()
    for yedek in sorted(glob.glob(os.path.join(dizin, "veri-*.json")), reverse=True):
        try:
            with open(yedek, "r", encoding="utf-8") as f:
                return json.load(f), yedek
        except (OSError, json.JSONDecodeError):
            continue
    return None, None


def _bozuk_dosyayi_kenara_al(yol):
    try:
        damga = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        os.replace(yol, f"{yol}.bozuk-{damga}")
    except OSError:
        pass


def _oku_kilitsiz():
    global son_kurtarma_mesaji
    yol = yollar.veri_dosyasi()

    if not os.path.exists(yol):
        veri = varsayilan_veri()
        _yaz_atomik(veri, yol)
        return veri

    try:
        with open(yol, "r", encoding="utf-8") as f:
            ham = json.load(f)
    except (OSError, json.JSONDecodeError) as hata:
        logger.error("veri.json okunamadı (%s), yedeğe düşülüyor", hata)
        yedek, yedek_yolu = _en_yeni_yedegi_oku()
        _bozuk_dosyayi_kenara_al(yol)
        if yedek is None:
            son_kurtarma_mesaji = (
                "Veri dosyası okunamadı ve kullanılabilir yedek bulunamadı; "
                "sıfırdan başlandı. Bozuk dosya yanına .bozuk uzantısıyla saklandı."
            )
            logger.error("Kullanılabilir yedek yok, sıfırdan başlanıyor")
            veri = varsayilan_veri()
            _yaz_atomik(veri, yol)
            return veri
        son_kurtarma_mesaji = (
            f"Veri dosyası bozuktu, {os.path.basename(yedek_yolu)} yedeğinden "
            "geri yüklendi."
        )
        ham = yedek

    veri, goc_yapildi = goc.goc_et(ham)
    if goc_yapildi:
        _gunluk_yedek_al(yol)
        _yaz_atomik(veri, yol)
    return veri


def _yaz_kilitsiz(veri):
    yol = yollar.veri_dosyasi()
    _gunluk_yedek_al(yol)
    _yaz_atomik(veri, yol)


def oku():
    with _kilit:
        return _oku_kilitsiz()


def yaz(veri):
    with _kilit:
        _yaz_kilitsiz(normallestir(veri))


@contextlib.contextmanager
def guncelle():
    """Oku + değiştir + yaz adımlarını tek kilit altında atomik yapar.

    Blok içinde istisna olursa yazma yapılmaz. Blok ``degisti = False``
    işaretlemek isterse ``veri`` sözlüğüne dokunmaması yeterlidir; yine de
    her çıkışta yazılır, bu yüzden yalnızca gerçekten değiştiren yerlerde
    kullanılmalıdır.
    """
    with _kilit:
        veri = _oku_kilitsiz()
        yield veri
        _yaz_kilitsiz(normallestir(veri))


@contextlib.contextmanager
def belki_guncelle():
    """``guncelle`` gibi ama yalnızca blok ``True`` işaretlerse yazar.

    Kullanım::

        with belki_guncelle() as (veri, isaret):
            if bir_sey_degisti:
                isaret()
    """
    with _kilit:
        veri = _oku_kilitsiz()
        durum = {"yaz": False}

        def isaret():
            durum["yaz"] = True

        yield veri, isaret
        if durum["yaz"]:
            _yaz_kilitsiz(normallestir(veri))


def kurtarma_mesajini_al_ve_temizle():
    global son_kurtarma_mesaji
    mesaj = son_kurtarma_mesaji
    son_kurtarma_mesaji = None
    return mesaj


def yedekleri_listele():
    dizin = yollar.yedek_dizini()
    sonuc = []
    for yedek in sorted(glob.glob(os.path.join(dizin, "veri-*.json")), reverse=True):
        try:
            sonuc.append({
                "dosya": os.path.basename(yedek),
                "boyut": os.path.getsize(yedek),
                "tarih": dt.datetime.fromtimestamp(os.path.getmtime(yedek)).isoformat(
                    timespec="seconds"
                ),
            })
        except OSError:
            continue
    return sonuc


def yedekten_geri_yukle(dosya_adi):
    """Verilen yedeği aktif veri dosyası yapar."""
    guvenli_ad = os.path.basename(dosya_adi)
    kaynak = os.path.join(yollar.yedek_dizini(), guvenli_ad)
    if not os.path.exists(kaynak):
        raise FileNotFoundError(f"Yedek bulunamadı: {guvenli_ad}")
    with _kilit:
        with open(kaynak, "r", encoding="utf-8") as f:
            ham = json.load(f)
        veri, _ = goc.goc_et(ham)
        _gunluk_yedek_al(yollar.veri_dosyasi())
        _yaz_atomik(veri, yollar.veri_dosyasi())
    return veri
