import os
import sys

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)


@pytest.fixture(autouse=True)
def gecici_veri_dizini(tmp_path, monkeypatch):
    """Her test kendi veri dizininde çalışır; gerçek veriye dokunulmaz."""
    monkeypatch.setenv("GELISIM_TAKIP_VERI_DIZINI", str(tmp_path / "veri"))

    # Modül seviyesinde önbelleklenmiş durumları sıfırla.
    from depo import json_deposu
    from servisler import api_anahtari, otomatik_izleme

    json_deposu.son_kurtarma_mesaji = None
    api_anahtari._onbellek = None
    otomatik_izleme._site_kalp_atislari.clear()
    otomatik_izleme._onceki_tur_zamani = None
    otomatik_izleme.devam_et()
    yield


@pytest.fixture
def veri():
    from depo import json_deposu

    return json_deposu.oku()
