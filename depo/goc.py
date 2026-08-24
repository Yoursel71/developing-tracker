"""Şema sürüm göçleri.

Sürüm geçmişi:

* **v0** — ilk sürüm: tekil ``aktif_oturum``, ``izleme`` bloğu yok.
* **v1** — ``aktif_oturumlar`` (kategoriye göre sözlük), ``izleme`` eklendi.
* **v2** — oturumlara ``id``/``not``, aktif oturumlara ``son_gorulme`` +
  ``birikmis_saniye`` (checkpoint modeli), ``yol_haritasi`` ve ``ayarlar``.
"""

import logging
import uuid

from depo.varsayilan import SEMA_SURUMU, normallestir

logger = logging.getLogger(__name__)


def _mevcut_surum(veri):
    """Sürüm alanı yoksa şeklinden çıkarım yapar."""
    surum = veri.get("surum")
    if isinstance(surum, int):
        return surum
    if "aktif_oturumlar" in veri or "izleme" in veri:
        return 1
    return 0


def _v0_dan_v1e(veri):
    aktif = veri.pop("aktif_oturum", None)
    aktif_oturumlar = {}
    if isinstance(aktif, dict) and aktif.get("kategori"):
        aktif_oturumlar[aktif["kategori"]] = {
            "baslangic": aktif.get("baslangic"),
            "kaynak": "manuel",
        }
    veri["aktif_oturumlar"] = aktif_oturumlar
    veri.setdefault("izleme", {"editorler": [], "siteler": []})
    veri["surum"] = 1
    return veri


def _v1_den_v2ye(veri):
    for oturum in veri.get("oturumlar", []):
        if not isinstance(oturum, dict):
            continue
        oturum.setdefault("id", uuid.uuid4().hex)
        oturum.setdefault("not", "")
        oturum.setdefault("kaynak", "manuel")
        oturum.setdefault("duzenlendi", False)

    yeni_aktifler = {}
    for kategori, aktif in (veri.get("aktif_oturumlar") or {}).items():
        if not isinstance(aktif, dict):
            continue
        baslangic = aktif.get("baslangic")
        yeni_aktifler[kategori] = {
            "baslangic": baslangic,
            "son_gorulme": aktif.get("son_gorulme") or baslangic,
            "birikmis_saniye": aktif.get("birikmis_saniye", 0),
            "bosta_mi": False,
            "kaynak": aktif.get("kaynak", "manuel"),
        }
    veri["aktif_oturumlar"] = yeni_aktifler

    veri.setdefault("yol_haritasi", [])
    veri["izleme"].setdefault("ertelemeler", {})
    veri["surum"] = 2
    return veri


_GOCLER = {
    0: _v0_dan_v1e,
    1: _v1_den_v2ye,
}


def goc_gerekli_mi(veri):
    return _mevcut_surum(veri) < SEMA_SURUMU


def goc_et(veri):
    """Veriyi güncel şemaya yükseltir. (veri, goc_yapildi) döner."""
    surum = _mevcut_surum(veri)
    if surum >= SEMA_SURUMU:
        return normallestir(veri), False

    logger.info("Şema göçü: v%s -> v%s", surum, SEMA_SURUMU)
    while surum < SEMA_SURUMU:
        gocmen = _GOCLER.get(surum)
        if gocmen is None:
            logger.warning("v%s için göç tanımlı değil, atlanıyor", surum)
            break
        veri = gocmen(veri)
        surum = _mevcut_surum(veri)

    veri["surum"] = SEMA_SURUMU
    return normallestir(veri), True
