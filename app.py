"""Flask uygulaması: sayfalar ve JSON API."""

import datetime as dt
import logging

from flask import (
    Flask, Response, flash, get_flashed_messages, jsonify, redirect,
    render_template, request, url_for,
)

import config
from depo import json_deposu
from platform_katmani import bosta, yollar
from servisler import (
    api_anahtari,
    dogrulama,
    kategoriler as kategori_servisi,
    github_entegrasyon,
    gunlukleme,
    hedef_gecmisi,
    heatmap,
    hedefler,
    istatistikler,
    izleme_ayarlari,
    otomatik_izleme,
    pomodoro,
    yil_ozeti,
    yol_haritasi,
    zaman_takibi,
)

gunlukleme.kur()
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=yollar.kaynak_yolu("templates"),
    static_folder=yollar.kaynak_yolu("static"),
)
app.secret_key = api_anahtari.anahtari_al()
app.jinja_env.globals["config"] = config


# --- Yardımcılar ------------------------------------------------------------

def _json_istegi_mi():
    return request.accept_mimetypes.best == "application/json" or request.is_json or \
        request.headers.get("X-Istek-Turu") == "json"


def _hata_yanit(mesaj, kod=400):
    if _json_istegi_mi():
        return jsonify({"tamam": False, "hata": mesaj}), kod
    flash(mesaj, "hata")
    return redirect(request.referrer or url_for("panel"))


def _basari_yanit(mesaj, hedef=None, **ek):
    if _json_istegi_mi():
        return jsonify({"tamam": True, "mesaj": mesaj, **ek})
    if mesaj:
        flash(mesaj, "basari")
    return redirect(hedef or request.referrer or url_for("panel"))


def _eklenti_yaniti(govde, kod=200):
    yanit = jsonify(govde)
    yanit.status_code = kod
    # Yalnızca eklenti kaynaklarına izin ver (jokerle her siteye değil).
    kaynak = request.headers.get("Origin", "")
    if kaynak.startswith("chrome-extension://") or kaynak.startswith("moz-extension://"):
        yanit.headers["Access-Control-Allow-Origin"] = kaynak
        yanit.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Api-Anahtari"
        yanit.headers["Vary"] = "Origin"
    return yanit


@app.context_processor
def sablon_degiskenleri():
    veri = json_deposu.oku()
    return {
        "tema": veri["ayarlar"].get("tema", "koyu"),
        "aktif_sayfa": request.endpoint,
        "kurtarma_uyarisi": json_deposu.kurtarma_mesajini_al_ve_temizle(),
        "bildirimler": get_flashed_messages(with_categories=True),
    }


@app.before_request
def kurulum_kontrolu():
    muaf = {"kurulum_sayfasi", "static", "api_izleme_ayarlari", "api_site_durumu"}
    if request.endpoint in muaf or request.endpoint is None:
        return None
    try:
        if not izleme_ayarlari.kurulum_tamamlandi_mi():
            return redirect(url_for("kurulum_sayfasi"))
    except Exception:
        logger.exception("Kurulum durumu okunamadı")
    return None


@app.errorhandler(dogrulama.DogrulamaHatasi)
def dogrulama_hatasi(hata):
    return _hata_yanit(hata.mesaj, 400)


@app.errorhandler(404)
def bulunamadi(_hata):
    return render_template("hata.html", kod=404,
                           mesaj="Aradığın sayfa bulunamadı."), 404


@app.errorhandler(Exception)
def beklenmeyen_hata(hata):
    logger.exception("Beklenmeyen hata")
    if _json_istegi_mi():
        return jsonify({"tamam": False, "hata": "Beklenmeyen bir hata oluştu."}), 500
    return render_template(
        "hata.html", kod=500,
        mesaj="Beklenmeyen bir hata oluştu. Ayrıntılar log dosyasında.",
        gunluk_yolu=gunlukleme.gunluk_dosyasi_yolu(),
    ), 500


# --- Kurulum / Ayarlar ------------------------------------------------------

def _form_izleme_listeleri():
    editorler = [
        {"program_adi": p, "islem_adi": i, "kategori": k}
        for p, i, k in zip(
            request.form.getlist("editor_program_adi[]"),
            request.form.getlist("editor_islem_adi[]"),
            request.form.getlist("editor_kategori[]"),
        )
    ]
    siteler = [
        {"alan_adi": a, "kategori": k}
        for a, k in zip(
            request.form.getlist("site_alan_adi[]"),
            request.form.getlist("site_kategori[]"),
        )
    ]
    return dogrulama.izleme_listelerini_dogrula(editorler, siteler)


@app.route("/kurulum", methods=["GET", "POST"])
def kurulum_sayfasi():
    if request.method == "POST":
        haftalik, toplam = dogrulama.hedefleri_dogrula(
            request.form.get("haftalik_saat"), request.form.get("toplam_hedef_saat") or 135
        )
        kullanici = dogrulama.github_kullanici(request.form.get("github_kullanici"))
        editorler, siteler = _form_izleme_listeleri()
        izleme_ayarlari.kurulumu_kaydet(
            haftalik, toplam, kullanici, editorler, siteler,
            yol_haritasi_ekle=request.form.get("yol_haritasi_ekle") == "1",
        )
        flash("Kurulum tamamlandı. Hoş geldin!", "basari")
        return redirect(url_for("panel"))

    veri = json_deposu.oku()
    return render_template(
        "kurulum.html",
        hedef=veri["hedefler"],
        github_kullanici=veri["github"]["kullanici"],
        izleme=veri["izleme"],
        bilinen_editorler=config.BILINEN_EDITORLER,
        bilinen_siteler=config.BILINEN_SITELER,
        kategoriler=config.VARSAYILAN_KATEGORILER,
        yol_haritasi_taslak=config.VARSAYILAN_YOL_HARITASI,
    )


@app.route("/ayarlar", methods=["GET", "POST"])
def ayarlar_sayfasi():
    if request.method == "POST":
        bolum = request.form.get("bolum", "izleme")
        if bolum == "izleme":
            kullanici = dogrulama.github_kullanici(request.form.get("github_kullanici"))
            editorler, siteler = _form_izleme_listeleri()
            izleme_ayarlari.izlemeyi_kaydet(kullanici, editorler, siteler)
            return _basari_yanit("İzleme ayarları kaydedildi.", url_for("ayarlar_sayfasi"))

        if bolum == "tercihler":
            izleme_ayarlari.ayarlari_kaydet(
                tema=request.form.get("tema"),
                bosta_esigi_dakika=dogrulama.sayi(
                    request.form.get("bosta_esigi_dakika"), "Boşta eşiği",
                    varsayilan=config.VARSAYILAN_BOSTA_ESIGI_DAKIKA, en_az=0, en_cok=240,
                ),
                seri_esigi_dakika=dogrulama.sayi(
                    request.form.get("seri_esigi_dakika"), "Seri eşiği",
                    varsayilan=config.VARSAYILAN_SERI_ESIGI_DAKIKA, en_az=1, en_cok=600,
                ),
                tepsiye_indir=request.form.get("tepsiye_indir") == "1",
                bildirimler_acik=request.form.get("bildirimler_acik") == "1",
                windows_ile_baslat=request.form.get("windows_ile_baslat") == "1",
                mola_hatirlatici=request.form.get("mola_hatirlatici") == "1",
                pomodoro_acik=request.form.get("pomodoro_acik") == "1",
                motivasyon_sozu=request.form.get("motivasyon_sozu") == "1",
            )
            _windows_baslangicini_uygula(request.form.get("windows_ile_baslat") == "1")
            return _basari_yanit("Tercihler kaydedildi.", url_for("ayarlar_sayfasi"))

        return _hata_yanit("Bilinmeyen ayar bölümü.")

    veri = json_deposu.oku()
    return render_template(
        "ayarlar.html",
        hedef=veri["hedefler"],
        ayarlar=veri["ayarlar"],
        github_kullanici=veri["github"]["kullanici"],
        izleme=veri["izleme"],
        bilinen_editorler=config.BILINEN_EDITORLER,
        bilinen_siteler=config.BILINEN_SITELER,
        kategoriler=kategori_servisi.adlar(veri),
        kategori_kayitlari=kategori_servisi.listele(veri),
        kategori_kullanimi=kategori_servisi.kullanim_sayilari(veri),
        api_anahtari=api_anahtari.anahtari_al(),
        yedekler=json_deposu.yedekleri_listele(),
        veri_dizini=yollar.veri_dizini(),
        bosta_destekleniyor=bosta.destekleniyor_mu(),
    )


@app.route("/kategori/ekle", methods=["POST"])
def kategori_ekle():
    try:
        yeni = kategori_servisi.ekle(request.form.get("ad"), request.form.get("renk") or None)
    except ValueError as hata:
        return _hata_yanit(str(hata), 400)
    return _basari_yanit(f"'{yeni['ad']}' eklendi.", url_for("ayarlar_sayfasi"))


@app.route("/kategori/<kategori_id>/guncelle", methods=["POST"])
def kategori_guncelle(kategori_id):
    try:
        if request.form.get("ad") is not None:
            kategori_servisi.yeniden_adlandir(kategori_id, request.form.get("ad"))
        if request.form.get("renk"):
            kategori_servisi.rengi_degistir(kategori_id, request.form.get("renk"))
    except ValueError as hata:
        return _hata_yanit(str(hata), 400)
    return _basari_yanit("Kategori güncellendi.", url_for("ayarlar_sayfasi"))


@app.route("/kategori/<kategori_id>/sil", methods=["POST"])
def kategori_sil(kategori_id):
    try:
        kategori_servisi.sil(kategori_id, request.form.get("tasima_hedefi") or None)
    except ValueError as hata:
        return _hata_yanit(str(hata), 400)
    return _basari_yanit("Kategori silindi.", url_for("ayarlar_sayfasi"))


def _windows_baslangicini_uygula(acik):
    try:
        from platform_katmani import otomatik_baslatma

        otomatik_baslatma.ayarla(acik)
    except Exception:
        logger.exception("Windows başlangıç ayarı uygulanamadı")


# --- Panel ------------------------------------------------------------------

@app.route("/")
def panel():
    hedefler.hatirlatmalari_kontrol_et()
    veri = json_deposu.oku()
    github_entegrasyon.arka_planda_senkronize_et()

    oturumlar = veri["oturumlar"]
    etkinlikler = veri["github"]["son_cekilen_etkinlikler"]
    seri = istatistikler.seri_hesapla(oturumlar, veri["ayarlar"].get("seri_esigi_dakika"))
    tempo = istatistikler.tempo_hesapla(oturumlar)

    return render_template(
        "panel.html",
        aktif_oturumlar=_aktif_oturum_gorunumu(veri),
        baslatilabilir=[k for k in kategori_servisi.adlar(veri) if k not in veri["aktif_oturumlar"]],
        bugun_dakika=seri["bugun_dakika"],
        seri=seri,
        haftalik=hedefler.haftalik_ilerleme(veri),
        mini_heatmap=heatmap.mini_grid(oturumlar, etkinlikler, hafta_sayisi=13),
        yol_ozeti=yol_haritasi.ozet(veri, tempo),
        son_oturumlar=_son_oturumlar(oturumlar, 8),
        renkler=kategori_servisi.renk_haritasi(veri),
        pomodoro_durumu=pomodoro.durum(veri),
        pomodoro_acik=veri["ayarlar"].get("pomodoro_acik", False),
        motivasyon=_motivasyon_sozu(veri),
        veri_var=bool(oturumlar),
    )


def _motivasyon_sozu(veri):
    """Varsayılan olarak kapalı; açıksa gün içinde sabit kalır."""
    if not veri["ayarlar"].get("motivasyon_sozu"):
        return None
    bugun = dt.date.today()
    return config.MOTIVASYON_SOZLERI[bugun.toordinal() % len(config.MOTIVASYON_SOZLERI)]


def _son_oturumlar(oturumlar, adet):
    return sorted(
        oturumlar, key=lambda o: (o.get("tarih", ""), o.get("bitis", "")), reverse=True
    )[:adet]


_DURUM_METINLERI = {
    "bosta": "boşta — hareket bekleniyor",
    "kayip": "program kapandı — bekleniyor",
}


def _aktif_oturum_gorunumu(veri):
    sonuc = []
    for kategori, aktif in veri["aktif_oturumlar"].items():
        durum = zaman_takibi.oturum_durumu(aktif)
        sonuc.append({
            "kategori": kategori,
            "kaynak": aktif.get("kaynak", "manuel"),
            "durum": durum,
            "duruyor": durum != "calisiyor",
            "durum_metni": _DURUM_METINLERI.get(durum, ""),
            "gecen_saniye": int(zaman_takibi.gecen_saniye(aktif)),
        })
    return sorted(sonuc, key=lambda o: o["kategori"])


# --- Oturum işlemleri -------------------------------------------------------

@app.route("/oturum/baslat", methods=["POST"])
def oturum_baslat():
    kategori = dogrulama.kategori(request.form.get("kategori") or (request.json or {}).get("kategori"))
    try:
        zaman_takibi.oturum_baslat(kategori, kaynak="manuel")
    except ValueError as hata:
        return _hata_yanit(str(hata), 409)
    return _basari_yanit(f"{kategori} oturumu başladı.")


@app.route("/oturum/durdur", methods=["POST"])
def oturum_durdur():
    kategori = (request.form.get("kategori") or (request.json or {}).get("kategori") or "").strip()
    try:
        kayitlar = zaman_takibi.oturum_durdur(kategori)
    except ValueError as hata:
        return _hata_yanit(str(hata), 409)
    dakika = round(sum(k["sure_dakika"] for k in kayitlar), 1)
    return _basari_yanit(f"{kategori}: {dakika} dakika kaydedildi.")


@app.route("/oturum/<oturum_id>/guncelle", methods=["POST"])
def oturum_guncelle(oturum_id):
    govde = request.form if request.form else (request.json or {})
    alanlar = {}
    if govde.get("tarih"):
        alanlar["tarih"] = dogrulama.tarih(govde.get("tarih"))
    if govde.get("kategori"):
        alanlar["kategori"] = dogrulama.kategori(govde.get("kategori"))
    if govde.get("sure_dakika") is not None and str(govde.get("sure_dakika")).strip():
        alanlar["sure_dakika"] = dogrulama.sayi(
            govde.get("sure_dakika"), "Süre", en_az=0, en_cok=config.OTURUM_TAVANI_SAAT * 60
        )
    if "not" in govde:
        alanlar["not"] = (govde.get("not") or "")[:500]

    try:
        zaman_takibi.oturum_guncelle(oturum_id, **alanlar)
    except ValueError as hata:
        return _hata_yanit(str(hata), 404)
    return _basari_yanit("Oturum güncellendi.")


@app.route("/oturum/<oturum_id>/sil", methods=["POST"])
def oturum_sil(oturum_id):
    try:
        zaman_takibi.oturum_sil(oturum_id)
    except ValueError as hata:
        return _hata_yanit(str(hata), 404)
    return _basari_yanit("Oturum silindi.")


@app.route("/oturum/ekle", methods=["POST"])
def oturum_ekle():
    govde = request.form if request.form else (request.json or {})
    tarih = dogrulama.tarih(govde.get("tarih"))
    kategori = dogrulama.kategori(govde.get("kategori"))
    sure = dogrulama.sayi(
        govde.get("sure_dakika"), "Süre", en_az=1,
        en_cok=config.OTURUM_TAVANI_SAAT * 60, zorunlu=True,
    )
    zaman_takibi.oturum_ekle(tarih, kategori, sure, (govde.get("not") or "")[:500])
    return _basari_yanit("Oturum eklendi.")


# --- Isı haritası -----------------------------------------------------------

@app.route("/heatmap")
def heatmap_sayfasi():
    veri = json_deposu.oku()
    etkinlikler = veri["github"]["son_cekilen_etkinlikler"]
    gorunum = request.args.get("gorunum", "yil")

    if gorunum == "ay":
        try:
            yil = int(request.args.get("yil") or dt.date.today().year)
            ay = int(request.args.get("ay") or dt.date.today().month)
            grid = heatmap.ay_gridi(veri["oturumlar"], etkinlikler, yil, ay)
        except (ValueError, TypeError):
            grid = heatmap.ay_gridi(veri["oturumlar"], etkinlikler)
        return render_template("heatmap.html", gorunum="ay", ay_grid=grid, veri_var=bool(veri["oturumlar"]))

    grid = heatmap.yil_gridi(veri["oturumlar"], etkinlikler)
    return render_template("heatmap.html", gorunum="yil", yil_grid=grid, veri_var=bool(veri["oturumlar"]))


# --- İstatistikler ----------------------------------------------------------

@app.route("/istatistikler")
def istatistikler_sayfasi():
    github_entegrasyon.arka_planda_senkronize_et()
    veri = json_deposu.oku()
    etkinlikler = veri["github"]["son_cekilen_etkinlikler"]
    hedef_gecmisi.gecmisi_guncelle()
    veri = json_deposu.oku()
    return render_template(
        "istatistikler.html",
        istatistik=istatistikler.istatistikleri_hesapla(veri),
        repolar=github_entegrasyon.repo_ozeti(etkinlikler),
        github_hatasi=github_entegrasyon.son_hata(),
        github_kullanici=veri["github"]["kullanici"],
        renkler=kategori_servisi.renk_haritasi(veri),
    )


@app.route("/github/yenile", methods=["POST"])
def github_yenile():
    _, hata = github_entegrasyon.senkronize_et(zorla=True)
    if hata:
        return _hata_yanit(hata, 502)
    return _basari_yanit("GitHub verisi güncellendi.", url_for("istatistikler_sayfasi"))


# --- Hedefler ve yol haritası ----------------------------------------------

@app.route("/yol-haritasi", methods=["GET", "POST"])
def yol_haritasi_sayfasi():
    if request.method == "POST":
        adlar = request.form.getlist("tas_ad[]")
        saatler = request.form.getlist("tas_saat[]")
        idler = request.form.getlist("tas_id[]")
        tamamlananlar = set(request.form.getlist("tas_tamamlandi[]"))
        taslar = []
        for indeks, ad in enumerate(adlar):
            if not ad.strip():
                continue
            tas_id = idler[indeks] if indeks < len(idler) else None
            taslar.append({
                "id": tas_id,
                "ad": ad,
                "tahmini_saat": dogrulama.sayi(
                    saatler[indeks] if indeks < len(saatler) else 0,
                    f"'{ad.strip()}' için tahmini saat", en_az=0, en_cok=1000,
                ),
                "tamamlandi": tas_id in tamamlananlar,
            })
        yol_haritasi.yol_haritasini_kaydet(taslar)
        return _basari_yanit("Yol haritası kaydedildi.", url_for("yol_haritasi_sayfasi"))

    veri = json_deposu.oku()
    tempo = istatistikler.tempo_hesapla(veri["oturumlar"])
    return render_template(
        "yol_haritasi.html",
        yol=sorted(veri["yol_haritasi"], key=lambda t: t.get("sira", 0)),
        ozet=yol_haritasi.ozet(veri, tempo),
        tempo=round(tempo, 1),
    )


@app.route("/yol-haritasi/<tas_id>/durum", methods=["POST"])
def yol_tas_durumu(tas_id):
    govde = request.form if request.form else (request.json or {})
    tamamlandi = str(govde.get("tamamlandi", "")).lower() in ("1", "true", "on", "evet")
    try:
        yol_haritasi.tas_durumu_degistir(tas_id, tamamlandi)
    except ValueError as hata:
        return _hata_yanit(str(hata), 404)
    return _basari_yanit("Kilometre taşı güncellendi.")


@app.route("/hedefler", methods=["GET", "POST"])
def hedefler_sayfasi():
    hedef_gecmisi.gecmisi_guncelle()
    if request.method == "POST":
        haftalik, toplam = dogrulama.hedefleri_dogrula(
            request.form.get("haftalik_saat"), request.form.get("toplam_hedef_saat")
        )
        hedefler.hedefleri_guncelle(haftalik, toplam)
        return _basari_yanit("Hedefler kaydedildi.", url_for("hedefler_sayfasi"))

    veri = json_deposu.oku()
    tempo = istatistikler.tempo_hesapla(veri["oturumlar"])
    return render_template(
        "hedefler.html",
        hedef=veri["hedefler"],
        haftalik=hedefler.haftalik_ilerleme(veri),
        tahmin=istatistikler.bitis_tahmini(
            veri["oturumlar"],
            veri["hedefler"]["toplam_hedef_saat"],
            veri["hedefler"]["haftalik_saat"],
        ),
        yol_ozeti=yol_haritasi.ozet(veri, tempo),
        gecmis=hedef_gecmisi.listele(veri),
        gecmis_ozeti=hedef_gecmisi.ozet(veri),
    )


# --- Geçmiş -----------------------------------------------------------------

@app.route("/gecmis")
def gecmis_sayfasi():
    veri = json_deposu.oku()
    oturumlar = sorted(
        veri["oturumlar"], key=lambda o: (o.get("tarih", ""), o.get("bitis", "")), reverse=True
    )
    return render_template(
        "gecmis.html", oturumlar=oturumlar[:300], kategoriler=kategori_servisi.adlar(veri),
        renkler=kategori_servisi.renk_haritasi(veri),
        toplam=len(oturumlar),
    )


@app.route("/yil-ozeti")
def yil_ozeti_sayfasi():
    veri = json_deposu.oku()
    try:
        yil = int(request.args.get("yil") or dt.date.today().year)
    except (TypeError, ValueError):
        yil = dt.date.today().year

    return render_template(
        "yil_ozeti.html",
        ozet=yil_ozeti.ozet(veri, yil),
        yillar=yil_ozeti.kullanilabilir_yillar(veri["oturumlar"]),
        renkler=kategori_servisi.renk_haritasi(veri),
        rozetler=yil_ozeti.rozet_secenekleri(veri),
    )


@app.route("/rozet/<anahtar>.svg")
def rozet(anahtar):
    """Yerel rozet üreteci — hiçbir yere yayınlanmaz, kullanıcı indirir."""
    try:
        svg = yil_ozeti.rozet_uret(json_deposu.oku(), anahtar)
    except ValueError:
        return _hata_yanit("Bilinmeyen rozet türü.", 404)
    return Response(svg, mimetype="image/svg+xml",
                    headers={"Cache-Control": "no-store"})


@app.route("/rapor")
def rapor_sayfasi():
    """Yazdırılabilir özet (tarayıcıdan PDF'e aktarılabilir)."""
    hedef_gecmisi.gecmisi_guncelle()
    veri = json_deposu.oku()
    tempo = istatistikler.tempo_hesapla(veri["oturumlar"])
    return render_template(
        "rapor.html",
        istatistik=istatistikler.istatistikleri_hesapla(veri),
        haftalik=hedefler.haftalik_ilerleme(veri),
        yol_ozeti=yol_haritasi.ozet(veri, tempo),
        yol=sorted(veri["yol_haritasi"], key=lambda t: t.get("sira", 0)),
        gecmis=hedef_gecmisi.listele(veri, limit=8),
        renkler=kategori_servisi.renk_haritasi(veri),
        uretim_tarihi=dt.date.today().isoformat(),
    )


# --- Dışa aktarma / yedek ---------------------------------------------------

@app.route("/disa-aktar/csv")
def disa_aktar_csv():
    icerik = izleme_ayarlari.oturumlari_csv_yap()
    return Response(
        icerik, mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=gelisim-takip-oturumlar.csv"},
    )


@app.route("/disa-aktar/json")
def disa_aktar_json():
    return Response(
        izleme_ayarlari.tum_veriyi_json_yap(), mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=gelisim-takip-veri.json"},
    )


@app.route("/yedek/geri-yukle", methods=["POST"])
def yedek_geri_yukle():
    dosya = request.form.get("dosya", "")
    try:
        json_deposu.yedekten_geri_yukle(dosya)
    except (FileNotFoundError, ValueError) as hata:
        return _hata_yanit(str(hata), 400)
    return _basari_yanit("Yedek geri yüklendi.", url_for("ayarlar_sayfasi"))


@app.route("/api-anahtari/yenile", methods=["POST"])
def api_anahtari_yenile():
    api_anahtari.anahtari_yenile()
    return _basari_yanit(
        "Yeni anahtar üretildi. Tarayıcı eklentisine yeniden yapıştırman gerekiyor.",
        url_for("ayarlar_sayfasi"),
    )


# --- JSON API ---------------------------------------------------------------

@app.route("/api/durum")
def api_durum():
    """Arayüzün canlı kalması için yoklanan uç nokta.

    Bu olmadan otomatik başlayan oturum ekranda görünmüyor ve daha kötüsü,
    kapanmış bir oturumun sayacı saymaya devam ediyordu.
    """
    veri = json_deposu.oku()
    seri = istatistikler.seri_hesapla(veri["oturumlar"], veri["ayarlar"].get("seri_esigi_dakika"))
    return jsonify({
        "aktif_oturumlar": _aktif_oturum_gorunumu(veri),
        "baslatilabilir": [k for k in kategori_servisi.adlar(veri) if k not in veri["aktif_oturumlar"]],
        "bugun_dakika": seri["bugun_dakika"],
        "seri": seri,
        "haftalik": hedefler.haftalik_ilerleme(veri),
        "izleme_duraklatildi": otomatik_izleme.duraklatildi_mi(),
        "pomodoro": pomodoro.durum(veri),
        "sunucu_zamani": zaman_takibi.simdi().isoformat(),
    })


@app.route("/api/pomodoro", methods=["POST"])
def api_pomodoro():
    govde = request.json or request.form or {}
    eylem = govde.get("eylem")
    if eylem == "baslat":
        pomodoro.baslat()
    elif eylem == "durdur":
        pomodoro.durdur()
    elif eylem == "atla":
        pomodoro.atla()
    else:
        return _hata_yanit("Bilinmeyen pomodoro eylemi.", 400)
    return jsonify({"tamam": True, "pomodoro": pomodoro.durum()})


@app.route("/api/izleme/duraklat", methods=["POST"])
def api_izleme_duraklat():
    govde = request.json or {}
    if govde.get("devam"):
        otomatik_izleme.devam_et()
        return jsonify({"tamam": True, "duraklatildi": False})
    otomatik_izleme.duraklat()
    return jsonify({"tamam": True, "duraklatildi": True})


# --- Tarayıcı eklentisi API'si ---------------------------------------------

@app.route("/api/izleme-ayarlari", methods=["GET", "OPTIONS"])
def api_izleme_ayarlari():
    if request.method == "OPTIONS":
        return _eklenti_yaniti({"tamam": True})
    sunulan = request.headers.get("X-Api-Anahtari") or request.args.get("anahtar")
    if not api_anahtari.dogrula(sunulan):
        return _eklenti_yaniti({"tamam": False, "hata": "Geçersiz API anahtarı"}, 403)
    veri = json_deposu.oku()
    return _eklenti_yaniti({
        "siteler": veri["izleme"]["siteler"],
        "kalp_atisi_saniye": 15,
    })


@app.route("/api/site-durumu", methods=["POST", "OPTIONS"])
def api_site_durumu():
    if request.method == "OPTIONS":
        return _eklenti_yaniti({"tamam": True})
    sunulan = request.headers.get("X-Api-Anahtari") or request.args.get("anahtar")
    if not api_anahtari.dogrula(sunulan):
        return _eklenti_yaniti({"tamam": False, "hata": "Geçersiz API anahtarı"}, 403)

    gelen = request.get_json(silent=True) or {}
    kategori = (gelen.get("kategori") or "").strip()
    durum = gelen.get("durum")
    if not kategori or durum not in ("acik", "kapandi"):
        return _eklenti_yaniti({"tamam": False, "hata": "Geçersiz istek"}, 400)
    if not kategori_servisi.gecerli_mi(kategori):
        return _eklenti_yaniti({"tamam": False, "hata": "Bilinmeyen kategori"}, 400)
    otomatik_izleme.site_durumu_bildir(kategori, durum)
    return _eklenti_yaniti({"tamam": True})


def uygulamayi_hazirla():
    """Sunucu başlamadan önce çağrılır (izleme motorunu başlatır).

    İçe aktarma yan etkisi olarak çalışmaz: testler ``import app`` yaptığında
    gerçek süreç taraması başlayıp gerçek veriye yazmasın diye.
    """
    otomatik_izleme.baslat()


if __name__ == "__main__":
    uygulamayi_hazirla()
    app.run(port=config.UYGULAMA_PORTU, debug=config.HATA_AYIKLAMA, use_reloader=False)
