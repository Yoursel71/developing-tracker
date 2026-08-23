from collections import defaultdict
from datetime import date, timedelta

from servisler import github_entegrasyon


def _ortalama_dakika_gun(oturumlar, gun_sayisi=None):
    if not oturumlar:
        return 0.0
    if gun_sayisi is None:
        ilk_tarih = min(date.fromisoformat(o["tarih"]) for o in oturumlar)
        gun_sayisi = max((date.today() - ilk_tarih).days + 1, 1)
        toplam = sum(o["sure_dakika"] for o in oturumlar)
    else:
        sinir = date.today() - timedelta(days=gun_sayisi - 1)
        toplam = sum(
            o["sure_dakika"] for o in oturumlar if date.fromisoformat(o["tarih"]) >= sinir
        )
    return toplam / gun_sayisi


def en_cok_calisilan_gun(oturumlar):
    toplamlar = defaultdict(float)
    for o in oturumlar:
        toplamlar[o["tarih"]] += o["sure_dakika"]
    if not toplamlar:
        return None
    tarih = max(toplamlar, key=toplamlar.get)
    return {"tarih": tarih, "dakika": toplamlar[tarih]}


def kategori_dagilimi(oturumlar):
    toplamlar = defaultdict(float)
    for o in oturumlar:
        toplamlar[o["kategori"]] += o["sure_dakika"]
    return dict(toplamlar)


def eta_tahmini(oturumlar, toplam_hedef_saat):
    toplam_biriken_dakika = sum(o["sure_dakika"] for o in oturumlar)
    hedef_dakika = toplam_hedef_saat * 60
    kalan_dakika = hedef_dakika - toplam_biriken_dakika

    if kalan_dakika <= 0:
        return {"tamamlandi": True, "kalan_saat": 0, "tahmini_hafta": 0}

    gunluk_tempo = _ortalama_dakika_gun(oturumlar, gun_sayisi=30)
    if gunluk_tempo <= 0:
        gunluk_tempo = _ortalama_dakika_gun(oturumlar)
    if gunluk_tempo <= 0:
        return {"tamamlandi": False, "kalan_saat": round(kalan_dakika / 60, 1), "tahmini_hafta": None}

    tahmini_gun = kalan_dakika / gunluk_tempo
    return {
        "tamamlandi": False,
        "kalan_saat": round(kalan_dakika / 60, 1),
        "tahmini_hafta": round(tahmini_gun / 7, 1),
    }


def istatistikleri_hesapla(veri):
    oturumlar = veri["oturumlar"]
    etkinlikler = veri["github"].get("son_cekilen_etkinlikler", [])
    return {
        "ortalama_tum_zamanlar": round(_ortalama_dakika_gun(oturumlar), 1),
        "ortalama_son_7_gun": round(_ortalama_dakika_gun(oturumlar, 7), 1),
        "ortalama_son_30_gun": round(_ortalama_dakika_gun(oturumlar, 30), 1),
        "en_cok_calisilan_gun": en_cok_calisilan_gun(oturumlar),
        "kategori_dagilimi": kategori_dagilimi(oturumlar),
        "en_aktif_repo": github_entegrasyon.en_aktif_repo(etkinlikler),
        "eta": eta_tahmini(oturumlar, veri["hedefler"]["toplam_hedef_saat"]),
    }
