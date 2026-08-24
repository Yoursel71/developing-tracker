"""Kullanıcının boşta kalma süresinin ölçümü (Windows).

Windows dışında "asla boşta değil" döner; böylece geliştirme ortamında
uygulama normal çalışır.

Uygulama incelikleri (MSDN kaynaklı):

* ``GetTickCount`` için ``restype`` mutlaka ``DWORD`` olmalı. ctypes'ın
  varsayılan işaretli ``c_int``'i, sistem 24.8 günden uzun açık kalınca
  negatife düşer ve hesabı bozar.
* ``GetTickCount64`` bu sorunu çözmez: ``LASTINPUTINFO.dwTime`` her hâlükârda
  32-bit. Doğru çözüm 32-bit modüler çıkarma.
* ``dwTime`` monoton değildir; "gelecekte" bir değer gelebilir.
* ``GetTickCount`` uyku sırasında ilerlemez — uzun boşluklar duvar saatiyle
  ayrıca tespit edilmelidir (bkz. ``servisler.otomatik_izleme``).
* API oturum genelinde çalışır: uygulama arka plandayken kullanıcının başka
  bir programda yazması da algılanır.
"""

import ctypes
import logging
import sys

logger = logging.getLogger(__name__)

_DESTEKLENIYOR = sys.platform == "win32"
_uyari_verildi = False

if _DESTEKLENIYOR:  # pragma: no cover - yalnızca Windows'ta çalışır
    from ctypes import wintypes

    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("dwTime", wintypes.DWORD),
        ]

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    _user32.GetLastInputInfo.argtypes = [ctypes.POINTER(_LASTINPUTINFO)]
    _user32.GetLastInputInfo.restype = wintypes.BOOL

    _kernel32.GetTickCount.argtypes = []
    _kernel32.GetTickCount.restype = wintypes.DWORD


def destekleniyor_mu():
    return _DESTEKLENIYOR


def bosta_gecen_saniye():
    """Son klavye/fare girdisinden bu yana geçen saniye.

    Windows dışında her zaman 0.0 döner (asla boşta sayılmaz).
    """
    global _uyari_verildi

    if not _DESTEKLENIYOR:
        if not _uyari_verildi:
            logger.info(
                "Boşta kalma algılama yalnızca Windows'ta çalışır; "
                "bu sistemde kullanıcı hiç boşta sayılmayacak."
            )
            _uyari_verildi = True
        return 0.0

    try:  # pragma: no cover - yalnızca Windows'ta çalışır
        bilgi = _LASTINPUTINFO()
        bilgi.cbSize = ctypes.sizeof(_LASTINPUTINFO)
        if not _user32.GetLastInputInfo(ctypes.byref(bilgi)):
            return 0.0

        simdi = _kernel32.GetTickCount()
        fark_ms = (simdi - bilgi.dwTime) & 0xFFFFFFFF
        if fark_ms > 0x7FFFFFFF:
            # dwTime "gelecekte" — MSDN bunun mümkün olduğunu söylüyor.
            return 0.0
        return fark_ms / 1000.0
    except Exception as hata:  # pragma: no cover
        logger.warning("Boşta süresi okunamadı: %s", hata)
        return 0.0
