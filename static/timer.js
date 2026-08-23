(function () {
  const sayac = document.getElementById("sayac");
  if (!sayac) return;
  const baslangic = new Date(sayac.dataset.baslangic);

  function guncelle() {
    const fark = Math.max(0, Math.floor((Date.now() - baslangic.getTime()) / 1000));
    const saat = String(Math.floor(fark / 3600)).padStart(2, "0");
    const dakika = String(Math.floor((fark % 3600) / 60)).padStart(2, "0");
    const saniye = String(fark % 60).padStart(2, "0");
    sayac.textContent = `${saat}:${dakika}:${saniye}`;
  }

  guncelle();
  setInterval(guncelle, 1000);
})();
