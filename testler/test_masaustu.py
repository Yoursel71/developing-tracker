"""Masaüstü kabuğu: arka plan bayrağı, açılış kaydı, ikinci örnek uyandırma."""

import masaustu
from platform_katmani import otomatik_baslatma


def test_arkaplan_bayragi_varsayilan_kapali():
    args = masaustu._argumanlari_ayristir([])
    assert args.arkaplan is False


def test_arkaplan_bayragi_ayristirilir():
    args = masaustu._argumanlari_ayristir(["--arkaplan"])
    assert args.arkaplan is True


def test_acilis_komutu_arkaplan_bayragini_icerir():
    """Windows ile başlatınca pencere gözüne sokulmasın diye --arkaplan eklenmeli."""
    assert "--arkaplan" in otomatik_baslatma._komut()


def test_calisan_ornegi_uyandirma_basarisizsa_false_doner():
    """Sunucu tamamen kapalıyken (örn. gerçek örnek yoksa) sessizce False dönmeli."""
    assert masaustu._calisan_ornegi_uyandir() is False
