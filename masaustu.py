"""Masaüstü giriş noktası (PyInstaller ile .exe olarak paketlenir).

Flask arka planda bir thread'de çalışır, pencere pywebview ile ana thread'te
açılır, tepsi ikonu ayrı bir thread'de durur.
"""

import argparse
import ctypes
import logging
import sys
import threading
import time
import urllib.request

import config
from depo import json_deposu
from platform_katmani import tek_ornek, tepsi
from servisler import bildirim, gunlukleme, otomatik_izleme, zaman_takibi

gunlukleme.kur()
logger = logging.getLogger(__name__)

_pencere = None
_gercekten_kapan = False


def _argumanlari_ayristir(argv):
    ayristirici = argparse.ArgumentParser(description="Gelişim Takip masaüstü uygulaması")
    ayristirici.add_argument(
        "--arkaplan", action="store_true",
        help="Pencereyi göstermeden, yalnızca tepside başlat (Windows açılışı için).",
    )
    return ayristirici.parse_args(argv)


def _sunucuyu_baslat():
    from app import app

    app.run(
        host="127.0.0.1", port=config.UYGULAMA_PORTU,
        debug=False, use_reloader=False, threaded=True,
    )


def _sunucu_hazir_mi():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{config.UYGULAMA_PORTU}/", timeout=1)
        return True
    except urllib.error.HTTPError:
        return True  # yönlendirme/hata da olsa sunucu ayakta
    except Exception:
        return False


def _tepsiye_inilsin_mi():
    try:
        return bool(json_deposu.oku()["ayarlar"].get("tepsiye_indir", True))
    except Exception:
        return True


def _one_getir():
    """pywebview'ın show()'u Windows'ta pencereyi öne getirmiyor."""
    if sys.platform != "win32" or _pencere is None:
        return
    try:
        ctypes.windll.user32.SetForegroundWindow(int(_pencere.native.Handle))
    except Exception:
        pass


def _pencereyi_ac():
    if _pencere is None:
        return
    try:
        _pencere.show()
        _pencere.restore()
        _one_getir()
        _acilis_animasyonunu_tetikle()
    except Exception:
        logger.exception("Pencere gösterilemedi")


def _acilis_animasyonunu_tetikle():
    """Pencere gizliyken sayfa zaten yüklenmiştir; show() anında CSS
    animasyonunu yeniden oynatmak için sınıfı JS ile tazeler."""
    if _pencere is None:
        return
    try:
        _pencere.evaluate_js(
            "(function(){var e=document.querySelector('.kabuk');"
            "if(!e)return;e.classList.remove('kabuk-canlanma');"
            "void e.offsetWidth;e.classList.add('kabuk-canlanma');})();"
        )
    except Exception:
        pass


def _takibi_degistir():
    if otomatik_izleme.duraklatildi_mi():
        otomatik_izleme.devam_et()
        tepsi.durumu_guncelle(True)
    else:
        otomatik_izleme.duraklat()
        tepsi.durumu_guncelle(False)


def _kapat():
    """Gerçek çıkış: önce izlemeyi durdur, sonra oturumları kaydet."""
    global _gercekten_kapan
    _gercekten_kapan = True

    # Sıra önemli: izleme durmadan oturumları kapatırsak, tarama uyanıp
    # yeni bir aktif oturum yaratır ve diskte hayalet kayıt bırakır.
    try:
        otomatik_izleme.durdur()
    except Exception:
        logger.exception("İzleme durdurulamadı")

    try:
        kategoriler = zaman_takibi.tum_oturumlari_durdur()
        if kategoriler:
            logger.info("Çıkışta kapatılan oturumlar: %s", ", ".join(kategoriler))
    except Exception:
        logger.exception("Oturumlar kapatılamadı")

    tepsi.durdur()
    tek_ornek.kilidi_birak()

    if _pencere is not None:
        try:
            _pencere.destroy()
        except Exception:
            pass


def _pencere_kapanirken():
    """closing handler; False döndürmek kapanışı iptal eder."""
    if _gercekten_kapan or not _tepsiye_inilsin_mi():
        _kapat()
        return None

    # hide()'ı burada senkron çağırmak Windows'ta süreci donduruyor
    # (pywebview #1103) — kısa ömürlü bir thread'e veriyoruz.
    threading.Thread(target=_gizle, daemon=True).start()
    return False


def _gizle():
    try:
        _pencere.hide()
        logger.info("Pencere tepsiye indirildi; takip sürüyor.")
    except Exception:
        logger.exception("Pencere gizlenemedi")


def _calisan_ornegi_uyandir():
    """Kilit alınamadığında, halihazırda çalışan örneğe pencereyi açtırır.

    Yanıt vermezse (yalnızca kilit soketini tutan ama Flask'ı ölmüş bir süreç
    gibi tutarsız bir durumda) True dönmez; kilit yine de başka bir sürece ait
    olduğu için port zorla devralınmaz — bu, tek örnek kilidinin var oluş
    sebebiyle (aynı veri.json'a çift yazım) çelişirdi.
    """
    from servisler import api_anahtari

    try:
        istek = urllib.request.Request(
            f"http://127.0.0.1:{config.UYGULAMA_PORTU}/api/pencereyi-ac",
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "X-Api-Anahtari": api_anahtari.anahtari_al(),
            },
            method="POST",
        )
        with urllib.request.urlopen(istek, timeout=2) as yanit:
            return yanit.status == 200
    except Exception:
        return False


def calistir():
    global _pencere

    args = _argumanlari_ayristir(sys.argv[1:])

    if not tek_ornek.kilidi_al():
        if _calisan_ornegi_uyandir():
            logger.info("Uygulama zaten çalışıyor; penceresi öne getirildi.")
        else:
            logger.warning(
                "Uygulama zaten çalışıyor ama yanıt vermiyor; "
                "görev yöneticisinden eski GelisimTakip.exe sürecini kontrol et."
            )
        return 1

    import webview

    threading.Thread(target=_sunucuyu_baslat, daemon=True, name="flask").start()
    for _ in range(80):
        if _sunucu_hazir_mi():
            break
        time.sleep(0.1)
    else:
        logger.error("Sunucu zamanında ayağa kalkmadı")

    from app import app as flask_app
    flask_app.pencere_ac_geri_cagri = _pencereyi_ac

    otomatik_izleme.baslat()

    _pencere = webview.create_window(
        "Gelişim Takip",
        f"http://127.0.0.1:{config.UYGULAMA_PORTU}/",
        width=1180, height=820, min_size=(760, 560),
        hidden=args.arkaplan,
    )
    _pencere.events.closing += _pencere_kapanirken

    tepsi.baslat(
        ac_geri_cagri=_pencereyi_ac,
        duraklat_geri_cagri=_takibi_degistir,
        cikis_geri_cagri=_kapat,
        duraklatildi_mi=otomatik_izleme.duraklatildi_mi,
    )

    if args.arkaplan:
        bildirim.bildirim_gonder(
            "Gelişim Takip",
            "Arka planda çalışıyor. Açmak için tepsi ikonuna tıkla.",
        )

    try:
        webview.start()
    finally:
        # webview.start() döndüyse pencere kapanmıştır; tepsi thread'i daemon
        # olmadığı için durdurulmazsa süreç görünmez şekilde asılı kalır.
        if not _gercekten_kapan:
            _kapat()
        tepsi.durdur()

    return 0


if __name__ == "__main__":
    sys.exit(calistir())
