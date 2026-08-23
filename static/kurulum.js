document.addEventListener("DOMContentLoaded", () => {
  function editorSatiriEkle(programAdi, islemAdi) {
    const sablon = document.getElementById("editor-satir-sablonu");
    const grup = document.getElementById("editor-satirlari");
    if (!sablon || !grup) return;
    const satir = sablon.content.firstElementChild.cloneNode(true);
    const girdiler = satir.querySelectorAll("input");
    girdiler[0].value = programAdi || "";
    girdiler[1].value = islemAdi || "";
    grup.appendChild(satir);
  }

  function siteSatiriEkle() {
    const sablon = document.getElementById("site-satir-sablonu");
    const grup = document.getElementById("site-satirlari");
    if (!sablon || !grup) return;
    grup.appendChild(sablon.content.firstElementChild.cloneNode(true));
  }

  document.body.addEventListener("click", (e) => {
    if (e.target.classList.contains("satir-sil")) {
      e.target.closest(".satir").remove();
      return;
    }
    if (e.target.classList.contains("hizli-editor-btn")) {
      editorSatiriEkle(e.target.dataset.programAdi, e.target.dataset.islemAdi);
      return;
    }
    if (e.target.classList.contains("site-satir-ekle-btn")) {
      siteSatiriEkle();
      return;
    }
  });

  // --- Sihirbaz adım geçişleri (yalnızca kurulum.html'de bulunur) ---
  const adimlar = document.querySelectorAll(".adim");
  if (!adimlar.length) return;

  const noktalar = document.querySelectorAll(".adim-nokta");
  let mevcutAdim = 0;

  function adimGoster(indeks) {
    adimlar.forEach((adim, i) => {
      adim.classList.toggle("aktif", i === indeks);
      adim.classList.toggle("solda", i < indeks);
    });
    noktalar.forEach((nokta, i) => nokta.classList.toggle("aktif", i <= indeks));
    mevcutAdim = indeks;
  }

  document.body.addEventListener("click", (e) => {
    if (e.target.classList.contains("ileri-btn") && mevcutAdim < adimlar.length - 1) {
      adimGoster(mevcutAdim + 1);
    }
    if (e.target.classList.contains("geri-btn") && mevcutAdim > 0) {
      adimGoster(mevcutAdim - 1);
    }
  });

  adimGoster(0);
});
