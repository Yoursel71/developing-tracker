"""Sunucu tarafı girdi doğrulama.

HTML'deki ``min="0"`` istemci tarafı bir öneridir; ``curl`` ya da DevTools
ile aşılabilir. Negatif hedef girildiğinde uygulama "Hedef tamamlandı!"
diyordu ve Türkçe ondalık virgülü (``15,5``) yakalanmamış bir ``ValueError``
ile 500 üretip kullanıcının tüm formunu kaybettiriyordu.
"""

import datetime as dt
import re

import config

ALAN_ADI_DESENI = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
GITHUB_KULLANICI_DESENI = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


class DogrulamaHatasi(ValueError):
    """Kullanıcıya gösterilebilir doğrulama hatası."""

    def __init__(self, mesaj, alan=None):
        super().__init__(mesaj)
        self.mesaj = mesaj
        self.alan = alan


def sayi(deger, alan_adi, varsayilan=0.0, en_az=0.0, en_cok=100000.0, zorunlu=False):
    """Türkçe ondalık virgülünü de kabul eden güvenli sayı ayrıştırma."""
    if deger is None or str(deger).strip() == "":
        if zorunlu:
            raise DogrulamaHatasi(f"{alan_adi} boş bırakılamaz.", alan_adi)
        return varsayilan

    metin = str(deger).strip().replace(",", ".")
    try:
        sonuc = float(metin)
    except ValueError:
        raise DogrulamaHatasi(f"{alan_adi} sayı olmalı (girilen: {deger}).", alan_adi)

    if sonuc != sonuc or sonuc in (float("inf"), float("-inf")):
        raise DogrulamaHatasi(f"{alan_adi} geçerli bir sayı değil.", alan_adi)
    if sonuc < en_az:
        raise DogrulamaHatasi(f"{alan_adi} {en_az:g} değerinden küçük olamaz.", alan_adi)
    if sonuc > en_cok:
        raise DogrulamaHatasi(f"{alan_adi} {en_cok:g} değerinden büyük olamaz.", alan_adi)
    return sonuc


def kategori(deger, gecerli_adlar=None):
    """Kategoriyi kullanıcının tanımlı listesine karşı doğrular.

    Uydurma bir kategori kabul edilirse ``aktif_oturumlar``'a yazılır ve
    arayüzde hiç görünmediği için asla durdurulamazdı.
    """
    temiz = (deger or "").strip()
    if gecerli_adlar is None:
        from servisler import kategoriler as kategori_servisi

        gecerli_adlar = kategori_servisi.adlar()
    if temiz not in gecerli_adlar:
        raise DogrulamaHatasi(f"Geçersiz kategori: {deger or '(boş)'}", "kategori")
    return temiz


def tarih(deger, alan_adi="Tarih"):
    temiz = (deger or "").strip()
    try:
        gun = dt.date.fromisoformat(temiz)
    except ValueError:
        raise DogrulamaHatasi(f"{alan_adi} GG.AA.YYYY biçiminde olmalı.", alan_adi)
    if gun > dt.date.today():
        raise DogrulamaHatasi(f"{alan_adi} gelecekte olamaz.", alan_adi)
    return gun.isoformat()


def github_kullanici(deger):
    temiz = (deger or "").strip()
    if not temiz:
        return ""
    if not GITHUB_KULLANICI_DESENI.match(temiz):
        raise DogrulamaHatasi(
            "GitHub kullanıcı adı geçersiz (yalnızca harf, rakam ve tire).",
            "github_kullanici",
        )
    return temiz


def alan_adi_normallestir(deger):
    """``https://www.udemy.com/course/x`` → ``udemy.com``.

    Kullanıcı tam URL yapıştırdığında eklenti eşleşmesi asla tutmuyordu ve
    site izleme sessizce hiç çalışmıyordu.
    """
    temiz = (deger or "").strip().lower()
    if not temiz:
        return ""
    temiz = re.sub(r"^[a-z]+://", "", temiz)
    temiz = temiz.split("/")[0].split("?")[0].split("#")[0]
    if "@" in temiz:
        temiz = temiz.split("@")[-1]
    temiz = temiz.split(":")[0]
    if temiz.startswith("www."):
        temiz = temiz[4:]
    if not ALAN_ADI_DESENI.match(temiz):
        raise DogrulamaHatasi(
            f"'{deger}' geçerli bir alan adı değil (örnek: udemy.com).", "alan_adi"
        )
    return temiz


def islem_adi(deger):
    temiz = (deger or "").strip()
    if not temiz:
        return ""
    if len(temiz) > 120 or "/" in temiz or "\\" in temiz:
        raise DogrulamaHatasi(
            f"'{deger}' geçerli bir işlem adı değil (örnek: Code.exe).", "islem_adi"
        )
    return temiz


def izleme_listelerini_dogrula(editorler, siteler, gecerli_adlar=None):
    """Çakışma ve tekrarları yakalar.

    Aynı işlem iki kategoriye eşlenirse VS Code açılınca iki oturum birden
    başlar ve süre çift sayılır; bu yüzden çakışma hata olarak döner.
    """
    temiz_editorler = []
    islem_kategorileri = {}
    for kayit in editorler:
        islem = islem_adi(kayit.get("islem_adi"))
        if not islem:
            continue
        kat = kategori(kayit.get("kategori"), gecerli_adlar)
        anahtar = islem.lower()
        if anahtar in islem_kategorileri:
            if islem_kategorileri[anahtar] != kat:
                raise DogrulamaHatasi(
                    f"'{islem}' iki farklı kategoriye eşlenmiş "
                    f"({islem_kategorileri[anahtar]} ve {kat}). Bu, süreyi çift "
                    "saydırır — her program yalnızca bir kategoriye bağlanabilir.",
                    "editorler",
                )
            continue  # birebir tekrar: sessizce yok say
        islem_kategorileri[anahtar] = kat
        temiz_editorler.append({
            "program_adi": (kayit.get("program_adi") or islem).strip(),
            "islem_adi": islem,
            "kategori": kat,
        })

    temiz_siteler = []
    alan_kategorileri = {}
    for kayit in siteler:
        alan = alan_adi_normallestir(kayit.get("alan_adi"))
        if not alan:
            continue
        kat = kategori(kayit.get("kategori"), gecerli_adlar)
        if alan in alan_kategorileri:
            if alan_kategorileri[alan] != kat:
                raise DogrulamaHatasi(
                    f"'{alan}' iki farklı kategoriye eşlenmiş "
                    f"({alan_kategorileri[alan]} ve {kat}). Her site yalnızca bir "
                    "kategoriye bağlanabilir.",
                    "siteler",
                )
            continue
        alan_kategorileri[alan] = kat
        temiz_siteler.append({"alan_adi": alan, "kategori": kat})

    return temiz_editorler, temiz_siteler


def hedefleri_dogrula(haftalik_saat, toplam_hedef_saat):
    haftalik = sayi(haftalik_saat, "Haftalık hedef", en_az=0, en_cok=168)
    toplam = sayi(toplam_hedef_saat, "Toplam hedef", en_az=0, en_cok=100000)
    if haftalik > 0 and toplam > 0 and haftalik > toplam:
        raise DogrulamaHatasi(
            "Haftalık hedef, toplam hedeften büyük olamaz.", "haftalik_saat"
        )
    return haftalik, toplam
