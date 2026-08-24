"""Tarayıcı eklentisi için yerel API anahtarı.

Yerel API'ler ``Access-Control-Allow-Origin: *`` ile açıktı ve kimlik
doğrulaması yoktu: kullanıcı herhangi bir siteyi gezerken o site sahte kalp
atışı gönderip veriye sahte oturum enjekte edebilir, ayrıca izlenen tüm
alan adlarını okuyabilirdi. Artık eklenti, kullanıcının Ayarlar sayfasından
kopyaladığı bir anahtarla kimliğini kanıtlıyor.
"""

import hmac
import logging
import os
import secrets

from platform_katmani import yollar

logger = logging.getLogger(__name__)

_ANAHTAR_DOSYASI = "api-anahtari.txt"
_onbellek = None


def _yol():
    return os.path.join(yollar.veri_dizini(), _ANAHTAR_DOSYASI)


def anahtari_al():
    """Anahtarı okur, yoksa üretir."""
    global _onbellek
    if _onbellek:
        return _onbellek

    yol = _yol()
    try:
        if os.path.exists(yol):
            with open(yol, "r", encoding="utf-8") as f:
                mevcut = f.read().strip()
            if mevcut:
                _onbellek = mevcut
                return _onbellek
    except OSError as hata:
        logger.warning("API anahtarı okunamadı: %s", hata)

    return anahtari_yenile()


def anahtari_yenile():
    global _onbellek
    yeni = secrets.token_urlsafe(24)
    try:
        yollar.dizini_hazirla(yollar.veri_dizini())
        with open(_yol(), "w", encoding="utf-8") as f:
            f.write(yeni)
    except OSError as hata:
        logger.warning("API anahtarı yazılamadı: %s", hata)
    _onbellek = yeni
    return yeni


def dogrula(sunulan):
    if not sunulan:
        return False
    return hmac.compare_digest(str(sunulan), anahtari_al())
