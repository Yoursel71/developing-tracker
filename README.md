# Gelişim Takip

Python/yazılım öğrenme sürecinde harcanan zamanı **dürüstçe** ölçen bir
Windows masaüstü uygulaması. Kod yazdığın programı ya da kurs siteni
açtığında zamanlayıcı kendiliğinden başlar, klavyeden elini çektiğinde
duraklar, kapattığında durur.

![Panel](https://img.shields.io/badge/arayüz-koyu%20tema-1f6feb) ![Test](https://img.shields.io/badge/test-157%20passing-3fb950)

## Ne yapar

- **Otomatik zaman takibi** — VS Code, PyCharm gibi programlar açıkken ya da
  Udemy gibi kurs siteleri sekmede açıkken süre kendiliğinden işler.
- **Boşta kalma algılama** — 10 dakika (ayarlanabilir) klavye/fare hareketi
  olmazsa sayaç duraklar. Gece açık unutulan editör saat yazmaz; bu olmadan
  tüm istatistikler anlamsızlaşırdı.
- **GitHub tarzı ısı haritası** — 7 satır × 53 hafta, kendi dağılımına göre
  ölçeklenen renkler, GitHub commit'lerin ikinci katman olarak.
- **Seri (streak)** — ardışık çalışma günleri, güncel ve en uzun seri.
- **İstatistikler** — günlük trend, kategori dağılımı, "en verimli günün
  Salı", "en çok 21:00–22:00 arası çalışıyorsun".
- **Akıllı tahmin** — mevcut tempoyla ve haftalık hedefine uyarsan olmak
  üzere iki senaryo, iyimser–kötümser aralık ve tahmini tarih.
- **Öğrenme yol haritası** — her biri tahmini saatli konular; toplam hedef
  bunlardan hesaplanır ve "sıradaki konuyu ~3 günde bitirirsin" der.
- **Oturum notları ve düzenleme** — yanlış kaydı düzelt, sil veya elle ekle.

## Kurulum (Windows)

1. Depo → **Releases** → **Gelişim Takip — Masaüstü (son derleme)**
2. `GelisimTakip.exe` dosyasını indir ve çalıştır.
3. İlk açılışta kurulum sihirbazı hedeflerini, GitHub kullanıcı adını ve
   takip edilecek program/siteleri sorar.

> **SmartScreen uyarısı:** `.exe` imzalı olmadığı için Windows "bilinmeyen
> yayımcı" uyarısı gösterir. "Daha fazla bilgi" → "Yine de çalıştır" ile
> açabilirsin.

Uygulama pencereyi kapatınca **sistem tepsisine iner** ve takibe devam
eder; tamamen çıkmak için tepsi ikonuna sağ tıklayıp "Çıkış" de.
Ayarlar'dan "Windows açılışında otomatik başlat" seçeneğini açabilirsin.

## Tarayıcı eklentisi (kurs siteleri için)

Site takibi için `tarayici-eklentisi/` klasöründeki eklentiyi kurman
gerekir — adımlar [tarayici-eklentisi/README.md](tarayici-eklentisi/README.md)
dosyasında. Eklenti, Ayarlar sayfasındaki **API anahtarını** ister; bu
anahtar olmadan hiçbir site uygulamaya veri gönderemez.

## Verilerin nerede

| Ortam | Konum |
|---|---|
| Windows (.exe) | `%LOCALAPPDATA%\GelisimTakip\` |
| macOS | `~/Library/Application Support/GelisimTakip/` |
| Linux | `~/.local/share/GelisimTakip/` |
| Geliştirme | depo içindeki `data/` |

Bu klasörde `veri.json`, `yedekler/` ve `uygulama.log` bulunur. Veri
**atomik olarak** yazılır (çökme yarım dosya bırakmaz), günde bir yedek
alınır (son 10 tutulur) ve dosya bozulursa otomatik olarak en yeni sağlam
yedeğe dönülür. Ayarlar'dan CSV/JSON dışa aktarabilir, yedekten geri
yükleyebilirsin.

`GELISIM_TAKIP_VERI_DIZINI` ortam değişkeniyle konumu değiştirebilirsin.
`.exe`'nin yanına `tasinabilir.txt` koyarsan veri exe'nin yanına yazılır
(USB'den taşınabilir kullanım).

## Kaynaktan çalıştırma

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python app.py        # tarayıcı sürümü → http://127.0.0.1:57391
python masaustu.py   # native pencere + tepsi ikonu (Windows)
python -m pytest testler/
```

## Nasıl çalışır

**Zaman ölçümü.** Aktif oturum her tarama turunda (10 sn) diske işaretlenir:
`son_gorulme` ve `birikmis_saniye`. Böylece çökmede tüm oturum değil, en
fazla bir tur kaybedilir; açılışta eski `son_gorulme` taşıyan oturumlar
otomatik kapatılır. Bu olmadan Cuma çöken bir uygulama Pazartesi 63 saatlik
sahte bir oturum yazardı.

**Durum makinesi.**

```
YOK ──(program/site algılandı)──> ÇALIŞIYOR
ÇALIŞIYOR ──(boşta eşiği)──> BOŞTA           # süre birikmez
BOŞTA ──(klavye/fare)──> ÇALIŞIYOR           # kesintisiz devam
ÇALIŞIYOR ──(algılanmıyor)──> KAYIP          # 60 sn grace
KAYIP ──(tekrar algılandı)──> ÇALIŞIYOR
KAYIP ──(grace doldu)──> YOK                 # oturum kaydedilir
```

Kısa molalar geçmişi onlarca parçaya bölmez; gece yarısını geçen oturumlar
gün sınırında bölünür (yoksa Pazar gecesi çalışması önceki haftaya yazılırdı).
Bir program yalnızca **tek bir** kategoriye bağlanabilir — aksi hâlde aynı
süre iki kez sayılırdı.

## Bilinen sınırlamalar

- **Boşta algılama, tepsi ikonu ve Windows açılışı yalnızca Windows'ta**
  çalışır. Linux/macOS'ta uygulama çalışır ama kullanıcı hiç boşta sayılmaz.
- Site takibi tarayıcı eklentisi olmadan çalışmaz.
- GitHub'ın herkese açık Events API'si yalnızca **son ~90 günü** ve yalnızca
  herkese açık push etkinliklerini döndürür; saatte 60 istek sınırı vardır
  (veri 1 saat önbelleklenir). `GITHUB_TOKEN` ortam değişkeniyle sınırı
  artırabilirsin.
- Uygulama sabit `57391` portunu kullanır (`GELISIM_TAKIP_PORT` ile
  değiştirilebilir). İkinci bir örnek açılmaz; veri bozulmasını önlemek için
  tek örnek kilidi vardır.

## Proje yapısı

```
app.py                  Flask rotaları ve JSON API
masaustu.py             pywebview + tepsi giriş noktası (.exe)
config.py               sabitler ve yol yardımcıları
depo/                   JSON deposu, şema göçü, varsayılanlar
servisler/              zaman takibi, izleme motoru, istatistik, doğrulama
platform_katmani/       Windows'a özgü kod (boşta, tepsi, autostart, yollar)
templates/ static/      arayüz
tarayici-eklentisi/     Chrome/Edge eklentisi (Manifest V3)
testler/                pytest paketi
```
