"""Kullanıcı tanımlı kategoriler."""

import pytest

import config
from depo import json_deposu
from servisler import kategoriler, zaman_takibi


def test_varsayilan_kategoriler_bastan_var():
    adlar = kategoriler.adlar()
    assert adlar == config.VARSAYILAN_KATEGORILER


def test_her_kategorinin_rengi_var():
    for kategori in kategoriler.listele():
        assert kategori["renk"].startswith("#")


def test_kendi_projeni_ekleyebilirsin():
    """Asıl eksik buydu: kategoriler kodda sabitti."""
    kategoriler.ekle("LocalRun")
    assert "LocalRun" in kategoriler.adlar()


def test_yeni_kategori_farkli_renk_alir():
    ilk = kategoriler.ekle("LocalRun")
    ikinci = kategoriler.ekle("BruceButBetter")
    assert ilk["renk"] != ikinci["renk"]


def test_ayni_ad_iki_kez_eklenemez():
    kategoriler.ekle("LocalRun")
    with pytest.raises(ValueError):
        kategoriler.ekle("localrun")


def test_bos_ad_reddedilir():
    with pytest.raises(ValueError):
        kategoriler.ekle("   ")


def test_yeni_kategoride_oturum_baslatilabilir():
    kategoriler.ekle("LocalRun")
    zaman_takibi.oturum_baslat("LocalRun")
    assert "LocalRun" in zaman_takibi.aktif_oturumlari_getir()


# --- Yeniden adlandırma -----------------------------------------------------

def test_yeniden_adlandirma_gecmis_oturumlari_gunceller():
    kategori = kategoriler.listele()[0]
    zaman_takibi.oturum_ekle("2026-03-10", kategori["ad"], 45)

    kategoriler.yeniden_adlandir(kategori["id"], "Python 3")

    oturumlar = json_deposu.oku()["oturumlar"]
    assert oturumlar[0]["kategori"] == "Python 3"
    assert "Python 3" in kategoriler.adlar()


def test_yeniden_adlandirma_aktif_oturumu_tasir():
    kategori = kategoriler.listele()[0]
    zaman_takibi.oturum_baslat(kategori["ad"])

    kategoriler.yeniden_adlandir(kategori["id"], "Yeni Ad")

    aktifler = zaman_takibi.aktif_oturumlari_getir()
    assert "Yeni Ad" in aktifler
    assert kategori["ad"] not in aktifler


def test_yeniden_adlandirma_izleme_eslemesini_gunceller():
    kategori = kategoriler.listele()[0]
    with json_deposu.guncelle() as veri:
        veri["izleme"]["editorler"] = [
            {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": kategori["ad"]}
        ]

    kategoriler.yeniden_adlandir(kategori["id"], "Kodlama")
    assert json_deposu.oku()["izleme"]["editorler"][0]["kategori"] == "Kodlama"


def test_mevcut_ada_yeniden_adlandirilamaz():
    birinci, ikinci = kategoriler.listele()[:2]
    with pytest.raises(ValueError):
        kategoriler.yeniden_adlandir(ikinci["id"], birinci["ad"])


# --- Silme ------------------------------------------------------------------

def test_bos_kategori_dogrudan_silinir():
    yeni = kategoriler.ekle("Geçici")
    kategoriler.sil(yeni["id"])
    assert "Geçici" not in kategoriler.adlar()


def test_dolu_kategori_hedefsiz_silinemez():
    """Sessizce veri kaybetmemek için hedef zorunlu."""
    kategori = kategoriler.listele()[0]
    zaman_takibi.oturum_ekle("2026-03-10", kategori["ad"], 45)

    with pytest.raises(ValueError) as hata:
        kategoriler.sil(kategori["id"])
    assert "oturum var" in str(hata.value)


def test_silme_oturumlari_hedefe_tasir():
    birinci, ikinci = kategoriler.listele()[:2]
    zaman_takibi.oturum_ekle("2026-03-10", birinci["ad"], 45)

    kategoriler.sil(birinci["id"], tasima_hedefi=ikinci["ad"])

    oturumlar = json_deposu.oku()["oturumlar"]
    assert oturumlar[0]["kategori"] == ikinci["ad"]
    assert birinci["ad"] not in kategoriler.adlar()


def test_silme_izleme_eslemelerini_temizler():
    kategori = kategoriler.listele()[0]
    with json_deposu.guncelle() as veri:
        veri["izleme"]["editorler"] = [
            {"program_adi": "VS Code", "islem_adi": "Code.exe", "kategori": kategori["ad"]}
        ]

    kategoriler.sil(kategori["id"])
    assert json_deposu.oku()["izleme"]["editorler"] == []


def test_son_kategori_silinemez():
    kayitlar = kategoriler.listele()
    for kategori in kayitlar[1:]:
        kategoriler.sil(kategori["id"])
    with pytest.raises(ValueError):
        kategoriler.sil(kategoriler.listele()[0]["id"])


# --- Göç --------------------------------------------------------------------

def test_v2_gocu_gecmiste_kullanilan_kategorileri_korur():
    """Sabit listede olmayan eski kategoriler sahipsiz kalmamalı."""
    from depo import goc

    eski = {
        "surum": 2,
        "kurulum_tamamlandi": True,
        "oturumlar": [
            {"id": "a", "tarih": "2026-01-01", "kategori": "Eski Projem", "sure_dakika": 60}
        ],
        "aktif_oturumlar": {},
        "hedefler": {"haftalik_saat": 10, "toplam_hedef_saat": 100},
        "izleme": {"editorler": [], "siteler": [], "ertelemeler": {}},
    }
    yeni, yapildi = goc.goc_et(eski)

    assert yapildi is True
    adlar = [k["ad"] for k in yeni["kategoriler"]]
    assert "Eski Projem" in adlar
    for varsayilan in config.VARSAYILAN_KATEGORILER:
        assert varsayilan in adlar
