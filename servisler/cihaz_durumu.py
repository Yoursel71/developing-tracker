"""ESP32 gibi harici, ekranlı donanım cihazları için özet durum API'si.

Küçük bir cihazın tek istekte ihtiyaç duyduğu her şeyi (bugün/haftalık
saat, seri, tempo durumu, mini ısı haritası) tek JSON gövdesinde toplar;
cihaz ``/api/durum`` ve heatmap sayfası gibi ayrı uçları birleştirmek
zorunda kalmaz. Mantık ve eşikler docs/esp32-display-entegrasyon-plani.md
ile birebir uyumludur.
"""

import datetime as dt

from servisler import heatmap, hedefler, istatistikler

HEATMAP_GUN_SAYISI = 70  # 10 hafta x 7 gün

# Beklenen saatin en az bu oranını tutturmuş olmak "yolunda" sayılır.
YOLUNDA_ORANI = 0.85
# Bunun altı "kritik", ikisi arası "geride".
KRITIK_ORANI = 0.50


def _pace_status(gecen_gun_orani, hedef_saat, biriken_saat):
    if hedef_saat <= 0:
        return "on_track"
    beklenen_saat = hedef_saat * gecen_gun_orani
    if beklenen_saat <= 0:
        return "on_track"
    oran = biriken_saat / beklenen_saat
    if oran >= YOLUNDA_ORANI:
        return "on_track"
    if oran >= KRITIK_ORANI:
        return "behind"
    return "critical"


def _heatmap_seviyeleri(oturumlar, bugun, gun_sayisi=HEATMAP_GUN_SAYISI):
    toplamlar = istatistikler.gunluk_toplamlar(oturumlar)
    baslangic = bugun - dt.timedelta(days=gun_sayisi - 1)
    gunler = [baslangic + dt.timedelta(days=i) for i in range(gun_sayisi)]
    dakikalar = [toplamlar.get(gun, 0) for gun in gunler]
    esikler = heatmap.esikleri_hesapla(dakikalar)
    return [heatmap.seviye(dakika, esikler) for dakika in dakikalar]


def durum_hesapla(veri, bugun=None, simdi=None):
    bugun = bugun or dt.date.today()
    simdi = simdi or dt.datetime.now().astimezone()
    oturumlar = veri["oturumlar"]

    seri = istatistikler.seri_hesapla(
        oturumlar, veri["ayarlar"].get("seri_esigi_dakika"), bugun
    )
    gunluk = istatistikler.gunluk_toplamlar(oturumlar)
    bugun_saat = round(gunluk.get(bugun, 0) / 60, 2)

    hedef_saat = veri["hedefler"].get("haftalik_saat", 0) or 0
    haftalik_dakika = hedefler.haftalik_toplam_dakika(oturumlar, bugun)
    haftalik_saat = round(haftalik_dakika / 60, 2)
    kalan_saat = round(max(hedef_saat - haftalik_saat, 0), 2)

    # hedefler.haftalik_ilerleme'deki "kalan_gun = 6 - weekday()" kuralıyla
    # tutarlı: bugün de "geçmiş günler" kümesine dahil sayılır.
    gecen_gun_orani = (bugun.weekday() + 1) / 7

    return {
        "today_hours": bugun_saat,
        "weekly_goal_hours": hedef_saat,
        "weekly_logged_hours": haftalik_saat,
        "weekly_remaining_hours": kalan_saat,
        "streak_days": seri["guncel"],
        "pace_status": _pace_status(gecen_gun_orani, hedef_saat, haftalik_saat),
        "heatmap": _heatmap_seviyeleri(oturumlar, bugun),
        "last_updated": simdi.isoformat(timespec="seconds"),
    }
