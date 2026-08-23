import os

GITHUB_KULLANICI = "Yoursel71"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

VARSAYILAN_HAFTALIK_HEDEF_SAAT = 15
VARSAYILAN_TOPLAM_HEDEF_SAAT = 135

GITHUB_ONBELLEK_SURESI_SANIYE = 60 * 60  # 1 saat

VERI_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "veri.json")

UYGULAMA_PORTU = 57391

# Otomatik izleme: kayıp tespit edilen bir işlem/site için oturumu hemen kapatmak
# yerine bu kadar saniye bekler (kısa kesintilerde oturumu bölmemek için).
IZLEME_KAYIP_GRACE_SANIYE = 60
# İşlem taraması periyodu.
IZLEME_TARAMA_ARALIGI_SANIYE = 10
# Eklenti ~15 saniyede bir kalp atışı gönderir; bu süreden uzun süre
# kalp atışı gelmezse site kapanmış sayılır (kayıp grace'i ayrıca işler).
IZLEME_SITE_KALP_ATISI_ZAMAN_ASIMI_SANIYE = 40
# Kullanıcı otomatik bir oturumu elle durdurduğunda, izleme motoru o
# kategoriyi bu kadar saniye boyunca yeniden başlatmaz.
IZLEME_ERTELEME_SANIYE = 10 * 60

# Kurulum sihirbazında hızlı seçim için bilinen editör -> işlem adı eşlemesi.
BILINEN_EDITORLER = {
    "VS Code": "Code.exe",
    "PyCharm": "pycharm64.exe",
    "Not Defteri": "notepad.exe",
    "Sublime Text": "sublime_text.exe",
}
