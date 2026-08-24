"""Uygulama sabitleri ve yapılandırması."""

import os

from platform_katmani import yollar

# --- Yollar -----------------------------------------------------------------
# Yollar fonksiyon olarak çözülür; testler GELISIM_TAKIP_VERI_DIZINI ile
# geçici bir dizine yönlendirebilsin diye modül seviyesinde sabitlenmezler.
kaynak_yolu = yollar.kaynak_yolu
veri_dizini = yollar.veri_dizini
veri_dosyasi = yollar.veri_dosyasi
yedek_dizini = yollar.yedek_dizini
gunluk_dosyasi = yollar.gunluk_dosyasi

# --- Sunucu -----------------------------------------------------------------
UYGULAMA_PORTU = int(os.environ.get("GELISIM_TAKIP_PORT", "57391"))
HATA_AYIKLAMA = os.environ.get("GELISIM_TAKIP_DEBUG") == "1"

# --- GitHub -----------------------------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_ONBELLEK_SURESI_SANIYE = 60 * 60

# --- Varsayılan hedefler ----------------------------------------------------
VARSAYILAN_HAFTALIK_HEDEF_SAAT = 10
VARSAYILAN_TOPLAM_HEDEF_SAAT = 135

# --- Otomatik izleme --------------------------------------------------------
# İşlem/site taraması periyodu.
IZLEME_TARAMA_ARALIGI_SANIYE = 10
# Algılanmayan bir kategori için oturumu hemen kapatmak yerine bu kadar
# beklenir (kısa kesintilerde oturumu bölmemek için).
IZLEME_KAYIP_GRACE_SANIYE = 60
# Eklenti ~15 sn'de bir kalp atışı gönderir; bu süre aşılırsa site kapalı sayılır.
IZLEME_SITE_KALP_ATISI_ZAMAN_ASIMI_SANIYE = 45
# Kullanıcı otomatik bir oturumu elle durdurunca kategori bu kadar ertelenir.
IZLEME_ERTELEME_SANIYE = 10 * 60
# Klavye/fare hareketsizliği bu süreyi aşarsa oturum duraklar (varsayılan).
VARSAYILAN_BOSTA_ESIGI_DAKIKA = 10
# İki tarama arasında duvar saati bu kadar fazla ilerlediyse uyku/askıya
# alma olmuş sayılır ve o boşluk süreye eklenmez.
UYKU_TESPIT_TOLERANSI_SANIYE = 90
# Tek bir oturumun kaydedilebileceği üst sınır (saat).
OTURUM_TAVANI_SAAT = 12

# --- Seri (streak) ----------------------------------------------------------
# Bir günün "çalışılmış" sayılması için gereken asgari dakika (varsayılan).
VARSAYILAN_SERI_ESIGI_DAKIKA = 15

# --- Kurulum sihirbazı ------------------------------------------------------
BILINEN_EDITORLER = {
    "VS Code": "Code.exe",
    "PyCharm": "pycharm64.exe",
    "Visual Studio": "devenv.exe",
    "Sublime Text": "sublime_text.exe",
    "Not Defteri": "notepad.exe",
    "Cursor": "Cursor.exe",
}

BILINEN_SITELER = {
    "Udemy": "udemy.com",
    "YouTube": "youtube.com",
    "Coursera": "coursera.org",
    "freeCodeCamp": "freecodecamp.org",
    "BTK Akademi": "btkakademi.gov.tr",
}

# İlk kurulumda oluşturulan kategoriler. Kullanıcı bunları Ayarlar'dan
# değiştirebilir, silebilir ve kendi projelerini ekleyebilir; bu liste
# yalnızca başlangıç değeridir.
VARSAYILAN_KATEGORILER = ["Python", "GitHub çalışması", "Sertifika kursu", "Diğer"]

# Yeni kategorilere sırayla atanan renkler.
KATEGORI_PALETI = [
    "#3fb950",  # yeşil
    "#58a6ff",  # mavi
    "#bc8cff",  # mor
    "#f0883e",  # turuncu
    "#e3b341",  # sarı
    "#ff7b72",  # kırmızı
    "#39c5cf",  # turkuaz
    "#db61a2",  # pembe
]

# --- Mola hatırlatıcısı -----------------------------------------------------
MOLA_ONERI_DAKIKA = 120          # bu kadar kesintisiz çalışınca mola öner
MOLA_TEKRAR_ARALIGI_DAKIKA = 60  # aynı oturumda tekrar önermeden önce

# --- Pomodoro ---------------------------------------------------------------
POMODORO_CALISMA_DAKIKA = 25
POMODORO_KISA_MOLA_DAKIKA = 5
POMODORO_UZUN_MOLA_DAKIKA = 15
POMODORO_UZUN_MOLA_ARALIGI = 4   # kaç turda bir uzun mola

# --- Motivasyon (varsayılan kapalı) -----------------------------------------
# Gün içinde sabit kalır; her sayfa yenilemede değişse gürültü olurdu.
MOTIVASYON_SOZLERI = [
    "Her uzman bir zamanlar acemiydi.",
    "Bugün 20 dakika, hiç yapmamaktan sonsuz daha iyi.",
    "Kod yazmayı okuyarak değil, yazarak öğrenirsin.",
    "Hata mesajı düşman değil, yol tarifidir.",
    "Küçük ve düzenli, büyük ve düzensizden hızlıdır.",
    "Anlamadığın satırı bir kez daha oku, sonra çalıştır.",
    "Dün bilmediğin bir şeyi bugün biliyorsun.",
    "Kopyaladığın kodu açıklayabiliyorsan öğrenmişsindir.",
    "Takıldığın yer, öğrenmenin başladığı yerdir.",
    "Bitmiş küçük proje, bitmemiş büyük projeden değerlidir.",
]

# Hazır Python yol haritası taslağı (kurulumda oluşturulur, düzenlenebilir).
VARSAYILAN_YOL_HARITASI = [
    ("Kurulum ve ilk adımlar", 4),
    ("Değişkenler ve veri tipleri", 8),
    ("Koşullar (if/elif/else)", 8),
    ("Döngüler (for/while)", 10),
    ("Listeler, sözlükler, kümeler", 12),
    ("Fonksiyonlar ve return", 12),
    ("Hata yönetimi (try/except)", 6),
    ("Dosya işlemleri", 6),
    ("Modüller ve paketler", 6),
    ("Nesne yönelimli programlama", 18),
    ("Sanal ortam ve pip", 4),
    ("Git ve GitHub", 8),
    ("Küçük proje: CLI uygulaması", 15),
    ("Küçük proje: web/API", 18),
]
