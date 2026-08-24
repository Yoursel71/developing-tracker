"""Pomodoro odak zamanlayıcısı.

Otomatik süre takibiyle **çakışmaz**: pomodoro yalnızca ritim tutar
(25 dk çalış / 5 dk mola) ve aşama değişince bildirim gönderir. Süre ölçümü
her zaman izleme motorunun işidir — burada ayrı bir oturum açılmaz, aksi
hâlde aynı çalışma iki kez sayılırdı.
"""

import datetime as dt

import config
from depo import json_deposu
from servisler import zaman_takibi


def _asama_suresi(asama, tur):
    if asama == "calisma":
        return config.POMODORO_CALISMA_DAKIKA
    if tur > 0 and tur % config.POMODORO_UZUN_MOLA_ARALIGI == 0:
        return config.POMODORO_UZUN_MOLA_DAKIKA
    return config.POMODORO_KISA_MOLA_DAKIKA


def baslat():
    with json_deposu.guncelle() as veri:
        veri["pomodoro"] = {
            "aktif": True,
            "asama": "calisma",
            "baslangic": zaman_takibi.simdi().isoformat(),
            "tur": 0,
        }
        return veri["pomodoro"]


def durdur():
    with json_deposu.guncelle() as veri:
        veri["pomodoro"] = {
            "aktif": False, "asama": "calisma", "baslangic": None, "tur": 0
        }
        return veri["pomodoro"]


def atla():
    """Mevcut aşamayı bitirip sonrakine geçer."""
    with json_deposu.guncelle() as veri:
        return _sonraki_asamaya_gec(veri, zaman_takibi.simdi())


def _sonraki_asamaya_gec(veri, su_an):
    pomodoro = veri["pomodoro"]
    if pomodoro["asama"] == "calisma":
        pomodoro["tur"] = pomodoro.get("tur", 0) + 1
        pomodoro["asama"] = "mola"
    else:
        pomodoro["asama"] = "calisma"
    pomodoro["baslangic"] = su_an.isoformat()
    return pomodoro


def durum(veri=None, su_an=None):
    """Arayüzün gösterdiği canlı pomodoro durumu."""
    veri = veri if veri is not None else json_deposu.oku()
    su_an = su_an or zaman_takibi.simdi()
    pomodoro = veri["pomodoro"]

    if not pomodoro.get("aktif"):
        return {
            "aktif": False, "asama": "calisma", "tur": 0,
            "kalan_saniye": 0, "toplam_saniye": config.POMODORO_CALISMA_DAKIKA * 60,
        }

    baslangic = zaman_takibi.zaman_coz(pomodoro.get("baslangic")) or su_an
    toplam = _asama_suresi(pomodoro["asama"], pomodoro.get("tur", 0)) * 60
    gecen = max((su_an - baslangic).total_seconds(), 0)
    return {
        "aktif": True,
        "asama": pomodoro["asama"],
        "asama_metni": "Çalışma" if pomodoro["asama"] == "calisma" else "Mola",
        "tur": pomodoro.get("tur", 0),
        "kalan_saniye": int(max(toplam - gecen, 0)),
        "toplam_saniye": int(toplam),
        "doldu": gecen >= toplam,
    }


def kontrol_et(su_an=None):
    """Aşama süresi dolduysa sonrakine geçirir. Bildirim metni döner."""
    su_an = su_an or zaman_takibi.simdi()

    with json_deposu.belki_guncelle() as (veri, isaret):
        pomodoro = veri["pomodoro"]
        if not pomodoro.get("aktif"):
            return None

        baslangic = zaman_takibi.zaman_coz(pomodoro.get("baslangic"))
        if baslangic is None:
            pomodoro["baslangic"] = su_an.isoformat()
            isaret()
            return None

        toplam = _asama_suresi(pomodoro["asama"], pomodoro.get("tur", 0)) * 60
        if (su_an - baslangic).total_seconds() < toplam:
            return None

        biten_asama = pomodoro["asama"]
        _sonraki_asamaya_gec(veri, su_an)
        yeni_sure = _asama_suresi(pomodoro["asama"], pomodoro.get("tur", 0))
        isaret()

    if biten_asama == "calisma":
        return ("Pomodoro: mola zamanı", f"{yeni_sure} dakika ara ver.")
    return ("Pomodoro: çalışma zamanı", f"{yeni_sure} dakikalık tur başlıyor.")
