"""İstatistikler, seri (streak) ve bitiş tahmini.

Eski sürümdeki ortalama hesabı böleni her zaman sabit tutuyordu; dün
kurulmuş bir uygulamada 3 saatlik çalışma "6 dk/gün" görünüyor ve tahmin
"78 hafta" diyordu. Burada bölen, verinin gerçek yaşıyla sınırlanır.
"""

import datetime as dt
from collections import defaultdict

import config

GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
# İlk üç harf alınırsa Pazartesi/Pazar ve Cuma/Cumartesi çakışır.
KISA_GUN_ADLARI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


# --- Yardımcılar ------------------------------------------------------------

def _tarih(oturum):
    try:
        return dt.date.fromisoformat(oturum["tarih"])
    except (KeyError, TypeError, ValueError):
        return None


def gunluk_toplamlar(oturumlar):
    toplamlar = defaultdict(float)
    for oturum in oturumlar:
        gun = _tarih(oturum)
        if gun:
            toplamlar[gun] += oturum.get("sure_dakika", 0)
    return dict(toplamlar)


def ilk_gun(oturumlar):
    gunler = [g for g in (_tarih(o) for o in oturumlar) if g]
    return min(gunler) if gunler else None


def veri_yasi_gun(oturumlar, bugun=None):
    """İlk oturumdan bugüne kaç takvim günü geçtiği (en az 1)."""
    bugun = bugun or dt.date.today()
    ilk = ilk_gun(oturumlar)
    if ilk is None:
        return 0
    return max((bugun - ilk).days + 1, 1)


def ortalama_dakika(oturumlar, pencere_gun=None, bugun=None):
    """Takvim günü başına ortalama dakika.

    Bölen, istenen pencere ile verinin gerçek yaşının küçüğüdür; böylece
    yeni kullanıcıda ortalama yapay olarak düşük çıkmaz.
    """
    bugun = bugun or dt.date.today()
    yas = veri_yasi_gun(oturumlar, bugun)
    if yas == 0:
        return 0.0

    if pencere_gun is None:
        bolen = yas
        toplam = sum(o.get("sure_dakika", 0) for o in oturumlar)
    else:
        bolen = min(pencere_gun, yas)
        sinir = bugun - dt.timedelta(days=pencere_gun - 1)
        toplam = sum(
            o.get("sure_dakika", 0)
            for o in oturumlar
            if (_tarih(o) or dt.date.min) >= sinir
        )
    return toplam / bolen if bolen else 0.0


def calisilan_gun_basina_ortalama(oturumlar):
    toplamlar = gunluk_toplamlar(oturumlar)
    dolu = [d for d in toplamlar.values() if d > 0]
    return sum(dolu) / len(dolu) if dolu else 0.0


# --- Seri (streak) ----------------------------------------------------------

def seri_hesapla(oturumlar, esik_dakika=None, bugun=None):
    """Ardışık çalışma günü sayısı.

    Bugün henüz eşiği geçmediyse seri kopmuş sayılmaz; dünden geriye doğru
    sayılır ve ``bugun_tamam`` False döner, böylece arayüz "serini sürdür"
    diyebilir.
    """
    esik = config.VARSAYILAN_SERI_ESIGI_DAKIKA if esik_dakika is None else esik_dakika
    bugun = bugun or dt.date.today()
    toplamlar = gunluk_toplamlar(oturumlar)
    dolu_gunler = {gun for gun, dakika in toplamlar.items() if dakika >= esik}

    bugun_tamam = bugun in dolu_gunler

    guncel = 0
    imlec = bugun if bugun_tamam else bugun - dt.timedelta(days=1)
    while imlec in dolu_gunler:
        guncel += 1
        imlec -= dt.timedelta(days=1)

    en_uzun = 0
    mevcut = 0
    for gun in sorted(dolu_gunler):
        if mevcut and (gun - onceki).days == 1:
            mevcut += 1
        else:
            mevcut = 1
        onceki = gun
        en_uzun = max(en_uzun, mevcut)

    return {
        "guncel": guncel,
        "en_uzun": en_uzun,
        "bugun_tamam": bugun_tamam,
        "esik_dakika": esik,
        "bugun_dakika": round(toplamlar.get(bugun, 0), 1),
    }


# --- Dağılımlar -------------------------------------------------------------

def kategori_dagilimi(oturumlar):
    toplamlar = defaultdict(float)
    for oturum in oturumlar:
        toplamlar[oturum.get("kategori", "Diğer")] += oturum.get("sure_dakika", 0)
    toplam = sum(toplamlar.values())
    return [
        {
            "kategori": kategori,
            "dakika": round(dakika, 1),
            "yuzde": round(dakika / toplam * 100, 1) if toplam else 0,
        }
        for kategori, dakika in sorted(toplamlar.items(), key=lambda x: -x[1])
    ]


def haftanin_gunleri_dagilimi(oturumlar):
    toplamlar = [0.0] * 7
    gun_sayilari = [0] * 7
    gunluk = gunluk_toplamlar(oturumlar)
    for gun, dakika in gunluk.items():
        toplamlar[gun.weekday()] += dakika
        gun_sayilari[gun.weekday()] += 1
    return [
        {
            "gun": GUN_ADLARI[i],
            "kisa": KISA_GUN_ADLARI[i],
            "dakika": round(toplamlar[i], 1),
            "ortalama": round(toplamlar[i] / gun_sayilari[i], 1) if gun_sayilari[i] else 0,
        }
        for i in range(7)
    ]


def saat_dagilimi(oturumlar):
    """Oturum başlangıç saatine göre dağılım."""
    toplamlar = [0.0] * 24
    for oturum in oturumlar:
        baslangic = oturum.get("baslangic") or ""
        if len(baslangic) >= 2 and baslangic[:2].isdigit():
            saat = int(baslangic[:2])
            if 0 <= saat < 24:
                toplamlar[saat] += oturum.get("sure_dakika", 0)
    return [{"saat": i, "dakika": round(toplamlar[i], 1)} for i in range(24)]


def gunluk_trend(oturumlar, gun_sayisi=30, bugun=None):
    bugun = bugun or dt.date.today()
    toplamlar = gunluk_toplamlar(oturumlar)
    return [
        {
            "tarih": (bugun - dt.timedelta(days=gun_sayisi - 1 - i)).isoformat(),
            "dakika": round(toplamlar.get(bugun - dt.timedelta(days=gun_sayisi - 1 - i), 0), 1),
        }
        for i in range(gun_sayisi)
    ]


def en_cok_calisilan_gun(oturumlar):
    toplamlar = gunluk_toplamlar(oturumlar)
    if not toplamlar:
        return None
    gun = max(toplamlar, key=toplamlar.get)
    return {"tarih": gun.isoformat(), "dakika": round(toplamlar[gun], 1)}


# --- Tahmin -----------------------------------------------------------------

def _haftalik_toplamlar(oturumlar):
    haftalar = defaultdict(float)
    for oturum in oturumlar:
        gun = _tarih(oturum)
        if gun:
            hafta_basi = gun - dt.timedelta(days=gun.weekday())
            haftalar[hafta_basi] += oturum.get("sure_dakika", 0)
    return haftalar


def _standart_sapma(degerler):
    if len(degerler) < 2:
        return 0.0
    ortalama = sum(degerler) / len(degerler)
    varyans = sum((d - ortalama) ** 2 for d in degerler) / (len(degerler) - 1)
    return varyans ** 0.5


def tempo_hesapla(oturumlar, bugun=None):
    """Son dönemi ağırlıklandıran günlük tempo (dakika/gün)."""
    bugun = bugun or dt.date.today()
    yas = veri_yasi_gun(oturumlar, bugun)
    if yas == 0:
        return 0.0
    son_14 = ortalama_dakika(oturumlar, 14, bugun)
    son_30 = ortalama_dakika(oturumlar, 30, bugun)
    if yas <= 14:
        return son_14
    return son_14 * 0.6 + son_30 * 0.4


def bitis_tahmini(oturumlar, toplam_hedef_saat, haftalik_hedef_saat, bugun=None):
    """İki senaryolu, aralıklı ve koruyuculu bitiş tahmini."""
    bugun = bugun or dt.date.today()
    toplam_dakika = sum(o.get("sure_dakika", 0) for o in oturumlar)
    hedef_dakika = max(toplam_hedef_saat, 0) * 60
    kalan = hedef_dakika - toplam_dakika

    sonuc = {
        "toplam_saat": round(toplam_dakika / 60, 1),
        "hedef_saat": round(hedef_dakika / 60, 1),
        "kalan_saat": round(max(kalan, 0) / 60, 1),
        "yuzde": round(min(toplam_dakika / hedef_dakika * 100, 100), 1) if hedef_dakika else 0,
        "tamamlandi": hedef_dakika > 0 and kalan <= 0,
        "durum": "tamam",
        "mesaj": "",
        "tempo_dakika": 0,
        "hafta": None,
        "iyimser_hafta": None,
        "kotumser_hafta": None,
        "hedef_temposuyla_hafta": None,
        "tahmini_tarih": None,
    }

    if hedef_dakika <= 0:
        sonuc["durum"] = "hedef_yok"
        sonuc["mesaj"] = "Önce bir toplam hedef belirle."
        return sonuc

    if sonuc["tamamlandi"]:
        sonuc["mesaj"] = "Hedefe ulaştın!"
        return sonuc

    # Haftalık hedefe göre senaryo (tempodan bağımsız hesaplanabilir).
    if haftalik_hedef_saat and haftalik_hedef_saat > 0:
        sonuc["hedef_temposuyla_hafta"] = round(kalan / (haftalik_hedef_saat * 60), 1)

    yas = veri_yasi_gun(oturumlar, bugun)
    if yas < 7:
        sonuc["durum"] = "veri_az"
        sonuc["mesaj"] = "Güvenilir tahmin için en az 1 haftalık veri gerekiyor."
        return sonuc

    tempo = tempo_hesapla(oturumlar, bugun)
    sonuc["tempo_dakika"] = round(tempo, 1)
    if tempo < 5:
        sonuc["durum"] = "tempo_dusuk"
        sonuc["mesaj"] = "Tempo çok düşük; bu hızda tahmin güvenilir değil."
        return sonuc

    gun = kalan / tempo
    sonuc["hafta"] = round(gun / 7, 1)
    sonuc["tahmini_tarih"] = (bugun + dt.timedelta(days=round(gun))).isoformat()

    haftaliklar = sorted(_haftalik_toplamlar(oturumlar).items())
    son_haftalar = [d for _, d in haftaliklar[-8:]]
    sapma = _standart_sapma(son_haftalar)
    haftalik_tempo = tempo * 7
    if sapma > 0 and haftalik_tempo > 0:
        iyimser_tempo = haftalik_tempo + sapma * 0.5
        kotumser_tempo = max(haftalik_tempo - sapma * 0.5, 1)
        sonuc["iyimser_hafta"] = round(kalan / iyimser_tempo, 1)
        sonuc["kotumser_hafta"] = round(kalan / kotumser_tempo, 1)

    return sonuc


# --- Toplu hesap ------------------------------------------------------------

def istatistikleri_hesapla(veri, bugun=None):
    bugun = bugun or dt.date.today()
    oturumlar = veri["oturumlar"]
    ayarlar = veri["ayarlar"]
    hedefler = veri["hedefler"]

    return {
        "toplam_saat": round(sum(o.get("sure_dakika", 0) for o in oturumlar) / 60, 1),
        "oturum_sayisi": len(oturumlar),
        "ortalama_tum_zamanlar": round(ortalama_dakika(oturumlar, None, bugun), 1),
        "ortalama_son_7_gun": round(ortalama_dakika(oturumlar, 7, bugun), 1),
        "ortalama_son_30_gun": round(ortalama_dakika(oturumlar, 30, bugun), 1),
        "calisilan_gun_ortalamasi": round(calisilan_gun_basina_ortalama(oturumlar), 1),
        "aktif_gun_sayisi": len([d for d in gunluk_toplamlar(oturumlar).values() if d > 0]),
        "en_cok_calisilan_gun": en_cok_calisilan_gun(oturumlar),
        "kategori_dagilimi": kategori_dagilimi(oturumlar),
        "haftanin_gunleri": haftanin_gunleri_dagilimi(oturumlar),
        "saat_dagilimi": saat_dagilimi(oturumlar),
        "gunluk_trend": gunluk_trend(oturumlar, 30, bugun),
        "seri": seri_hesapla(oturumlar, ayarlar.get("seri_esigi_dakika"), bugun),
        "tahmin": bitis_tahmini(
            oturumlar,
            hedefler.get("toplam_hedef_saat", 0),
            hedefler.get("haftalik_saat", 0),
            bugun,
        ),
        "veri_var": bool(oturumlar),
    }
