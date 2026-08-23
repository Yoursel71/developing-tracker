# Gelişim Takip — Tarayıcı Eklentisi

Bu eklenti, Ayarlar sayfasında eklediğin kurs sitelerinin (ör. `udemy.com`)
bir sekmede açık olduğunu masaüstü uygulamasına bildirir; böylece o siteye
girdiğinde zamanlayıcı otomatik başlar, sekmeyi kapatınca/siteden
uzaklaşınca ~1 dakika içinde durur.

## Kurulum (Chrome / Edge)

1. Gelişim Takip masaüstü uygulamasını aç (eklenti, `http://127.0.0.1:57391`
   adresindeki uygulamayla konuşur).
2. Tarayıcıda `chrome://extensions` (Edge'de `edge://extensions`) adresine
   git.
3. Sağ üstten **Geliştirici modu**'nu aç.
4. **Paketlenmemiş öğe yükle**'ye tıkla ve bu depodaki `tarayici-eklentisi`
   klasörünü seç.
5. Ayarlar sayfasından ("Kurs Aldığın Site(ler)") eklediğin alan adları artık
   otomatik izlenecek.

## Nasıl çalışır

- Eklenti açılışta ve her 5 dakikada bir `GET /api/izleme-ayarlari`
  ile takip edilecek alan adı → kategori listesini uygulamadan çeker.
- Takip edilen bir alan adına ait bir sekme açıldığında `POST
  /api/site-durumu {"kategori": ..., "durum": "acik"}` gönderir, ~15
  saniyede bir kalp atışı tekrarlar.
- Sekme kapanınca veya başka bir siteye gidince anında `{"durum":
  "kapandi"}` gönderir.
- Uygulama kapalıyken istekler sessizce başarısız olur, hata vermez;
  uygulama tekrar açıldığında eklenti otomatik yeniden bağlanır.

## Sınırlamalar

- Yalnızca `http://127.0.0.1:57391` adresindeki yerel uygulamayla konuşur,
  başka bir yere veri göndermez.
- Chrome Web Store'a paketlenip yayınlanacaksa `arkaplan.js` içindeki kalp
  atışı periyodu (`periodInMinutes: 0.25`) en az `1`'e çıkarılmalı — alt
  dakika alarmlar yalnızca geliştirici modunda desteklenir.
