"""Depo katmanı: atomik yazma, kurtarma, göç, normalizasyon."""

import json
import os

from depo import goc, json_deposu
from depo.varsayilan import SEMA_SURUMU, normallestir, varsayilan_veri
from platform_katmani import yollar


def test_ilk_okumada_varsayilan_olusur():
    veri = json_deposu.oku()
    assert veri["surum"] == SEMA_SURUMU
    assert veri["kurulum_tamamlandi"] is False
    assert os.path.exists(yollar.veri_dosyasi())


def test_yazma_atomik_gecici_dosya_birakmaz():
    veri = json_deposu.oku()
    veri["hedefler"]["haftalik_saat"] = 12
    json_deposu.yaz(veri)

    assert not os.path.exists(yollar.veri_dosyasi() + ".tmp")
    assert json_deposu.oku()["hedefler"]["haftalik_saat"] == 12


def test_guncelle_baglami_yazar():
    with json_deposu.guncelle() as veri:
        veri["hedefler"]["haftalik_saat"] = 7
    assert json_deposu.oku()["hedefler"]["haftalik_saat"] == 7


def test_belki_guncelle_isaretlenmezse_yazmaz():
    json_deposu.oku()
    ilk_mtime = os.path.getmtime(yollar.veri_dosyasi())

    with json_deposu.belki_guncelle() as (veri, isaret):
        veri["hedefler"]["haftalik_saat"] = 99  # işaretlenmedi

    assert os.path.getmtime(yollar.veri_dosyasi()) == ilk_mtime
    assert json_deposu.oku()["hedefler"]["haftalik_saat"] != 99


def test_belki_guncelle_isaretlenirse_yazar():
    with json_deposu.belki_guncelle() as (veri, isaret):
        veri["hedefler"]["haftalik_saat"] = 21
        isaret()
    assert json_deposu.oku()["hedefler"]["haftalik_saat"] == 21


def test_bozuk_dosya_yedekten_kurtarilir():
    import shutil

    with json_deposu.guncelle() as veri:
        veri["oturumlar"].append(
            {"id": "a", "tarih": "2026-01-01", "kategori": "Python", "sure_dakika": 60}
        )

    # Yedek, yazmadan ÖNCEki durumu saklar (günün başındaki anlık görüntü).
    # Kurtarmayı sınamak için güncel içeriği en yeni yedek olarak koyuyoruz.
    yedek_dizini = yollar.dizini_hazirla(yollar.yedek_dizini())
    for eski in os.listdir(yedek_dizini):
        os.remove(os.path.join(yedek_dizini, eski))
    shutil.copy2(yollar.veri_dosyasi(), os.path.join(yedek_dizini, "veri-20991231-235959.json"))

    with open(yollar.veri_dosyasi(), "w", encoding="utf-8") as f:
        f.write("{ bu gecerli json degil")

    veri = json_deposu.oku()
    assert len(veri["oturumlar"]) == 1
    assert json_deposu.son_kurtarma_mesaji is not None


def test_yedek_yazmadan_onceki_durumu_saklar():
    """Yedek, o günkü ilk yazmadan önceki içeriği tutar."""
    with json_deposu.guncelle() as veri:
        veri["hedefler"]["haftalik_saat"] = 3

    yedekler = os.listdir(yollar.yedek_dizini())
    assert yedekler, "İlk yazmada yedek alınmalı"

    with open(os.path.join(yollar.yedek_dizini(), yedekler[0]), encoding="utf-8") as f:
        yedek = json.load(f)
    # Yedek, değişiklikten önceki (varsayılan) hâli içerir.
    assert yedek["hedefler"]["haftalik_saat"] != 3


def test_bozuk_dosya_yedek_yoksa_sifirlanir_ama_cokmez():
    json_deposu.oku()
    with open(yollar.veri_dosyasi(), "w", encoding="utf-8") as f:
        f.write("bozuk")

    veri = json_deposu.oku()
    assert veri["surum"] == SEMA_SURUMU
    assert json_deposu.son_kurtarma_mesaji is not None
    # Bozuk dosya kenara alınmış olmalı
    kalanlar = os.listdir(yollar.veri_dizini())
    assert any(".bozuk-" in ad for ad in kalanlar)


# --- Göç --------------------------------------------------------------------

def test_v0_gocu_tekil_aktif_oturumu_donusturur():
    eski = {
        "oturumlar": [{"tarih": "2026-01-01", "kategori": "Python", "sure_dakika": 30}],
        "aktif_oturum": {"kategori": "Python", "baslangic": "2026-01-01T10:00:00"},
        "hedefler": {"haftalik_saat": 10, "toplam_hedef_saat": 100},
    }
    yeni, yapildi = goc.goc_et(eski)

    assert yapildi is True
    assert yeni["surum"] == SEMA_SURUMU
    assert "aktif_oturum" not in yeni
    assert "Python" in yeni["aktif_oturumlar"]
    assert yeni["aktif_oturumlar"]["Python"]["birikmis_saniye"] == 0
    assert yeni["oturumlar"][0]["id"]
    assert yeni["izleme"]["editorler"] == []


def test_v1_gocu_eksik_alanlari_ekler():
    eski = {
        "kurulum_tamamlandi": True,
        "oturumlar": [{"tarih": "2026-01-01", "kategori": "Python", "sure_dakika": 30}],
        "aktif_oturumlar": {"Python": {"baslangic": "2026-01-01T10:00:00", "kaynak": "otomatik"}},
        "hedefler": {"haftalik_saat": 15, "toplam_hedef_saat": 135},
        "izleme": {"editorler": [], "siteler": []},
    }
    yeni, yapildi = goc.goc_et(eski)

    assert yapildi is True
    aktif = yeni["aktif_oturumlar"]["Python"]
    assert aktif["son_gorulme"] == "2026-01-01T10:00:00"
    assert aktif["kaynak"] == "otomatik"
    assert yeni["yol_haritasi"] == []
    assert yeni["ayarlar"]["tema"] == "koyu"


def test_guncel_surum_tekrar_goc_etmez():
    veri = varsayilan_veri()
    _, yapildi = goc.goc_et(veri)
    assert yapildi is False


def test_v0_verisi_diskten_okundugunda_calisir():
    """Faz 1 kullanıcısının dosyası açıldığında KeyError vermemeli."""
    yollar.dizini_hazirla(yollar.veri_dizini())
    with open(yollar.veri_dosyasi(), "w", encoding="utf-8") as f:
        json.dump({
            "oturumlar": [],
            "aktif_oturum": None,
            "hedefler": {"haftalik_saat": 15, "toplam_hedef_saat": 135},
            "github": {"kullanici": "biri", "son_cekilen_etkinlikler": [], "son_senkron": None},
        }, f)

    veri = json_deposu.oku()
    assert veri["izleme"]["editorler"] == []
    assert veri["ayarlar"]["bosta_esigi_dakika"] > 0
    assert veri["github"]["kullanici"] == "biri"


# --- Normalizasyon ----------------------------------------------------------

def test_normallestir_eksik_anahtarlari_tamamlar():
    veri = normallestir({"oturumlar": None, "izleme": {"editorler": "bozuk"}})
    assert veri["oturumlar"] == []
    assert veri["izleme"]["editorler"] == []
    assert veri["izleme"]["siteler"] == []
    assert "ayarlar" in veri


def test_normallestir_sozluk_olmayani_reddeder():
    assert normallestir("metin")["surum"] == SEMA_SURUMU


# --- Yedek ------------------------------------------------------------------

def test_yedekten_geri_yukleme():
    with json_deposu.guncelle() as veri:
        veri["hedefler"]["haftalik_saat"] = 5

    yedek_dizini = yollar.dizini_hazirla(yollar.yedek_dizini())
    yedek_yolu = os.path.join(yedek_dizini, "veri-20260101-000000.json")
    import shutil
    shutil.copy2(yollar.veri_dosyasi(), yedek_yolu)

    with json_deposu.guncelle() as veri:
        veri["hedefler"]["haftalik_saat"] = 40

    json_deposu.yedekten_geri_yukle("veri-20260101-000000.json")
    assert json_deposu.oku()["hedefler"]["haftalik_saat"] == 5
