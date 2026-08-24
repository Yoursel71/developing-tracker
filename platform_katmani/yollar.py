"""Dosya yollarının çözümü.

Kritik ayrım:

* **Paket kaynakları** (templates, static) salt-okunurdur ve PyInstaller
  ``--onefile`` derlemesinde geçici ``sys._MEIPASS`` klasöründen okunur.
* **Kullanıcı verisi** (veri.json, yedekler, log) ASLA oraya yazılmamalıdır:
  bootloader o klasörü süreç çıkışında siler ve klasör adı her çalıştırmada
  rastgeledir. Yazılabilir veri işletim sisteminin kullanıcı veri dizinine
  gider.
"""

import os
import sys

UYGULAMA_ADI = "GelisimTakip"

# Bu dosyanın yanında bu isimde bir dosya varsa veri exe'nin yanına yazılır
# (USB'den taşınabilir kullanım senaryosu).
TASINABILIR_ISARET_DOSYASI = "tasinabilir.txt"


def donmus_mu():
    """PyInstaller ile paketlenmiş bir çalıştırılabilir içinde miyiz?"""
    return getattr(sys, "frozen", False)


def paket_kok_dizini():
    """--add-data ile paketlenmiş salt-okunur kaynakların kökü."""
    if donmus_mu() and hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def kaynak_yolu(*parcalar):
    """Paketlenmiş salt-okunur dosya yolu (templates, static, ...)."""
    return os.path.join(paket_kok_dizini(), *parcalar)


def _isletim_sistemi_veri_dizini():
    if sys.platform == "win32":
        temel = os.environ.get("LOCALAPPDATA") or os.path.expanduser(
            os.path.join("~", "AppData", "Local")
        )
    elif sys.platform == "darwin":
        temel = os.path.expanduser("~/Library/Application Support")
    else:
        temel = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(temel, UYGULAMA_ADI)


def veri_dizini():
    """Kalıcı kullanıcı verisinin yazılacağı dizin.

    Geliştirme modunda depo içindeki ``data/`` kullanılır; donmuş modda
    işletim sisteminin kullanıcı veri dizini (ya da taşınabilir mod).
    """
    ozel = os.environ.get("GELISIM_TAKIP_VERI_DIZINI")
    if ozel:
        return ozel

    if not donmus_mu():
        return os.path.join(paket_kok_dizini(), "data")

    exe_dizini = os.path.dirname(os.path.abspath(sys.executable))
    isaret = os.path.join(exe_dizini, TASINABILIR_ISARET_DOSYASI)
    if os.path.exists(isaret) and os.access(exe_dizini, os.W_OK):
        return os.path.join(exe_dizini, "data")

    return _isletim_sistemi_veri_dizini()


def veri_dosyasi():
    return os.path.join(veri_dizini(), "veri.json")


def yedek_dizini():
    return os.path.join(veri_dizini(), "yedekler")


def gunluk_dosyasi():
    return os.path.join(veri_dizini(), "uygulama.log")


def dizini_hazirla(yol):
    os.makedirs(yol, exist_ok=True)
    return yol
