import logging

logger = logging.getLogger(__name__)


def bildirim_gonder(baslik, mesaj):
    """Masaüstü bildirimi gönderir. Desteklenmeyen ortamlarda sessizce başarısız olur."""
    try:
        from plyer import notification

        notification.notify(title=baslik, message=mesaj, timeout=10)
        return True
    except Exception as hata:
        logger.warning("Bildirim gönderilemedi: %s", hata)
        return False
