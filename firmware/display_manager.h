// SSD1306 128x64 I2C OLED üzerine üç sayfanın çizimi (saat, istatistik,
// heatmap) ve "henüz veri yok" durumu.
#pragma once

#include <Arduino.h>

#include "api_client.h"

namespace DisplayManager {

// I2C + SSD1306'yı başlatır. Ekran bulunamazsa/arızalıysa false döner;
// çağıran taraf ekran olmadan da (yalnızca LED ile) çalışmaya devam eder.
bool baslat();

void saat_sayfasini_ciz(const String &saat, const String &tarih, bool wifiBagli);
void istatistik_sayfasini_ciz(const CihazDurumu &durum);
void heatmap_sayfasini_ciz(const CihazDurumu &durum);
void veri_bekleniyor_sayfasini_ciz();

}  // namespace DisplayManager
