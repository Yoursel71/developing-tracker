(function () {
  const sayaclar = document.querySelectorAll(".sayac");
  if (!sayaclar.length) return;

  function guncelle() {
    sayaclar.forEach((eleman) => {
      const baslangic = new Date(eleman.dataset.baslangic);
      const fark = Math.max(0, Math.floor((Date.now() - baslangic.getTime()) / 1000));
      const saat = String(Math.floor(fark / 3600)).padStart(2, "0");
      const dakika = String(Math.floor((fark % 3600) / 60)).padStart(2, "0");
      const saniye = String(fark % 60).padStart(2, "0");
      eleman.textContent = `${saat}:${dakika}:${saniye}`;
    });
  }

  guncelle();
  setInterval(guncelle, 1000);
})();
