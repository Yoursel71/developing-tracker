# Değişiklik Geçmişi

## v4 — Katkı grafiği, ikon ve vitrin (2026-08)

- Tek kaynaktan üretilen uygulama ikonu: `.exe`, tepsi ve web favicon.
- Windows açılışında pencere göstermeden, yalnızca tepside başlama;
  `.exe`'ye tekrar tıklamak çalışan pencereyi öne getirir.
- Pencere açılış animasyonu.
- Bağımlılık güncellemeleri (Flask, requests, psutil, Pillow, pywebview 6),
  derleme sürümlerinin pinlenmesi, Dependabot.
- README'nin gerçek rozetler ve ekran görüntüleriyle yenilenmesi; MIT
  lisansı, katkı rehberi, issue şablonları.

## v3 — Veri güvenliği, dürüst ölçüm, yeni arayüz (2026-08)

- Yayınlanan `.exe`'nin veri kaybetme hatasının düzeltilmesi (kullanıcı
  verisi artık `%LOCALAPPDATA%`'da).
- Atomik yazma, günlük yedekler, bozuk dosyadan kurtarma, şema göçü.
- Windows boşta kalma algılaması; checkpoint'li oturum modeli ile çökme
  sonrası hayalet oturumların önlenmesi.
- Gerçek GitHub tarzı ısı haritası (7×53), göreli renk ölçeği.
- Seri (streak), akıllı tahmin, kategori/saat/gün dağılımları.
- Canlı durum yoklaması, AJAX'a geçiş, toast bildirimleri.
- Tasarım sistemi, koyu tema, kenar çubuğu, panel.
- Öğrenme yol haritası, oturum notları ve düzenleme.
- Sistem tepsisi, Windows ile başlatma, tek örnek kilidi.
- Özel kategoriler, hafta karşılaştırması, hedef geçmişi, mola
  hatırlatıcısı, Pomodoro modu, yıl özeti ve rozetler, klavye kısayolları.
- 212 testlik pytest paketi ve CI'da test-önce-derle sırası.

## v2 — Masaüstü kabuğu ve otomatik izleme (2026-08)

- pywebview ile native pencere, PyInstaller ile `.exe` derlemesi.
- Kurulum sihirbazı: hedefler, GitHub kullanıcı adı, izlenecek
  program/siteler.
- Program ve tarayıcı sekmesi algılamasıyla otomatik zaman takibi.
- Tarayıcı eklentisi (Manifest V3) ile site takibi.

## v1 — İlk sürüm (2026-08)

- Zaman takibi, GitHub tarzı ısı haritası, GitHub API entegrasyonu,
  haftalık hedef ve Windows bildirimleri, temel istatistikler.
