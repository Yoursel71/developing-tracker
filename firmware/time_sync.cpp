#include "time_sync.h"

#include <time.h>

#include "config.h"

namespace {
// 2023-11-14 civarı; bir ESP32'nin senkronsuz iç saati bunun çok altında
// kalır, bu yüzden basit ve güvenilir bir "gerçek zaman mı" eşiği olarak
// kullanılır.
const time_t GECERLI_ZAMAN_ESIGI = 1700000000;
const unsigned long DENEME_ARALIGI_MS = 60000UL;
unsigned long sonDenemeMs = 0;

// SSD1306'nın varsayılan fontu yalnızca ASCII içerir; "Çar" gibi Türkçe
// özel karakterler ekranda bozuk basılır, o yüzden burada "Car" kullanılır.
const char *GUN_ADLARI[] = {"Paz", "Pzt", "Sal", "Car", "Per", "Cum", "Cmt"};
}  // namespace

void TimeSync::baslat() {
  configTime(GMT_OFSET_SN, YAZ_SAATI_OFSET_SN, NTP_SUNUCU);
}

bool TimeSync::senkron_mu() {
  return time(nullptr) > GECERLI_ZAMAN_ESIGI;
}

void TimeSync::guncelle() {
  if (senkron_mu()) {
    return;
  }
  unsigned long simdi = millis();
  if (simdi - sonDenemeMs < DENEME_ARALIGI_MS) {
    return;
  }
  sonDenemeMs = simdi;
  configTime(GMT_OFSET_SN, YAZ_SAATI_OFSET_SN, NTP_SUNUCU);  // non-blocking yeniden deneme
}

String TimeSync::saat_metni() {
  if (!senkron_mu()) {
    return "--:--:--";
  }
  time_t simdi = time(nullptr);
  struct tm zaman;
  localtime_r(&simdi, &zaman);
  char arabellek[9];
  snprintf(arabellek, sizeof(arabellek), "%02d:%02d:%02d",
           zaman.tm_hour, zaman.tm_min, zaman.tm_sec);
  return String(arabellek);
}

String TimeSync::tarih_metni() {
  if (!senkron_mu()) {
    return "senkron bekleniyor";
  }
  time_t simdi = time(nullptr);
  struct tm zaman;
  localtime_r(&simdi, &zaman);
  char arabellek[24];
  snprintf(arabellek, sizeof(arabellek), "%s %02d.%02d.%04d",
           GUN_ADLARI[zaman.tm_wday], zaman.tm_mday, zaman.tm_mon + 1,
           zaman.tm_year + 1900);
  return String(arabellek);
}
