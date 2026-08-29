// WiFi bağlantısı + GET /api/device/status + JSON ayrıştırma.
//
// Her hata sınıfında (WiFi kopuk, HTTP timeout/hata, bozuk JSON, beklenmeyen
// şema) durumu_getir() false döner ve `durum` DEĞİŞTİRİLMEZ; çağıran taraf
// son bilinen iyi veriyi ekranda tutmaya devam eder.
#pragma once

#include <Arduino.h>

struct CihazDurumu {
  float today_hours = 0;
  float weekly_goal_hours = 0;
  float weekly_logged_hours = 0;
  float weekly_remaining_hours = 0;
  int streak_days = 0;
  String pace_status = "on_track";
  uint8_t heatmap[70] = {0};
  String last_updated = "";
  bool gecerli = false;  // en az bir kez başarıyla dolduruldu mu
};

namespace ApiClient {

void baslat();

// WiFi kopuksa engellemeyen (non-blocking) aralıklarla yeniden bağlanmayı
// dener; her loop() turunda çağrılması güvenlidir.
void wifi_durumunu_kontrol_et();

bool wifi_bagli_mi();

// Tek bir HTTP GET + JSON parse denemesi yapar. WiFi kopuksa hemen false
// döner (istek bile başlatmaz).
bool durumu_getir(CihazDurumu &durum);

}  // namespace ApiClient
