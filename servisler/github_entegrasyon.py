"""GitHub etkinlik entegrasyonu.

Senkron ağ çağrısı istek işleyicisini 10 saniyeye kadar dondurabildiği için
çekme arka planda yapılır; sayfalar her zaman önbellekteki veriyle anında
render edilir.
"""

import datetime as dt
import logging
import threading

import requests

import config
from depo import json_deposu

logger = logging.getLogger(__name__)

_senkron_kilidi = threading.Lock()
_son_hata = None


def son_hata():
    return _son_hata


def _headers():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "GelisimTakip"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return headers


def _push_etkinliklerini_donustur(ham):
    sonuc = []
    for etkinlik in ham:
        if not isinstance(etkinlik, dict) or etkinlik.get("type") != "PushEvent":
            continue
        olusturma = etkinlik.get("created_at") or ""
        sonuc.append({
            "tarih": olusturma[:10],
            "repo": (etkinlik.get("repo") or {}).get("name", "bilinmiyor"),
            "commit_sayisi": len((etkinlik.get("payload") or {}).get("commits", [])),
        })
    return sonuc


def _onbellek_taze_mi(gh, simdi):
    damga = gh.get("son_senkron")
    if not damga:
        return False
    try:
        son = dt.datetime.fromisoformat(damga)
    except (TypeError, ValueError):
        return False
    if son.tzinfo is None:
        son = son.replace(tzinfo=dt.timezone.utc)
    return (simdi - son).total_seconds() < config.GITHUB_ONBELLEK_SURESI_SANIYE


def senkronize_et(zorla=False):
    """Etkinlikleri çeker. (etkinlikler, hata_mesaji) döner."""
    global _son_hata

    if not _senkron_kilidi.acquire(blocking=False):
        veri = json_deposu.oku()
        return veri["github"]["son_cekilen_etkinlikler"], None

    try:
        simdi = dt.datetime.now(dt.timezone.utc)
        veri = json_deposu.oku()
        gh = veri["github"]
        kullanici = (gh.get("kullanici") or "").strip()

        if not kullanici:
            return gh["son_cekilen_etkinlikler"], None
        if not zorla and _onbellek_taze_mi(gh, simdi):
            return gh["son_cekilen_etkinlikler"], None

        try:
            yanit = requests.get(
                f"https://api.github.com/users/{kullanici}/events/public",
                headers=_headers(),
                timeout=10,
            )
            yanit.raise_for_status()
            etkinlikler = _push_etkinliklerini_donustur(yanit.json())
        except requests.RequestException as hata:
            _son_hata = _anlasilir_hata(hata)
            logger.warning("GitHub senkronu başarısız: %s", hata)
            return gh.get("son_cekilen_etkinlikler", []), _son_hata
        except ValueError as hata:
            _son_hata = "GitHub beklenmedik bir yanıt döndürdü."
            logger.warning("GitHub yanıtı çözümlenemedi: %s", hata)
            return gh.get("son_cekilen_etkinlikler", []), _son_hata

        # Yazma kilit altında ve yalnızca github alt ağacına: ağ beklerken
        # izleme motorunun kaydettiği oturumları eskimiş kopyayla silmemek için.
        with json_deposu.guncelle() as taze:
            taze["github"]["son_cekilen_etkinlikler"] = etkinlikler
            taze["github"]["son_senkron"] = simdi.isoformat()

        _son_hata = None
        return etkinlikler, None
    finally:
        _senkron_kilidi.release()


def _anlasilir_hata(hata):
    """Ham istisna metni yerine kullanıcıya gösterilebilir mesaj."""
    if isinstance(hata, requests.HTTPError) and hata.response is not None:
        kod = hata.response.status_code
        if kod == 404:
            return "GitHub kullanıcısı bulunamadı. Ayarlar'dan kullanıcı adını kontrol et."
        if kod in (403, 429):
            return "GitHub istek sınırına takıldı. Bir süre sonra tekrar denenecek."
        return f"GitHub {kod} döndürdü."
    if isinstance(hata, requests.Timeout):
        return "GitHub zaman aşımına uğradı."
    if isinstance(hata, requests.ConnectionError):
        return "GitHub'a bağlanılamadı (internet bağlantısını kontrol et)."
    return "GitHub verisi güncellenemedi."


def arka_planda_senkronize_et(zorla=False):
    """Sayfa render'ını bloklamadan senkron başlatır."""
    threading.Thread(
        target=senkronize_et, args=(zorla,), daemon=True, name="github-senkron"
    ).start()


def en_aktif_repo(etkinlikler):
    sayac = {}
    for etkinlik in etkinlikler:
        if not isinstance(etkinlik, dict):
            continue
        repo = etkinlik.get("repo")
        if repo:
            sayac[repo] = sayac.get(repo, 0) + etkinlik.get("commit_sayisi", 0)
    if not sayac:
        return None
    repo = max(sayac, key=sayac.get)
    return {"repo": repo, "commit_sayisi": sayac[repo]}


def repo_ozeti(etkinlikler, limit=5):
    sayac = {}
    for etkinlik in etkinlikler:
        if not isinstance(etkinlik, dict):
            continue
        repo = etkinlik.get("repo")
        if repo:
            sayac[repo] = sayac.get(repo, 0) + etkinlik.get("commit_sayisi", 0)
    return [
        {"repo": repo, "commit_sayisi": sayi}
        for repo, sayi in sorted(sayac.items(), key=lambda x: -x[1])[:limit]
    ]
