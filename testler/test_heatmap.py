"""Isı haritası: grid şekli, hafta hizalaması, göreli renk ölçeği."""

import datetime as dt

from servisler import heatmap


def oturum(tarih, dakika):
    return {"tarih": tarih, "kategori": "Python", "sure_dakika": dakika}


def test_yil_gridi_7_satir_uretir():
    grid = heatmap.yil_gridi([], [], bitis=dt.date(2026, 3, 20), hafta_sayisi=53)
    assert len(grid["haftalar"]) == 53
    assert all(len(hafta) == 7 for hafta in grid["haftalar"])


def test_yil_gridi_sutunlari_pazartesiyle_baslar():
    grid = heatmap.yil_gridi([], [], bitis=dt.date(2026, 3, 20), hafta_sayisi=4)
    for hafta in grid["haftalar"]:
        ilk = dt.date.fromisoformat(hafta[0]["tarih"])
        assert ilk.weekday() == 0, "Her sütun Pazartesi ile başlamalı"


def test_yil_gridi_bugunu_icerir():
    bugun = dt.date(2026, 3, 20)
    grid = heatmap.yil_gridi([], [], bitis=bugun, hafta_sayisi=4)
    tarihler = {gun["tarih"] for hafta in grid["haftalar"] for gun in hafta}
    assert bugun.isoformat() in tarihler


def test_ay_gridi_hafta_gunune_hizalanir():
    """Ayın 1'i hangi güne denk geliyorsa o sütuna düşmeli."""
    # 1 Mart 2026 Pazar (weekday=6) → başta 6 boş hücre
    grid = heatmap.ay_gridi([], [], 2026, 3)
    bos_sayisi = 0
    for hucre in grid["hucreler"]:
        if hucre is None:
            bos_sayisi += 1
        else:
            break
    assert bos_sayisi == dt.date(2026, 3, 1).weekday()


def test_ay_gridi_tam_haftalara_tamamlanir():
    grid = heatmap.ay_gridi([], [], 2026, 3)
    assert len(grid["hucreler"]) % 7 == 0


def test_ay_gridi_tum_gunleri_icerir():
    grid = heatmap.ay_gridi([], [], 2026, 2)
    dolu = [h for h in grid["hucreler"] if h is not None]
    assert len(dolu) == 28
    assert dolu[0]["gun"] == 1 and dolu[-1]["gun"] == 28


def test_ay_gecisi_dogru():
    grid = heatmap.ay_gridi([], [], 2026, 12)
    assert grid["sonraki"] == (2027, 1)
    assert grid["onceki"] == (2026, 11)


# --- Renk ölçeği ------------------------------------------------------------

def test_yetersiz_veride_mutlak_esikler():
    assert heatmap.esikleri_hesapla([30, 60]) == heatmap.YEDEK_ESIKLER


def test_goreli_esikler_kullanicinin_dagilimina_uyar():
    """Günde 30 dk çalışan biri de koyu yeşil görebilmeli."""
    dakikalar = [5, 10, 12, 15, 18, 20, 25, 30, 35, 40]
    esikler = heatmap.esikleri_hesapla(dakikalar)
    assert esikler != heatmap.YEDEK_ESIKLER
    assert heatmap.seviye(40, esikler) == heatmap.SEVIYE_SAYISI
    assert heatmap.seviye(5, esikler) == 1


def test_esikler_artan_olur():
    esikler = heatmap.esikleri_hesapla([10] * 12)
    assert esikler[0] < esikler[1] < esikler[2]


def test_sifir_dakika_seviye_sifir():
    assert heatmap.seviye(0, [30, 60, 120]) == 0


def test_seviyeler_sinirlarda_dogru():
    esikler = [30, 60, 120]
    assert heatmap.seviye(30, esikler) == 1
    assert heatmap.seviye(31, esikler) == 2
    assert heatmap.seviye(120, esikler) == 3
    assert heatmap.seviye(121, esikler) == 4


# --- İçerik -----------------------------------------------------------------

def test_gunluk_toplamlar_ayni_gunu_birlestirir():
    oturumlar = [oturum("2026-03-20", 30), oturum("2026-03-20", 45)]
    assert heatmap.gunluk_toplamlar(oturumlar)["2026-03-20"] == 75


def test_github_commitleri_hucreye_islenir():
    etkinlikler = [{"tarih": "2026-03-20", "repo": "a/b", "commit_sayisi": 3}]
    grid = heatmap.yil_gridi([], etkinlikler, bitis=dt.date(2026, 3, 20), hafta_sayisi=2)
    hucre = [g for h in grid["haftalar"] for g in h if g["tarih"] == "2026-03-20"][0]
    assert hucre["commit_sayisi"] == 3


def test_gelecek_gunler_isaretlenir():
    grid = heatmap.yil_gridi([], [], bitis=dt.date.today(), hafta_sayisi=2)
    gelecekler = [g for h in grid["haftalar"] for g in h if g["gelecek"]]
    for gun in gelecekler:
        assert dt.date.fromisoformat(gun["tarih"]) > dt.date.today()


def test_toplam_metni_okunabilir():
    grid = heatmap.yil_gridi(
        [oturum("2026-03-20", 90)], [], bitis=dt.date(2026, 3, 20), hafta_sayisi=2
    )
    assert grid["toplam_metni"] == "1s 30dk"
    assert grid["aktif_gun_sayisi"] == 1


def test_bos_veride_grid_yine_uretilir():
    grid = heatmap.yil_gridi([], [], bitis=dt.date(2026, 3, 20), hafta_sayisi=4)
    assert grid["toplam_dakika"] == 0
    assert grid["aktif_gun_sayisi"] == 0
    assert len(grid["haftalar"]) == 4


def test_ay_etiketleri_uretilir():
    grid = heatmap.yil_gridi([], [], bitis=dt.date(2026, 3, 20), hafta_sayisi=20)
    assert len(grid["ay_etiketleri"]) >= 4
    assert all("etiket" in e and "hafta" in e for e in grid["ay_etiketleri"])


def test_ay_etiketleri_ust_uste_binmez():
    """Ardışık ay etiketleri çok yakınsa görsel olarak çakışıyordu."""
    grid = heatmap.yil_gridi([], [], bitis=dt.date(2026, 3, 20), hafta_sayisi=53)
    haftalar = [e["hafta"] for e in grid["ay_etiketleri"]]
    for onceki, sonraki in zip(haftalar, haftalar[1:]):
        assert sonraki - onceki >= 3, f"Etiketler çok yakın: {haftalar}"
