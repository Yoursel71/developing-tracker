#include "display_manager.h"

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>

namespace {
const int EKRAN_GENISLIK = 128;
const int EKRAN_YUKSEKLIK = 64;
const uint8_t OLED_ADRES = 0x3C;
const int SDA_PIN = 8;
const int SCL_PIN = 9;

Adafruit_SSD1306 ekran(EKRAN_GENISLIK, EKRAN_YUKSEKLIK, &Wire, -1);
bool ekranHazir = false;

const char *pace_status_etiketi(const String &durum) {
  if (durum == "on_track") return "Durum: yolunda";
  if (durum == "behind") return "Durum: geride";
  return "Durum: KRITIK";
}
}  // namespace

bool DisplayManager::baslat() {
  Wire.begin(SDA_PIN, SCL_PIN);
  ekranHazir = ekran.begin(SSD1306_SWITCHCAPVCC, OLED_ADRES);
  if (ekranHazir) {
    ekran.clearDisplay();
    ekran.display();
  }
  return ekranHazir;
}

void DisplayManager::saat_sayfasini_ciz(const String &saat, const String &tarih,
                                         bool wifiBagli) {
  if (!ekranHazir) return;
  ekran.clearDisplay();
  ekran.setTextColor(SSD1306_WHITE);

  ekran.setTextSize(3);
  ekran.setCursor(4, 16);
  ekran.print(saat);

  ekran.setTextSize(1);
  ekran.setCursor(4, 50);
  ekran.print(tarih);

  if (!wifiBagli) {
    ekran.setCursor(118, 0);
    ekran.print("!");  // sağ üstte küçük bağlantı-yok işareti
  }

  ekran.display();
}

void DisplayManager::istatistik_sayfasini_ciz(const CihazDurumu &durum) {
  if (!ekranHazir) return;
  ekran.clearDisplay();
  ekran.setTextColor(SSD1306_WHITE);
  ekran.setTextSize(1);

  ekran.setCursor(0, 0);
  ekran.print("Bugun: ");
  ekran.print(durum.today_hours, 1);
  ekran.print(" sa");

  ekran.setCursor(0, 16);
  ekran.print("Hafta: ");
  ekran.print(durum.weekly_logged_hours, 1);
  ekran.print("/");
  ekran.print(durum.weekly_goal_hours, 1);
  ekran.print(" sa");

  const int cubukX = 0;
  const int cubukY = 28;
  const int cubukGenislik = 122;
  const int cubukYukseklik = 8;
  int dolu = 0;
  if (durum.weekly_goal_hours > 0) {
    dolu = (int)(cubukGenislik * durum.weekly_logged_hours / durum.weekly_goal_hours);
    dolu = constrain(dolu, 0, cubukGenislik);
  }
  ekran.drawRect(cubukX, cubukY, cubukGenislik, cubukYukseklik, SSD1306_WHITE);
  ekran.fillRect(cubukX, cubukY, dolu, cubukYukseklik, SSD1306_WHITE);

  ekran.setCursor(0, 44);
  ekran.print("Seri: ");
  ekran.print(durum.streak_days);
  ekran.print(" gun");

  ekran.setCursor(0, 56);
  ekran.print(pace_status_etiketi(durum.pace_status));

  ekran.display();
}

void DisplayManager::heatmap_sayfasini_ciz(const CihazDurumu &durum) {
  if (!ekranHazir) return;
  ekran.clearDisplay();
  ekran.setTextColor(SSD1306_WHITE);
  ekran.setTextSize(1);
  ekran.setCursor(0, 0);
  ekran.print("Son 10 hafta");

  // 10 sütun (hafta) x 7 satır (gün); eskiden yeniye soldan sağa.
  const int hucreGenislik = 8;
  const int hucreYukseklik = 6;
  const int baslangicX = 4;
  const int baslangicY = 14;

  for (int gun = 0; gun < 70; gun++) {
    int hafta = gun / 7;
    int haftaGunu = gun % 7;
    int x = baslangicX + hafta * (hucreGenislik + 1);
    int y = baslangicY + haftaGunu * (hucreYukseklik + 1);

    uint8_t seviye = durum.heatmap[gun];  // 0..4
    if (seviye == 0) {
      ekran.drawRect(x, y, hucreGenislik, hucreYukseklik, SSD1306_WHITE);
      continue;
    }
    // Monokrom ekranda "yoğunluk" hissi vermek için hücre, seviyeyle
    // orantılı yükseklikte alttan yukarı doldurulur.
    int doluYukseklik = max(1, (hucreYukseklik * seviye) / 4);
    ekran.fillRect(x, y + (hucreYukseklik - doluYukseklik), hucreGenislik,
                   doluYukseklik, SSD1306_WHITE);
  }

  ekran.display();
}

void DisplayManager::veri_bekleniyor_sayfasini_ciz() {
  if (!ekranHazir) return;
  ekran.clearDisplay();
  ekran.setTextColor(SSD1306_WHITE);
  ekran.setTextSize(1);
  ekran.setCursor(4, 28);
  ekran.print("Veri bekleniyor...");
  ekran.display();
}
