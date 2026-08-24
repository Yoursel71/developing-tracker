"""İstatistikler: ortalama böleni, seri, tahmin koruyucuları."""

import datetime as dt

import pytest

from servisler import istatistikler


def oturum(tarih, dakika, kategori="Python", baslangic="20:00:00"):
    return {
        "id": tarih + str(dakika), "tarih": tarih, "kategori": kategori,
        "baslangic": baslangic, "bitis": "21:00:00", "sure_dakika": dakika,
    }


BUGUN = dt.date(2026, 3, 20)


# --- Ortalamalar ------------------------------------------------------------

def test_yeni_kullanicida_ortalama_sisirilmez():
    """Dün kurulmuş uygulamada 180 dk, 180/30=6 dk/gün göstermemeli."""
    oturumlar = [oturum("2026-03-19", 180)]
    ortalama = istatistikler.ortalama_dakika(oturumlar, 30, BUGUN)
    assert ortalama == pytest.approx(90, abs=1)  # 180 / 2 gün


def test_pencere_veri_yasindan_kucukse_pencere_kullanilir():
    oturumlar = [oturum("2026-01-01", 60), oturum("2026-03-19", 140)]
    # Veri yaşı ~79 gün; 7 günlük pencerede bölen 7 olmalı
    assert istatistikler.ortalama_dakika(oturumlar, 7, BUGUN) == pytest.approx(20, abs=0.5)


def test_veri_yoksa_ortalama_sifir():
    assert istatistikler.ortalama_dakika([], 30, BUGUN) == 0.0
    assert istatistikler.veri_yasi_gun([], BUGUN) == 0


def test_calisilan_gun_ortalamasi_bos_gunleri_saymaz():
    oturumlar = [oturum("2026-03-18", 60), oturum("2026-03-20", 120)]
    assert istatistikler.calisilan_gun_basina_ortalama(oturumlar) == 90.0


# --- Seri -------------------------------------------------------------------

def test_ardisik_gunler_seri_olur():
    oturumlar = [oturum(f"2026-03-{g}", 60) for g in (18, 19, 20)]
    seri = istatistikler.seri_hesapla(oturumlar, 15, BUGUN)
    assert seri["guncel"] == 3
    assert seri["bugun_tamam"] is True


def test_bugun_calisilmadiysa_seri_kopmaz():
    """Akşam 6'da seri sıfır görünmemeli — dünden geriye sayılır."""
    oturumlar = [oturum(f"2026-03-{g}", 60) for g in (17, 18, 19)]
    seri = istatistikler.seri_hesapla(oturumlar, 15, BUGUN)
    assert seri["guncel"] == 3
    assert seri["bugun_tamam"] is False


def test_esigin_altinda_kalan_gun_seriye_girmez():
    oturumlar = [oturum("2026-03-19", 60), oturum("2026-03-20", 5)]
    seri = istatistikler.seri_hesapla(oturumlar, 15, BUGUN)
    assert seri["bugun_tamam"] is False
    assert seri["guncel"] == 1


def test_bosluk_seriyi_koparir():
    oturumlar = [oturum("2026-03-15", 60), oturum("2026-03-19", 60), oturum("2026-03-20", 60)]
    seri = istatistikler.seri_hesapla(oturumlar, 15, BUGUN)
    assert seri["guncel"] == 2
    assert seri["en_uzun"] == 2


def test_en_uzun_seri_gecmisten_gelir():
    gunler = [f"2026-03-{g:02d}" for g in (1, 2, 3, 4, 5)] + ["2026-03-20"]
    oturumlar = [oturum(g, 60) for g in gunler]
    seri = istatistikler.seri_hesapla(oturumlar, 15, BUGUN)
    assert seri["en_uzun"] == 5
    assert seri["guncel"] == 1


def test_bos_veride_seri_sifir():
    seri = istatistikler.seri_hesapla([], 15, BUGUN)
    assert seri["guncel"] == 0 and seri["en_uzun"] == 0


# --- Tahmin -----------------------------------------------------------------

def test_veri_azken_tahmin_yapilmaz():
    """İlk gün '78 hafta kaldı' gibi saçma bir sayı gösterilmemeli."""
    oturumlar = [oturum("2026-03-19", 180)]
    tahmin = istatistikler.bitis_tahmini(oturumlar, 135, 10, BUGUN)
    assert tahmin["durum"] == "veri_az"
    assert tahmin["hafta"] is None
    assert "1 hafta" in tahmin["mesaj"]


def test_veri_azken_bile_hedef_senaryosu_verilir():
    oturumlar = [oturum("2026-03-19", 180)]
    tahmin = istatistikler.bitis_tahmini(oturumlar, 135, 10, BUGUN)
    assert tahmin["hedef_temposuyla_hafta"] is not None


def test_yeterli_veriyle_tahmin_uretilir():
    oturumlar = [
        oturum((BUGUN - dt.timedelta(days=i)).isoformat(), 60) for i in range(30)
    ]
    tahmin = istatistikler.bitis_tahmini(oturumlar, 100, 7, BUGUN)
    assert tahmin["durum"] == "tamam"
    assert tahmin["hafta"] > 0
    assert tahmin["tahmini_tarih"]
    assert tahmin["tempo_dakika"] == pytest.approx(60, abs=2)


def test_dusuk_tempoda_tahmin_guvenilir_degil():
    oturumlar = [
        oturum((BUGUN - dt.timedelta(days=i * 10)).isoformat(), 10) for i in range(4)
    ]
    tahmin = istatistikler.bitis_tahmini(oturumlar, 135, 10, BUGUN)
    assert tahmin["durum"] == "tempo_dusuk"


def test_hedefe_ulasilinca_tamamlandi():
    oturumlar = [oturum("2026-03-19", 6000)]
    tahmin = istatistikler.bitis_tahmini(oturumlar, 100, 10, BUGUN)
    assert tahmin["tamamlandi"] is True
    assert tahmin["kalan_saat"] == 0


def test_negatif_hedef_tamamlandi_gostermez():
    """Negatif hedef 'Hedef tamamlandı!' yazdırıyordu."""
    tahmin = istatistikler.bitis_tahmini([], 0, 10, BUGUN)
    assert tahmin["durum"] == "hedef_yok"
    assert tahmin["tamamlandi"] is False


def test_yuzde_yuzu_asmaz():
    oturumlar = [oturum("2026-03-19", 12000)]
    tahmin = istatistikler.bitis_tahmini(oturumlar, 100, 10, BUGUN)
    assert tahmin["yuzde"] == 100


# --- Dağılımlar -------------------------------------------------------------

def test_kategori_dagilimi_yuzdeleri():
    oturumlar = [oturum("2026-03-19", 60, "Python"), oturum("2026-03-19", 20, "Diğer")]
    dagilim = istatistikler.kategori_dagilimi(oturumlar)
    assert dagilim[0]["kategori"] == "Python"
    assert dagilim[0]["yuzde"] == 75.0


def test_haftanin_gunleri_dogru_gune_dusiyor():
    # 2026-03-20 Cuma
    dagilim = istatistikler.haftanin_gunleri_dagilimi([oturum("2026-03-20", 90)])
    cuma = [g for g in dagilim if g["gun"] == "Cuma"][0]
    assert cuma["dakika"] == 90


def test_saat_dagilimi_baslangictan_okur():
    oturumlar = [oturum("2026-03-19", 60, baslangic="21:30:00")]
    dagilim = istatistikler.saat_dagilimi(oturumlar)
    assert dagilim[21]["dakika"] == 60


def test_saat_dagilimi_bos_baslangici_yok_sayar():
    oturumlar = [{"tarih": "2026-03-19", "kategori": "Python", "sure_dakika": 60, "baslangic": ""}]
    assert sum(d["dakika"] for d in istatistikler.saat_dagilimi(oturumlar)) == 0


def test_gunluk_trend_uzunlugu():
    trend = istatistikler.gunluk_trend([oturum("2026-03-20", 60)], 30, BUGUN)
    assert len(trend) == 30
    assert trend[-1]["tarih"] == BUGUN.isoformat()
    assert trend[-1]["dakika"] == 60


def test_bozuk_tarih_cokmez():
    oturumlar = [{"tarih": "abc", "kategori": "Python", "sure_dakika": 60}]
    assert istatistikler.gunluk_toplamlar(oturumlar) == {}
    assert istatistikler.en_cok_calisilan_gun(oturumlar) is None


def test_kisa_gun_adlari_cakismaz():
    """Pazartesi/Pazar ve Cuma/Cumartesi ilk üç harfte çakışıyordu."""
    kisalar = [g["kisa"] for g in istatistikler.haftanin_gunleri_dagilimi([])]
    assert len(set(kisalar)) == 7, f"Çakışan kısaltma: {kisalar}"
    assert kisalar == ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


# --- Rekorlar ve hafta karşılaştırması --------------------------------------

def test_en_uzun_oturum():
    oturumlar = [oturum("2026-03-18", 45), oturum("2026-03-19", 210), oturum("2026-03-20", 60)]
    en_uzun = istatistikler.en_uzun_oturum(oturumlar)
    assert en_uzun["dakika"] == 210
    assert en_uzun["tarih"] == "2026-03-19"


def test_en_uzun_oturum_bos_veride_none():
    assert istatistikler.en_uzun_oturum([]) is None


def test_hafta_karsilastirmasi_ayni_gune_kadar_kiyaslar():
    """Salı günü tam bir haftayla kıyaslamak yanıltıcı olurdu."""
    # BUGUN = 2026-03-20 Cuma. Bu hafta 16-22, geçen hafta 09-15.
    oturumlar = [
        oturum("2026-03-16", 60), oturum("2026-03-17", 60),   # bu hafta: 120
        oturum("2026-03-09", 30), oturum("2026-03-10", 30),   # geçen hafta ilk 2 gün: 60
        oturum("2026-03-14", 120),                            # geçen hafta Cmt (bugünden sonra)
    ]
    k = istatistikler.hafta_karsilastirmasi(oturumlar, BUGUN)

    assert k["bu_hafta_dakika"] == 120
    assert k["gecen_hafta_dakika"] == 180
    assert k["gecen_hafta_ayni_gun_dakika"] == 60
    assert k["degisim_yuzde"] == 100.0
    assert k["yonu"] == "artis"


def test_hafta_karsilastirmasi_veri_yoksa_yuzde_none():
    k = istatistikler.hafta_karsilastirmasi([oturum("2026-03-16", 60)], BUGUN)
    assert k["degisim_yuzde"] is None
    assert k["yonu"] == "veri_yok"


def test_son_haftalar_uzunluk_ve_isaret():
    haftalar = istatistikler.son_haftalar([oturum("2026-03-16", 90)], 8, BUGUN)
    assert len(haftalar) == 8
    assert haftalar[-1]["bu_hafta"] is True
    assert haftalar[-1]["dakika"] == 90
