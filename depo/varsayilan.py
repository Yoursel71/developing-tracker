"""Veri şemasının güncel sürümü ve varsayılan içeriği."""

import uuid

import config

SEMA_SURUMU = 3


def _varsayilan_kategoriler():
    """Kategoriler ilk dosya oluşturulurken hazır olmalı.

    Kurulum sihirbazı girdileri kategori listesine karşı doğruluyor; liste
    kurulum tamamlanınca oluşturulsaydı sihirbaz kendi seçeneklerini
    reddederdi.
    """
    palet = config.KATEGORI_PALETI
    return [
        {"id": uuid.uuid4().hex, "ad": ad, "renk": palet[i % len(palet)], "sira": i}
        for i, ad in enumerate(config.VARSAYILAN_KATEGORILER)
    ]


def varsayilan_veri():
    return {
        "surum": SEMA_SURUMU,
        "kurulum_tamamlandi": False,
        "oturumlar": [],
        "aktif_oturumlar": {},
        "kategoriler": _varsayilan_kategoriler(),
        "hedef_gecmisi": [],
        "hedefler": {
            "haftalik_saat": config.VARSAYILAN_HAFTALIK_HEDEF_SAAT,
            "toplam_hedef_saat": config.VARSAYILAN_TOPLAM_HEDEF_SAAT,
            "son_bildirim_tarihi": None,
        },
        "github": {
            "kullanici": "",
            "son_cekilen_etkinlikler": [],
            "son_senkron": None,
        },
        "izleme": {
            "editorler": [],
            "siteler": [],
            "ertelemeler": {},
        },
        "yol_haritasi": [],
        "ayarlar": {
            "tema": "koyu",
            "bosta_esigi_dakika": config.VARSAYILAN_BOSTA_ESIGI_DAKIKA,
            "seri_esigi_dakika": config.VARSAYILAN_SERI_ESIGI_DAKIKA,
            "tepsiye_indir": True,
            "windows_ile_baslat": False,
            "bildirimler_acik": True,
            "mola_hatirlatici": True,
            "motivasyon_sozu": False,
            "pomodoro_acik": False,
        },
        "pomodoro": {
            "aktif": False,
            "asama": "calisma",
            "baslangic": None,
            "tur": 0,
        },
    }


def _sozluk_tamamla(hedef, varsayilan):
    """Eksik anahtarları varsayılandan tamamlar (yinelemeli)."""
    for anahtar, deger in varsayilan.items():
        if anahtar not in hedef:
            hedef[anahtar] = deger
        elif isinstance(deger, dict) and isinstance(hedef.get(anahtar), dict):
            _sozluk_tamamla(hedef[anahtar], deger)


def normallestir(veri):
    """Eksik/bozuk alanları güvenli varsayılanlarla tamamlar.

    Kod genelinde ``veri["..."]`` doğrudan erişimleri güvenli olsun diye her
    okuma bu fonksiyondan geçer.
    """
    if not isinstance(veri, dict):
        return varsayilan_veri()

    _sozluk_tamamla(veri, varsayilan_veri())

    if not isinstance(veri.get("oturumlar"), list):
        veri["oturumlar"] = []
    if not isinstance(veri.get("aktif_oturumlar"), dict):
        veri["aktif_oturumlar"] = {}
    if not isinstance(veri.get("yol_haritasi"), list):
        veri["yol_haritasi"] = []
    if not isinstance(veri.get("kategoriler"), list) or not veri["kategoriler"]:
        veri["kategoriler"] = _varsayilan_kategoriler()
    if not isinstance(veri.get("hedef_gecmisi"), list):
        veri["hedef_gecmisi"] = []
    for alan in ("editorler", "siteler"):
        if not isinstance(veri["izleme"].get(alan), list):
            veri["izleme"][alan] = []
    if not isinstance(veri["izleme"].get("ertelemeler"), dict):
        veri["izleme"]["ertelemeler"] = {}
    if not isinstance(veri["github"].get("son_cekilen_etkinlikler"), list):
        veri["github"]["son_cekilen_etkinlikler"] = []

    return veri
