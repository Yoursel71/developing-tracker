"""Kurulum ve ayarların kaydı, veri dışa aktarma."""

import csv
import io
import json

from depo import json_deposu
from servisler import yol_haritasi


def kurulum_tamamlandi_mi():
    return bool(json_deposu.oku().get("kurulum_tamamlandi"))


def izleme_ayarlarini_getir():
    return json_deposu.oku()["izleme"]


def kurulumu_kaydet(haftalik_saat, toplam_hedef_saat, github_kullanici,
                    editorler, siteler, yol_haritasi_ekle=True):
    with json_deposu.guncelle() as veri:
        veri["hedefler"]["haftalik_saat"] = haftalik_saat
        veri["github"]["kullanici"] = github_kullanici
        veri["izleme"]["editorler"] = editorler
        veri["izleme"]["siteler"] = siteler

        if yol_haritasi_ekle and not veri["yol_haritasi"]:
            veri["yol_haritasi"] = yol_haritasi.varsayilan_yol_haritasi()

        # Yol haritası varsa toplam hedef onun toplamıdır; yoksa girilen değer.
        if veri["yol_haritasi"]:
            veri["hedefler"]["toplam_hedef_saat"] = yol_haritasi.toplam_hedef_saat(
                veri["yol_haritasi"]
            )
        else:
            veri["hedefler"]["toplam_hedef_saat"] = toplam_hedef_saat

        veri["kurulum_tamamlandi"] = True
        return veri


def izlemeyi_kaydet(github_kullanici, editorler, siteler):
    with json_deposu.guncelle() as veri:
        veri["github"]["kullanici"] = github_kullanici
        veri["izleme"]["editorler"] = editorler
        veri["izleme"]["siteler"] = siteler
        return veri["izleme"]


def ayarlari_kaydet(**degerler):
    with json_deposu.guncelle() as veri:
        for anahtar, deger in degerler.items():
            if deger is not None:
                veri["ayarlar"][anahtar] = deger
        return veri["ayarlar"]


# --- Dışa aktarma -----------------------------------------------------------

def oturumlari_csv_yap():
    veri = json_deposu.oku()
    tampon = io.StringIO()
    yazici = csv.writer(tampon)
    yazici.writerow(["tarih", "kategori", "baslangic", "bitis", "sure_dakika", "kaynak", "not"])
    for oturum in sorted(veri["oturumlar"], key=lambda o: (o.get("tarih", ""), o.get("baslangic", ""))):
        yazici.writerow([
            oturum.get("tarih", ""),
            oturum.get("kategori", ""),
            oturum.get("baslangic", ""),
            oturum.get("bitis", ""),
            oturum.get("sure_dakika", 0),
            oturum.get("kaynak", ""),
            oturum.get("not", ""),
        ])
    return tampon.getvalue()


def tum_veriyi_json_yap():
    return json.dumps(json_deposu.oku(), ensure_ascii=False, indent=2)
