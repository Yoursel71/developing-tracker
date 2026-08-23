from datetime import datetime

from depo import json_deposu

KATEGORILER = ["Python", "GitHub çalışması", "Sertifika kursu", "Diğer"]


def oturum_baslat(kategori, kaynak="manuel"):
    with json_deposu.guncelle() as veri:
        if kategori in veri["aktif_oturumlar"]:
            raise ValueError(f"'{kategori}' için zaten aktif bir oturum var.")
        veri["aktif_oturumlar"][kategori] = {
            "baslangic": datetime.now().isoformat(timespec="seconds"),
            "kaynak": kaynak,
            "kayip_zamani": None,
        }
        return veri["aktif_oturumlar"][kategori]


def oturum_durdur(kategori):
    with json_deposu.guncelle() as veri:
        aktif = veri["aktif_oturumlar"].get(kategori)
        if aktif is None:
            raise ValueError(f"'{kategori}' için aktif oturum yok.")
        baslangic = datetime.fromisoformat(aktif["baslangic"])
        bitis = datetime.now()
        sure_dakika = round((bitis - baslangic).total_seconds() / 60, 1)
        oturum = {
            "tarih": baslangic.date().isoformat(),
            "kategori": kategori,
            "baslangic": baslangic.strftime("%H:%M:%S"),
            "bitis": bitis.strftime("%H:%M:%S"),
            "sure_dakika": sure_dakika,
        }
        veri["oturumlar"].append(oturum)
        del veri["aktif_oturumlar"][kategori]
        return oturum


def tum_oturumlari_durdur():
    """Uygulama kapanırken açık kalan tüm oturumları kapatır."""
    kategoriler = list(aktif_oturumlari_getir().keys())
    for kategori in kategoriler:
        oturum_durdur(kategori)
    return kategoriler


def aktif_oturumlari_getir():
    return json_deposu.oku()["aktif_oturumlar"]
