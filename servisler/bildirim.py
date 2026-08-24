"""Masaüstü bildirimleri.

PyInstaller'ın ``plyer`` için hook'u yoktur; platform modülü dinamik import
edildiği için paketlenmiş ``.exe``'de bulunamaz. Derlemede
``--hidden-import plyer.platforms.win.notification`` verilmesi şart —
aksi hâlde bildirimler sessizce hiç gelmez.
"""

import logging

logger = logging.getLogger(__name__)

_kullanilamaz_loglandi = False


def bildirim_gonder(baslik, mesaj):
    """Bildirim gönderir; desteklenmeyen ortamda sessizce False döner."""
    global _kullanilamaz_loglandi
    try:
        from plyer import notification

        notification.notify(title=baslik, message=mesaj, app_name="Gelişim Takip", timeout=10)
        logger.info("Bildirim gönderildi: %s", baslik)
        return True
    except Exception as hata:
        if not _kullanilamaz_loglandi:
            logger.warning(
                "Bildirim gönderilemedi (%s). Bu ortamda masaüstü bildirimi "
                "desteklenmiyor olabilir.", hata,
            )
            _kullanilamaz_loglandi = True
        return False


def kullanilabilir_mi():
    try:
        from plyer import notification  # noqa: F401

        return True
    except Exception:
        return False
