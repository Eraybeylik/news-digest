# News Digest — Kurulum (Arch Linux, Hyprland)

Ne yapıyor: Hacker News top story'leri + GitHub Trending repolarını çekip tek bir
HTML sayfası üretiyor (koyu tema, okunaklı). Hiç Electron/headless browser yok —
sadece birkaç HTTP isteği atan ~2 saniyelik bir Python scripti (stdlib only,
ekstra paket kurmana gerek yok).

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

## Kaynak kodunu değiştirmek istersen
- `HN_COUNT` / `GH_COUNT` — kaç haber/repo gösterileceği
- `SECURITY_KEYWORDS` — hangi kelimelerin "security" etiketi tetikleyeceği
- CSS bloğu `render_html()` içinde — renk/tema değişiklikleri için
