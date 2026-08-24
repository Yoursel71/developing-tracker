const API_TABANI = "http://127.0.0.1:57391";

let siteler = [];
let anahtar = "";
const sekmeKategorileri = new Map(); // tabId -> kategori | null
const acikKategoriSayaci = new Map(); // kategori -> açık sekme sayısı

async function anahtariYukle() {
  const saklanan = await chrome.storage.local.get("apiAnahtari");
  anahtar = saklanan.apiAnahtari || "";
  return anahtar;
}

function eslesenKategori(url) {
  let hostname;
  try {
    hostname = new URL(url).hostname.toLowerCase();
  } catch (hata) {
    return null;
  }
  if (hostname.startsWith("www.")) hostname = hostname.slice(4);

  for (const site of siteler) {
    const alanAdi = (site.alan_adi || "").toLowerCase();
    if (alanAdi && (hostname === alanAdi || hostname.endsWith("." + alanAdi))) {
      return site.kategori;
    }
  }
  return null;
}

async function istek(yol, secenekler = {}) {
  if (!anahtar) await anahtariYukle();
  if (!anahtar) return null;

  try {
    const yanit = await fetch(`${API_TABANI}${yol}`, {
      ...secenekler,
      headers: {
        "Content-Type": "application/json",
        "X-Api-Anahtari": anahtar,
        ...(secenekler.headers || {}),
      },
    });
    if (yanit.status === 403) {
      await chrome.storage.local.set({ sonHata: "Anahtar geçersiz. Ayarlar'dan yeni anahtarı yapıştır." });
      return null;
    }
    await chrome.storage.local.set({ sonHata: "" });
    return await yanit.json();
  } catch (hata) {
    // Masaüstü uygulaması kapalı olabilir; sessizce geç.
    return null;
  }
}

async function ayarlariYenile() {
  const veri = await istek("/api/izleme-ayarlari");
  if (veri && Array.isArray(veri.siteler)) {
    siteler = veri.siteler;
    await tumSekmeleriDegerlendir();
  }
}

async function siteDurumuBildir(kategori, durum) {
  await istek("/api/site-durumu", {
    method: "POST",
    body: JSON.stringify({ kategori, durum }),
  });
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
    if (sayi === 1) siteDurumuBildir(yeniKategori, "acik");
  }
}

function sekmeyiDegerlendir(tabId, url) {
  const yeniKategori = url ? eslesenKategori(url) : null;
  const eskiKategori = sekmeKategorileri.get(tabId) || null;
  if (yeniKategori === eskiKategori) return;
  sekmeKategorileri.set(tabId, yeniKategori);
  kategoriSayaciniGuncelle(eskiKategori, yeniKategori);
}

async function tumSekmeleriDegerlendir() {
  const sekmeler = await chrome.tabs.query({});
  const gecerliIdler = new Set(sekmeler.map((s) => s.id));
  for (const tabId of Array.from(sekmeKategorileri.keys())) {
    if (!gecerliIdler.has(tabId)) {
      const eski = sekmeKategorileri.get(tabId);
      sekmeKategorileri.delete(tabId);
      if (eski) kategoriSayaciniGuncelle(eski, null);
    }
  }
  for (const sekme of sekmeler) {
    sekmeyiDegerlendir(sekme.id, sekme.url);
  }
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

chrome.storage.onChanged.addListener((degisiklikler, alan) => {
  if (alan === "local" && degisiklikler.apiAnahtari) {
    anahtar = degisiklikler.apiAnahtari.newValue || "";
    ayarlariYenile();
  }
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "kalp-atisi") {
    for (const kategori of acikKategoriSayaci.keys()) {
      await siteDurumuBildir(kategori, "acik");
    }
  } else if (alarm.name === "ayarlari-yenile") {
    await ayarlariYenile();
  }
});

async function baslat() {
  await anahtariYukle();
  await ayarlariYenile();
  await tumSekmeleriDegerlendir();

  // periodInMinutes < 1 yalnızca paketlenmemiş (geliştirici modu)
  // eklentilerde desteklenir. Web Store'a yayınlanacaksa en az 1 yapılmalı.
  chrome.alarms.create("kalp-atisi", { periodInMinutes: 0.25 });
  chrome.alarms.create("ayarlari-yenile", { periodInMinutes: 5 });
}

chrome.runtime.onInstalled.addListener(baslat);
chrome.runtime.onStartup.addListener(baslat);
baslat();
