# ESP32-S3 Ekran Entegrasyonu — Plan

Gelişim Takip'in masaüstü/tarayıcı dışında, masada duran küçük bir donanım
ekranından da izlenebilmesi için: Flask backend'e özet bir durum ucu ve
ESP32-S3-N16R8 üzerinde çalışan bir Arduino istemcisi.

## 1. Amaç

Bilgisayarı kapalıyken bile masadaki cihaz son bilinen durumu (en son
başarılı senkrondan kalan veriyle) göstermeye devam eder; bilgisayar
açıkken 30 saniyede bir tazelenir. Cihaz salt-okunur bir istemcidir —
veriyi değiştirmez, yalnızca `GET /api/device/status` uç noktasını okur.

## 2. Backend: `GET /api/device/status`

Tarayıcı eklentisiyle aynı yerel API anahtarı mekanizması kullanılır
(`servisler/api_anahtari.py`) — `X-Api-Anahtari` header'ı ya da `?anahtar=`
sorgu parametresi. Anahtarsız ya da geçersiz istek `403` döner.

### JSON şeması

```json
{
  "today_hours": 2.5,
  "weekly_goal_hours": 10.0,
  "weekly_logged_hours": 6.3,
  "weekly_remaining_hours": 3.7,
  "streak_days": 5,
  "pace_status": "on_track",
  "heatmap": [0, 1, 0, 2, 3, 4, 1, "...(70 değer)"],
  "last_updated": "2026-08-29T14:32:10+03:00"
}
```

| Alan | Tip | Açıklama |
|---|---|---|
| `today_hours` | float | Bugün birikmiş saat (`gunluk_toplamlar`'dan, 2 ondalık). |
| `weekly_goal_hours` | float | `hedefler.haftalik_saat` (0 = hedef yok). |
| `weekly_logged_hours` | float | Bu hafta (Pazartesi–bugün) toplam saat. |
| `weekly_remaining_hours` | float | `max(hedef - biriken, 0)`. |
| `streak_days` | int | `istatistikler.seri_hesapla`'nın `guncel` alanı. |
| `pace_status` | `"on_track"｜"behind"｜"critical"` | Aşağıdaki mantıkla. |
| `heatmap` | int[70] | Son 70 gün (10 hafta × 7 gün), **eskiden yeniye** sıralı, her değer 0–4 seviye. Son eleman bugün. |
| `last_updated` | ISO 8601 | Sunucunun yanıtı ürettiği an (yerel saat dilimi). |

### `pace_status` mantığı

Haftanın "geçmiş" gün oranı, `hedefler.haftalik_ilerleme`'deki
`kalan_gun = 6 - bugun.weekday()` kuralıyla tutarlı sayılır — yani bugün
zaten "geçmiş günler" kümesine dahildir:

```
gecen_gun_orani = (bugun.weekday() + 1) / 7        # Pazartesi=1/7 .. Pazar=7/7
beklenen_saat   = weekly_goal_hours * gecen_gun_orani
oran            = weekly_logged_hours / beklenen_saat   (beklenen_saat > 0 ise)
```

- `weekly_goal_hours <= 0` **veya** `beklenen_saat <= 0` → `on_track`
  (hedef yoksa geride kalınacak bir şey de yok).
- `oran >= 0.85` → `on_track`
- `0.50 <= oran < 0.85` → `behind`
- `oran < 0.50` → `critical`

### `heatmap` normalizasyonu

Ayrı bir GitHub commit verisi değil, **uygulamanın kendi ısı haritası
altyapısı** (`servisler/heatmap.py`) yeniden kullanılır: son 70 günün
günlük dakika toplamları alınır, `heatmap.esikleri_hesapla()` ile
kullanıcının kendi dağılımına göre yüzdelik dilim eşikleri çıkarılır,
`heatmap.seviye()` ile her gün 0 (boş) – 4 (en yoğun) arası seviyeye
çevrilir. 8'den az dolu gün varsa modül otomatik olarak sabit eşiklere
(30/60/120 dk) düşer — yeni kurulumda boş haritanın anlamsız
görünmesini önler.

## 3. Donanım

**ESP32-S3-N16R8**

| Bileşen | Bağlantı |
|---|---|
| Onboard RGB LED (WS2812) | GPIO48, `Adafruit_NeoPixel` |
| OLED SSD1306 128×64 | I2C: SDA=GPIO8, SCL=GPIO9, adres `0x3C` |

## 4. Firmware dosya yapısı

```
firmware/
  gelisim_takip_ekran.ino   Giriş noktası: setup()/loop(), state machine
  config.h.example          Şablon (WiFi, API adresi, anahtar) — commit edilir
  config.h                  Gerçek sırlar — .gitignore'da, commit edilmez
  api_client.h / .cpp       WiFi + HTTP GET + JSON parse
  display_manager.h / .cpp  SSD1306 sayfa çizimleri
  led_status.h / .cpp       WS2812 pace_status renklendirmesi
  time_sync.h / .cpp        NTP senkronizasyonu, yerel saat
```

## 5. State machine

Tamamen `millis()` tabanlı, `loop()` içinde **hiçbir `delay()` yok**:

```
CLOCK (120 sn) -> STATS (30 sn) -> HEATMAP (30 sn) -> CLOCK -> ...
```

- **CLOCK**: büyük dijital saat + tarih (NTP'den, senkron başarısızsa son
  bilinen zamandan `millis()` farkıyla dahili sayaç).
- **STATS**: `today_hours`, `weekly_logged_hours` / `weekly_goal_hours`,
  `streak_days`.
- **HEATMAP**: son 70 günün 10×7 hücrelik mini ızgarası (piksel
  yoğunluğu = seviye).

Veri, ekran döngüsünden **bağımsız** bir zamanlayıcıyla 30 saniyede bir
`GET /api/device/status`'tan tazelenir (ekranın hangi sayfada olduğuna
bakılmaksızın). RGB LED de bu bağımsız döngüde, ekran hangi sayfada
olursa olsun `pace_status`'a göre sürekli günceldir:

- `on_track` → yeşil
- `behind` → sarı/turuncu
- `critical` → kırmızı
- Henüz hiç veri alınamadıysa (ilk açılış/uzun süreli bağlantı yokluğu) → sönük mavi (nötr "veri bekleniyor" sinyali, hataymış gibi kırmızı yakılmaz)

## 6. Hata toleransı (zorunlu, tamamı uygulanır)

Cihaz asla kilitlenmez/kendini resetlemez; her hata sınıfı için **son
bilinen iyi veri** ekranda kalır ve arka planda yeniden deneme sürer:

1. **WiFi kopması** — `WiFi.status() != WL_CONNECTED` tespit edilince
   engellemeyen (non-blocking) yeniden bağlanma denemesi başlatılır
   (`WiFi.reconnect()`), belirli aralıklarla tekrar denenir; ekranda son
   veri + küçük bir "bağlantı yok" göstergesi kalır.
2. **HTTP timeout / bağlantı reddi** — `HTTPClient` zaman aşımı kısa
   tutulur (örn. 5 sn); başarısız istek sayacı artırılır, veri
   değiştirilmez, bir sonraki 30 sn'lik tazeleme döngüsünde tekrar
   denenir.
3. **JSON parse hatası** (bozuk/eksik gövde, beklenmeyen alan tipi) —
   `ArduinoJson`'ın `deserializeJson` hata kodu kontrol edilir; hata
   varsa gövde tamamen yok sayılır, önceki durum korunur.
4. **NTP başarısızlığı** — `configTime` sonrası zaman senkron
   olmadıysa (`time(nullptr) < eşik`) saat sayfası "senkron bekleniyor"
   gösterir ya da son senkron zamanından `millis()` farkıyla tahmini
   saat üretir; NTP periyodik olarak arka planda tekrar denenir.

Hiçbir hata sınıfı `ESP.restart()` çağırmaz veya `while(1){}` gibi
sonsuz engelleyici bir bekleme içermez.

## 7. Sırlar

`firmware/config.h` (gerçek WiFi şifresi + API adresi/anahtarı)
`.gitignore`'a eklenir; repoya yalnızca `firmware/config.h.example`
şablonu commit edilir.
