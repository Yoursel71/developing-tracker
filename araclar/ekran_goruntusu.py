"""README için demo veriyle 4 sayfanın koyu temalı ekran görüntüsünü çeker.

Gerçek Chromium ile çalışır (bu depoda ``/opt/pw-browsers`` altında hazır).
Geçici bir veri dizini kullanır; kullanıcının gerçek ``veri.json``'ına
dokunmaz.
"""

import datetime as dt
import os
import random
import sys
import tempfile
import threading
import time
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

CHROME_YOLU = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
PORT = 57392
GENISLIK, YUKSEKLIK = 1280, 900


def _demo_verisini_yaz():
    from depo import json_deposu
    from servisler import yol_haritasi

    rastgele = random.Random(42)
    bugun = dt.date.today()

    with json_deposu.guncelle() as veri:
        veri["kurulum_tamamlandi"] = True
        veri["ayarlar"]["tema"] = "koyu"
        veri["ayarlar"]["motivasyon_sozu"] = True
        veri["github"]["kullanici"] = ""
        veri["hedefler"]["haftalik_saat"] = 10
        veri["hedefler"]["toplam_hedef_saat"] = 135

        kategoriler = [k["ad"] for k in veri["kategoriler"]]

        yol = yol_haritasi.varsayilan_yol_haritasi()
        for tas in yol[:3]:
            tas["tamamlandi"] = True
            tas["tamamlanma_tarihi"] = (bugun - dt.timedelta(days=20)).isoformat()
        veri["yol_haritasi"] = yol

        oturumlar = []
        for gun_once in range(89, -1, -1):
            tarih = bugun - dt.timedelta(days=gun_once)
            # Son 12 gün kesintisiz (güncel seri); geri kalanı düzensiz.
            if gun_once > 11:
                if tarih.weekday() >= 5 and rastgele.random() < 0.5:
                    continue
                if rastgele.random() < 0.12:
                    continue
            gunluk_oturum = 1 if rastgele.random() < 0.7 else 2
            for _ in range(gunluk_oturum):
                kategori = rastgele.choices(kategoriler, weights=[5, 2, 2, 1])[0]
                dakika = rastgele.randint(20, 150)
                baslangic_saat = rastgele.randint(18, 22)
                oturumlar.append({
                    "id": f"demo-{tarih.isoformat()}-{len(oturumlar)}",
                    "tarih": tarih.isoformat(),
                    "kategori": kategori,
                    "baslangic": f"{baslangic_saat:02d}:00:00",
                    "bitis": f"{(baslangic_saat + dakika // 60) % 24:02d}:{dakika % 60:02d}:00",
                    "sure_dakika": dakika,
                    "kaynak": "otomatik",
                    "not": "",
                    "duzenlendi": False,
                })
        veri["oturumlar"] = oturumlar


def _sunucuyu_baslat():
    from app import app

    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False, threaded=True)


def _sunucu_hazir_mi():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
        return True
    except Exception:
        return False


def _ekran_goruntuleri_al():
    from playwright.sync_api import sync_playwright

    hedef_dizin = os.path.join(KOK, "varliklar", "ekran")
    os.makedirs(hedef_dizin, exist_ok=True)

    sayfalar = [
        ("/", "panel.png"),
        ("/heatmap", "isi-haritasi.png"),
        ("/istatistikler", "istatistikler.png"),
        ("/yil-ozeti", "yil-ozeti.png"),
    ]

    with sync_playwright() as p:
        tarayici = p.chromium.launch(executable_path=CHROME_YOLU)
        sayfa = tarayici.new_page(viewport={"width": GENISLIK, "height": YUKSEKLIK})
        for yol, dosya_adi in sayfalar:
            sayfa.goto(f"http://127.0.0.1:{PORT}{yol}", wait_until="networkidle")
            sayfa.wait_for_timeout(300)  # animasyonların bitmesini bekle
            sayfa.screenshot(path=os.path.join(hedef_dizin, dosya_adi))
            print(f"Üretildi: varliklar/ekran/{dosya_adi}")
        tarayici.close()


def calistir():
    with tempfile.TemporaryDirectory() as gecici_dizin:
        os.environ["GELISIM_TAKIP_VERI_DIZINI"] = gecici_dizin

        _demo_verisini_yaz()

        threading.Thread(target=_sunucuyu_baslat, daemon=True).start()
        for _ in range(50):
            if _sunucu_hazir_mi():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Sunucu zamanında ayağa kalkmadı")

        _ekran_goruntuleri_al()


if __name__ == "__main__":
    calistir()
