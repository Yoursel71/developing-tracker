"""Yıl özeti ("wrapped") ve paylaşılabilir rozet.

Rozet **yerel olarak** üretilir; hiçbir yere yayınlanmaz. Kullanıcı SVG'yi
indirip istediği yerde kullanır — verisinin nereye gideceğine kendi karar
verir.
"""

import datetime as dt
import html
from collections import defaultdict

from servisler import heatmap, istatistikler


def _yil_oturumlari(oturumlar, yil):
    sonuc = []
    for oturum in oturumlar:
        try:
            gun = dt.date.fromisoformat(oturum["tarih"])
        except (KeyError, TypeError, ValueError):
            continue
        if gun.year == yil:
            sonuc.append(oturum)
    return sonuc


def kullanilabilir_yillar(oturumlar):
    yillar = set()
    for oturum in oturumlar:
        try:
            yillar.add(dt.date.fromisoformat(oturum["tarih"]).year)
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(yillar, reverse=True)


def _aylik_dagilim(oturumlar):
    aylar = defaultdict(float)
    for oturum in oturumlar:
        try:
            gun = dt.date.fromisoformat(oturum["tarih"])
        except (KeyError, TypeError, ValueError):
            continue
        aylar[gun.month] += oturum.get("sure_dakika", 0)
    return [
        {"ay": i, "etiket": heatmap.TURKCE_AYLAR[i - 1], "dakika": round(aylar.get(i, 0), 1)}
        for i in range(1, 13)
    ]


def ozet(veri, yil=None, bugun=None):
    bugun = bugun or dt.date.today()
    yil = yil or bugun.year
    oturumlar = _yil_oturumlari(veri["oturumlar"], yil)

    toplam_dakika = sum(o.get("sure_dakika", 0) for o in oturumlar)
    gunluk = istatistikler.gunluk_toplamlar(oturumlar)
    aktif_gunler = [d for d in gunluk.values() if d > 0]

    aylar = _aylik_dagilim(oturumlar)
    en_iyi_ay = max(aylar, key=lambda a: a["dakika"]) if toplam_dakika else None

    gunler = istatistikler.haftanin_gunleri_dagilimi(oturumlar)
    en_iyi_gun = max(gunler, key=lambda g: g["dakika"]) if toplam_dakika else None

    saatler = istatistikler.saat_dagilimi(oturumlar)
    en_iyi_saat = max(saatler, key=lambda s: s["dakika"]) if toplam_dakika else None

    # Seri hesabı yıl içinde: yılın son gününe göre bak (geçmiş yıllar için).
    referans = bugun if yil == bugun.year else dt.date(yil, 12, 31)
    seri = istatistikler.seri_hesapla(
        oturumlar, veri["ayarlar"].get("seri_esigi_dakika"), referans
    )

    tamamlanan_taslar = [
        t for t in veri["yol_haritasi"]
        if t.get("tamamlandi") and str(t.get("tamamlanma_tarihi") or "").startswith(str(yil))
    ]

    return {
        "yil": yil,
        "veri_var": bool(oturumlar),
        "toplam_saat": round(toplam_dakika / 60, 1),
        "toplam_dakika": round(toplam_dakika, 1),
        "oturum_sayisi": len(oturumlar),
        "aktif_gun_sayisi": len(aktif_gunler),
        "gunluk_ortalama": round(toplam_dakika / len(aktif_gunler), 1) if aktif_gunler else 0,
        "en_uzun_seri": seri["en_uzun"],
        "en_uzun_oturum": istatistikler.en_uzun_oturum(oturumlar),
        "en_cok_calisilan_gun": istatistikler.en_cok_calisilan_gun(oturumlar),
        "aylar": aylar,
        "en_iyi_ay": en_iyi_ay,
        "en_iyi_gun": en_iyi_gun,
        "en_iyi_saat": en_iyi_saat,
        "kategoriler": istatistikler.kategori_dagilimi(oturumlar),
        "tamamlanan_taslar": tamamlanan_taslar,
        "gece_kusu_mu": bool(en_iyi_saat and (en_iyi_saat["saat"] >= 21 or en_iyi_saat["saat"] < 5)),
    }


# --- Rozet ------------------------------------------------------------------

_KARAKTER_GENISLIGI = 6.6  # ortalama, 11px yazı için


def _metin_genisligi(metin):
    return int(len(metin) * _KARAKTER_GENISLIGI) + 16


def rozet_svg(etiket, deger, renk="#3fb950"):
    """shields.io tarzı, bağımlılıksız SVG rozet."""
    etiket = html.escape(str(etiket))
    deger = html.escape(str(deger))
    sol = _metin_genisligi(etiket)
    sag = _metin_genisligi(deger)
    toplam = sol + sag

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{toplam}" height="20" \
role="img" aria-label="{etiket}: {deger}">
  <title>{etiket}: {deger}</title>
  <linearGradient id="parlak" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="kirp"><rect width="{toplam}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#kirp)">
    <rect width="{sol}" height="20" fill="#555"/>
    <rect x="{sol}" width="{sag}" height="20" fill="{renk}"/>
    <rect width="{toplam}" height="20" fill="url(#parlak)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{sol / 2}" y="15" fill="#010101" fill-opacity=".3">{etiket}</text>
    <text x="{sol / 2}" y="14">{etiket}</text>
    <text x="{sol + sag / 2}" y="15" fill="#010101" fill-opacity=".3">{deger}</text>
    <text x="{sol + sag / 2}" y="14">{deger}</text>
  </g>
</svg>'''


def rozet_secenekleri(veri, bugun=None):
    """Kullanıcının seçebileceği hazır rozetler."""
    bugun = bugun or dt.date.today()
    oturumlar = veri["oturumlar"]
    toplam_saat = round(sum(o.get("sure_dakika", 0) for o in oturumlar) / 60, 1)
    seri = istatistikler.seri_hesapla(oturumlar, veri["ayarlar"].get("seri_esigi_dakika"), bugun)
    bu_yil = ozet(veri, bugun.year, bugun)

    return [
        {"anahtar": "toplam", "etiket": "öğrenme", "deger": f"{toplam_saat} saat"},
        {"anahtar": "seri", "etiket": "seri", "deger": f"{seri['guncel']} gün"},
        {"anahtar": "yil", "etiket": str(bugun.year), "deger": f"{bu_yil['toplam_saat']} saat"},
        {"anahtar": "gun", "etiket": "aktif gün", "deger": str(bu_yil["aktif_gun_sayisi"])},
    ]


def rozet_uret(veri, anahtar, bugun=None):
    for secenek in rozet_secenekleri(veri, bugun):
        if secenek["anahtar"] == anahtar:
            return rozet_svg(secenek["etiket"], secenek["deger"])
    raise ValueError("Bilinmeyen rozet türü.")
