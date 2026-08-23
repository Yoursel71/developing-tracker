import contextlib
import json
import os
import threading

from config import GITHUB_KULLANICI, VARSAYILAN_HAFTALIK_HEDEF_SAAT, VARSAYILAN_TOPLAM_HEDEF_SAAT, VERI_DOSYASI

_kilit = threading.Lock()


def _varsayilan_veri_olustur():
    return {
        "kurulum_tamamlandi": False,
        "oturumlar": [],
        "aktif_oturumlar": {},
        "hedefler": {
            "haftalik_saat": VARSAYILAN_HAFTALIK_HEDEF_SAAT,
            "toplam_hedef_saat": VARSAYILAN_TOPLAM_HEDEF_SAAT,
            "son_bildirim_tarihi": None,
        },
        "github": {
            "kullanici": GITHUB_KULLANICI,
            "son_cekilen_etkinlikler": [],
            "son_senkron": None,
        },
        "izleme": {
            "editorler": [],
            "siteler": [],
        },
    }


def _oku_kilitsiz():
    if not os.path.exists(VERI_DOSYASI):
        veri = _varsayilan_veri_olustur()
        _yaz_kilitsiz(veri)
        return veri
    with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)


def _yaz_kilitsiz(veri):
    os.makedirs(os.path.dirname(VERI_DOSYASI), exist_ok=True)
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def oku():
    with _kilit:
        return _oku_kilitsiz()


def yaz(veri):
    with _kilit:
        _yaz_kilitsiz(veri)


@contextlib.contextmanager
def guncelle():
    """Oku + değiştir + yaz adımlarını tek bir kilit altında atomik yapar.

    Arka plan izleme thread'i ile Flask istekleri aynı anda veri.json'a
    yazabildiği için (oku sonra yaz) yarış durumunu önlemek gerekiyor.
    """
    with _kilit:
        veri = _oku_kilitsiz()
        yield veri
        _yaz_kilitsiz(veri)
