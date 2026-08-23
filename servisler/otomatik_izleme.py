import logging
import threading
from datetime import datetime, timedelta

import psutil

from config import (
    IZLEME_ERTELEME_SANIYE,
    IZLEME_KAYIP_GRACE_SANIYE,
    IZLEME_SITE_KALP_ATISI_ZAMAN_ASIMI_SANIYE,
    IZLEME_TARAMA_ARALIGI_SANIYE,
)
from depo import json_deposu

logger = logging.getLogger(__name__)

# Kullanıcı bir otomatik oturumu elle durdurduğunda, o kategori bu zamana
# kadar yeniden otomatik başlatılmaz (işlem/site hâlâ açık olsa bile).
_erteleme_bitisleri = {}
# Tarayıcı eklentisinden gelen son "açık" kalp atışı zamanı (kategoriye göre).
_site_son_kalp_atisi = {}

_durdur_bayragi = threading.Event()
_thread = None


def site_durumu_bildir(kategori, durum):
    """Tarayıcı eklentisinden gelen POST /api/site-durumu çağrısını işler."""
    if durum == "acik":
        _site_son_kalp_atisi[kategori] = datetime.now()
    elif durum == "kapandi":
        _site_son_kalp_atisi.pop(kategori, None)


def oturumu_ertele(kategori):
    """Kullanıcı otomatik bir oturumu elle durdurduğunda çağrılır; izleme
    motorunun işlemi/siteyi hâlâ açık görüp hemen yeniden başlatmasını önler."""
    _erteleme_bitisleri[kategori] = datetime.now() + timedelta(seconds=IZLEME_ERTELEME_SANIYE)


def _calisan_islem_adlari():
    adlar = set()
    for surec in psutil.process_iter(["name"]):
        ad = surec.info.get("name")
        if ad:
            adlar.add(ad.lower())
    return adlar


def _kategori_algilaniyor_mu(kategori, editor_kategorileri, site_kategorileri, calisan_islemler, simdi):
    for islem_adi in editor_kategorileri.get(kategori, []):
        if islem_adi.lower() in calisan_islemler:
            return True
    son_kalp_atisi = _site_son_kalp_atisi.get(kategori)
    if kategori in site_kategorileri and son_kalp_atisi is not None:
        if (simdi - son_kalp_atisi).total_seconds() < IZLEME_SITE_KALP_ATISI_ZAMAN_ASIMI_SANIYE:
            return True
    return False


def tara_bir_kez():
    """İzlenen editör/site listesine göre kategorileri kontrol eder ve
    aktif_oturumlar'ı gerektiği gibi başlatır/durdurur. Tek bir tur çalıştırır."""
    simdi = datetime.now()
    calisan_islemler = _calisan_islem_adlari()

    with json_deposu.guncelle() as veri:
        editor_kategorileri = {}
        for e in veri["izleme"]["editorler"]:
            editor_kategorileri.setdefault(e["kategori"], []).append(e["islem_adi"])

        site_kategorileri = {}
        for s in veri["izleme"]["siteler"]:
            site_kategorileri.setdefault(s["kategori"], []).append(s["alan_adi"])

        for kategori in set(editor_kategorileri) | set(site_kategorileri):
            algilaniyor = _kategori_algilaniyor_mu(
                kategori, editor_kategorileri, site_kategorileri, calisan_islemler, simdi
            )
            aktif = veri["aktif_oturumlar"].get(kategori)

            if algilaniyor:
                if aktif is None:
                    erteleme_bitisi = _erteleme_bitisleri.get(kategori)
                    if erteleme_bitisi is None or simdi >= erteleme_bitisi:
                        veri["aktif_oturumlar"][kategori] = {
                            "baslangic": simdi.isoformat(timespec="seconds"),
                            "kaynak": "otomatik",
                            "kayip_zamani": None,
                        }
                elif aktif.get("kayip_zamani"):
                    aktif["kayip_zamani"] = None
                continue

            if aktif is None or aktif.get("kaynak") != "otomatik":
                continue

            if aktif.get("kayip_zamani") is None:
                aktif["kayip_zamani"] = simdi.isoformat(timespec="seconds")
                continue

            kayip_zamani = datetime.fromisoformat(aktif["kayip_zamani"])
            if (simdi - kayip_zamani).total_seconds() < IZLEME_KAYIP_GRACE_SANIYE:
                continue

            baslangic = datetime.fromisoformat(aktif["baslangic"])
            sure_dakika = round((kayip_zamani - baslangic).total_seconds() / 60, 1)
            veri["oturumlar"].append({
                "tarih": baslangic.date().isoformat(),
                "kategori": kategori,
                "baslangic": baslangic.strftime("%H:%M:%S"),
                "bitis": kayip_zamani.strftime("%H:%M:%S"),
                "sure_dakika": sure_dakika,
            })
            del veri["aktif_oturumlar"][kategori]


def _dongu():
    while not _durdur_bayragi.is_set():
        try:
            tara_bir_kez()
        except Exception:
            logger.exception("Otomatik izleme taramasında hata")
        _durdur_bayragi.wait(IZLEME_TARAMA_ARALIGI_SANIYE)


def baslat():
    global _thread
    if _thread is not None:
        return
    _durdur_bayragi.clear()
    _thread = threading.Thread(target=_dongu, daemon=True, name="otomatik-izleme")
    _thread.start()


def durdur():
    _durdur_bayragi.set()
