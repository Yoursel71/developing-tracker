/* Bağımlılıksız SVG grafikler.
 *
 * Uygulama çevrimdışı bir .exe olarak çalıştığı için CDN'den grafik
 * kütüphanesi çekilemez; grafikler burada elle çizilir.
 */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";

  function ogeYap(ad, ozellikler) {
    var oge = document.createElementNS(NS, ad);
    Object.keys(ozellikler || {}).forEach(function (anahtar) {
      oge.setAttribute(anahtar, ozellikler[anahtar]);
    });
    return oge;
  }

  function svgYap(genislik, yukseklik) {
    var svg = ogeYap("svg", {
      viewBox: "0 0 " + genislik + " " + yukseklik,
      class: "grafik",
      preserveAspectRatio: "none",
      role: "img",
    });
    svg.style.height = yukseklik + "px";
    return svg;
  }

  function sureMetni(dakika) {
    if (dakika <= 0) return "0 dk";
    var saat = Math.floor(dakika / 60);
    var kalan = Math.round(dakika % 60);
    if (saat && kalan) return saat + "s " + kalan + "dk";
    if (saat) return saat + "s";
    return kalan + " dk";
  }

  /* ---------------------------------------------------- Çizgi/alan grafiği */
  function trendCiz(kap, veri) {
    if (!veri.length) return;

    var G = 600, Y = 150, ust = 10, alt = 22, sol = 4, sag = 4;
    var enBuyuk = Math.max.apply(null, veri.map(function (d) { return d.dakika; }));
    if (enBuyuk <= 0) enBuyuk = 60;

    var svg = svgYap(G, Y);
    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("aria-label", "Son " + veri.length + " günün günlük çalışma süresi");

    var cizimG = G - sol - sag;
    var cizimY = Y - ust - alt;

    // Yatay ızgara
    [0, 0.5, 1].forEach(function (oran) {
      var y = ust + cizimY * oran;
      svg.appendChild(ogeYap("line", {
        x1: sol, y1: y, x2: G - sag, y2: y, class: "izgara",
        "stroke-dasharray": oran === 1 ? "0" : "3 3",
      }));
    });

    function nokta(i, deger) {
      var x = sol + (veri.length === 1 ? cizimG / 2 : (cizimG * i) / (veri.length - 1));
      var y = ust + cizimY - (cizimY * deger) / enBuyuk;
      return [x, y];
    }

    var noktalar = veri.map(function (d, i) { return nokta(i, d.dakika); });
    var cizgiYolu = noktalar.map(function (n, i) {
      return (i === 0 ? "M" : "L") + n[0].toFixed(1) + " " + n[1].toFixed(1);
    }).join(" ");

    var alanYolu = cizgiYolu +
      " L" + noktalar[noktalar.length - 1][0].toFixed(1) + " " + (ust + cizimY) +
      " L" + noktalar[0][0].toFixed(1) + " " + (ust + cizimY) + " Z";

    svg.appendChild(ogeYap("path", { d: alanYolu, class: "alan" }));
    svg.appendChild(ogeYap("path", { d: cizgiYolu, class: "cizgi", "vector-effect": "non-scaling-stroke" }));

    // İlk/orta/son tarih etiketi
    [0, Math.floor(veri.length / 2), veri.length - 1].forEach(function (i, sira) {
      var parcalar = veri[i].tarih.split("-");
      var metin = ogeYap("text", {
        x: nokta(i, 0)[0], y: Y - 6,
        "text-anchor": sira === 0 ? "start" : (sira === 2 ? "end" : "middle"),
      });
      metin.textContent = parcalar[2] + "." + parcalar[1];
      svg.appendChild(metin);
    });

    kap.appendChild(svg);

    var ozet = document.createElement("p");
    ozet.style.cssText = "font-size:var(--olcek-xs);color:var(--metin-2);margin-top:var(--bosluk-2)";
    var toplam = veri.reduce(function (t, d) { return t + d.dakika; }, 0);
    ozet.textContent = "Toplam " + sureMetni(toplam) + " · en yoğun gün " + sureMetni(enBuyuk);
    kap.appendChild(ozet);
  }

  /* ------------------------------------------------------- Çubuk grafiği */
  function cubukCiz(kap, veri, etiketAl, degerAl, aciklama, vurguAl) {
    if (!veri.length) return;

    var G = 600, Y = 140, ust = 8, alt = 20;
    var enBuyuk = Math.max.apply(null, veri.map(degerAl));
    if (enBuyuk <= 0) enBuyuk = 1;

    var svg = svgYap(G, Y);
    svg.setAttribute("aria-label", aciklama);

    var bosluk = 3;
    var genislik = (G - bosluk * (veri.length - 1)) / veri.length;
    var cizimY = Y - ust - alt;

    veri.forEach(function (d, i) {
      var deger = degerAl(d);
      var yukseklik = Math.max((cizimY * deger) / enBuyuk, deger > 0 ? 2 : 0);
      var x = i * (genislik + bosluk);

      var vurgulu = typeof vurguAl === "function" && vurguAl(d);
      var cubuk = ogeYap("rect", {
        x: x.toFixed(1), y: (ust + cizimY - yukseklik).toFixed(1),
        width: genislik.toFixed(1), height: yukseklik.toFixed(1),
        rx: 2, class: vurgulu ? "cubuk vurgulu" : "cubuk",
      });
      var baslik = ogeYap("title");
      baslik.textContent = etiketAl(d) + ": " + sureMetni(deger);
      cubuk.appendChild(baslik);
      svg.appendChild(cubuk);

      if (veri.length <= 12 || i % 3 === 0) {
        var metin = ogeYap("text", {
          x: (x + genislik / 2).toFixed(1), y: Y - 6, "text-anchor": "middle",
        });
        metin.textContent = etiketAl(d);
        svg.appendChild(metin);
      }
    });

    kap.appendChild(svg);
  }

  /* ------------------------------------------------------------ Başlangıç */
  function veriOku(kap) {
    try { return JSON.parse(kap.dataset.veri || "[]"); } catch (h) { return []; }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var trend = document.getElementById("trend-grafik");
    if (trend) trendCiz(trend, veriOku(trend));

    var gun = document.getElementById("gun-grafik");
    if (gun) {
      cubukCiz(gun, veriOku(gun),
        function (d) { return d.kisa; },
        function (d) { return d.dakika; },
        "Haftanın günlerine göre toplam çalışma süresi");
    }

    var saat = document.getElementById("saat-grafik");
    if (saat) {
      cubukCiz(saat, veriOku(saat),
        function (d) { return String(d.saat).padStart(2, "0"); },
        function (d) { return d.dakika; },
        "Gün içi saatlere göre çalışma dağılımı");
    }

    var hafta = document.getElementById("hafta-grafik");
    if (hafta) {
      cubukCiz(hafta, veriOku(hafta),
        function (d) { return d.etiket; },
        function (d) { return d.dakika; },
        "Son 8 haftanın toplam çalışma süresi",
        function (d) { return d.bu_hafta; });
    }

    var ay = document.getElementById("ay-grafik");
    if (ay) {
      cubukCiz(ay, veriOku(ay),
        function (d) { return d.etiket; },
        function (d) { return d.dakika; },
        "Aylara göre çalışma süresi");
    }
  });
})();
