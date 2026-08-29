# Gelişim Takip — ESP32-S3 Ekran İstemcisi

Masada duran küçük bir donanım ekranından Gelişim Takip'in özet durumunu
gösterir: saat, bugünkü/haftalık ilerleme, seri ve son 10 haftanın mini
ısı haritası. Tasarım ve API şeması için bkz.
[`docs/esp32-display-entegrasyon-plani.md`](../docs/esp32-display-entegrasyon-plani.md).

## Donanım

- **ESP32-S3-N16R8**
- Onboard RGB LED (WS2812) — GPIO48
- SSD1306 128×64 I2C OLED — SDA=GPIO8, SCL=GPIO9, adres `0x3C`

## Kurulum

1. `config.h.example` dosyasını `config.h` olarak kopyala ve WiFi
   bilgilerini, Gelişim Takip'in çalıştığı bilgisayarın yerel ağ adresini
   ve Ayarlar sayfasından kopyaladığın API anahtarını gir.
   `config.h` asla commit edilmez (`.gitignore`'da).
2. Arduino IDE → Kütüphane Yöneticisi'nden kur:
   - Adafruit GFX Library
   - Adafruit SSD1306
   - Adafruit NeoPixel
   - ArduinoJson (v6)
3. Board olarak bir ESP32-S3 varyantı seç (örn. "ESP32S3 Dev Module"),
   `gelisim_takip_ekran.ino`'yu aç ve yükle.

## Dosyalar

| Dosya | Görev |
|---|---|
| `gelisim_takip_ekran.ino` | `setup()`/`loop()`, sayfa durum makinesi |
| `api_client.h/.cpp` | WiFi + `GET /api/device/status` + JSON ayrıştırma |
| `time_sync.h/.cpp` | NTP senkronu, saat/tarih metni |
| `display_manager.h/.cpp` | SSD1306 sayfa çizimleri |
| `led_status.h/.cpp` | WS2812 üzerinden `pace_status` göstergesi |

## Davranış

- Sayfa döngüsü: **Saat (120sn) → İstatistik (30sn) → Isı haritası (30sn)**.
- Veri, ekrandan bağımsız olarak **30 saniyede bir** tazelenir; RGB LED de
  bu döngüde, ekran hangi sayfada olursa olsun güncellenir.
- `loop()` içinde `delay()` kullanılmaz; tüm zamanlama `millis()`
  tabanlıdır.
- WiFi kopması, HTTP zaman aşımı, bozuk/eksik JSON ya da NTP
  başarısızlığında cihaz **kilitlenmez/resetlenmez** — son bilinen iyi
  veri ekranda kalır ve bağlantı arka planda periyodik olarak yeniden
  denenir.
