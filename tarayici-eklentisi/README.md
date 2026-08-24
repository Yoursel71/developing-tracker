# Gelişim Takip — Tarayıcı Eklentisi

Ayarlar sayfasında eklediğin kurs sitelerinin (ör. `udemy.com`) bir sekmede
açık olduğunu masaüstü uygulamasına bildirir; böylece o siteye girdiğinde
zamanlayıcı otomatik başlar, sekmeyi kapatınca ~1 dakika içinde durur.

## Kurulum (Chrome / Edge)

1. **Gelişim Takip** masaüstü uygulamasını aç.
2. Uygulamada **Ayarlar → Tarayıcı eklentisi** bölümündeki **API anahtarını**
   kopyala.
3. Tarayıcıda `chrome://extensions` (Edge'de `edge://extensions`) adresine git.
4. Sağ üstten **Geliştirici modu**'nu aç.
5. **Paketlenmemiş öğe yükle** → bu depodaki `tarayici-eklentisi` klasörünü seç.
6. Eklentinin **Ayrıntılar → Uzantı seçenekleri** sayfasını aç, anahtarı
   yapıştır ve **Kaydet**'e bas. "Bağlandı — N site izleniyor" görmelisin.

## Neden anahtar gerekiyor

Anahtar olmadan, ziyaret ettiğin herhangi bir web sitesi yerel uygulamaya
istek gönderip verine sahte oturum ekleyebilir ya da izlediğin site
listesini okuyabilirdi. Eklenti kimliğini bu anahtarla kanıtlar; anahtarsız
istekler `403` ile reddedilir.

Anahtarı Ayarlar'dan yenilersen eklentiye yeni anahtarı tekrar yapıştırman
gerekir.

## Nasıl çalışır

- Açılışta ve her 5 dakikada bir `GET /api/izleme-ayarlari` ile takip
  edilecek alan adı → kategori listesini uygulamadan çeker.
- Takip edilen bir alan adına ait sekme açıldığında `POST /api/site-durumu`
  ile `{"durum": "acik"}` gönderir ve ~15 saniyede bir kalp atışı tekrarlar.
- Son eşleşen sekme kapanınca ya da başka siteye gidilince anında
  `{"durum": "kapandi"}` gönderir.
- Uygulama kapalıyken istekler sessizce başarısız olur; uygulama tekrar
  açıldığında eklenti kendiliğinden bağlanır.

## Sınırlamalar

- Yalnızca `http://127.0.0.1:57391` adresindeki yerel uygulamayla konuşur,
  başka hiçbir yere veri göndermez.
- Chrome Web Store'a paketlenip yayınlanacaksa `arkaplan.js` içindeki kalp
  atışı periyodu (`periodInMinutes: 0.25`) en az `1`'e çıkarılmalı — alt
  dakika alarmlar yalnızca geliştirici modunda desteklenir.
