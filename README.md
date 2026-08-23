# Gelişim Takip Uygulaması

Python/yazılım öğrenme sürecinde harcanan zamanı takip eden, GitHub
aktivitesiyle görselleştiren, kod yazdığın program veya kurs sitesini
açtığında zamanlayıcıyı **otomatik başlatıp durduran** ve tempoya göre
tahmin üreten bir masaüstü uygulaması.

## .exe olarak indirme (Windows)

Her push'ta GitHub Actions (`.github/workflows/exe-derle.yml`) Windows
üzerinde otomatik bir `.exe` derler ve **Releases** sayfasındaki
`masaustu-son-surum` adlı release'i günceller — bu release her zaman en son
commit'ten üretilen `.exe`'yi içerir:

1. Depo → sağ taraftaki **Releases** bölümü → "Gelişim Takip - Masaüstü
   (son derleme)".
2. Ekli `GelisimTakip.exe` dosyasını indir ve çalıştır.

Alternatif olarak: Depo → **Actions** sekmesi → en son "exe-derle"
çalıştırması → **Artifacts** bölümünden `GelisimTakip-exe` indirilebilir
(bu artifact 90 gün sonra otomatik silinir, release ise kalıcıdır).

İlk açılışta bir kurulum sihirbazı seni karşılar: hedeflerini, GitHub
kullanıcı adını, kod yazdığın program(lar)ı ve kurs aldığın site(leri)
sorar. Bunlardan sonra zamanlayıcı, o program/site açıkken **otomatik**
çalışır; kapatınca (yaklaşık 1 dakika içinde) durur. Ayarları daha sonra
uygulama içindeki **Ayarlar** sayfasından değiştirebilirsin.

Kurs sitesi takibinin çalışması için ayrıca tarayıcı eklentisini kurman
gerekir — bkz. `tarayici-eklentisi/README.md`.

## Kaynaktan çalıştırma (geliştirme / diğer işletim sistemleri)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py       # tarayıcıda çalışan Flask sürümü (http://127.0.0.1:57391)
# veya
python masaustu.py  # native pencereli masaüstü sürümü (yalnızca Windows'ta pencere açar)
```

`pywebview` ve `pywin32` Windows'a özgü masaüstü kabuğu içindir; sadece
`app.py`'yi çalıştırmak (tarayıcı sürümü) her işletim sisteminde çalışır.

## Veri

Tüm veriler `data/veri.json` dosyasında saklanır (ilk çalıştırmada otomatik
oluşturulur, `.gitignore` ile depoya dahil edilmez). `data/veri.ornek.json`
dosyası şemayı göstermek için örnek olarak bırakılmıştır.

## Otomatik İzleme

- **Programlar**: Arka planda ~10 saniyede bir çalışan işlemler taranır
  (`psutil`). Ayarlar'da eklediğin bir programın işlemi (ör. `Code.exe`)
  çalışıyorsa, eşlediğin kategori için zamanlayıcı otomatik başlar.
- **Siteler**: Tarayıcı eklentisi, takip edilen bir alan adına (ör.
  `udemy.com`) ait sekme açıkken ~15 saniyede bir uygulamaya haber verir.
- Program/site sadece minimize edilir ya da arka plana alınırsa (hâlâ
  çalışıyor/sekme açık) oturum **süresiz** devam eder. Program kapatılır ya
  da sekme kapanırsa/uzaklaşılırsa **1 dakika** grace süresi sonunda oturum
  kapanır; bu süre içinde geri gelinirse oturum kesintisiz sürer.
- Birden fazla kategori aynı anda aktif olabilir (ör. editör + kurs sitesi
  aynı anda açıksa).
- Bir otomatik oturumu elle "Durdur" ile kesersen, o kategori 10 dakika
  boyunca yeniden otomatik başlatılmaz.
- Uygulama penceresi kapatıldığında tüm açık oturumlar kapatılır.

## GitHub Entegrasyonu

`config.py` içindeki `GITHUB_KULLANICI` değeri (varsayılan: `Yoursel71`,
kurulum sihirbazından değiştirilebilir) kullanılarak GitHub'ın herkese açık
Events API'sinden (`/users/{kullanici}/events/public`) push etkinlikleri
çekilir. Bu API kimlik doğrulama gerektirmez ancak:

- Sadece **son ~90 günlük** etkinliği döner (GitHub'ın kendi sınırlaması).
- Saatte 60 istek limiti vardır; bu yüzden veri 1 saatliğine önbelleklenir
  (`data/veri.json` içindeki `github.son_senkron` alanı üzerinden).
- İstatistikler sayfasındaki "GitHub'ı Yenile" butonu önbelleği aşarak
  anında yeniden çeker.

Rate limit'i artırmak isterseniz `GITHUB_TOKEN` ortam değişkenini
ayarlayabilirsiniz (zorunlu değildir).

## Bildirimler

Haftalık hedef karşılanmadığında, haftanın son 2 gününde (Cumartesi/Pazar)
günde en fazla 1 kez masaüstü bildirimi gönderilir (`plyer` ile). Bildirim
API'sinin desteklenmediği ortamlarda (ör. sunucu/konteyner) hata sessizce
loglanır, uygulama çökmez.

## Modüller

- **Kurulum Sihirbazı**: İlk açılışta hedefler, GitHub kullanıcı adı,
  izlenecek program(lar) ve site(ler) sorulur; animasyonlu, adım adım.
- **Zaman Takibi**: Elle Başlat/Durdur ya da otomatik izleme; birden fazla
  kategori aynı anda aktif olabilir, her biri kendi canlı sayacıyla.
- **Isı Haritası**: Manuel süreye göre renklendirilmiş grid (haftalık/aylık
  görünüm), GitHub commit günleri aynı grid üzerinde ikincil işaret olarak
  gösterilir.
- **GitHub Entegrasyonu**: Yukarıda açıklandığı gibi.
- **Hedefler**: Haftalık ve toplam hedef saat belirleme, ilerleme yüzdesi.
- **İstatistikler**: Ortalama süreler, en çok çalışılan gün, kategori
  dağılımı, en aktif repo, tempoya göre tahmini bitiş süresi (ETA).

## Bilinen Sınırlamalar

- Otomatik program/site izleme yalnızca Windows'ta anlamlıdır (`psutil`
  işlem adları Windows'a özgü, ör. `Code.exe`); Linux/Mac'te kaynak koddan
  çalıştırılabilir ama otomatik izleme farklı işlem adları gerektirir.
- Site takibi için tarayıcı eklentisinin ayrıca kurulması gerekir.
- Uygulama sabit `57391` portunu kullanır; bu port başka bir uygulama
  tarafından kullanılıyorsa çakışma olabilir.
