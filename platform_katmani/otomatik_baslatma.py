"""Windows açılışında otomatik başlatma (HKCU\\...\\Run)."""

import logging
import sys

logger = logging.getLogger(__name__)

_ANAHTAR_YOLU = r"Software\Microsoft\Windows\CurrentVersion\Run"
_DEGER_ADI = "GelisimTakip"


def destekleniyor_mu():
    return sys.platform == "win32" and getattr(sys, "frozen", False)


def _komut():
    return f'"{sys.executable}" --arkaplan'


def ayarla(acik):
    """Kaydı ekler veya siler. Başarılıysa True."""
    if not destekleniyor_mu():
        if acik:
            logger.info(
                "Windows ile başlatma yalnızca paketlenmiş .exe içinde çalışır; atlandı."
            )
        return False

    try:  # pragma: no cover - yalnızca Windows'ta çalışır
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _ANAHTAR_YOLU, 0, winreg.KEY_SET_VALUE
        ) as anahtar:
            if acik:
                winreg.SetValueEx(anahtar, _DEGER_ADI, 0, winreg.REG_SZ, _komut())
                logger.info("Windows açılışına eklendi")
            else:
                try:
                    winreg.DeleteValue(anahtar, _DEGER_ADI)
                    logger.info("Windows açılışından kaldırıldı")
                except FileNotFoundError:
                    pass
        return True
    except OSError as hata:  # pragma: no cover
        logger.warning("Windows açılış kaydı güncellenemedi: %s", hata)
        return False


def acik_mi():
    if not destekleniyor_mu():
        return False
    try:  # pragma: no cover
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _ANAHTAR_YOLU, 0, winreg.KEY_READ
        ) as anahtar:
            winreg.QueryValueEx(anahtar, _DEGER_ADI)
        return True
    except OSError:
        return False
