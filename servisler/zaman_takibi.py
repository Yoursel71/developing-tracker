from datetime import datetime

from depo import json_deposu

KATEGORILER = ["Python", "GitHub çalışması", "Sertifika kursu", "Diğer"]


def oturum_baslat(kategori):
    veri = json_deposu.oku()
    if veri["aktif_oturum"] is not None:
        raise ValueError("Zaten aktif bir oturum var.")
    veri["aktif_oturum"] = {
        "kategori": kategori,
        "baslangic": datetime.now().isoformat(timespec="seconds"),
    }
    json_deposu.yaz(veri)
    return veri["aktif_oturum"]


def oturum_durdur():
    veri = json_deposu.oku()
    aktif = veri["aktif_oturum"]
    if aktif is None:
        raise ValueError("Aktif oturum yok.")
    baslangic = datetime.fromisoformat(aktif["baslangic"])
    bitis = datetime.now()
    sure_dakika = round((bitis - baslangic).total_seconds() / 60, 1)
    oturum = {
        "tarih": baslangic.date().isoformat(),
        "kategori": aktif["kategori"],
        "baslangic": baslangic.strftime("%H:%M:%S"),
        "bitis": bitis.strftime("%H:%M:%S"),
        "sure_dakika": sure_dakika,
    }
    veri["oturumlar"].append(oturum)
    veri["aktif_oturum"] = None
    json_deposu.yaz(veri)
    return oturum


def aktif_oturumu_getir():
    return json_deposu.oku()["aktif_oturum"]
