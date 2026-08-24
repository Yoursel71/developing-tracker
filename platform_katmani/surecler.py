"""Çalışan süreçlerin sorgulanması."""

import logging

import psutil

logger = logging.getLogger(__name__)


def aranan_islemler_calisiyor_mu(aranan_adlar):
    """Verilen işlem adlarından hangilerinin çalıştığını döner.

    Tüm süreç listesini toplamak yerine aranan isimler bulunur bulunmaz
    erken çıkılır; tarama 10 saniyede bir çalıştığı için bu fark eder.
    """
    aranan = {ad.lower() for ad in aranan_adlar if ad}
    if not aranan:
        return set()

    bulunan = set()
    try:
        for surec in psutil.process_iter(["name"]):
            ad = (surec.info.get("name") or "").lower()
            if ad in aranan:
                bulunan.add(ad)
                if len(bulunan) == len(aranan):
                    break
    except Exception as hata:
        logger.warning("Süreç taraması başarısız: %s", hata)
    return bulunan
