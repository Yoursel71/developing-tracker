import os

GITHUB_KULLANICI = "Yoursel71"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

VARSAYILAN_HAFTALIK_HEDEF_SAAT = 15
VARSAYILAN_TOPLAM_HEDEF_SAAT = 135

GITHUB_ONBELLEK_SURESI_SANIYE = 60 * 60  # 1 saat

VERI_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "veri.json")
