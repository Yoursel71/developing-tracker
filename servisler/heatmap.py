"""GitHub tarzı katkı ısı haritası.

GitHub'ın grafiği 7 satır (haftanın günleri) × N hafta sütunudur ve
sütun-öncelikli dolar. Renk yoğunluğu mutlak eşiklerle değil, kullanıcının
kendi dağılımının yüzdelik dilimleriyle belirlenir; aksi hâlde günde 30
dakika çalışan biri hiç koyu yeşil göremez, günde 4 saat çalışan ise her
günü koyu görüp varyansı kaybeder.
"""

import calendar
import datetime as dt
from collections import defaultdict

SEVIYE_SAYISI = 4  # 1..4 (0 = boş gün)

TURKCE_AYLAR = [
    "Oca", "Şub", "Mar", "Nis", "May", "Haz",
    "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara",
]
GUN_ETIKETLERI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

# Yeterli veri yokken kullanılan mutlak eşikler (dakika).
YEDEK_ESIKLER = [30, 60, 120]


def gunluk_toplamlar(oturumlar):
    toplamlar = defaultdict(float)
    for oturum in oturumlar:
        toplamlar[oturum["tarih"]] += oturum.get("sure_dakika", 0)
    return dict(toplamlar)


def github_gunleri(etkinlikler):
    gunler = defaultdict(int)
    for etkinlik in etkinlikler:
        if isinstance(etkinlik, dict) and etkinlik.get("tarih"):
            gunler[etkinlik["tarih"]] += etkinlik.get("commit_sayisi", 0)
    return dict(gunler)


def esikleri_hesapla(dakikalar):
    """Sıfır olmayan günlerin yüzdelik dilimlerinden eşik üretir."""
    dolu = sorted(d for d in dakikalar if d > 0)
    if len(dolu) < 8:
        return list(YEDEK_ESIKLER)

    def yuzdelik(oran):
        indeks = min(int(len(dolu) * oran), len(dolu) - 1)
        return dolu[indeks]

    esikler = [yuzdelik(0.25), yuzdelik(0.50), yuzdelik(0.75)]
    # Eşikler artan ve birbirinden farklı olmalı.
    for i in range(1, len(esikler)):
        if esikler[i] <= esikler[i - 1]:
            esikler[i] = esikler[i - 1] + 1
    return esikler


def seviye(dakika, esikler):
    if dakika <= 0:
        return 0
    for indeks, esik in enumerate(esikler):
        if dakika <= esik:
            return indeks + 1
    return SEVIYE_SAYISI


def _gun_hucresi(gun, toplamlar, gh_gunler, esikler):
    tarih = gun.isoformat()
    dakika = round(toplamlar.get(tarih, 0), 1)
    return {
        "tarih": tarih,
        "gun": gun.day,
        "dakika": dakika,
        "saat_metni": _sure_metni(dakika),
        "seviye": seviye(dakika, esikler),
        "commit_sayisi": gh_gunler.get(tarih, 0),
        "gelecek": gun > dt.date.today(),
    }


def _sure_metni(dakika):
    if dakika <= 0:
        return "çalışılmadı"
    saat, kalan = divmod(int(round(dakika)), 60)
    if saat and kalan:
        return f"{saat}s {kalan}dk"
    if saat:
        return f"{saat}s"
    return f"{kalan}dk"


def yil_gridi(oturumlar, etkinlikler, bitis=None, hafta_sayisi=53):
    """7 satır × N hafta sütunu; GitHub'ın grafiğiyle aynı düzen.

    Sütunlar Pazartesi ile başlar. Dönen yapı şablonda doğrudan
    ``grid-auto-flow: column`` ile basılabilir.
    """
    bitis = bitis or dt.date.today()
    # Bitiş gününün haftasının Pazar'ına kadar doldur.
    hafta_sonu = bitis + dt.timedelta(days=6 - bitis.weekday())
    baslangic = hafta_sonu - dt.timedelta(weeks=hafta_sayisi - 1, days=6)

    toplamlar = gunluk_toplamlar(oturumlar)
    gh_gunler = github_gunleri(etkinlikler)

    aralik_dakikalari = []
    gun = baslangic
    while gun <= hafta_sonu:
        aralik_dakikalari.append(toplamlar.get(gun.isoformat(), 0))
        gun += dt.timedelta(days=1)
    esikler = esikleri_hesapla(aralik_dakikalari)

    haftalar = []
    ay_etiketleri = []
    gun = baslangic
    hafta_indeksi = 0
    onceki_ay = None
    son_etiket_haftasi = None
    while gun <= hafta_sonu:
        hafta = []
        for _ in range(7):
            hafta.append(_gun_hucresi(gun, toplamlar, gh_gunler, esikler))
            gun += dt.timedelta(days=1)
        haftalar.append(hafta)

        ilk_gun = dt.date.fromisoformat(hafta[0]["tarih"])
        if ilk_gun.month != onceki_ay:
            onceki_ay = ilk_gun.month
            # Etiketler üst üste binmesin: en az 3 hafta ara olsun.
            if son_etiket_haftasi is None or hafta_indeksi - son_etiket_haftasi >= 3:
                ay_etiketleri.append({
                    "hafta": hafta_indeksi,
                    "etiket": TURKCE_AYLAR[ilk_gun.month - 1],
                })
                son_etiket_haftasi = hafta_indeksi
        hafta_indeksi += 1

    toplam_dakika = round(sum(aralik_dakikalari), 1)
    return {
        "haftalar": haftalar,
        "ay_etiketleri": ay_etiketleri,
        "gun_etiketleri": GUN_ETIKETLERI,
        "esikler": esikler,
        "toplam_dakika": toplam_dakika,
        "toplam_metni": _sure_metni(toplam_dakika),
        "aktif_gun_sayisi": sum(1 for d in aralik_dakikalari if d > 0),
        "baslangic": baslangic.isoformat(),
        "bitis": hafta_sonu.isoformat(),
    }


def ay_gridi(oturumlar, etkinlikler, yil=None, ay=None):
    """Takvim düzeninde tek ay (haftanın günü hizalamalı)."""
    bugun = dt.date.today()
    yil = yil or bugun.year
    ay = ay or bugun.month

    ilk = dt.date(yil, ay, 1)
    gun_sayisi = calendar.monthrange(yil, ay)[1]
    son = dt.date(yil, ay, gun_sayisi)

    toplamlar = gunluk_toplamlar(oturumlar)
    gh_gunler = github_gunleri(etkinlikler)
    ay_dakikalari = [
        toplamlar.get((ilk + dt.timedelta(days=i)).isoformat(), 0)
        for i in range(gun_sayisi)
    ]
    esikler = esikleri_hesapla(ay_dakikalari)

    hucreler = [None] * ilk.weekday()  # ayın 1'i doğru güne hizalansın
    for i in range(gun_sayisi):
        hucreler.append(_gun_hucresi(ilk + dt.timedelta(days=i), toplamlar, gh_gunler, esikler))
    while len(hucreler) % 7:
        hucreler.append(None)

    toplam = round(sum(ay_dakikalari), 1)
    return {
        "hucreler": hucreler,
        "gun_etiketleri": GUN_ETIKETLERI,
        "esikler": esikler,
        "yil": yil,
        "ay": ay,
        "ay_adi": TURKCE_AYLAR[ay - 1],
        "toplam_dakika": toplam,
        "toplam_metni": _sure_metni(toplam),
        "aktif_gun_sayisi": sum(1 for d in ay_dakikalari if d > 0),
        "onceki": ((ilk - dt.timedelta(days=1)).year, (ilk - dt.timedelta(days=1)).month),
        "sonraki": ((son + dt.timedelta(days=1)).year, (son + dt.timedelta(days=1)).month),
    }


def mini_grid(oturumlar, etkinlikler, hafta_sayisi=12):
    """Panelde gösterilen kısa heatmap."""
    return yil_gridi(oturumlar, etkinlikler, hafta_sayisi=hafta_sayisi)
