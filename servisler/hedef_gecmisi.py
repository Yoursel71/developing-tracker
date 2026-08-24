"""Haftalık hedef geçmişi.

Geçmiş haftaların hedefi tutturup tutturmadığı, o haftanın hedefiyle
birlikte saklanır — hedef sonradan değiştiğinde geçmiş çarpıtılmasın diye.
Kayıtlar tamamlanmış haftalar için üretilir; içinde bulunulan hafta canlı
hesaplanır.
"""

import datetime as dt

from depo import json_deposu
from servisler import hedefler


def _hafta_basi(gun):
    return gun - dt.timedelta(days=gun.weekday())


def _hafta_toplami(oturumlar, hafta_basi):
    bitis = hafta_basi + dt.timedelta(days=6)
    toplam = 0.0
    for oturum in oturumlar:
        try:
            gun = dt.date.fromisoformat(oturum["tarih"])
        except (KeyError, TypeError, ValueError):
            continue
        if hafta_basi <= gun <= bitis:
            toplam += oturum.get("sure_dakika", 0)
    return toplam


def gecmisi_guncelle(bugun=None):
    """Kapanmış haftaları geçmişe işler. Yeni eklenen hafta sayısını döner."""
    bugun = bugun or dt.date.today()
    bu_hafta = _hafta_basi(bugun)

    with json_deposu.belki_guncelle() as (veri, isaret):
        oturumlar = veri["oturumlar"]
        if not oturumlar:
            return 0

        kayitli = {k["hafta_basi"] for k in veri["hedef_gecmisi"]}
        hedef_saat = veri["hedefler"].get("haftalik_saat", 0) or 0

        ilk = min(
            (dt.date.fromisoformat(o["tarih"]) for o in oturumlar
             if _gecerli_tarih(o)), default=None
        )
        if ilk is None:
            return 0

        eklenen = 0
        hafta = _hafta_basi(ilk)
        while hafta < bu_hafta:
            anahtar = hafta.isoformat()
            if anahtar not in kayitli:
                dakika = _hafta_toplami(oturumlar, hafta)
                veri["hedef_gecmisi"].append({
                    "hafta_basi": anahtar,
                    "dakika": round(dakika, 1),
                    "hedef_saat": hedef_saat,
                    "basarili": hedef_saat > 0 and dakika >= hedef_saat * 60,
                })
                eklenen += 1
            hafta += dt.timedelta(days=7)

        if eklenen:
            veri["hedef_gecmisi"].sort(key=lambda k: k["hafta_basi"])
            isaret()
        return eklenen


def _gecerli_tarih(oturum):
    try:
        dt.date.fromisoformat(oturum["tarih"])
        return True
    except (KeyError, TypeError, ValueError):
        return False


def listele(veri=None, limit=12, bugun=None):
    """Geçmiş haftalar + içinde bulunulan hafta (canlı), en yeni önce."""
    bugun = bugun or dt.date.today()
    veri = veri if veri is not None else json_deposu.oku()

    kayitlar = list(veri["hedef_gecmisi"])
    bu_hafta = _hafta_basi(bugun)
    ilerleme = hedefler.haftalik_ilerleme(veri, bugun)

    satirlar = [{
        "hafta_basi": bu_hafta.isoformat(),
        "etiket": _etiket(bu_hafta, bugun),
        "dakika": ilerleme["dakika"],
        "saat": ilerleme["saat"],
        "hedef_saat": ilerleme["hedef_saat"],
        "yuzde": ilerleme["yuzde"],
        "basarili": ilerleme["yuzde"] >= 100,
        "devam_ediyor": True,
    }]

    for kayit in reversed(kayitlar[-limit:]):
        hafta = dt.date.fromisoformat(kayit["hafta_basi"])
        hedef_dakika = (kayit.get("hedef_saat") or 0) * 60
        satirlar.append({
            "hafta_basi": kayit["hafta_basi"],
            "etiket": _etiket(hafta, bugun),
            "dakika": kayit["dakika"],
            "saat": round(kayit["dakika"] / 60, 1),
            "hedef_saat": kayit.get("hedef_saat", 0),
            "yuzde": round(kayit["dakika"] / hedef_dakika * 100, 1) if hedef_dakika else 0,
            "basarili": kayit.get("basarili", False),
            "devam_ediyor": False,
        })
    return satirlar


def _etiket(hafta_basi, bugun):
    bitis = hafta_basi + dt.timedelta(days=6)
    if hafta_basi == _hafta_basi(bugun):
        return "Bu hafta"
    if hafta_basi == _hafta_basi(bugun) - dt.timedelta(days=7):
        return "Geçen hafta"
    return f"{hafta_basi.strftime('%d.%m')} – {bitis.strftime('%d.%m')}"


def ozet(veri=None, bugun=None):
    veri = veri if veri is not None else json_deposu.oku()
    kayitlar = veri["hedef_gecmisi"]
    if not kayitlar:
        return {"toplam": 0, "basarili": 0, "oran": 0}
    basarili = sum(1 for k in kayitlar if k.get("basarili"))
    return {
        "toplam": len(kayitlar),
        "basarili": basarili,
        "oran": round(basarili / len(kayitlar) * 100, 1),
    }
