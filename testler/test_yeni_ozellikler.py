"""Pomodoro, mola hatırlatıcısı, yıl özeti ve rozet."""

import datetime as dt

import pytest

import config
from depo import json_deposu
from servisler import otomatik_izleme, pomodoro, yil_ozeti, zaman_takibi


# --- Pomodoro ---------------------------------------------------------------

def test_pomodoro_baslat_ve_durdur():
    pomodoro.baslat()
    durum = pomodoro.durum()
    assert durum["aktif"] is True
    assert durum["asama"] == "calisma"
    assert durum["kalan_saniye"] <= config.POMODORO_CALISMA_DAKIKA * 60

    pomodoro.durdur()
    assert pomodoro.durum()["aktif"] is False


def test_pomodoro_sure_dolunca_molaya_gecer():
    pomodoro.baslat()
    ileri = zaman_takibi.simdi() + dt.timedelta(minutes=config.POMODORO_CALISMA_DAKIKA + 1)

    bildirim = pomodoro.kontrol_et(ileri)

    assert bildirim is not None
    assert "mola" in bildirim[0].lower()
    assert json_deposu.oku()["pomodoro"]["asama"] == "mola"
    assert json_deposu.oku()["pomodoro"]["tur"] == 1


def test_pomodoro_moladan_calismaya_doner():
    pomodoro.baslat()
    pomodoro.atla()  # molaya geç
    assert json_deposu.oku()["pomodoro"]["asama"] == "mola"

    ileri = zaman_takibi.simdi() + dt.timedelta(minutes=config.POMODORO_KISA_MOLA_DAKIKA + 1)
    bildirim = pomodoro.kontrol_et(ileri)

    assert bildirim is not None
    assert json_deposu.oku()["pomodoro"]["asama"] == "calisma"


def test_kisa_molalar_ilk_turlarda():
    pomodoro.baslat()
    pomodoro.atla()  # çalışma -> mola (1. tur)
    assert pomodoro.durum()["asama"] == "mola"
    assert pomodoro.durum()["toplam_saniye"] == config.POMODORO_KISA_MOLA_DAKIKA * 60


def test_dorduncu_turdan_sonra_uzun_mola():
    """atla() aşamalar arasında geçer; bir tur = iki atla."""
    pomodoro.baslat()
    for _ in range(config.POMODORO_UZUN_MOLA_ARALIGI):
        pomodoro.atla()  # çalışma -> mola
        if json_deposu.oku()["pomodoro"]["tur"] < config.POMODORO_UZUN_MOLA_ARALIGI:
            pomodoro.atla()  # mola -> çalışma

    durum = pomodoro.durum()
    assert json_deposu.oku()["pomodoro"]["tur"] == config.POMODORO_UZUN_MOLA_ARALIGI
    assert durum["asama"] == "mola"
    assert durum["toplam_saniye"] == config.POMODORO_UZUN_MOLA_DAKIKA * 60


def test_pomodoro_kapaliyken_kontrol_none_doner():
    assert pomodoro.kontrol_et() is None


def test_pomodoro_oturum_acmaz():
    """Pomodoro yalnızca ritim tutar; süre ölçümü izleme motorunun işi."""
    pomodoro.baslat()
    pomodoro.kontrol_et(
        zaman_takibi.simdi() + dt.timedelta(minutes=config.POMODORO_CALISMA_DAKIKA + 1)
    )
    assert json_deposu.oku()["aktif_oturumlar"] == {}
    assert json_deposu.oku()["oturumlar"] == []


# --- Mola hatırlatıcısı -----------------------------------------------------

@pytest.fixture
def izlemeli():
    with json_deposu.guncelle() as veri:
        veri["kurulum_tamamlandi"] = True
        veri["izleme"]["editorler"] = [
            {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": "Python"}
        ]
    otomatik_izleme._bildirim_kuyrugu.clear()
    otomatik_izleme._onceki_tur_zamani = None
    return json_deposu.oku()


def test_uzun_calismada_mola_onerilir(izlemeli, monkeypatch):
    gonderilen = []
    monkeypatch.setattr(
        otomatik_izleme.bildirim, "bildirim_gonder",
        lambda b, m: gonderilen.append((b, m)) or True,
    )

    t0 = zaman_takibi.simdi()
    otomatik_izleme.tara_bir_kez(su_an=t0, bosta_saniye=0, calisan_islemler={"code.exe"})

    # Oturumu mola eşiğinin üstüne taşı
    with json_deposu.guncelle() as veri:
        veri["aktif_oturumlar"]["Python"]["birikmis_saniye"] = config.MOLA_ONERI_DAKIKA * 60 + 60

    otomatik_izleme.tara_bir_kez(
        su_an=t0 + dt.timedelta(seconds=10), bosta_saniye=0, calisan_islemler={"code.exe"}
    )

    assert any("Mola" in b for b, _ in gonderilen)


def test_mola_onerisi_tekrar_etmez(izlemeli, monkeypatch):
    gonderilen = []
    monkeypatch.setattr(
        otomatik_izleme.bildirim, "bildirim_gonder",
        lambda b, m: gonderilen.append((b, m)) or True,
    )

    t0 = zaman_takibi.simdi()
    otomatik_izleme.tara_bir_kez(su_an=t0, bosta_saniye=0, calisan_islemler={"code.exe"})
    with json_deposu.guncelle() as veri:
        veri["aktif_oturumlar"]["Python"]["birikmis_saniye"] = config.MOLA_ONERI_DAKIKA * 60 + 60

    for saniye in (10, 20, 30):
        otomatik_izleme.tara_bir_kez(
            su_an=t0 + dt.timedelta(seconds=saniye), bosta_saniye=0,
            calisan_islemler={"code.exe"},
        )

    mola_sayisi = sum(1 for b, _ in gonderilen if "Mola" in b)
    assert mola_sayisi == 1


def test_mola_hatirlatici_kapatilabilir(izlemeli, monkeypatch):
    gonderilen = []
    monkeypatch.setattr(
        otomatik_izleme.bildirim, "bildirim_gonder",
        lambda b, m: gonderilen.append((b, m)) or True,
    )
    with json_deposu.guncelle() as veri:
        veri["ayarlar"]["mola_hatirlatici"] = False

    t0 = zaman_takibi.simdi()
    otomatik_izleme.tara_bir_kez(su_an=t0, bosta_saniye=0, calisan_islemler={"code.exe"})
    with json_deposu.guncelle() as veri:
        veri["aktif_oturumlar"]["Python"]["birikmis_saniye"] = config.MOLA_ONERI_DAKIKA * 60 + 60
    otomatik_izleme.tara_bir_kez(
        su_an=t0 + dt.timedelta(seconds=10), bosta_saniye=0, calisan_islemler={"code.exe"}
    )

    assert not any("Mola" in b for b, _ in gonderilen)


# --- Yıl özeti --------------------------------------------------------------

def _yil_verisi(yil=2026):
    with json_deposu.guncelle() as veri:
        for gun, dakika in [(15, 120), (16, 90), (17, 200)]:
            zaman_takibi_kaydi = {
                "id": f"x{gun}", "tarih": f"{yil}-03-{gun}", "kategori": "Python",
                "baslangic": "21:00:00", "bitis": "23:00:00", "sure_dakika": dakika,
                "kaynak": "otomatik", "not": "", "duzenlendi": False,
            }
            veri["oturumlar"].append(zaman_takibi_kaydi)
    return json_deposu.oku()


def test_yil_ozeti_toplamlari():
    veri = _yil_verisi()
    ozet = yil_ozeti.ozet(veri, 2026, dt.date(2026, 12, 31))

    assert ozet["veri_var"] is True
    assert ozet["toplam_saat"] == pytest.approx((120 + 90 + 200) / 60, abs=0.1)
    assert ozet["aktif_gun_sayisi"] == 3
    assert ozet["oturum_sayisi"] == 3


def test_yil_ozeti_gece_kusunu_tespit_eder():
    veri = _yil_verisi()
    ozet = yil_ozeti.ozet(veri, 2026, dt.date(2026, 12, 31))
    assert ozet["gece_kusu_mu"] is True


def test_yil_ozeti_diger_yili_karistirmaz():
    veri = _yil_verisi(2026)
    ozet = yil_ozeti.ozet(veri, 2025, dt.date(2026, 12, 31))
    assert ozet["veri_var"] is False
    assert ozet["toplam_saat"] == 0


def test_kullanilabilir_yillar():
    veri = _yil_verisi()
    assert 2026 in yil_ozeti.kullanilabilir_yillar(veri["oturumlar"])


def test_aylik_dagilim_12_ay():
    veri = _yil_verisi()
    ozet = yil_ozeti.ozet(veri, 2026, dt.date(2026, 12, 31))
    assert len(ozet["aylar"]) == 12
    assert ozet["en_iyi_ay"]["ay"] == 3


# --- Rozet ------------------------------------------------------------------

def test_rozet_gecerli_svg_uretir():
    svg = yil_ozeti.rozet_svg("öğrenme", "42 saat")
    assert svg.startswith("<svg")
    assert "öğrenme" in svg
    assert "42 saat" in svg
    assert svg.rstrip().endswith("</svg>")


def test_rozet_html_kacisi_yapar():
    svg = yil_ozeti.rozet_svg("<script>", "&x")
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_rozet_secenekleri_uretilir():
    veri = _yil_verisi()
    secenekler = yil_ozeti.rozet_secenekleri(veri, dt.date(2026, 12, 31))
    assert {s["anahtar"] for s in secenekler} == {"toplam", "seri", "yil", "gun"}


def test_bilinmeyen_rozet_hata_verir():
    with pytest.raises(ValueError):
        yil_ozeti.rozet_uret(json_deposu.oku(), "yok")
