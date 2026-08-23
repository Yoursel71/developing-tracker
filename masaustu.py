import threading
import time
import urllib.request

import webview

from app import app
from config import UYGULAMA_PORTU
from servisler import zaman_takibi


def _sunucuyu_baslat():
    app.run(host="127.0.0.1", port=UYGULAMA_PORTU, debug=False, use_reloader=False)


def _sunucu_hazir_mi():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{UYGULAMA_PORTU}/", timeout=1)
        return True
    except Exception:
        return False


def _pencere_kapanirken():
    try:
        zaman_takibi.tum_oturumlari_durdur()
    except Exception:
        pass


def calistir():
    threading.Thread(target=_sunucuyu_baslat, daemon=True).start()

    for _ in range(50):
        if _sunucu_hazir_mi():
            break
        time.sleep(0.1)

    pencere = webview.create_window(
        "Gelişim Takip",
        f"http://127.0.0.1:{UYGULAMA_PORTU}/",
        width=1000,
        height=750,
        min_size=(700, 500),
    )
    pencere.events.closing += _pencere_kapanirken
    webview.start()


if __name__ == "__main__":
    calistir()
