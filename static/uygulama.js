/* Gelişim Takip — arayüz davranışı
 *
 * Önemli: sayaç ve aktif oturum listesi sunucudan düzenli olarak yenilenir.
 * Bu olmadan otomatik başlayan oturum ekranda hiç görünmüyordu ve daha kötüsü,
 * izleyici oturumu kapattıktan sonra bile sayaç saymaya devam edip yanlış
 * veri gösteriyordu.
 */
(function () {
  "use strict";

  var YOKLAMA_MS = 3000;

  // ---------------------------------------------------------------- Toast
  function toast(mesaj, tur) {
    var alan = document.getElementById("toast-alani");
    if (!alan || !mesaj) return;
    var kutu = document.createElement("div");
    kutu.className = "toast" + (tur === "hata" ? " hata" : "");
    kutu.setAttribute("role", tur === "hata" ? "alert" : "status");
    kutu.textContent = mesaj;
    alan.appendChild(kutu);
    setTimeout(function () {
      kutu.classList.add("cikis");
      setTimeout(function () { kutu.remove(); }, 220);
    }, tur === "hata" ? 6000 : 3600);
  }

  (window.BASLANGIC_BILDIRIMLERI || []).forEach(function (parca) {
    toast(parca[1], parca[0] === "hata" ? "hata" : "basari");
  });

  // ------------------------------------------------------------- Sayaçlar
  function sureMetni(saniye) {
    var s = Math.max(0, Math.floor(saniye));
    var saat = String(Math.floor(s / 3600)).padStart(2, "0");
    var dk = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
    var sn = String(s % 60).padStart(2, "0");
    return saat + ":" + dk + ":" + sn;
  }

  function sayaclariTikla() {
    document.querySelectorAll(".sayac").forEach(function (el) {
      var gecen = parseFloat(el.dataset.gecen || "0");
      // Boştayken sunucu da süreyi artırmıyor; ekran da durmalı.
      if (el.dataset.duruyor !== "1") {
        gecen += 1;
        el.dataset.gecen = String(gecen);
      }
      el.textContent = sureMetni(gecen);
    });
  }

  function sayaclariCiz() {
    document.querySelectorAll(".sayac").forEach(function (el) {
      el.textContent = sureMetni(parseFloat(el.dataset.gecen || "0"));
    });
  }

  // -------------------------------------------------------- Canlı durum
  function oturumKartiHtml(oturum) {
    var kaynakRozeti = oturum.kaynak === "otomatik"
      ? '<span class="rozet rozet-otomatik"><span class="nokta nokta-canli"></span>otomatik</span>'
      : '<span class="rozet rozet-manuel">elle</span>';
    var durumRozeti = oturum.durum_metni
      ? '<span class="rozet rozet-bosta">' + kacis(oturum.durum_metni) + "</span>" : "";

    return '<div class="oturum-kart' + (oturum.duruyor ? " bosta" : "") + '" data-kategori="' +
      kacis(oturum.kategori) + '">' +
      '<div class="oturum-ust"><span class="oturum-kategori">' + kacis(oturum.kategori) + "</span>" +
      kaynakRozeti + durumRozeti + "</div>" +
      '<div class="sayac" role="timer" aria-live="off" data-gecen="' + oturum.gecen_saniye +
      '" data-duruyor="' + (oturum.duruyor ? "1" : "0") + '">' + sureMetni(oturum.gecen_saniye) + "</div>" +
      '<form method="post" action="/oturum/durdur" data-ajax>' +
      '<input type="hidden" name="kategori" value="' + kacis(oturum.kategori) + '">' +
      '<button type="submit" class="btn">Durdur ve kaydet</button>' +
      "</form></div>";
  }

  function kacis(metin) {
    var d = document.createElement("div");
    d.textContent = metin == null ? "" : String(metin);
    return d.innerHTML;
  }

  function durumuUygula(durum) {
    var alan = document.getElementById("aktif-oturumlar");
    if (alan) {
      var mevcut = Array.prototype.map.call(
        alan.querySelectorAll(".oturum-kart"),
        function (k) { return k.dataset.kategori + ":" + (k.classList.contains("bosta") ? "1" : "0"); }
      ).join("|");
      var yeni = durum.aktif_oturumlar.map(function (o) {
        return o.kategori + ":" + (o.duruyor ? "1" : "0");
      }).join("|");

      if (mevcut !== yeni) {
        // Oturum kümesi değişti (otomatik başladı/durdu) → kartları yeniden kur.
        alan.innerHTML = durum.aktif_oturumlar.map(oturumKartiHtml).join("");
      } else {
        // Aynı oturumlar: sayaç değerini sunucuyla senkronla (kayma olmasın).
        durum.aktif_oturumlar.forEach(function (o) {
          var kart = alan.querySelector('.oturum-kart[data-kategori="' + cssKacis(o.kategori) + '"]');
          if (!kart) return;
          var sayac = kart.querySelector(".sayac");
          if (sayac) {
            sayac.dataset.gecen = String(o.gecen_saniye);
            sayac.dataset.duruyor = o.duruyor ? "1" : "0";
          }
        });
      }
      sayaclariCiz();
    }

    metniAyarla("metrik-bugun", Math.round(durum.bugun_dakika) +
      '<span style="font-size:var(--olcek-md);color:var(--metin-3)"> dk</span>', true);
    metniAyarla("metrik-seri", durum.seri.guncel +
      '<span style="font-size:var(--olcek-md);color:var(--metin-3)"> gün</span>', true);

    var dolgu = document.getElementById("hafta-dolgu");
    if (dolgu) dolgu.style.width = durum.haftalik.cubuk_yuzde + "%";

    var kenar = document.getElementById("kenar-durum");
    if (kenar) {
      kenar.textContent = durum.aktif_oturumlar.length
        ? durum.aktif_oturumlar.length + " oturum açık"
        : (durum.izleme_duraklatildi ? "İzleme duraklatıldı" : "İzleme aktif");
    }
  }

  function cssKacis(metin) {
    return String(metin).replace(/["\\]/g, "\\$&");
  }

  function metniAyarla(id, html, htmlMi) {
    var el = document.getElementById(id);
    if (!el) return;
    if (htmlMi) { el.innerHTML = html; } else { el.textContent = html; }
  }

  function durumuYokla() {
    fetch("/api/durum", { headers: { "X-Istek-Turu": "json" } })
      .then(function (y) { return y.ok ? y.json() : null; })
      .then(function (durum) { if (durum) durumuUygula(durum); })
      .catch(function () { /* uygulama kapanıyor olabilir; sessizce geç */ });
  }

  // ------------------------------------------------------------ AJAX form
  function formuGonder(form) {
    var onay = form.dataset.onay;
    if (onay && !window.confirm(onay)) return;

    var buton = form.querySelector('button[type="submit"]');
    if (buton) { buton.classList.add("mesgul"); buton.disabled = true; }

    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { "X-Istek-Turu": "json" },
    })
      .then(function (y) { return y.json().catch(function () { return {}; }); })
      .then(function (sonuc) {
        if (sonuc.tamam) {
          toast(sonuc.mesaj || "Tamam");
          durumuYokla();
        } else {
          toast(sonuc.hata || "İşlem başarısız oldu.", "hata");
        }
      })
      .catch(function () { toast("Sunucuya ulaşılamadı.", "hata"); })
      .finally(function () {
        if (buton) { buton.classList.remove("mesgul"); buton.disabled = false; }
      });
  }

  // ------------------------------------------------- Tekrarlanan satırlar
  function satirEkle(grupId, sablonId, doldur) {
    var grup = document.getElementById(grupId);
    var sablon = document.getElementById(sablonId);
    if (!grup || !sablon) return;
    var satir = sablon.content.firstElementChild.cloneNode(true);
    if (doldur) doldur(satir);
    grup.appendChild(satir);
    var ilk = satir.querySelector("input");
    if (ilk) ilk.focus();
  }

  // --------------------------------------------------- Kurulum sihirbazı
  function sihirbaziKur() {
    var adimlar = Array.prototype.slice.call(document.querySelectorAll(".adim"));
    if (!adimlar.length) return;

    var noktalar = document.querySelectorAll(".adim-nokta");
    var sayac = document.getElementById("adim-sayaci");
    var mevcut = 0;

    function goster(indeks) {
      adimlar.forEach(function (adim, i) { adim.classList.toggle("aktif", i === indeks); });
      noktalar.forEach(function (n, i) { n.classList.toggle("aktif", i <= indeks); });
      if (sayac) sayac.textContent = "Adım " + (indeks + 1) + " / " + adimlar.length;
      mevcut = indeks;
      // Odak yeni adıma taşınmazsa Tab sırası body'ye düşer.
      adimlar[indeks].focus({ preventScroll: true });
    }

    function dogrula(indeks) {
      var eksik = null;
      adimlar[indeks].querySelectorAll("[data-zorunlu]").forEach(function (girdi) {
        if (eksik) return;
        if (!girdi.value.trim()) eksik = girdi;
        else if (girdi.type === "number" && (isNaN(parseFloat(girdi.value)) || parseFloat(girdi.value) < 0)) eksik = girdi;
      });
      if (eksik) {
        toast("Devam etmek için bu alanı doldur.", "hata");
        eksik.focus();
        return false;
      }
      return true;
    }

    document.addEventListener("click", function (olay) {
      if (olay.target.classList.contains("ileri-btn")) {
        if (dogrula(mevcut) && mevcut < adimlar.length - 1) goster(mevcut + 1);
      } else if (olay.target.classList.contains("geri-btn") && mevcut > 0) {
        goster(mevcut - 1);
      }
    });

    // Enter tuşu formu erkenden göndermesin.
    var form = document.getElementById("kurulum-formu");
    if (form) {
      form.addEventListener("keydown", function (olay) {
        if (olay.key === "Enter" && olay.target.tagName === "INPUT") {
          olay.preventDefault();
          if (dogrula(mevcut) && mevcut < adimlar.length - 1) goster(mevcut + 1);
        }
      });
    }

    goster(0);
  }

  // ----------------------------------------------------- Olay bağlantıları
  document.addEventListener("click", function (olay) {
    var hedef = olay.target;

    if (hedef.classList.contains("satir-sil")) {
      var satir = hedef.closest(".satir");
      if (satir) satir.remove();
      return;
    }

    if (hedef.hasAttribute("data-editor-ekle")) {
      satirEkle("editor-satirlari", "editor-satir-sablonu", function (satir) {
        var girdiler = satir.querySelectorAll("input");
        girdiler[0].value = hedef.dataset.program || "";
        girdiler[1].value = hedef.dataset.islem || "";
      });
      return;
    }

    if (hedef.hasAttribute("data-site-ekle")) {
      satirEkle("site-satirlari", "site-satir-sablonu", function (satir) {
        satir.querySelector("input").value = hedef.dataset.alan || "";
      });
      return;
    }

    if (hedef.dataset.satirEkle === "tas") {
      satirEkle("tas-satirlari", "tas-satir-sablonu");
      return;
    }

    if (hedef.dataset.ac) {
      var kutu = document.getElementById(hedef.dataset.ac);
      if (kutu) {
        kutu.hidden = false;
        var ilk = kutu.querySelector("input, select");
        if (ilk) ilk.focus();
      }
      return;
    }

    if (hedef.dataset.kapat) {
      var kapanan = document.getElementById(hedef.dataset.kapat);
      if (kapanan) kapanan.hidden = true;
      return;
    }

    if (hedef.dataset.duzenle) {
      var satirEl = document.getElementById("duzenle-" + hedef.dataset.duzenle);
      if (satirEl) {
        satirEl.hidden = !satirEl.hidden;
        if (!satirEl.hidden) {
          var alan = satirEl.querySelector("input");
          if (alan) alan.focus();
        }
      }
      return;
    }

    if (hedef.dataset.duzenleKapat) {
      var kapat = document.getElementById("duzenle-" + hedef.dataset.duzenleKapat);
      if (kapat) kapat.hidden = true;
      return;
    }

    if (hedef.dataset.kopyala) {
      var kaynak = document.getElementById(hedef.dataset.kopyala);
      if (kaynak && navigator.clipboard) {
        navigator.clipboard.writeText(kaynak.textContent.trim())
          .then(function () { toast("Panoya kopyalandı."); })
          .catch(function () { toast("Kopyalanamadı.", "hata"); });
      }
    }
  });

  document.addEventListener("submit", function (olay) {
    var form = olay.target;
    if (form.hasAttribute("data-ajax")) {
      olay.preventDefault();
      formuGonder(form);
    }
  });

  // ------------------------------------------------------------- Başlangıç
  document.addEventListener("DOMContentLoaded", function () {
    sihirbaziKur();
    sayaclariCiz();

    if (document.getElementById("aktif-oturumlar")) {
      setInterval(sayaclariTikla, 1000);
      setInterval(durumuYokla, YOKLAMA_MS);
      durumuYokla();
    }

    var bugun = document.getElementById("ekle-tarih");
    if (bugun && !bugun.value) bugun.value = new Date().toISOString().slice(0, 10);
  });
})();
