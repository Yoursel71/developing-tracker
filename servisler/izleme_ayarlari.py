from depo import json_deposu


def izleme_ayarlarini_getir():
    veri = json_deposu.oku()
    return veri["izleme"]


def kurulum_tamamlandi_mi():
    return json_deposu.oku()["kurulum_tamamlandi"]


def kurulumu_kaydet(haftalik_saat, toplam_hedef_saat, github_kullanici, editorler, siteler):
    with json_deposu.guncelle() as veri:
        veri["hedefler"]["haftalik_saat"] = haftalik_saat
        veri["hedefler"]["toplam_hedef_saat"] = toplam_hedef_saat
        veri["github"]["kullanici"] = github_kullanici
        veri["izleme"]["editorler"] = editorler
        veri["izleme"]["siteler"] = siteler
        veri["kurulum_tamamlandi"] = True
        return veri
