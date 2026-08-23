# Gelişim Takip Uygulaması

Python/yazılım öğrenme sürecinde harcanan zamanı takip eden, GitHub
aktivitesiyle görselleştiren ve tempoya göre tahmin üreten bir Flask
uygulaması.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma

```bash
python app.py
```

Uygulama varsayılan olarak http://127.0.0.1:5000 adresinde açılır.

## Veri

Tüm veriler `data/veri.json` dosyasında saklanır (ilk çalıştırmada otomatik
oluşturulur, `.gitignore` ile depoya dahil edilmez). `data/veri.ornek.json`
dosyası şemayı göstermek için örnek olarak bırakılmıştır.

## GitHub Entegrasyonu

`config.py` içindeki `GITHUB_KULLANICI` değeri (varsayılan: `Yoursel71`)
kullanılarak GitHub'ın herkese açık Events API'sinden (`/users/{kullanici}/events/public`)
push etkinlikleri çekilir. Bu API kimlik doğrulama gerektirmez ancak:

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

- **Zaman Takibi**: Başlat/Durdur, kategori seçimi, canlı sayaç.
- **Isı Haritası**: Manuel süreye göre renklendirilmiş grid (haftalık/aylık
  görünüm), GitHub commit günleri aynı grid üzerinde ikincil işaret olarak
  gösterilir.
- **GitHub Entegrasyonu**: Yukarıda açıklandığı gibi.
- **Hedefler**: Haftalık ve toplam hedef saat belirleme, ilerleme yüzdesi.
- **İstatistikler**: Ortalama süreler, en çok çalışılan gün, kategori
  dağılımı, en aktif repo, tempoya göre tahmini bitiş süresi (ETA).
