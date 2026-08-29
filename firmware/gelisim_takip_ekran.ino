// Gelişim Takip — ESP32-S3 Ekran İstemcisi
//
// Donanım: ESP32-S3-N16R8, onboard WS2812 RGB LED (GPIO48),
// SSD1306 128x64 I2C OLED (SDA=GPIO8, SCL=GPIO9, adres 0x3C).
//
// Kurulum:
//   1. config.h.example dosyasını "config.h" olarak kopyala ve doldur.
//   2. Arduino IDE Kütüphane Yöneticisi'nden şunları kur:
//      Adafruit GFX Library, Adafruit SSD1306, Adafruit NeoPixel,
//      ArduinoJson (v6).
//   3. Board: "ESP32S3 Dev Module" (ya da kartına uygun ESP32-S3 varyantı).
//
// Tasarım/şema referansı: docs/esp32-display-entegrasyon-plani.md
//
// loop() içinde hiçbir yerde delay() KULLANILMAZ — tüm zamanlama millis()
// tabanlıdır; WiFi kopması, HTTP hatası, bozuk JSON ya da NTP
// başarısızlığı cihazı kilitlemez/resetlemez (bkz. plan dokümanı Bölüm 6).

#include "api_client.h"
#include "config.h"
#include "display_manager.h"
#include "led_status.h"
#include "time_sync.h"

namespace {

enum class Sayfa { SAAT, ISTATISTIK, HEATMAP };

const unsigned long SAAT_SURESI_MS = 120000UL;
const unsigned long ISTATISTIK_SURESI_MS = 30000UL;
const unsigned long HEATMAP_SURESI_MS = 30000UL;
const unsigned long CIZIM_ARALIGI_MS = 500UL;  // saat sayfasında saniye ilerlesin diye

Sayfa aktifSayfa = Sayfa::SAAT;
unsigned long sayfaBaslangicMs = 0;
unsigned long sonCizimMs = 0;
unsigned long sonVeriTazelemeMs = 0;

CihazDurumu durum;

unsigned long aktif_sayfa_suresi() {
  switch (aktifSayfa) {
    case Sayfa::SAAT: return SAAT_SURESI_MS;
    case Sayfa::ISTATISTIK: return ISTATISTIK_SURESI_MS;
    case Sayfa::HEATMAP: return HEATMAP_SURESI_MS;
  }
  return SAAT_SURESI_MS;
}

void sonraki_sayfaya_gec() {
  switch (aktifSayfa) {
    case Sayfa::SAAT: aktifSayfa = Sayfa::ISTATISTIK; break;
    case Sayfa::ISTATISTIK: aktifSayfa = Sayfa::HEATMAP; break;
    case Sayfa::HEATMAP: aktifSayfa = Sayfa::SAAT; break;
  }
  sayfaBaslangicMs = millis();
}

void sayfayi_ciz() {
  // Saat sayfası veri olmadan da anlamlıdır (NTP ile çalışır); istatistik
  // ve heatmap sayfaları veri gerektirir.
  if (!durum.gecerli && aktifSayfa != Sayfa::SAAT) {
    DisplayManager::veri_bekleniyor_sayfasini_ciz();
    return;
  }
  switch (aktifSayfa) {
    case Sayfa::SAAT:
      DisplayManager::saat_sayfasini_ciz(
          TimeSync::saat_metni(), TimeSync::tarih_metni(), ApiClient::wifi_bagli_mi());
      break;
    case Sayfa::ISTATISTIK:
      DisplayManager::istatistik_sayfasini_ciz(durum);
      break;
    case Sayfa::HEATMAP:
      DisplayManager::heatmap_sayfasini_ciz(durum);
      break;
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);

  DisplayManager::baslat();  // ekran yoksa/arızalıysa false döner, cihaz LED ile çalışmaya devam eder
  LedStatus::baslat();
  ApiClient::baslat();
  TimeSync::baslat();

  sayfaBaslangicMs = millis();
  sonVeriTazelemeMs = 0;  // ilk loop() turunda hemen bir deneme yapılsın

  LedStatus::guncelle(durum.pace_status, durum.gecerli);
  sayfayi_ciz();
}

void loop() {
  unsigned long simdi = millis();

  // 1) WiFi bağlantısını canlı tut (non-blocking; kopuksa aralıklarla dener).
  ApiClient::wifi_durumunu_kontrol_et();

  // 2) NTP senkronunu canlı tut (non-blocking; senkron değilse aralıklarla dener).
  TimeSync::guncelle();

  // 3) Veri tazeleme: ekran hangi sayfada olursa olsun bağımsız çalışır.
  //    Başarısız olursa `durum` DEĞİŞMEZ — son iyi veri korunur.
  if (simdi - sonVeriTazelemeMs >= VERI_TAZELEME_ARALIGI_MS) {
    sonVeriTazelemeMs = simdi;
    if (ApiClient::durumu_getir(durum)) {
      LedStatus::guncelle(durum.pace_status, durum.gecerli);
    }
  }

  // 4) Sayfa döngüsü: CLOCK(120sn) -> STATS(30sn) -> HEATMAP(30sn) -> ...
  if (simdi - sayfaBaslangicMs >= aktif_sayfa_suresi()) {
    sonraki_sayfaya_gec();
  }

  // 5) Ekranı saniyede ~2 kez yeniden çiz (saat ilerlesin, I2C'yi
  //    gereksiz meşgul etmesin).
  if (simdi - sonCizimMs >= CIZIM_ARALIGI_MS) {
    sonCizimMs = simdi;
    sayfayi_ciz();
  }
}
