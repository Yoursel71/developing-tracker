"""Zaman matematiği: gece yarısı bölme, oturum tavanı, checkpoint."""

import datetime as dt

import pytest

import config
from depo import json_deposu
from servisler import zaman_takibi


def an(yil, ay, gun, saat=0, dakika=0):
    return dt.datetime(yil, ay, gun, saat, dakika).astimezone()


def test_normal_oturum_tek_gune_yazilir():
    baslangic = an(2026, 3, 10, 19, 0)
    bitis = an(2026, 3, 10, 21, 0)
    kayitlar = zaman_takibi.oturumlari_uret("Python", baslangic, bitis, 7200, "manuel")

    assert len(kayitlar) == 1
    assert kayitlar[0]["tarih"] == "2026-03-10"
    assert kayitlar[0]["sure_dakika"] == 120.0
    assert kayitlar[0]["baslangic"] == "19:00:00"


def test_gece_yarisini_gecen_oturum_iki_gune_bolunur():
    """23:00-01:00 tek güne yazılırsa gece çalışanların heatmap'i kayar."""
    baslangic = an(2026, 3, 10, 23, 0)
    bitis = an(2026, 3, 11, 1, 0)
    kayitlar = zaman_takibi.oturumlari_uret("Python", baslangic, bitis, 7200, "otomatik")

    assert len(kayitlar) == 2
    assert kayitlar[0]["tarih"] == "2026-03-10"
    assert kayitlar[1]["tarih"] == "2026-03-11"
    assert kayitlar[0]["sure_dakika"] == pytest.approx(60, abs=1)
    assert kayitlar[1]["sure_dakika"] == pytest.approx(60, abs=1)
    # Toplam korunmalı
    assert sum(k["sure_dakika"] for k in kayitlar) == pytest.approx(120, abs=1)


def test_pazar_gecesi_calismasi_dogru_haftaya_yazilir():
    from servisler import hedefler

    # 2026-03-15 Pazar, 2026-03-16 Pazartesi
    kayitlar = zaman_takibi.oturumlari_uret(
        "Python", an(2026, 3, 15, 23, 30), an(2026, 3, 16, 0, 30), 3600, "otomatik"
    )
    pazartesi_kayitlari = [k for k in kayitlar if k["tarih"] == "2026-03-16"]
    assert pazartesi_kayitlari, "Pazartesiye düşen kısım ayrı kaydedilmeli"

    yeni_hafta = hedefler.haftalik_toplam_dakika(kayitlar, dt.date(2026, 3, 16))
    assert yeni_hafta == pytest.approx(30, abs=1)


def test_bosta_gecen_sure_kayda_girmez():
    """Duvar saati 2 saat ama gerçek çalışma 30 dakikaysa 30 yazılmalı."""
    kayitlar = zaman_takibi.oturumlari_uret(
        "Python", an(2026, 3, 10, 19, 0), an(2026, 3, 10, 21, 0), 1800, "otomatik"
    )
    assert kayitlar[0]["sure_dakika"] == 30.0


def test_oturum_tavani_uygulanir():
    kayitlar = zaman_takibi.oturumlari_uret(
        "Python", an(2026, 3, 10, 0, 0), an(2026, 3, 11, 0, 0), 24 * 3600, "otomatik"
    )
    toplam = sum(k["sure_dakika"] for k in kayitlar)
    assert toplam == pytest.approx(config.OTURUM_TAVANI_SAAT * 60, abs=1)


def test_ters_aralik_kayit_uretmez():
    kayitlar = zaman_takibi.oturumlari_uret(
        "Python", an(2026, 3, 10, 21, 0), an(2026, 3, 10, 19, 0), 100, "manuel"
    )
    assert kayitlar == []


# --- Başlat / durdur --------------------------------------------------------

def _oturumu_geriye_al(kategori, dakika):
    """Aktif oturumu geçmişe kaydırır (gerçek süre geçmiş gibi)."""
    with json_deposu.guncelle() as veri:
        aktif = veri["aktif_oturumlar"][kategori]
        geride = zaman_takibi.simdi() - dt.timedelta(minutes=dakika)
        aktif["baslangic"] = geride.isoformat(timespec="seconds")
        aktif["son_gorulme"] = geride.isoformat(timespec="seconds")
        aktif["birikmis_saniye"] = dakika * 60


def test_oturum_baslat_ve_durdur():
    zaman_takibi.oturum_baslat("Python")
    aktifler = zaman_takibi.aktif_oturumlari_getir()
    assert "Python" in aktifler
    assert aktifler["Python"]["kaynak"] == "manuel"

    _oturumu_geriye_al("Python", 25)
    kayitlar = zaman_takibi.oturum_durdur("Python")

    assert zaman_takibi.aktif_oturumlari_getir() == {}
    assert len(kayitlar) == 1
    assert kayitlar[0]["sure_dakika"] == pytest.approx(25, abs=1)


def test_saniyeden_kisa_oturum_kaydedilmez():
    """Yanlışlıkla başlat-durdur yapılan oturum geçmişi kirletmemeli."""
    zaman_takibi.oturum_baslat("Python")
    kayitlar = zaman_takibi.oturum_durdur("Python")
    assert kayitlar == []
    assert json_deposu.oku()["oturumlar"] == []


def test_ayni_kategori_iki_kez_baslatilamaz():
    zaman_takibi.oturum_baslat("Python")
    with pytest.raises(ValueError):
        zaman_takibi.oturum_baslat("Python")


def test_farkli_kategoriler_es_zamanli_olabilir():
    zaman_takibi.oturum_baslat("Python")
    zaman_takibi.oturum_baslat("Sertifika kursu")
    assert len(zaman_takibi.aktif_oturumlari_getir()) == 2


def test_olmayan_oturum_durdurulamaz():
    with pytest.raises(ValueError):
        zaman_takibi.oturum_durdur("Python")


def test_otomatik_oturum_elle_durdurulunca_ertelenir():
    """Erteleme olmadan izleme motoru oturumu anında yeniden başlatırdı."""
    zaman_takibi.oturum_baslat("Python", kaynak="otomatik")
    zaman_takibi.oturum_durdur("Python")

    ertelemeler = json_deposu.oku()["izleme"]["ertelemeler"]
    assert "Python" in ertelemeler
    bitis = zaman_takibi.zaman_coz(ertelemeler["Python"])
    assert bitis > zaman_takibi.simdi()


def test_manuel_oturum_durdurulunca_ertelenmez():
    zaman_takibi.oturum_baslat("Python", kaynak="manuel")
    zaman_takibi.oturum_durdur("Python")
    assert json_deposu.oku()["izleme"]["ertelemeler"] == {}


def test_tum_oturumlari_durdur():
    zaman_takibi.oturum_baslat("Python")
    zaman_takibi.oturum_baslat("Diğer")
    kapatilan = zaman_takibi.tum_oturumlari_durdur()
    assert sorted(kapatilan) == ["Diğer", "Python"]
    assert zaman_takibi.aktif_oturumlari_getir() == {}


# --- Düzenleme --------------------------------------------------------------

def test_oturum_duzenleme_ve_silme():
    oturum = zaman_takibi.oturum_ekle("2026-03-10", "Python", 45, "notum")
    assert oturum["duzenlendi"] is True

    zaman_takibi.oturum_guncelle(oturum["id"], sure_dakika=60, **{"not": "yeni"})
    kayitli = json_deposu.oku()["oturumlar"][0]
    assert kayitli["sure_dakika"] == 60
    assert kayitli["not"] == "yeni"

    zaman_takibi.oturum_sil(oturum["id"])
    assert json_deposu.oku()["oturumlar"] == []


def test_olmayan_oturum_silinemez():
    with pytest.raises(ValueError):
        zaman_takibi.oturum_sil("yok-boyle-bir-id")


# --- Zaman dilimi -----------------------------------------------------------

def test_simdi_zaman_dilimi_tasir():
    assert zaman_takibi.simdi().tzinfo is not None


def test_naive_damga_yerel_dilime_baglanir():
    coz = zaman_takibi.zaman_coz("2026-03-10T19:00:00")
    assert coz is not None and coz.tzinfo is not None


def test_gecersiz_damga_none_doner():
    assert zaman_takibi.zaman_coz("saçma") is None
    assert zaman_takibi.zaman_coz(None) is None
