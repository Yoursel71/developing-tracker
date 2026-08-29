#include "led_status.h"

#include <Adafruit_NeoPixel.h>

namespace {
const int LED_PIN = 48;
const int LED_SAYISI = 1;
const uint8_t PARLAKLIK = 40;  // onboard LED çok parlak; göz yormasın

Adafruit_NeoPixel led(LED_SAYISI, LED_PIN, NEO_GRB + NEO_KHZ800);
}  // namespace

void LedStatus::baslat() {
  led.begin();
  led.setBrightness(PARLAKLIK);
  led.show();
}

void LedStatus::guncelle(const String &pace_status, bool gecerli) {
  uint32_t renk;
  if (!gecerli) {
    renk = led.Color(0, 0, 40);  // soluk mavi: veri bekleniyor
  } else if (pace_status == "on_track") {
    renk = led.Color(0, 60, 0);  // yeşil
  } else if (pace_status == "behind") {
    renk = led.Color(60, 35, 0);  // turuncu
  } else {
    renk = led.Color(60, 0, 0);  // kırmızı: critical (ya da bilinmeyen değer, temkinli taraf)
  }
  led.setPixelColor(0, renk);
  led.show();
}
