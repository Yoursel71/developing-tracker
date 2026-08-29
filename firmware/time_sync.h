// NTP senkronizasyonu ve yerel saat.
//
// NTP hiç ulaşamazsa saat_metni()/tarih_metni() "senkron bekleniyor"
// gösterir; cihaz kilitlenmez, guncelle() periyodik olarak arka planda
// yeniden dener.
#pragma once

#include <Arduino.h>

namespace TimeSync {

void baslat();

// loop() içinden her turda çağrılması güvenlidir; senkron zaten
// sağlanmışsa hiçbir şey yapmaz, değilse aralıklarla yeniden dener.
void guncelle();

bool senkron_mu();

String saat_metni();  // "HH:MM:SS" ya da senkron yoksa "--:--:--"
String tarih_metni();  // "Sal 24.03.2026" ya da senkron yoksa açıklayıcı metin

}  // namespace TimeSync
