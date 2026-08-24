const alan = document.getElementById("anahtar");
const durum = document.getElementById("durum");

chrome.storage.local.get(["apiAnahtari", "sonHata"]).then((saklanan) => {
  alan.value = saklanan.apiAnahtari || "";
  if (saklanan.sonHata) {
    durum.textContent = saklanan.sonHata;
    durum.className = "durum hata";
  }
});

document.getElementById("kaydet").addEventListener("click", async () => {
  const deger = alan.value.trim();
  if (!deger) {
    durum.textContent = "Anahtar boş olamaz.";
    durum.className = "durum hata";
    return;
  }

  await chrome.storage.local.set({ apiAnahtari: deger, sonHata: "" });

  try {
    const yanit = await fetch("http://127.0.0.1:57391/api/izleme-ayarlari", {
      headers: { "X-Api-Anahtari": deger },
    });
    if (yanit.ok) {
      const veri = await yanit.json();
      const adet = (veri.siteler || []).length;
      durum.textContent = `Bağlandı — ${adet} site izleniyor.`;
      durum.className = "durum ok";
    } else if (yanit.status === 403) {
      durum.textContent = "Anahtar reddedildi. Ayarlar sayfasından tekrar kopyala.";
      durum.className = "durum hata";
    } else {
      durum.textContent = `Uygulama ${yanit.status} döndürdü.`;
      durum.className = "durum hata";
    }
  } catch (hata) {
    durum.textContent = "Uygulamaya ulaşılamadı — Gelişim Takip açık mı?";
    durum.className = "durum hata";
  }
});
