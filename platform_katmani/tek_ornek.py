"""Tek örnek (single instance) kilidi.

İki örnek aynı ``veri.json``'a yazarsa kayıtlar birbirini ezebilir. Kilit,
sabit uygulama portunu dinlemeye çalışarak kurulur: port zaten kullanımdaysa
başka bir örnek çalışıyordur.
"""

import logging
import socket

import config

logger = logging.getLogger(__name__)

_soket = None


def kilidi_al():
    """Kilidi almaya çalışır. Başka örnek çalışıyorsa False döner."""
    global _soket
    kilit_portu = config.UYGULAMA_PORTU + 1
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # SO_REUSEADDR verilmez: portun gerçekten boş olduğunu görmek istiyoruz.
        s.bind(("127.0.0.1", kilit_portu))
        s.listen(1)
        _soket = s
        return True
    except OSError:
        logger.info("Başka bir örnek zaten çalışıyor (port %s meşgul)", kilit_portu)
        return False


def kilidi_birak():
    global _soket
    if _soket is not None:
        try:
            _soket.close()
        except OSError:
            pass
        _soket = None
