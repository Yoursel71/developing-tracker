# Katkı Rehberi

Bu, kişisel bir öğrenme takip aracı olarak başladı; yine de düzeltme ve
öneriler memnuniyetle karşılanır.

## Geliştirme ortamı

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest testler/
```

`python app.py` tarayıcı sürümünü, `python masaustu.py` (yalnızca Windows'ta
tam işlevsel) native pencere + tepsi ikonunu çalıştırır.

## Kod stili

- Fonksiyon, değişken ve dosya adları **Türkçe**; bu, projenin baştan beri
  tuttuğu bir gelenek, tutarlılık için sürdürülüyor.
- Yorum yalnızca *neden*i açıklamak için yazılır (gizli bir kısıt, bilinen
  bir hatanın etrafından dolaşma, şaşırtıcı bir davranış) — kodun zaten
  söylediğini tekrar eden yorum eklenmez.
- Yeni bir servis veya modül eklerken önce `servisler/`, `depo/` ya da
  `platform_katmani/` altında benzer bir örneğe bakıp aynı deseni izle.

## Test

Her yeni davranış bir testle gelmeli. `testler/conftest.py`'deki
`gecici_veri_dizini` fixture'ı her testi kendi geçici veri dizininde
çalıştırır — gerçek `data/veri.json`'a asla dokunulmaz. PR'lar CI'da
testler geçmeden derlenmez.

## Pull request

1. Değişikliğini küçük ve odaklı tut.
2. `python -m pytest testler/`'in yeşil olduğundan emin ol.
3. PR açıklamasında neyi, neden değiştirdiğini kısaca anlat.
