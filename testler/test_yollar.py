"""Veri yolu çözümü.

Bu, projedeki en kritik hatanın testi: PyInstaller ``--onefile`` derlemesinde
``__file__`` geçici ``_MEIPASS`` klasörüne çözülür ve o klasör süreç
çıkışında silinir. Veri oraya yazılırsa kullanıcı her kapanışta tüm
geçmişini kaybeder.
"""

import os
import sys

import pytest

from platform_katmani import yollar


@pytest.fixture
def donmus_taklit(monkeypatch, tmp_path):
    """PyInstaller onefile ortamını taklit eder."""
    sahte_meipass = tmp_path / "_MEI123456"
    sahte_meipass.mkdir()
    sahte_exe = tmp_path / "kurulum" / "GelisimTakip.exe"
    sahte_exe.parent.mkdir()
    sahte_exe.write_text("")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(sahte_meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(sahte_exe))
    monkeypatch.delenv("GELISIM_TAKIP_VERI_DIZINI", raising=False)
    return sahte_meipass, sahte_exe


def test_donmus_modda_veri_meipass_disina_yazilir(donmus_taklit, monkeypatch, tmp_path):
    """Veri ASLA _MEIPASS altına yazılmamalı — orası silinen geçici klasör."""
    sahte_meipass, _ = donmus_taklit
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    dizin = yollar.veri_dizini()

    assert str(sahte_meipass) not in dizin, (
        "Veri geçici _MEIPASS klasörüne yazılıyor; uygulama kapanınca silinir!"
    )
    assert "GelisimTakip" in dizin


def test_donmus_modda_kaynaklar_meipass_altindan_okunur(donmus_taklit):
    """templates/static ise paketten, yani _MEIPASS'ten okunmalı."""
    sahte_meipass, _ = donmus_taklit
    assert yollar.kaynak_yolu("templates").startswith(str(sahte_meipass))
    assert yollar.kaynak_yolu("static").startswith(str(sahte_meipass))


def test_gelistirme_modunda_depo_icindeki_data_kullanilir(monkeypatch):
    monkeypatch.delenv("GELISIM_TAKIP_VERI_DIZINI", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert yollar.veri_dizini().endswith("data")


def test_tasinabilir_isaret_dosyasi_exe_yanina_yazdirir(donmus_taklit):
    _, sahte_exe = donmus_taklit
    isaret = os.path.join(os.path.dirname(sahte_exe), yollar.TASINABILIR_ISARET_DOSYASI)
    with open(isaret, "w", encoding="utf-8") as f:
        f.write("")

    dizin = yollar.veri_dizini()
    assert dizin.startswith(os.path.dirname(str(sahte_exe)))


def test_ortam_degiskeni_her_seyi_ezer(monkeypatch, tmp_path):
    ozel = str(tmp_path / "ozel-yer")
    monkeypatch.setenv("GELISIM_TAKIP_VERI_DIZINI", ozel)
    assert yollar.veri_dizini() == ozel


def test_veri_dosyasi_ve_yedekler_ayni_dizinde(monkeypatch, tmp_path):
    monkeypatch.setenv("GELISIM_TAKIP_VERI_DIZINI", str(tmp_path / "v"))
    assert os.path.dirname(yollar.veri_dosyasi()) == str(tmp_path / "v")
    assert yollar.yedek_dizini().startswith(str(tmp_path / "v"))
    assert yollar.gunluk_dosyasi().startswith(str(tmp_path / "v"))
