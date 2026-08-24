"""Sistem tepsisi ikonu.

pywebview ana thread'te çalışmak zorunda; pystray ise Windows'ta ayrı bir
thread'de güvenle çalışır (``run_detached``). Bu yüzden pencere ana
thread'te, tepsi arka planda tutulur.

Dikkat: ``run_detached`` daemon olmayan bir thread açar — çıkışta
``durdur()`` çağrılmazsa süreç görünmez şekilde ayakta kalır.
"""

import logging

logger = logging.getLogger(__name__)

_ikon = None


def _gorsel(aktif=True):
    from PIL import Image, ImageDraw

    renk = "#3fb950" if aktif else "#6e7d8d"
    gorsel = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    cizim = ImageDraw.Draw(gorsel)
    cizim.ellipse((4, 4, 60, 60), fill="#151b23", outline=renk, width=5)
    # Yükselen grafik çizgisi
    cizim.line([(18, 42), (28, 32), (36, 38), (48, 22)], fill=renk, width=5, joint="curve")
    return gorsel


def baslat(ac_geri_cagri, duraklat_geri_cagri, cikis_geri_cagri, duraklatildi_mi):
    """Tepsi ikonunu ayrı thread'de başlatır. Başarılıysa True."""
    global _ikon
    try:
        import pystray
    except ImportError:
        logger.info("pystray kurulu değil; tepsi ikonu devre dışı.")
        return False

    def duraklat_etiketi(_oge):
        return "Takibi sürdür" if duraklatildi_mi() else "Takibi duraklat"

    try:
        _ikon = pystray.Icon(
            "GelisimTakip",
            _gorsel(True),
            "Gelişim Takip",
            menu=pystray.Menu(
                pystray.MenuItem("Aç", lambda *_: ac_geri_cagri(), default=True),
                pystray.MenuItem(duraklat_etiketi, lambda *_: duraklat_geri_cagri()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Çıkış", lambda *_: cikis_geri_cagri()),
            ),
        )
        _ikon.run_detached()
        logger.info("Tepsi ikonu başlatıldı")
        return True
    except Exception as hata:
        logger.warning("Tepsi ikonu başlatılamadı: %s", hata)
        _ikon = None
        return False


def durumu_guncelle(aktif):
    if _ikon is None:
        return
    try:
        _ikon.icon = _gorsel(aktif)
        _ikon.update_menu()
    except Exception:
        pass


def durdur():
    global _ikon
    if _ikon is None:
        return
    try:
        _ikon.stop()
    except Exception:
        pass
    _ikon = None
