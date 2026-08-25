"""varliklar/ikon.svg'deki tasarımı .ico ve .png olarak üretir.

Bu ortamda SVG rasterleme kütüphanesi (cairosvg vb.) yok; tasarım basit
olduğu için aynı geometri doğrudan Pillow ile yüksek çözünürlükte çizilip
küçültülür. SVG kaynak dosyası, tasarımın tek referansı olarak kalır —
buradaki koordinatlar onunla aynı oranları kullanır (64x64 ızgara).
"""

import os

from PIL import Image, ImageDraw

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEDEF_DIZIN = os.path.join(KOK, "varliklar")
STATIK_DIZIN = os.path.join(KOK, "static")

RENK_ZEMIN = (21, 27, 35, 255)      # #151b23
RENK_VURGU = (63, 185, 80, 255)     # #3fb950
OLCEK = 16  # 64x64 ızgarayı 1024x1024'e büyütüp aşağı örnekle (kenar yumuşatma)


def _yuksek_cozunurluklu_gorsel():
    boyut = 64 * OLCEK
    gorsel = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
    cizim = ImageDraw.Draw(gorsel)

    def olcekle(deger):
        return round(deger * OLCEK)

    cizim.rounded_rectangle(
        [olcekle(2), olcekle(2), olcekle(62), olcekle(62)],
        radius=olcekle(14), fill=RENK_ZEMIN, outline=RENK_VURGU, width=olcekle(2.5),
    )
    # Kronometre kurma düğmesi (crown) ve gövdeye bağlayan sap.
    cizim.rounded_rectangle(
        [olcekle(28), olcekle(6), olcekle(36), olcekle(12)],
        radius=olcekle(2), fill=RENK_VURGU,
    )
    cizim.line(
        [(olcekle(32), olcekle(12)), (olcekle(32), olcekle(16))],
        fill=RENK_VURGU, width=olcekle(3),
    )
    # Kronometre gövdesi.
    r_govde = olcekle(17)
    cizim.ellipse(
        [olcekle(32) - r_govde, olcekle(38) - r_govde,
         olcekle(32) + r_govde, olcekle(38) + r_govde],
        outline=RENK_VURGU, width=olcekle(3.5),
    )
    # Akrep (12 yönü) ve yelkovan (~2 yönü).
    cizim.line(
        [(olcekle(32), olcekle(38)), (olcekle(32), olcekle(26))],
        fill=RENK_VURGU, width=olcekle(3),
    )
    cizim.line(
        [(olcekle(32), olcekle(38)), (olcekle(40), olcekle(33))],
        fill=RENK_VURGU, width=olcekle(3),
    )
    r_merkez = olcekle(2.2)
    cizim.ellipse(
        [olcekle(32) - r_merkez, olcekle(38) - r_merkez,
         olcekle(32) + r_merkez, olcekle(38) + r_merkez],
        fill=RENK_VURGU,
    )
    return gorsel


def uret():
    os.makedirs(HEDEF_DIZIN, exist_ok=True)
    kaynak = _yuksek_cozunurluklu_gorsel()

    png_256 = kaynak.resize((256, 256), Image.LANCZOS)

    png_yolu = os.path.join(HEDEF_DIZIN, "ikon.png")
    png_256.save(png_yolu)

    ico_yolu = os.path.join(HEDEF_DIZIN, "ikon.ico")
    boyutlar = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    kaynak.save(ico_yolu, format="ICO", sizes=boyutlar)

    # Web favicon: statik klasörden url_for('static', ...) ile sunulabilsin diye
    # ayrı bir kopya (kaynak, tek gerçek: varliklar/ikon.png; bu yalnızca sunum kopyası).
    os.makedirs(STATIK_DIZIN, exist_ok=True)
    statik_png_yolu = os.path.join(STATIK_DIZIN, "ikon.png")
    png_256.save(statik_png_yolu)

    print(f"Üretildi: {png_yolu}")
    print(f"Üretildi: {ico_yolu}")
    print(f"Üretildi: {statik_png_yolu}")


if __name__ == "__main__":
    uret()
