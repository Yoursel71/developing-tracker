const API_TABANI = "http://127.0.0.1:57391";

let siteler = [];
const sekmeKategorileri = new Map(); // tabId -> kategori | null
const acikKategoriSayaci = new Map(); // kategori -> açık sekme sayısı

function eslesenKategori(url) {
  let hostname;
  try {
    hostname = new URL(url).hostname.toLowerCase();
  } catch (hata) {
    return null;
  }
  for (const site of siteler) {
    const alanAdi = (site.alan_adi || "").toLowerCase();
    if (alanAdi && (hostname === alanAdi || hostname.endsWith("." + alanAdi))) {
      return site.kategori;
    }
  }
  return null;
}

async function ayarlariYenile() {
  try {
    const yanit = await fetch(`${API_TABANI}/api/izleme-ayarlari`);
    const veri = await yanit.json();
    siteler = veri.siteler || [];
  } catch (hata) {
    // Masaüstü uygulaması kapalı olabilir; sessizce yoksay, bir sonraki
    // alarm'da tekrar denenecek.
  }
}

async function siteDurumuBildir(kategori, durum) {
  try {
    await fetch(`${API_TABANI}/api/site-durumu`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kategori, durum }),
    });
  } catch (hata) {
    // Masaüstü uygulaması kapalı olabilir; sessizce yoksay.
  }
}

function kategoriSayaciniGuncelle(eskiKategori, yeniKategori) {
  if (eskiKategori === yeniKategori) return;

  if (eskiKategori) {
    const sayi = (acikKategoriSayaci.get(eskiKategori) || 1) - 1;
    if (sayi <= 0) {
      acikKategoriSayaci.delete(eskiKategori);
      siteDurumuBildir(eskiKategori, "kapandi");
    } else {
      acikKategoriSayaci.set(eskiKategori, sayi);
    }
  }

  if (yeniKategori) {
    const sayi = (acikKategoriSayaci.get(yeniKategori) || 0) + 1;
    acikKategoriSayaci.set(yeniKategori, sayi);
    if (sayi === 1) {
      siteDurumuBildir(yeniKategori, "acik");
    }
  }
}

function sekmeyiDegerlendir(tabId, url) {
  const yeniKategori = url ? eslesenKategori(url) : null;
  const eskiKategori = sekmeKategorileri.get(tabId) || null;
  if (yeniKategori === eskiKategori) return;
  sekmeKategorileri.set(tabId, yeniKategori);
  kategoriSayaciniGuncelle(eskiKategori, yeniKategori);
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url || changeInfo.status === "complete") {
    sekmeyiDegerlendir(tabId, tab.url);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  const eskiKategori = sekmeKategorileri.get(tabId) || null;
  sekmeKategorileri.delete(tabId);
  if (eskiKategori) kategoriSayaciniGuncelle(eskiKategori, null);
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "kalp-atisi") {
    for (const kategori of acikKategoriSayaci.keys()) {
      siteDurumuBildir(kategori, "acik");
    }
  } else if (alarm.name === "ayarlari-yenile") {
    ayarlariYenile();
  }
});

async function baslat() {
  await ayarlariYenile();
  const sekmeler = await chrome.tabs.query({});
  for (const sekme of sekmeler) {
    sekmeyiDegerlendir(sekme.id, sekme.url);
  }
  // Not: periodInMinutes < 1 yalnızca "paketlenmemiş" (geliştirici modu)
  // eklentilerde desteklenir. Chrome Web Store'a yayınlanacaksa bu değer
  // en az 1 dakikaya çıkarılmalı.
  chrome.alarms.create("kalp-atisi", { periodInMinutes: 0.25 });
  chrome.alarms.create("ayarlari-yenile", { periodInMinutes: 5 });
}

chrome.runtime.onInstalled.addListener(baslat);
chrome.runtime.onStartup.addListener(baslat);
baslat();
