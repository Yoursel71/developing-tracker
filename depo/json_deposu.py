import json
import os

from config import GITHUB_KULLANICI, VARSAYILAN_HAFTALIK_HEDEF_SAAT, VARSAYILAN_TOPLAM_HEDEF_SAAT, VERI_DOSYASI


def _varsayilan_veri_olustur():
    return {
        "oturumlar": [],
        "aktif_oturum": None,
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
    }


def oku():
    if not os.path.exists(VERI_DOSYASI):
        veri = _varsayilan_veri_olustur()
        yaz(veri)
        return veri
    with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)


def yaz(veri):
    os.makedirs(os.path.dirname(VERI_DOSYASI), exist_ok=True)
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
