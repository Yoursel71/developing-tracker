from flask import Flask, redirect, render_template, request, url_for

from depo import json_deposu
from servisler import github_entegrasyon, heatmap, hedefler, istatistikler, zaman_takibi

app = Flask(__name__)


@app.route("/")
def index():
    hedefler.haftasonu_bildirimini_kontrol_et()
    veri = json_deposu.oku()
    return render_template(
        "index.html",
        aktif_oturum=veri["aktif_oturum"],
        kategoriler=zaman_takibi.KATEGORILER,
        son_oturumlar=list(reversed(veri["oturumlar"][-10:])),
    )


@app.route("/oturum/baslat", methods=["POST"])
def oturum_baslat():
    kategori = request.form.get("kategori") or "Diğer"
    try:
        zaman_takibi.oturum_baslat(kategori)
    except ValueError:
        pass
    return redirect(url_for("index"))


@app.route("/oturum/durdur", methods=["POST"])
def oturum_durdur():
    try:
        zaman_takibi.oturum_durdur()
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


if __name__ == "__main__":
    app.run(debug=True)
