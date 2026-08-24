"""Haftalık/toplam hedefler, ilerleme ve hatırlatmalar."""

import datetime as dt
import logging

from depo import json_deposu
from servisler import bildirim, istatistikler

logger = logging.getLogger(__name__)


def hafta_baslangici(gun=None):
    gun = gun or dt.date.today()
    return gun - dt.timedelta(days=gun.weekday())


def haftalik_toplam_dakika(oturumlar, referans_tarih=None):
    baslangic = hafta_baslangici(referans_tarih)
    bitis = baslangic + dt.timedelta(days=6)
    toplam = 0.0
    for oturum in oturumlar:
        try:
            gun = dt.date.fromisoformat(oturum["tarih"])
        except (KeyError, TypeError, ValueError):
            continue
        if baslangic <= gun <= bitis:
            toplam += oturum.get("sure_dakika", 0)
    return toplam


def haftalik_ilerleme(veri, bugun=None):
    bugun = bugun or dt.date.today()
    hedef_saat = veri["hedefler"].get("haftalik_saat", 0) or 0
    dakika = haftalik_toplam_dakika(veri["oturumlar"], bugun)
    hedef_dakika = hedef_saat * 60
    yuzde = round(dakika / hedef_dakika * 100, 1) if hedef_dakika else 0
    return {
        "saat": round(dakika / 60, 1),
        "hedef_saat": hedef_saat,
        "dakika": round(dakika, 1),
        "yuzde": yuzde,
        # Çubuk tavan yapar ama aşım ayrıca gösterilir; hedefi %180 aşmak
        # tam %100 yapmakla aynı görünmemeli.
        "cubuk_yuzde": min(yuzde, 100),
        "asildi": yuzde > 100,
        "kalan_saat": round(max(hedef_dakika - dakika, 0) / 60, 1),
        "kalan_gun": 6 - bugun.weekday(),
    }


def hedefleri_guncelle(haftalik_saat, toplam_hedef_saat):
    with json_deposu.guncelle() as veri:
        veri["hedefler"]["haftalik_saat"] = haftalik_saat
        veri["hedefler"]["toplam_hedef_saat"] = toplam_hedef_saat
        return veri["hedefler"]


def _bildirim_metni(veri, bugun):
    """Gönderilecek hatırlatmayı seçer; gerek yoksa None."""
    ayarlar = veri["ayarlar"]
    if not ayarlar.get("bildirimler_acik", True):
        return None

    ilerleme = haftalik_ilerleme(veri, bugun)
    seri = istatistikler.seri_hesapla(
        veri["oturumlar"], ayarlar.get("seri_esigi_dakika"), bugun
    )

    # 1) Pazar akşamı haftalık özet.
    if bugun.weekday() == 6 and dt.datetime.now().hour >= 18:
        karsilastirma = istatistikler.hafta_karsilastirmasi(veri["oturumlar"], bugun)
        if karsilastirma["degisim_yuzde"] is not None:
            yon = ("geçen haftadan %{:.0f} fazla".format(abs(karsilastirma["degisim_yuzde"]))
                   if karsilastirma["yonu"] == "artis"
                   else "geçen haftadan %{:.0f} az".format(abs(karsilastirma["degisim_yuzde"]))
                   if karsilastirma["yonu"] == "azalis" else "geçen haftayla aynı")
            ek = f" — {yon}."
        else:
            ek = "."
        durum = "Hedefi tutturdun 🎉" if ilerleme["yuzde"] >= 100 else \
            f"Hedefin {ilerleme['hedef_saat']} saatti."
        return (
            "Haftalık özet",
            f"Bu hafta {ilerleme['saat']} saat çalıştın{ek} {durum}",
        )

    # 2) Seri riski: akşam olmuş, bugün henüz eşiği geçmemiş, seri var.
    if seri["guncel"] >= 3 and not seri["bugun_tamam"] and bugun.weekday() is not None:
        simdi = dt.datetime.now()
        if simdi.hour >= 19:
            return (
                "Serini kaybetme",
                f"{seri['guncel']} günlük serin var ama bugün henüz "
                f"{seri['esik_dakika']} dakikayı geçmedin.",
            )

    # 3) Hafta sonu hedef uyarısı.
    if bugun.weekday() >= 5 and ilerleme["hedef_saat"] > 0 and ilerleme["yuzde"] < 100:
        return (
            "Haftalık hedef uyarısı",
            f"Bu hafta hedefine {ilerleme['kalan_saat']} saat kaldı, hafta bitiyor!",
        )

    # 4) Hafta ortası ilerleme bilgisi.
    if bugun.weekday() == 2 and ilerleme["hedef_saat"] > 0 and ilerleme["yuzde"] < 40:
        return (
            "Hafta ortası",
            f"Haftalık hedefinin %{ilerleme['yuzde']:.0f}'ındasın, "
            f"{ilerleme['kalan_gun']} gün kaldı.",
        )

    return None


def hatirlatmalari_kontrol_et(bugun=None):
    """Günde en fazla bir hatırlatma gönderir."""
    bugun = bugun or dt.date.today()
    with json_deposu.belki_guncelle() as (veri, degisti_isaretle):
        if veri["hedefler"].get("son_bildirim_tarihi") == bugun.isoformat():
            return False

        icerik = _bildirim_metni(veri, bugun)
        if icerik is None:
            return False

        veri["hedefler"]["son_bildirim_tarihi"] = bugun.isoformat()
        degisti_isaretle()

    # Bildirim gönderimi kilit DIŞINDA: plyer/Windows toast API'si takılırsa
    # tüm istekler ve izleme thread'i kilitlenmemeli.
    baslik, mesaj = icerik
    return bildirim.bildirim_gonder(baslik, mesaj)
