"""Haftalık hedef geçmişi."""

import datetime as dt

from depo import json_deposu
from servisler import hedef_gecmisi, zaman_takibi

BUGUN = dt.date(2026, 3, 20)  # Cuma


def _oturum_ekle(tarih, dakika):
    zaman_takibi.oturum_ekle(tarih, "Python", dakika)


def _hedef_ayarla(saat):
    with json_deposu.guncelle() as veri:
        veri["hedefler"]["haftalik_saat"] = saat


def test_kapanmis_haftalar_gecmise_islenir():
    _hedef_ayarla(2)
    _oturum_ekle("2026-03-09", 150)   # geçen hafta: 2.5 saat -> başarılı
    _oturum_ekle("2026-03-16", 30)    # bu hafta (henüz kapanmadı)

    eklenen = hedef_gecmisi.gecmisi_guncelle(BUGUN)

    assert eklenen >= 1
    kayitlar = json_deposu.oku()["hedef_gecmisi"]
    gecen = [k for k in kayitlar if k["hafta_basi"] == "2026-03-09"][0]
    assert gecen["basarili"] is True
    assert gecen["dakika"] == 150


def test_icinde_bulunulan_hafta_gecmise_yazilmaz():
    _hedef_ayarla(2)
    _oturum_ekle("2026-03-16", 300)
    hedef_gecmisi.gecmisi_guncelle(BUGUN)

    kayitlar = json_deposu.oku()["hedef_gecmisi"]
    assert all(k["hafta_basi"] != "2026-03-16" for k in kayitlar)


def test_basarisiz_hafta_isaretlenir():
    _hedef_ayarla(10)
    _oturum_ekle("2026-03-09", 60)
    hedef_gecmisi.gecmisi_guncelle(BUGUN)

    gecen = [k for k in json_deposu.oku()["hedef_gecmisi"]
             if k["hafta_basi"] == "2026-03-09"][0]
    assert gecen["basarili"] is False


def test_tekrar_calistirmak_kopya_uretmez():
    _hedef_ayarla(2)
    _oturum_ekle("2026-03-09", 150)
    hedef_gecmisi.gecmisi_guncelle(BUGUN)
    ilk = len(json_deposu.oku()["hedef_gecmisi"])

    hedef_gecmisi.gecmisi_guncelle(BUGUN)
    assert len(json_deposu.oku()["hedef_gecmisi"]) == ilk


def test_hedef_degisince_gecmis_carpitilmaz():
    """Geçmiş, o haftanın hedefiyle saklanır."""
    _hedef_ayarla(2)
    _oturum_ekle("2026-03-09", 150)
    hedef_gecmisi.gecmisi_guncelle(BUGUN)

    _hedef_ayarla(40)  # hedef sonradan yükseltildi
    gecen = [k for k in json_deposu.oku()["hedef_gecmisi"]
             if k["hafta_basi"] == "2026-03-09"][0]
    assert gecen["hedef_saat"] == 2
    assert gecen["basarili"] is True


def test_listele_bu_haftayi_basa_koyar():
    _hedef_ayarla(2)
    _oturum_ekle("2026-03-09", 150)
    _oturum_ekle("2026-03-16", 30)
    hedef_gecmisi.gecmisi_guncelle(BUGUN)

    satirlar = hedef_gecmisi.listele(bugun=BUGUN)
    assert satirlar[0]["etiket"] == "Bu hafta"
    assert satirlar[0]["devam_ediyor"] is True
    assert satirlar[1]["etiket"] == "Geçen hafta"


def test_ozet_orani_hesaplar():
    _hedef_ayarla(2)
    _oturum_ekle("2026-03-02", 150)   # başarılı
    _oturum_ekle("2026-03-09", 30)    # başarısız
    hedef_gecmisi.gecmisi_guncelle(BUGUN)

    ozet = hedef_gecmisi.ozet(bugun=BUGUN)
    assert ozet["toplam"] >= 2
    assert ozet["basarili"] >= 1


def test_veri_yoksa_cokmez():
    assert hedef_gecmisi.gecmisi_guncelle(BUGUN) == 0
    assert hedef_gecmisi.listele(bugun=BUGUN)[0]["etiket"] == "Bu hafta"
