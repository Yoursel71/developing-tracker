"""Flask rotaları: kurulum akışı, API'ler, hata yanıtları, yetkilendirme."""

import pytest

from depo import json_deposu
from servisler import api_anahtari, zaman_takibi


@pytest.fixture
def istemci():
    import app as app_modulu

    app_modulu.app.config["TESTING"] = True
    # secret_key modül yüklenirken alınmıştı; geçici dizin için tazele.
    app_modulu.app.secret_key = api_anahtari.anahtari_al()
    with app_modulu.app.test_client() as c:
        yield c


@pytest.fixture
def kurulu(istemci):
    with json_deposu.guncelle() as veri:
        veri["kurulum_tamamlandi"] = True
    return istemci


# --- Kurulum akışı ----------------------------------------------------------

def test_kurulum_yapilmadan_panele_gidilemez(istemci):
    yanit = istemci.get("/")
    assert yanit.status_code == 302
    assert "/kurulum" in yanit.headers["Location"]


def test_kurulum_sayfasi_acilir(istemci):
    assert istemci.get("/kurulum").status_code == 200


def test_kurulum_kaydedilir(istemci):
    yanit = istemci.post("/kurulum", data={
        "haftalik_saat": "10",
        "github_kullanici": "birisi",
        "editor_program_adi[]": "VS Code",
        "editor_islem_adi[]": "Code.exe",
        "editor_kategori[]": "Python",
        "site_alan_adi[]": "https://www.udemy.com/course/x",
        "site_kategori[]": "Sertifika kursu",
        "yol_haritasi_ekle": "1",
    })
    assert yanit.status_code == 302

    veri = json_deposu.oku()
    assert veri["kurulum_tamamlandi"] is True
    assert veri["github"]["kullanici"] == "birisi"
    assert veri["izleme"]["siteler"][0]["alan_adi"] == "udemy.com"
    assert veri["yol_haritasi"], "Yol haritası oluşturulmalı"
    # Toplam hedef yol haritasından hesaplanır
    assert veri["hedefler"]["toplam_hedef_saat"] > 0


def test_kurulumda_cakisan_editor_reddedilir(istemci):
    yanit = istemci.post("/kurulum", data={
        "haftalik_saat": "10",
        "editor_program_adi[]": ["VS Code", "VS Code"],
        "editor_islem_adi[]": ["Code.exe", "Code.exe"],
        "editor_kategori[]": ["Python", "Diğer"],
    })
    assert yanit.status_code == 302  # hata mesajıyla geri yönlendirilir
    assert json_deposu.oku()["kurulum_tamamlandi"] is False


# --- Sayfalar ---------------------------------------------------------------

@pytest.mark.parametrize("yol", [
    "/", "/heatmap", "/heatmap?gorunum=ay", "/istatistikler",
    "/hedefler", "/ayarlar", "/yol-haritasi", "/gecmis",
])
def test_sayfalar_acilir(kurulu, yol):
    assert kurulu.get(yol).status_code == 200


def test_bilinmeyen_sayfa_404(kurulu):
    assert kurulu.get("/boyle-bir-sayfa-yok").status_code == 404


# --- Oturum işlemleri -------------------------------------------------------

def test_oturum_baslat_ve_durdur(kurulu):
    yanit = kurulu.post("/oturum/baslat", data={"kategori": "Python"},
                        headers={"X-Istek-Turu": "json"})
    assert yanit.status_code == 200
    assert yanit.get_json()["tamam"] is True
    assert "Python" in zaman_takibi.aktif_oturumlari_getir()

    yanit = kurulu.post("/oturum/durdur", data={"kategori": "Python"},
                        headers={"X-Istek-Turu": "json"})
    assert yanit.get_json()["tamam"] is True


def test_uydurma_kategori_reddedilir(kurulu):
    yanit = kurulu.post("/oturum/baslat", data={"kategori": "Uydurma"},
                        headers={"X-Istek-Turu": "json"})
    assert yanit.status_code == 400
    assert zaman_takibi.aktif_oturumlari_getir() == {}


def test_ayni_oturum_iki_kez_baslatilinca_hata_gorunur(kurulu):
    """Hata sessizce yutulunca buton bozuk görünüyordu."""
    kurulu.post("/oturum/baslat", data={"kategori": "Python"},
                headers={"X-Istek-Turu": "json"})
    yanit = kurulu.post("/oturum/baslat", data={"kategori": "Python"},
                        headers={"X-Istek-Turu": "json"})
    assert yanit.status_code == 409
    assert "zaten aktif" in yanit.get_json()["hata"]


def test_olmayan_oturum_durdurma_hatasi(kurulu):
    yanit = kurulu.post("/oturum/durdur", data={"kategori": "Python"},
                        headers={"X-Istek-Turu": "json"})
    assert yanit.status_code == 409


def test_oturum_ekle_duzenle_sil(kurulu):
    kurulu.post("/oturum/ekle", data={
        "tarih": "2026-03-10", "kategori": "Python", "sure_dakika": "45",
        "not": "while döngüleri",
    }, headers={"X-Istek-Turu": "json"})

    oturumlar = json_deposu.oku()["oturumlar"]
    assert len(oturumlar) == 1
    oturum_id = oturumlar[0]["id"]

    kurulu.post(f"/oturum/{oturum_id}/guncelle", data={"sure_dakika": "60"},
                headers={"X-Istek-Turu": "json"})
    assert json_deposu.oku()["oturumlar"][0]["sure_dakika"] == 60

    kurulu.post(f"/oturum/{oturum_id}/sil", headers={"X-Istek-Turu": "json"})
    assert json_deposu.oku()["oturumlar"] == []


def test_olmayan_oturum_silme_404(kurulu):
    yanit = kurulu.post("/oturum/yok/sil", headers={"X-Istek-Turu": "json"})
    assert yanit.status_code == 404


# --- Hedef doğrulama --------------------------------------------------------

def test_negatif_hedef_500_uretmez(kurulu):
    yanit = kurulu.post("/hedefler", data={"haftalik_saat": "-5", "toplam_hedef_saat": "100"},
                        headers={"X-Istek-Turu": "json"})
    assert yanit.status_code == 400
    assert json_deposu.oku()["hedefler"]["haftalik_saat"] >= 0


def test_turkce_virgullu_hedef_kabul_edilir(kurulu):
    yanit = kurulu.post("/hedefler", data={"haftalik_saat": "12,5", "toplam_hedef_saat": "100"},
                        headers={"X-Istek-Turu": "json"})
    assert yanit.status_code == 200
    assert json_deposu.oku()["hedefler"]["haftalik_saat"] == 12.5


# --- /api/durum -------------------------------------------------------------

def test_api_durum_canli_veri_doner(kurulu):
    veri = kurulu.get("/api/durum").get_json()
    assert "aktif_oturumlar" in veri
    assert "seri" in veri
    assert "haftalik" in veri


def test_api_durum_aktif_oturumu_gosterir(kurulu):
    zaman_takibi.oturum_baslat("Python", kaynak="otomatik")
    veri = kurulu.get("/api/durum").get_json()
    assert len(veri["aktif_oturumlar"]) == 1
    assert veri["aktif_oturumlar"][0]["kategori"] == "Python"
    assert veri["aktif_oturumlar"][0]["kaynak"] == "otomatik"


def test_izleme_duraklat_ve_devam(kurulu):
    assert kurulu.post("/api/izleme/duraklat", json={}).get_json()["duraklatildi"] is True
    assert kurulu.post("/api/izleme/duraklat", json={"devam": True}).get_json()["duraklatildi"] is False


# --- Eklenti API'si ---------------------------------------------------------

def test_eklenti_api_anahtarsiz_reddedilir(kurulu):
    """Herhangi bir site sahte oturum enjekte edebiliyordu."""
    yanit = kurulu.get("/api/izleme-ayarlari")
    assert yanit.status_code == 403

    yanit = kurulu.post("/api/site-durumu", json={"kategori": "Python", "durum": "acik"})
    assert yanit.status_code == 403


def test_eklenti_api_dogru_anahtarla_calisir(kurulu):
    anahtar = api_anahtari.anahtari_al()
    yanit = kurulu.get("/api/izleme-ayarlari", headers={"X-Api-Anahtari": anahtar})
    assert yanit.status_code == 200
    assert "siteler" in yanit.get_json()

    yanit = kurulu.post("/api/site-durumu", json={"kategori": "Python", "durum": "acik"},
                        headers={"X-Api-Anahtari": anahtar})
    assert yanit.get_json()["tamam"] is True


def test_eklenti_api_bilinmeyen_kategoriyi_reddeder(kurulu):
    anahtar = api_anahtari.anahtari_al()
    yanit = kurulu.post("/api/site-durumu", json={"kategori": "Uydurma", "durum": "acik"},
                        headers={"X-Api-Anahtari": anahtar})
    assert yanit.status_code == 400


def test_anahtar_yenilenince_eskisi_gecersiz(kurulu):
    eski = api_anahtari.anahtari_al()
    api_anahtari.anahtari_yenile()
    yanit = kurulu.get("/api/izleme-ayarlari", headers={"X-Api-Anahtari": eski})
    assert yanit.status_code == 403


# --- İkinci örnek: pencereyi öne getirme ------------------------------------

def test_pencereyi_ac_anahtarsiz_reddedilir(kurulu):
    yanit = kurulu.post("/api/pencereyi-ac")
    assert yanit.status_code == 403


def test_pencereyi_ac_gecerli_anahtarla_geri_cagriyi_tetikler(kurulu):
    import app as app_modulu

    cagrildi = []
    app_modulu.pencere_ac_geri_cagri = lambda: cagrildi.append(True)
    try:
        anahtar = api_anahtari.anahtari_al()
        yanit = kurulu.post("/api/pencereyi-ac", headers={"X-Api-Anahtari": anahtar})
        assert yanit.status_code == 200
        assert yanit.get_json()["tamam"] is True
        assert cagrildi == [True]
    finally:
        app_modulu.pencere_ac_geri_cagri = None


def test_pencereyi_ac_masaustu_disinda_hata_vermez(kurulu):
    """Tarayıcıdan çalıştırıldığında geri çağrı bağlı değildir; sessizce başarılı döner."""
    anahtar = api_anahtari.anahtari_al()
    yanit = kurulu.post("/api/pencereyi-ac", headers={"X-Api-Anahtari": anahtar})
    assert yanit.status_code == 200


# --- Harici cihaz API'si (ESP32 vb.) ----------------------------------------

def test_cihaz_durumu_anahtarsiz_reddedilir(kurulu):
    yanit = kurulu.get("/api/device/status")
    assert yanit.status_code == 403


def test_cihaz_durumu_gecerli_anahtarla_sema_doner(kurulu):
    kurulu.post("/oturum/ekle", data={
        "tarih": "2026-03-10", "kategori": "Python", "sure_dakika": "45",
    }, headers={"X-Istek-Turu": "json"})

    anahtar = api_anahtari.anahtari_al()
    yanit = kurulu.get("/api/device/status", headers={"X-Api-Anahtari": anahtar})
    assert yanit.status_code == 200

    govde = yanit.get_json()
    for alan in (
        "today_hours", "weekly_goal_hours", "weekly_logged_hours",
        "weekly_remaining_hours", "streak_days", "pace_status",
        "heatmap", "last_updated",
    ):
        assert alan in govde
    assert govde["pace_status"] in ("on_track", "behind", "critical")
    assert len(govde["heatmap"]) == 70


def test_cihaz_durumu_sorgu_parametresiyle_de_calisir(kurulu):
    anahtar = api_anahtari.anahtari_al()
    yanit = kurulu.get(f"/api/device/status?anahtar={anahtar}")
    assert yanit.status_code == 200


# --- Dışa aktarma -----------------------------------------------------------

def test_csv_disa_aktarma(kurulu):
    kurulu.post("/oturum/ekle", data={
        "tarih": "2026-03-10", "kategori": "Python", "sure_dakika": "45",
    }, headers={"X-Istek-Turu": "json"})

    yanit = kurulu.get("/disa-aktar/csv")
    assert yanit.status_code == 200
    metin = yanit.data.decode("utf-8")
    assert "tarih,kategori" in metin
    assert "2026-03-10" in metin


def test_json_disa_aktarma(kurulu):
    yanit = kurulu.get("/disa-aktar/json")
    assert yanit.status_code == 200
    assert b"oturumlar" in yanit.data


# --- Yol haritası -----------------------------------------------------------

def test_yol_haritasi_kaydedilir(kurulu):
    yanit = kurulu.post("/yol-haritasi", data={
        "tas_id[]": ["", ""],
        "tas_ad[]": ["Fonksiyonlar", "Döngüler"],
        "tas_saat[]": ["8", "6"],
    }, headers={"X-Istek-Turu": "json"})
    assert yanit.status_code == 200

    veri = json_deposu.oku()
    assert len(veri["yol_haritasi"]) == 2
    assert veri["hedefler"]["toplam_hedef_saat"] == 14


def test_kilometre_tasi_isaretlenir(kurulu):
    kurulu.post("/yol-haritasi", data={
        "tas_id[]": [""], "tas_ad[]": ["Fonksiyonlar"], "tas_saat[]": ["8"],
    }, headers={"X-Istek-Turu": "json"})

    tas_id = json_deposu.oku()["yol_haritasi"][0]["id"]
    kurulu.post(f"/yol-haritasi/{tas_id}/durum", data={"tamamlandi": "1"},
                headers={"X-Istek-Turu": "json"})

    tas = json_deposu.oku()["yol_haritasi"][0]
    assert tas["tamamlandi"] is True
    assert tas["tamamlanma_tarihi"]
