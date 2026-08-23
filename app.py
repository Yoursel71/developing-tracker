from flask import Flask, jsonify, redirect, render_template, request, url_for

from config import BILINEN_EDITORLER, UYGULAMA_PORTU
from depo import json_deposu
from servisler import (
    github_entegrasyon,
    heatmap,
    hedefler,
    istatistikler,
    izleme_ayarlari,
    otomatik_izleme,
    zaman_takibi,
)

app = Flask(__name__)

# Uygulama nasıl başlatılırsa başlatılsın (python app.py veya masaustu.py
# üzerinden import), bu modül bir kez yüklendiğinde izleme thread'i başlar.
otomatik_izleme.baslat()


@app.before_request
def kurulum_kontrolu():
    muaf_uc_noktalar = {"kurulum_sayfasi", "static", "api_izleme_ayarlari", "api_site_durumu"}
    if request.endpoint in muaf_uc_noktalar:
        return
    if not izleme_ayarlari.kurulum_tamamlandi_mi():
        return redirect(url_for("kurulum_sayfasi"))


def _kurulum_formunu_kaydet():
    haftalik_saat = float(request.form.get("haftalik_saat", 0) or 0)
    toplam_hedef_saat = float(request.form.get("toplam_hedef_saat", 0) or 0)
    github_kullanici = (request.form.get("github_kullanici") or "").strip()

    program_adlari = request.form.getlist("editor_program_adi[]")
    islem_adlari = request.form.getlist("editor_islem_adi[]")
    editor_kategorileri = request.form.getlist("editor_kategori[]")
    editorler = [
        {"program_adi": p.strip(), "islem_adi": i.strip(), "kategori": k.strip()}
        for p, i, k in zip(program_adlari, islem_adlari, editor_kategorileri)
        if i.strip() and k.strip()
    ]

    alan_adlari = request.form.getlist("site_alan_adi[]")
    site_kategorileri = request.form.getlist("site_kategori[]")
    siteler = [
        {"alan_adi": a.strip().lower(), "kategori": k.strip()}
        for a, k in zip(alan_adlari, site_kategorileri)
        if a.strip() and k.strip()
    ]

    izleme_ayarlari.kurulumu_kaydet(haftalik_saat, toplam_hedef_saat, github_kullanici, editorler, siteler)


@app.route("/kurulum", methods=["GET", "POST"])
def kurulum_sayfasi():
    if request.method == "POST":
        _kurulum_formunu_kaydet()
        return redirect(url_for("index"))
    veri = json_deposu.oku()
    return render_template(
        "kurulum.html",
        hedef=veri["hedefler"],
        github_kullanici=veri["github"]["kullanici"],
        izleme=veri["izleme"],
        bilinen_editorler=BILINEN_EDITORLER,
        kategoriler=zaman_takibi.KATEGORILER,
    )


@app.route("/ayarlar", methods=["GET", "POST"])
def ayarlar_sayfasi():
    if request.method == "POST":
        _kurulum_formunu_kaydet()
        return redirect(url_for("ayarlar_sayfasi"))
    veri = json_deposu.oku()
    return render_template(
        "ayarlar.html",
        hedef=veri["hedefler"],
        github_kullanici=veri["github"]["kullanici"],
        izleme=veri["izleme"],
        bilinen_editorler=BILINEN_EDITORLER,
        kategoriler=zaman_takibi.KATEGORILER,
    )


@app.route("/")
def index():
    hedefler.haftasonu_bildirimini_kontrol_et()
    veri = json_deposu.oku()
    uygun_kategoriler = [k for k in zaman_takibi.KATEGORILER if k not in veri["aktif_oturumlar"]]
    return render_template(
        "index.html",
        aktif_oturumlar=veri["aktif_oturumlar"],
        kategoriler=uygun_kategoriler,
        son_oturumlar=list(reversed(veri["oturumlar"][-10:])),
    )


@app.route("/oturum/baslat", methods=["POST"])
def oturum_baslat():
    kategori = request.form.get("kategori") or "Diğer"
    try:
        zaman_takibi.oturum_baslat(kategori, kaynak="manuel")
    except ValueError:
        pass
    return redirect(url_for("index"))


@app.route("/oturum/durdur", methods=["POST"])
def oturum_durdur():
    kategori = request.form.get("kategori")
    aktif = zaman_takibi.aktif_oturumlari_getir().get(kategori)
    try:
        zaman_takibi.oturum_durdur(kategori)
        if aktif and aktif.get("kaynak") == "otomatik":
            otomatik_izleme.oturumu_ertele(kategori)
    except ValueError:
        pass
    return redirect(url_for("index"))


@app.route("/heatmap")
def heatmap_sayfasi():
    veri = json_deposu.oku()
    etkinlikler = veri["github"].get("son_cekilen_etkinlikler", [])
    gorunum = request.args.get("gorunum", "aylik")
    if gorunum == "haftalik":
        gunler = heatmap.haftalik_grid(veri["oturumlar"], etkinlikler)
    else:
        gorunum = "aylik"
        gunler = heatmap.aylik_grid(veri["oturumlar"], etkinlikler)
    return render_template("heatmap.html", gunler=gunler, gorunum=gorunum)


@app.route("/istatistikler")
def istatistikler_sayfasi():
    _, hata = github_entegrasyon.senkronize_et()
    veri = json_deposu.oku()
    istatistik = istatistikler.istatistikleri_hesapla(veri)
    return render_template("istatistikler.html", istatistik=istatistik, github_hatasi=hata)


@app.route("/github/yenile", methods=["POST"])
def github_yenile():
    github_entegrasyon.senkronize_et(zorla=True)
    return redirect(url_for("istatistikler_sayfasi"))


@app.route("/hedefler", methods=["GET", "POST"])
def hedefler_sayfasi():
    if request.method == "POST":
        haftalik_saat = float(request.form.get("haftalik_saat", 0) or 0)
        toplam_hedef_saat = float(request.form.get("toplam_hedef_saat", 0) or 0)
        hedefler.hedefleri_guncelle(haftalik_saat, toplam_hedef_saat)
        return redirect(url_for("hedefler_sayfasi"))

    veri = json_deposu.oku()
    hedef = veri["hedefler"]
    haftalik_dakika = hedefler.haftalik_toplam_dakika(veri["oturumlar"])
    ilerleme_yuzde = 0
    if hedef["haftalik_saat"] > 0:
        ilerleme_yuzde = min(100, round(haftalik_dakika / (hedef["haftalik_saat"] * 60) * 100, 1))
    return render_template(
        "hedefler.html",
        hedef=hedef,
        haftalik_saat_bugune_kadar=round(haftalik_dakika / 60, 1),
        ilerleme_yuzde=ilerleme_yuzde,
    )


@app.route("/api/izleme-ayarlari")
def api_izleme_ayarlari():
    veri = json_deposu.oku()
    yanit = jsonify({"siteler": veri["izleme"]["siteler"]})
    yanit.headers["Access-Control-Allow-Origin"] = "*"
    return yanit


@app.route("/api/site-durumu", methods=["POST"])
def api_site_durumu():
    gelen = request.get_json(silent=True) or {}
    kategori = gelen.get("kategori")
    durum = gelen.get("durum")
    if kategori and durum in ("acik", "kapandi"):
        otomatik_izleme.site_durumu_bildir(kategori, durum)
    yanit = jsonify({"tamam": True})
    yanit.headers["Access-Control-Allow-Origin"] = "*"
    return yanit


if __name__ == "__main__":
    app.run(port=UYGULAMA_PORTU, debug=True, use_reloader=False)
