"""Log yapılandırması.

``--windowed`` derlemede ``sys.stderr`` ``None`` olduğu için varsayılan
logging çıktısı hiçbir yere gitmez. Bu yüzden loglar kullanıcı veri
dizinindeki dönen bir dosyaya yazılır.
"""

import logging
import logging.handlers
import os
import sys

from platform_katmani import yollar

_kuruldu = False


def kur(seviye=logging.INFO):
    global _kuruldu
    if _kuruldu:
        return

    kok = logging.getLogger()
    kok.setLevel(seviye)

    bicim = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    try:
        yollar.dizini_hazirla(yollar.veri_dizini())
        dosya_isleyici = logging.handlers.RotatingFileHandler(
            yollar.gunluk_dosyasi(), maxBytes=512 * 1024, backupCount=3, encoding="utf-8"
        )
        dosya_isleyici.setFormatter(bicim)
        kok.addHandler(dosya_isleyici)
    except OSError:
        # Log dosyası açılamazsa uygulama yine de çalışmalı.
        pass

    if sys.stderr is not None:
        konsol = logging.StreamHandler(sys.stderr)
        konsol.setFormatter(bicim)
        kok.addHandler(konsol)

    # Flask/werkzeug her isteği loglamasın.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    _kuruldu = True


def gunluk_dosyasi_yolu():
    return yollar.gunluk_dosyasi()


def gunluk_klasorunu_ac():
    """Ayarlardaki 'log klasörünü aç' bağlantısı için."""
    dizin = yollar.veri_dizini()
    try:
        if sys.platform == "win32":
            os.startfile(dizin)  # noqa: S606 - kullanıcının kendi klasörü
        elif sys.platform == "darwin":
            os.system(f'open "{dizin}"')
        else:
            os.system(f'xdg-open "{dizin}"')
        return True
    except Exception:
        logging.getLogger(__name__).warning("Klasör açılamadı: %s", dizin)
        return False
