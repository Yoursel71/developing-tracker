"""Öğrenme yol haritası (kilometre taşları).

"135 saat" tek başına soyut bir sayı; her biri tahmini saatli konulara
bölününce hem hedef anlam kazanır hem de tahmin "sıradaki konuyu ~3 günde
bitirirsin" diye somutlaşır.
"""

import datetime as dt
import uuid

import config
from depo import json_deposu


def varsayilan_yol_haritasi():
    return [
        {
            "id": uuid.uuid4().hex,
            "ad": ad,
            "tahmini_saat": saat,
            "tamamlandi": False,
            "tamamlanma_tarihi": None,
            "sira": sira,
        }
        for sira, (ad, saat) in enumerate(config.VARSAYILAN_YOL_HARITASI)
    ]


def toplam_hedef_saat(yol_haritasi):
    return sum(t.get("tahmini_saat", 0) for t in yol_haritasi)


def kalan_hedef_saat(yol_haritasi):
    return sum(
        t.get("tahmini_saat", 0) for t in yol_haritasi if not t.get("tamamlandi")
    )


def siradaki_tas(yol_haritasi):
    for tas in sorted(yol_haritasi, key=lambda t: t.get("sira", 0)):
        if not tas.get("tamamlandi"):
            return tas
    return None


def ozet(veri, tempo_dakika=None):
    """Panelde ve yol haritası sayfasında kullanılan özet."""
    yol = veri["yol_haritasi"]
    toplam = toplam_hedef_saat(yol)
    tamamlanan = sum(t.get("tahmini_saat", 0) for t in yol if t.get("tamamlandi"))
    siradaki = siradaki_tas(yol)

    siradaki_gun = None
    if siradaki and tempo_dakika and tempo_dakika > 0:
        siradaki_gun = round(siradaki["tahmini_saat"] * 60 / tempo_dakika, 1)

    return {
        "toplam_saat": toplam,
        "tamamlanan_saat": tamamlanan,
        "kalan_saat": toplam - tamamlanan,
        "yuzde": round(tamamlanan / toplam * 100, 1) if toplam else 0,
        "tamamlanan_sayisi": sum(1 for t in yol if t.get("tamamlandi")),
        "toplam_sayisi": len(yol),
        "siradaki": siradaki,
        "siradaki_tahmini_gun": siradaki_gun,
    }


def yol_haritasini_kaydet(taslar):
    """Tüm yol haritasını değiştirir ve toplam hedefi ona eşitler."""
    with json_deposu.guncelle() as veri:
        temiz = []
        for sira, tas in enumerate(taslar):
            ad = (tas.get("ad") or "").strip()
            if not ad:
                continue
            temiz.append({
                "id": tas.get("id") or uuid.uuid4().hex,
                "ad": ad,
                "tahmini_saat": max(float(tas.get("tahmini_saat") or 0), 0),
                "tamamlandi": bool(tas.get("tamamlandi")),
                "tamamlanma_tarihi": tas.get("tamamlanma_tarihi"),
                "sira": sira,
            })
        veri["yol_haritasi"] = temiz
        if temiz:
            veri["hedefler"]["toplam_hedef_saat"] = toplam_hedef_saat(temiz)
        return temiz


def tas_durumu_degistir(tas_id, tamamlandi):
    with json_deposu.guncelle() as veri:
        for tas in veri["yol_haritasi"]:
            if tas.get("id") == tas_id:
                tas["tamamlandi"] = bool(tamamlandi)
                tas["tamamlanma_tarihi"] = (
                    dt.date.today().isoformat() if tamamlandi else None
                )
                return tas
        raise ValueError("Kilometre taşı bulunamadı.")
