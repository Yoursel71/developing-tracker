#include "api_client.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "config.h"

namespace {
const unsigned long BAGLANTI_DENEME_ARALIGI_MS = 10000UL;
const unsigned long HTTP_ZAMAN_ASIMI_MS = 5000UL;
unsigned long sonBaglantiDenemesiMs = 0;
}  // namespace

void ApiClient::baslat() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

bool ApiClient::wifi_bagli_mi() {
  return WiFi.status() == WL_CONNECTED;
}

void ApiClient::wifi_durumunu_kontrol_et() {
  if (wifi_bagli_mi()) {
    return;
  }
  unsigned long simdi = millis();
  if (simdi - sonBaglantiDenemesiMs < BAGLANTI_DENEME_ARALIGI_MS) {
    return;
  }
  sonBaglantiDenemesiMs = simdi;
  WiFi.reconnect();  // non-blocking; sonucu bir sonraki durum kontrolünde görülür
}

bool ApiClient::durumu_getir(CihazDurumu &durum) {
  if (!wifi_bagli_mi()) {
    return false;
  }

  HTTPClient http;
  http.setConnectTimeout(HTTP_ZAMAN_ASIMI_MS);
  http.setTimeout(HTTP_ZAMAN_ASIMI_MS);

  String url = String(API_BASE_URL) + "/api/device/status";
  if (!http.begin(url)) {
    return false;
  }
  http.addHeader("X-Api-Anahtari", API_ANAHTARI);

  int durumKodu = http.GET();
  if (durumKodu != HTTP_CODE_OK) {
    http.end();
    return false;
  }

  String govde = http.getString();
  http.end();

  // 70 elemanlı tam sayı dizisi + birkaç sayısal/metin alan için yeterli pay.
  StaticJsonDocument<3072> belge;
  DeserializationError hata = deserializeJson(belge, govde);
  if (hata) {
    return false;
  }

  JsonArray heatmapDizisi = belge["heatmap"].as<JsonArray>();
  if (heatmapDizisi.isNull() || heatmapDizisi.size() != 70) {
    return false;  // beklenmeyen şema; son iyi veriyi koru
  }

  durum.today_hours = belge["today_hours"] | 0.0f;
  durum.weekly_goal_hours = belge["weekly_goal_hours"] | 0.0f;
  durum.weekly_logged_hours = belge["weekly_logged_hours"] | 0.0f;
  durum.weekly_remaining_hours = belge["weekly_remaining_hours"] | 0.0f;
  durum.streak_days = belge["streak_days"] | 0;
  durum.pace_status = belge["pace_status"] | "on_track";
  durum.last_updated = belge["last_updated"] | "";

  for (int i = 0; i < 70; i++) {
    durum.heatmap[i] = heatmapDizisi[i].as<uint8_t>();
  }

  durum.gecerli = true;
  return true;
}
