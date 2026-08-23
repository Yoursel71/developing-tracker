from datetime import datetime, timezone

import requests

from config import GITHUB_ONBELLEK_SURESI_SANIYE, GITHUB_TOKEN
from depo import json_deposu


def _headers():
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _etkinlikleri_cek(kullanici):
    url = f"https://api.github.com/users/{kullanici}/events/public"
    yanit = requests.get(url, headers=_headers(), timeout=10)
    yanit.raise_for_status()
    return yanit.json()


def _push_etkinliklerini_donustur(ham_etkinlikler):
    sonuc = []
    for e in ham_etkinlikler:
        if e.get("type") != "PushEvent":
            continue
        sonuc.append({
            "tarih": e["created_at"][:10],
            "repo": e.get("repo", {}).get("name", "bilinmiyor"),
            "commit_sayisi": len(e.get("payload", {}).get("commits", [])),
        })
    return sonuc


def senkronize_et(zorla=False):
    """GitHub etkinliklerini çeker ve önbelleğe alır. (etkinlikler, hata_mesaji) döner."""
    veri = json_deposu.oku()
    gh = veri["github"]
    simdi = datetime.now(timezone.utc)

    if not zorla and gh.get("son_senkron"):
        son = datetime.fromisoformat(gh["son_senkron"])
        if (simdi - son).total_seconds() < GITHUB_ONBELLEK_SURESI_SANIYE:
            return gh["son_cekilen_etkinlikler"], None

    try:
        ham = _etkinlikleri_cek(gh["kullanici"])
        etkinlikler = _push_etkinliklerini_donustur(ham)
        gh["son_cekilen_etkinlikler"] = etkinlikler
        gh["son_senkron"] = simdi.isoformat()
        json_deposu.yaz(veri)
        return etkinlikler, None
    except requests.RequestException as hata:
        return gh.get("son_cekilen_etkinlikler", []), str(hata)


def en_aktif_repo(etkinlikler):
    sayac = {}
    for e in etkinlikler:
        sayac[e["repo"]] = sayac.get(e["repo"], 0) + e["commit_sayisi"]
    if not sayac:
        return None
    repo = max(sayac, key=sayac.get)
    return {"repo": repo, "commit_sayisi": sayac[repo]}
