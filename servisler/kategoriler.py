"""Kullanıcı tanımlı kategoriler (projeler).

Kategoriler önceden ``config.py``'de sabitti; kullanıcı kendi projelerini
(ör. "LocalRun", "BruceButBetter") ekleyemiyordu. Artık veride tutulur.

Oturumlar kategoriyi **adıyla** saklar (CSV dışa aktarımı okunaklı kalsın
diye); bu yüzden yeniden adlandırma tüm referanslara yayılır.
"""

import uuid

import config
from depo import json_deposu

PALET = config.KATEGORI_PALETI


def varsayilan_kategoriler():
    return [
        {"id": uuid.uuid4().hex, "ad": ad, "renk": PALET[i % len(PALET)], "sira": i}
        for i, ad in enumerate(config.VARSAYILAN_KATEGORILER)
    ]


def listele(veri=None):
    veri = veri if veri is not None else json_deposu.oku()
    return sorted(veri.get("kategoriler") or [], key=lambda k: k.get("sira", 0))


def adlar(veri=None):
    return [k["ad"] for k in listele(veri)]


def renk_haritasi(veri=None):
    """kategori adı -> renk. Bilinmeyen kategoriler için nötr renk döner."""
    return {k["ad"]: k.get("renk") or PALET[0] for k in listele(veri)}


def renk_al(ad, veri=None):
    return renk_haritasi(veri).get(ad, "#6e7d8d")


def gecerli_mi(ad, veri=None):
    return ad in adlar(veri)


def _sonraki_renk(mevcut):
    kullanilan = {k.get("renk") for k in mevcut}
    for renk in PALET:
        if renk not in kullanilan:
            return renk
    return PALET[len(mevcut) % len(PALET)]


def ekle(ad, renk=None):
    ad = (ad or "").strip()
    if not ad:
        raise ValueError("Kategori adı boş olamaz.")
    if len(ad) > 40:
        raise ValueError("Kategori adı en fazla 40 karakter olabilir.")

    with json_deposu.guncelle() as veri:
        mevcut = veri["kategoriler"]
        if any(k["ad"].lower() == ad.lower() for k in mevcut):
            raise ValueError(f"'{ad}' zaten var.")
        if len(mevcut) >= 20:
            raise ValueError("En fazla 20 kategori olabilir.")
        yeni = {
            "id": uuid.uuid4().hex,
            "ad": ad,
            "renk": renk or _sonraki_renk(mevcut),
            "sira": len(mevcut),
        }
        mevcut.append(yeni)
        return yeni


def yeniden_adlandir(kategori_id, yeni_ad):
    """Adı değiştirir ve tüm referansları günceller."""
    yeni_ad = (yeni_ad or "").strip()
    if not yeni_ad:
        raise ValueError("Kategori adı boş olamaz.")

    with json_deposu.guncelle() as veri:
        hedef = _bul(veri, kategori_id)
        eski_ad = hedef["ad"]
        if eski_ad == yeni_ad:
            return hedef
        if any(k["ad"].lower() == yeni_ad.lower() and k["id"] != kategori_id
               for k in veri["kategoriler"]):
            raise ValueError(f"'{yeni_ad}' zaten var.")

        hedef["ad"] = yeni_ad
        _referanslari_yenile(veri, eski_ad, yeni_ad)
        return hedef


def rengi_degistir(kategori_id, renk):
    with json_deposu.guncelle() as veri:
        hedef = _bul(veri, kategori_id)
        hedef["renk"] = renk
        return hedef


def sil(kategori_id, tasima_hedefi=None):
    """Kategoriyi siler; kayıtlı oturumlar ``tasima_hedefi``'ne taşınır.

    Hedef verilmezse kategori kullanımdaysa silme reddedilir — sessizce
    veri kaybetmemek için.
    """
    with json_deposu.guncelle() as veri:
        if len(veri["kategoriler"]) <= 1:
            raise ValueError("En az bir kategori kalmalı.")

        hedef = _bul(veri, kategori_id)
        ad = hedef["ad"]
        kullanim = sum(1 for o in veri["oturumlar"] if o.get("kategori") == ad)

        if kullanim and not tasima_hedefi:
            raise ValueError(
                f"'{ad}' kategorisinde {kullanim} oturum var. Silmeden önce "
                "bunların taşınacağı bir kategori seç."
            )

        if kullanim:
            if not any(k["ad"] == tasima_hedefi for k in veri["kategoriler"]
                       if k["id"] != kategori_id):
                raise ValueError("Taşıma hedefi geçersiz.")
            _referanslari_yenile(veri, ad, tasima_hedefi)

        # Aktif oturum varsa kapat (taşımak yerine sonlandır).
        veri["aktif_oturumlar"].pop(ad, None)
        veri["izleme"]["ertelemeler"].pop(ad, None)
        veri["izleme"]["editorler"] = [
            e for e in veri["izleme"]["editorler"] if e.get("kategori") != ad
        ]
        veri["izleme"]["siteler"] = [
            s for s in veri["izleme"]["siteler"] if s.get("kategori") != ad
        ]

        veri["kategoriler"] = [k for k in veri["kategoriler"] if k["id"] != kategori_id]
        for sira, kategori in enumerate(veri["kategoriler"]):
            kategori["sira"] = sira


def _bul(veri, kategori_id):
    for kategori in veri["kategoriler"]:
        if kategori["id"] == kategori_id:
            return kategori
    raise ValueError("Kategori bulunamadı.")


def _referanslari_yenile(veri, eski_ad, yeni_ad):
    for oturum in veri["oturumlar"]:
        if oturum.get("kategori") == eski_ad:
            oturum["kategori"] = yeni_ad

    if eski_ad in veri["aktif_oturumlar"]:
        veri["aktif_oturumlar"][yeni_ad] = veri["aktif_oturumlar"].pop(eski_ad)
    if eski_ad in veri["izleme"]["ertelemeler"]:
        veri["izleme"]["ertelemeler"][yeni_ad] = veri["izleme"]["ertelemeler"].pop(eski_ad)

    for kayit in veri["izleme"]["editorler"] + veri["izleme"]["siteler"]:
        if kayit.get("kategori") == eski_ad:
            kayit["kategori"] = yeni_ad


def kullanim_sayilari(veri=None):
    veri = veri if veri is not None else json_deposu.oku()
    sayac = {}
    for oturum in veri["oturumlar"]:
        ad = oturum.get("kategori")
        sayac[ad] = sayac.get(ad, 0) + 1
    return sayac
