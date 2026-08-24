"""İzleme durum makinesi: boşta, grace, çökme kurtarma, çift sayım."""

import datetime as dt

import pytest

import config
from depo import json_deposu
from servisler import otomatik_izleme, zaman_takibi


@pytest.fixture
def izlemeli_veri():
    with json_deposu.guncelle() as veri:
        veri["kurulum_tamamlandi"] = True
        veri["izleme"]["editorler"] = [
            {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": "Python"}
        ]
        veri["izleme"]["siteler"] = [
            {"alan_adi": "udemy.com", "kategori": "Sertifika kursu"}
        ]
    return json_deposu.oku()


def tara(su_an, bosta=0.0, islemler=frozenset()):
    otomatik_izleme.tara_bir_kez(
        su_an=su_an, bosta_saniye=bosta, calisan_islemler=set(islemler)
    )


def aktif(kategori):
    return json_deposu.oku()["aktif_oturumlar"].get(kategori)


def test_islem_algilaninca_oturum_baslar(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})

    oturum = aktif("Python")
    assert oturum is not None
    assert oturum["kaynak"] == "otomatik"
    assert oturum["birikmis_saniye"] == 0


def test_sure_turlar_boyunca_birikir(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=10), islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=20), islemler={"code.exe"})

    assert aktif("Python")["birikmis_saniye"] == pytest.approx(20, abs=1)


def test_bosta_kalinca_sure_birikmez(izlemeli_veri):
    """Açık unutulan editör saat yazmamalı — ürünün ana değer önerisi bu."""
    t0 = zaman_takibi.simdi()
    esik = config.VARSAYILAN_BOSTA_ESIGI_DAKIKA * 60

    tara(t0, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=10), islemler={"code.exe"})
    onceki = aktif("Python")["birikmis_saniye"]

    # Kullanıcı klavyeye dokunmuyor
    tara(t0 + dt.timedelta(seconds=20), bosta=esik + 1, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=30), bosta=esik + 11, islemler={"code.exe"})

    oturum = aktif("Python")
    assert oturum is not None, "Boşta oturum kapanmamalı, sadece duraklamalı"
    assert oturum["bosta_mi"] is True
    assert oturum["birikmis_saniye"] == pytest.approx(onceki, abs=1)


def test_bostan_donunce_ayni_oturum_devam_eder(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    esik = config.VARSAYILAN_BOSTA_ESIGI_DAKIKA * 60

    tara(t0, islemler={"code.exe"})
    baslangic = aktif("Python")["baslangic"]

    tara(t0 + dt.timedelta(seconds=10), bosta=esik + 1, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=20), bosta=0, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=30), bosta=0, islemler={"code.exe"})

    oturum = aktif("Python")
    assert oturum["baslangic"] == baslangic, "Oturum bölünmemeli"
    assert oturum["bosta_mi"] is False
    assert oturum["birikmis_saniye"] == pytest.approx(10, abs=2)


def test_islem_kapaninca_grace_boyunca_beklenir(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=10), islemler=set())

    assert aktif("Python") is not None
    assert aktif("Python")["kayip_zamani"] is not None


def test_grace_icinde_geri_gelirse_oturum_surer(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    baslangic = aktif("Python")["baslangic"]

    tara(t0 + dt.timedelta(seconds=10), islemler=set())
    tara(t0 + dt.timedelta(seconds=30), islemler={"code.exe"})

    oturum = aktif("Python")
    assert oturum["baslangic"] == baslangic
    assert oturum.get("kayip_zamani") is None


def test_grace_dolunca_oturum_kapanir(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=60), islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=70), islemler=set())  # kayıp başlar
    tara(
        t0 + dt.timedelta(seconds=70 + config.IZLEME_KAYIP_GRACE_SANIYE + 5),
        islemler=set(),
    )

    assert aktif("Python") is None
    oturumlar = json_deposu.oku()["oturumlar"]
    assert len(oturumlar) == 1
    assert oturumlar[0]["kategori"] == "Python"
    assert oturumlar[0]["sure_dakika"] > 0


def test_erteleme_suresince_yeniden_baslamaz(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    zaman_takibi.oturum_durdur("Python")  # elle durdurma → erteleme

    tara(t0 + dt.timedelta(seconds=10), islemler={"code.exe"})
    assert aktif("Python") is None, "Erteleme sırasında yeniden başlamamalı"


def test_erteleme_bitince_yeniden_baslar(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    zaman_takibi.oturum_durdur("Python")

    sonra = t0 + dt.timedelta(seconds=config.IZLEME_ERTELEME_SANIYE + 10)
    tara(sonra, islemler={"code.exe"})
    assert aktif("Python") is not None


def test_erteleme_yeniden_baslatmaya_dayanir(izlemeli_veri):
    """Erteleme RAM'de tutulsaydı uygulama yeniden açılınca kaybolurdu."""
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    zaman_takibi.oturum_durdur("Python")

    # Süreç yeniden başlamış gibi modül durumunu sıfırla
    otomatik_izleme._site_kalp_atislari.clear()
    otomatik_izleme._onceki_tur_zamani = None

    tara(t0 + dt.timedelta(seconds=20), islemler={"code.exe"})
    assert aktif("Python") is None


def test_duraklatilinca_oturum_baslamaz(izlemeli_veri):
    otomatik_izleme.duraklat()
    tara(zaman_takibi.simdi(), islemler={"code.exe"})
    assert aktif("Python") is None
    otomatik_izleme.devam_et()


# --- Site (tarayıcı eklentisi) ---------------------------------------------

def test_site_kalp_atisiyla_oturum_baslar(izlemeli_veri):
    otomatik_izleme.site_durumu_bildir("Sertifika kursu", "acik")
    tara(zaman_takibi.simdi())
    assert aktif("Sertifika kursu") is not None


def test_site_kapaninca_grace_sonunda_kapanir(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    otomatik_izleme.site_durumu_bildir("Sertifika kursu", "acik")
    tara(t0)
    otomatik_izleme.site_durumu_bildir("Sertifika kursu", "kapandi")

    tara(t0 + dt.timedelta(seconds=10))
    assert aktif("Sertifika kursu") is not None

    tara(t0 + dt.timedelta(seconds=config.IZLEME_KAYIP_GRACE_SANIYE + 20))
    assert aktif("Sertifika kursu") is None


def test_kalp_atisi_zaman_asiminda_kapanir(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    otomatik_izleme.site_durumu_bildir("Sertifika kursu", "acik")
    tara(t0)

    # Eklenti susarsa (tarayıcı kapandı) oturum kapanmalı
    uzak = t0 + dt.timedelta(
        seconds=config.IZLEME_SITE_KALP_ATISI_ZAMAN_ASIMI_SANIYE
        + config.IZLEME_KAYIP_GRACE_SANIYE + 20
    )
    tara(t0 + dt.timedelta(seconds=config.IZLEME_SITE_KALP_ATISI_ZAMAN_ASIMI_SANIYE + 5))
    tara(uzak)
    assert aktif("Sertifika kursu") is None


# --- Çift sayım -------------------------------------------------------------

def test_ayni_islem_tek_kategoriye_baglanir():
    """Aynı işlem iki kategoriye eşlenirse süre çift sayılırdı."""
    with json_deposu.guncelle() as veri:
        veri["izleme"]["editorler"] = [
            {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": "Python"},
            {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": "GitHub çalışması"},
        ]

    tara(zaman_takibi.simdi(), islemler={"code.exe"})
    aktifler = json_deposu.oku()["aktif_oturumlar"]
    assert len(aktifler) == 1, "Tek işlem yalnızca tek oturum başlatmalı"


# --- Uyku / askıya alma -----------------------------------------------------

def test_uyku_bosluğu_sureye_eklenmez(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=10), islemler={"code.exe"})
    onceki = aktif("Python")["birikmis_saniye"]

    # Dizüstünün kapağı kapandı: duvar saati 3 saat ilerledi
    tara(t0 + dt.timedelta(hours=3), islemler={"code.exe"})

    oturum = aktif("Python")
    assert oturum["birikmis_saniye"] == pytest.approx(onceki, abs=2)


# --- Çökme kurtarma ---------------------------------------------------------

def test_acilis_kurtarmasi_hayalet_oturumu_kapatir(izlemeli_veri):
    """Cuma çöken uygulama, Pazartesi 63 saatlik sahte oturum yazmamalı."""
    # Gün ortasına sabitle: gece yarısına yakın çalıştırılırsa oturum
    # (doğru şekilde) iki güne bölünür ve bu testin konusu o değil.
    eski = (zaman_takibi.simdi() - dt.timedelta(days=3)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    with json_deposu.guncelle() as veri:
        veri["aktif_oturumlar"]["Python"] = {
            "baslangic": eski.isoformat(timespec="seconds"),
            "son_gorulme": (eski + dt.timedelta(minutes=30)).isoformat(timespec="seconds"),
            "birikmis_saniye": 1800,
            "bosta_mi": False,
            "kaynak": "otomatik",
        }

    otomatik_izleme.acilis_kurtarmasi()

    assert json_deposu.oku()["aktif_oturumlar"] == {}
    oturumlar = json_deposu.oku()["oturumlar"]
    assert len(oturumlar) == 1
    assert oturumlar[0]["sure_dakika"] == pytest.approx(30, abs=1)
    assert oturumlar[0]["tarih"] == eski.date().isoformat()


def test_acilis_kurtarmasi_manuel_oturumu_da_kapatir(izlemeli_veri):
    """Manuel oturumlar sonsuza kadar açık kalıyordu."""
    eski = (zaman_takibi.simdi() - dt.timedelta(days=7)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    with json_deposu.guncelle() as veri:
        veri["aktif_oturumlar"]["Diğer"] = {
            "baslangic": eski.isoformat(timespec="seconds"),
            "son_gorulme": (eski + dt.timedelta(minutes=45)).isoformat(timespec="seconds"),
            "birikmis_saniye": 2700,
            "bosta_mi": False,
            "kaynak": "manuel",
        }

    otomatik_izleme.acilis_kurtarmasi()
    assert json_deposu.oku()["aktif_oturumlar"] == {}


def test_acilis_kurtarmasi_taze_oturuma_dokunmaz(izlemeli_veri):
    simdi = zaman_takibi.simdi()
    with json_deposu.guncelle() as veri:
        veri["aktif_oturumlar"]["Python"] = {
            "baslangic": (simdi - dt.timedelta(minutes=5)).isoformat(timespec="seconds"),
            "son_gorulme": simdi.isoformat(timespec="seconds"),
            "birikmis_saniye": 300,
            "bosta_mi": False,
            "kaynak": "otomatik",
        }

    otomatik_izleme.acilis_kurtarmasi()
    assert "Python" in json_deposu.oku()["aktif_oturumlar"]


def test_kayip_durumu_bosta_olarak_gosterilmez(izlemeli_veri):
    """Program kapandığında 'hareket bekleniyor' demek yanıltıcıydı."""
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=10), bosta=0, islemler=set())

    oturum = aktif("Python")
    assert zaman_takibi.oturum_durumu(oturum) == "kayip"
    assert oturum["bosta_mi"] is False


def test_kayipken_sayac_ilerlemez(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    tara(t0, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=10), bosta=0, islemler=set())

    oturum = aktif("Python")
    gosterilen = zaman_takibi.gecen_saniye(oturum)
    assert gosterilen == pytest.approx(oturum["birikmis_saniye"], abs=0.1)


def test_calisirken_durum_calisiyor(izlemeli_veri):
    tara(zaman_takibi.simdi(), islemler={"code.exe"})
    assert zaman_takibi.oturum_durumu(aktif("Python")) == "calisiyor"


def test_kullanici_bostayken_durum_bosta(izlemeli_veri):
    t0 = zaman_takibi.simdi()
    esik = config.VARSAYILAN_BOSTA_ESIGI_DAKIKA * 60
    tara(t0, islemler={"code.exe"})
    tara(t0 + dt.timedelta(seconds=10), bosta=esik + 1, islemler={"code.exe"})
    assert zaman_takibi.oturum_durumu(aktif("Python")) == "bosta"
