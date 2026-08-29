"""ESP32 vb. harici cihazlar için özet durum hesaplama (servisler/cihaz_durumu.py)."""

import datetime as dt

from depo import varsayilan
from servisler import cihaz_durumu

# 2026-03-20 bir Cuma (weekday=4); "geçen gün oranı" = (4+1)/7.
BUGUN = dt.date(2026, 3, 20)


def oturum(tarih, dakika, kategori="Python"):
    return {
        "id": tarih + str(dakika), "tarih": tarih, "kategori": kategori,
        "baslangic": "20:00:00", "bitis": "21:00:00", "sure_dakika": dakika,
    }


def veri_olustur(oturumlar=None, haftalik_saat=10):
    veri = varsayilan.varsayilan_veri()
    veri["oturumlar"] = oturumlar or []
    veri["hedefler"]["haftalik_saat"] = haftalik_saat
    return veri


def test_bugun_ve_hafta_toplamlari():
    # Hafta başı Pazartesi 2026-03-16.
    veri = veri_olustur([
        oturum("2026-03-16", 60),
        oturum("2026-03-20", 90),  # bugün
    ])
    durum = cihaz_durumu.durum_hesapla(veri, bugun=BUGUN)
    assert durum["today_hours"] == 1.5
    assert durum["weekly_logged_hours"] == 2.5
    assert durum["weekly_goal_hours"] == 10
    assert durum["weekly_remaining_hours"] == 7.5


def test_hedef_yoksa_yolunda_sayilir():
    veri = veri_olustur([], haftalik_saat=0)
    durum = cihaz_durumu.durum_hesapla(veri, bugun=BUGUN)
    assert durum["pace_status"] == "on_track"


def test_pace_status_yolunda():
    # beklenen = 10 * 5/7 ≈ 7.14; 6.5 saat -> oran ≈ 0.91 (>= 0.85)
    veri = veri_olustur([oturum("2026-03-16", 390)], haftalik_saat=10)
    assert cihaz_durumu.durum_hesapla(veri, bugun=BUGUN)["pace_status"] == "on_track"


def test_pace_status_geride():
    # 5 saat -> oran = 5 / 7.14 ≈ 0.70 (0.50 <= oran < 0.85)
    veri = veri_olustur([oturum("2026-03-16", 300)], haftalik_saat=10)
    assert cihaz_durumu.durum_hesapla(veri, bugun=BUGUN)["pace_status"] == "behind"


def test_pace_status_kritik():
    # 2 saat -> oran ≈ 0.28 (< 0.50)
    veri = veri_olustur([oturum("2026-03-16", 120)], haftalik_saat=10)
    assert cihaz_durumu.durum_hesapla(veri, bugun=BUGUN)["pace_status"] == "critical"


def test_heatmap_70_gun_ve_0_4_araliginda():
    oturumlar = [
        oturum((BUGUN - dt.timedelta(days=i)).isoformat(), 30 * (i % 5))
        for i in range(70)
    ]
    heatmap = cihaz_durumu.durum_hesapla(veri_olustur(oturumlar), bugun=BUGUN)["heatmap"]
    assert len(heatmap) == 70
    assert all(0 <= seviye <= 4 for seviye in heatmap)


def test_heatmap_bugun_son_eleman():
    veri = veri_olustur([oturum(BUGUN.isoformat(), 200)])
    heatmap = cihaz_durumu.durum_hesapla(veri, bugun=BUGUN)["heatmap"]
    assert heatmap[-1] > 0
    assert heatmap[0] == 0


def test_last_updated_verilen_zamani_kullanir():
    simdi = dt.datetime(2026, 3, 20, 14, 32, 10, tzinfo=dt.timezone.utc)
    durum = cihaz_durumu.durum_hesapla(veri_olustur([]), bugun=BUGUN, simdi=simdi)
    assert durum["last_updated"] == "2026-03-20T14:32:10+00:00"
