"""Sunucu tarafı doğrulama: negatif değerler, çakışmalar, alan adı normalizasyonu."""

import pytest

from servisler import dogrulama
from servisler.dogrulama import DogrulamaHatasi


# --- Sayı -------------------------------------------------------------------

def test_negatif_saat_reddedilir():
    """curl -d 'haftalik_saat=-10' kabul ediliyordu ve 'Hedef tamamlandı' diyordu."""
    with pytest.raises(DogrulamaHatasi):
        dogrulama.sayi(-10, "Haftalık hedef", en_az=0)


def test_turkce_ondalik_virgulu_kabul_edilir():
    """'15,5' yakalanmamış ValueError ile 500 üretip formu kaybettiriyordu."""
    assert dogrulama.sayi("15,5", "Süre") == 15.5


def test_gecersiz_sayi_dogrulama_hatasi_verir():
    with pytest.raises(DogrulamaHatasi) as hata:
        dogrulama.sayi("abc", "Süre")
    assert "sayı olmalı" in hata.value.mesaj


def test_ust_sinir_uygulanir():
    with pytest.raises(DogrulamaHatasi):
        dogrulama.sayi(999999, "Toplam hedef", en_cok=100000)


def test_bos_deger_varsayilana_duser():
    assert dogrulama.sayi("", "Süre", varsayilan=7) == 7


def test_zorunlu_alan_bos_birakilamaz():
    with pytest.raises(DogrulamaHatasi):
        dogrulama.sayi("", "Süre", zorunlu=True)


# --- Kategori ---------------------------------------------------------------

def test_gecerli_kategori():
    assert dogrulama.kategori("Python") == "Python"


def test_uydurma_kategori_reddedilir():
    """Uydurma kategori aktif_oturumlar'a yazılıp asla durdurulamıyordu."""
    with pytest.raises(DogrulamaHatasi):
        dogrulama.kategori("HackerKategori")


# --- Tarih ------------------------------------------------------------------

def test_gelecek_tarih_reddedilir():
    with pytest.raises(DogrulamaHatasi):
        dogrulama.tarih("2099-01-01")


def test_bozuk_tarih_reddedilir():
    with pytest.raises(DogrulamaHatasi):
        dogrulama.tarih("20.03.2026")


# --- GitHub kullanıcı adı ---------------------------------------------------

def test_gecerli_github_kullanici():
    assert dogrulama.github_kullanici(" Yoursel71 ") == "Yoursel71"


def test_bos_github_kullanici_serbest():
    assert dogrulama.github_kullanici("") == ""


def test_gecersiz_github_kullanici():
    with pytest.raises(DogrulamaHatasi):
        dogrulama.github_kullanici("kullanici adi!")


# --- Alan adı ---------------------------------------------------------------

def test_tam_url_alan_adina_indirgenir():
    """Kullanıcı URL yapıştırınca eşleşme hiç tutmuyordu."""
    assert dogrulama.alan_adi_normallestir("https://www.udemy.com/course/xyz") == "udemy.com"


def test_www_ve_port_temizlenir():
    assert dogrulama.alan_adi_normallestir("www.Udemy.com:443") == "udemy.com"


def test_gecersiz_alan_adi_reddedilir():
    with pytest.raises(DogrulamaHatasi):
        dogrulama.alan_adi_normallestir("bu bir alan adi degil")


def test_tek_kelime_alan_adi_reddedilir():
    with pytest.raises(DogrulamaHatasi):
        dogrulama.alan_adi_normallestir("localhost")


# --- İzleme listeleri -------------------------------------------------------

def test_ayni_islem_iki_kategoriye_baglanamaz():
    """VS Code iki kategoriye eşlenirse süre %100 şişiyordu."""
    editorler = [
        {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": "Python"},
        {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": "GitHub çalışması"},
    ]
    with pytest.raises(DogrulamaHatasi) as hata:
        dogrulama.izleme_listelerini_dogrula(editorler, [])
    assert "çift" in hata.value.mesaj


def test_birebir_tekrar_sessizce_tekillestirilir():
    editorler = [
        {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": "Python"},
        {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": "Python"},
    ]
    temiz, _ = dogrulama.izleme_listelerini_dogrula(editorler, [])
    assert len(temiz) == 1


def test_ayni_site_iki_kategoriye_baglanamaz():
    siteler = [
        {"alan_adi": "udemy.com", "kategori": "Python"},
        {"alan_adi": "https://udemy.com/x", "kategori": "Sertifika kursu"},
    ]
    with pytest.raises(DogrulamaHatasi):
        dogrulama.izleme_listelerini_dogrula([], siteler)


def test_bos_satirlar_atlanir():
    editorler = [{"program_adi": "", "islem_adi": "", "kategori": "Python"}]
    temiz, _ = dogrulama.izleme_listelerini_dogrula(editorler, [])
    assert temiz == []


def test_siteler_normallestirilerek_kaydedilir():
    siteler = [{"alan_adi": "https://www.Udemy.com/course/x", "kategori": "Python"}]
    _, temiz = dogrulama.izleme_listelerini_dogrula([], siteler)
    assert temiz[0]["alan_adi"] == "udemy.com"


# --- Hedefler ---------------------------------------------------------------

def test_haftalik_toplamdan_buyuk_olamaz():
    with pytest.raises(DogrulamaHatasi):
        dogrulama.hedefleri_dogrula(50, 10)


def test_gecerli_hedefler():
    assert dogrulama.hedefleri_dogrula("10", "135") == (10.0, 135.0)


def test_haftalik_168_saati_asamaz():
    with pytest.raises(DogrulamaHatasi):
        dogrulama.hedefleri_dogrula(200, 500)
