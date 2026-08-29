// Onboard WS2812 RGB LED (GPIO48) üzerinden pace_status göstergesi.
// Ekranın hangi sayfada olduğundan bağımsız olarak her veri tazelemesinde
// güncellenir.
#pragma once

#include <Arduino.h>

namespace LedStatus {

void baslat();

// gecerli == false ise (henüz hiç başarılı veri alınmadı) nötr bir renk
// yakılır; bu bir hata değil, "veri bekleniyor" durumudur.
void guncelle(const String &pace_status, bool gecerli);

}  // namespace LedStatus
