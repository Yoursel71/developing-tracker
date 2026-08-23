import calendar
from collections import defaultdict
from datetime import date, timedelta


def gunluk_toplamlar(oturumlar):
    toplamlar = defaultdict(float)
    for o in oturumlar:
        toplamlar[o["tarih"]] += o["sure_dakika"]
    return toplamlar


def github_gunleri(etkinlikler):
    gunler = defaultdict(int)
    for e in etkinlikler:
        gunler[e["tarih"]] += e.get("commit_sayisi", 0)
    return gunler


def renk_kovasi(dakika):
    if dakika <= 0:
        return "gri"
    if dakika <= 60:
        return "acik-yesil"
    if dakika <= 180:
        return "orta-yesil"
    return "koyu-yesil"


def _gun_bilgisi(gun, toplamlar, gh_gunler):
    tarih_str = gun.isoformat()
    dakika = toplamlar.get(tarih_str, 0)
    return {
        "tarih": tarih_str,
        "dakika": dakika,
        "renk": renk_kovasi(dakika),
        "commit_sayisi": gh_gunler.get(tarih_str, 0),
    }


def haftalik_grid(oturumlar, etkinlikler, referans_tarih=None):
    referans_tarih = referans_tarih or date.today()
    baslangic = referans_tarih - timedelta(days=6)
    toplamlar = gunluk_toplamlar(oturumlar)
    gh_gunler = github_gunleri(etkinlikler)
    return [
        _gun_bilgisi(baslangic + timedelta(days=i), toplamlar, gh_gunler)
        for i in range(7)
    ]


def aylik_grid(oturumlar, etkinlikler, yil=None, ay=None):
    bugun = date.today()
    yil = yil or bugun.year
    ay = ay or bugun.month
    ilk_gun = date(yil, ay, 1)
    gun_sayisi = calendar.monthrange(yil, ay)[1]
    toplamlar = gunluk_toplamlar(oturumlar)
    gh_gunler = github_gunleri(etkinlikler)
    return [
        _gun_bilgisi(ilk_gun + timedelta(days=i), toplamlar, gh_gunler)
        for i in range(gun_sayisi)
    ]
