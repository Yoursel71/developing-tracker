from datetime import date, timedelta

from depo import json_deposu
from servisler import bildirim


def hafta_baslangici(gun=None):
    gun = gun or date.today()
    return gun - timedelta(days=gun.weekday())


def haftalik_toplam_dakika(oturumlar, referans_tarih=None):
    baslangic = hafta_baslangici(referans_tarih)
    bitis = baslangic + timedelta(days=6)
    return sum(
        o["sure_dakika"]
        for o in oturumlar
        if baslangic <= date.fromisoformat(o["tarih"]) <= bitis
    )


def hedefleri_guncelle(haftalik_saat, toplam_hedef_saat):
    veri = json_deposu.oku()
    veri["hedefler"]["haftalik_saat"] = haftalik_saat
    veri["hedefler"]["toplam_hedef_saat"] = toplam_hedef_saat
    json_deposu.yaz(veri)
    return veri["hedefler"]


def haftasonu_bildirimini_kontrol_et():
    """Haftanın son 2 gününde (Cmt/Paz), hedef karşılanmadıysa günde en fazla 1 bildirim gönderir."""
    veri = json_deposu.oku()
    bugun = date.today()
    if bugun.weekday() < 5:
        return False

    hedefler = veri["hedefler"]
    if hedefler.get("son_bildirim_tarihi") == bugun.isoformat():
        return False

    toplam_dakika = haftalik_toplam_dakika(veri["oturumlar"], bugun)
    hedef_dakika = hedefler["haftalik_saat"] * 60
    if toplam_dakika >= hedef_dakika:
        return False

    kalan_saat = round((hedef_dakika - toplam_dakika) / 60, 1)
    gonderildi = bildirim.bildirim_gonder(
        "Haftalık hedef uyarısı",
        f"Bu hafta hedefine {kalan_saat} saat kaldı, hafta bitiyor!",
    )
    hedefler["son_bildirim_tarihi"] = bugun.isoformat()
    json_deposu.yaz(veri)
    return gonderildi
