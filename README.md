# News Digest — Kurulum (Arch Linux, Hyprland)

Ne yapıyor: dört bölümlü tek bir HTML sayfası üretiyor (koyu tema, okunaklı):
1. **Hacker News** — top story'ler
2. **GitHub Trending** — genel popüler repolar (bugün trend olanlar)
3. **GitHub — New Security Projects** — `security` topic'li, son 14 günde
   açılmış, yıldıza göre sıralı repolar (rastgele trend değil, gerçekten yeni
   siber güvenlik araçları/PoC'ler)
4. **Latest CVEs (NVD)** — son günlerde yayınlanmış CVE'ler; her biri açığın
   ne olduğunu ve nasıl istismar edildiğini anlatan açıklama, CVSS skoru/severity
   ve referans linkiyle geliyor. Üstte de "CVE nedir, CVSS nasıl çalışır"
   anlatan sabit bir bilgi kutusu var.

Hiç Electron/headless browser yok — sadece birkaç HTTP isteği atan birkaç
saniyelik bir Python scripti (stdlib only, ekstra paket kurmana gerek yok).

## Dosyalar
- `news_digest.py` — asıl script
- `news-digest.desktop` — XDG autostart girişi (GNOME/KDE/XFCE gibi masaüstlerinde otomatik açılış için; Hyprland bunu okumuyor, aşağıya bak)
- `news-digest-app.desktop` — app-launcher girişi: rofi `drun` (senin zaten kullandığın temalı menü) içinde "News Digest" olarak görünmesini sağlar
- `news-digest-rofi.sh` — opsiyonel, kendi `rofi -dmenu` penceresini açan "Aç / Yenile" menüsü
- `news-digest.service` + `news-digest.timer` — arka planda sessizce her 3 saatte bir içeriği tazeleyen systemd user timer
- `install.sh` — hepsini yerine kopyalayıp aktif eden script

## Kurulum

```bash
cd ~/news-digest   # bu klasör
chmod +x install.sh
./install.sh
```

Bu işlem:
1. `news_digest.py`'yi `~/.local/bin/`'a koyar
2. `news-digest-app.desktop`'ı `~/.local/share/applications/news-digest.desktop`
   olarak koyar → rofi `drun` menünde diğer uygulamalarla aynı yerde görünür
3. `news-digest-rofi.sh`'ı `~/.local/bin/`'a koyar (opsiyonel ayrı menü)
4. `systemctl --user enable --now news-digest.timer` ile arka planda 3 saatte
   bir içeriği sessizce yeniler

## Hyprland'da girişte otomatik açılması için
Hyprland `~/.config/autostart`'ı okumuyor. `~/.config/hypr/hyprland.conf`
içine şunu ekle:
```
exec-once = /usr/bin/python3 ~/.local/bin/news_digest.py
```
Bu satır her oturum açılışında (bilgisayarı açtığında/login olduğunda) tetiklenir.

## Rofi'de kullanmak
- **Normal (temalı) menün:** Kurulumdan sonra rofi `drun` menünde (WhatsApp,
  Discord vb. ile aynı listede) "News Digest" olarak görünür — tıklayınca
  digest'i üretip tarayıcıda açar. Görünmezse: `rm -rf ~/.cache/rofi*` ile
  cache'i temizle ve menüyü tekrar aç.
- **Ayrı "Aç / Yenile" menüsü (opsiyonel):** `news-digest-rofi.sh`'ı bir
  hotkey'e bağla:
  ```
  bind = $mainMod, N, exec, ~/.local/bin/news-digest-rofi.sh
  ```
  Bu kendi `rofi -dmenu` penceresini açar (varsayılan rofi teması, drun
  temanla aynı olmayabilir).

## Diğer notlar
- Manuel çalıştırmak için: `python3 ~/.local/bin/news_digest.py`
- Sadece dosyayı üretip tarayıcı açmadan güncellemek için: `python3 ~/.local/bin/news_digest.py --no-open`
- Çıktı dosyası: `~/.cache/news-digest/digest.html`
- Timer'ı durdurmak istersen: `systemctl --user disable --now news-digest.timer`
- Kaynak tüketimi: script birkaç saniyede çalışıp kapanıyor, sürekli arka planda
  yaşayan bir süreç yok (idle'da 0 CPU/RAM).

## İngilizce pratiği için
Başlıklar ve GitHub repo açıklamaları orijinal İngilizce haliyle kalıyor —
bilinçli olarak çeviri yapılmadı, günlük okuma pratiği için. Kırmızı çizgili
kartlar (security etiketli) siber güvenlikle ilgili başlıkları otomatik
işaretliyor (CVE, vulnerability, breach, exploit vb. anahtar kelimelere göre).

## Kaynaklar
- Hacker News: resmi Firebase API (`hacker-news.firebaseio.com`)
- GitHub Trending: `github.com/trending` sayfası
- GitHub Security Projects: GitHub Search API (`api.github.com/search/repositories`,
  `topic:security created:>...`) — API key gerektirmiyor ama GitHub'ın
  unauthenticated rate limiti dakikada ~10 istek; script sadece 1 istek attığı
  için sorun olmaz.
- CVE: NVD API 2.0 (`services.nvd.nist.gov/rest/json/cves/2.0`), resmi ABD
  hükümeti CVE veritabanı, API key gerektirmiyor.

## Kaynak kodunu değiştirmek istersen
- `HN_COUNT` / `GH_COUNT` / `SEC_REPO_COUNT` / `CVE_COUNT` — kaç öğe gösterileceği
- `SEC_REPO_WINDOW_DAYS` — security repoları kaç günlük pencerede arayacağı (varsayılan 14)
- `CVE_WINDOW_DAYS` — CVE'leri kaç günlük pencerede arayacağı (varsayılan 3)
- `SECURITY_KEYWORDS` — HN başlıklarında hangi kelimelerin "security" etiketi tetikleyeceği
- CSS bloğu `render_html()` içinde — renk/tema değişiklikleri için
