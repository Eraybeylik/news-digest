# News Digest — Kurulum (Fedora, GNOME)

> Bu branch Fedora + GNOME için uyarlanmıştır. Arch/Hyprland kurulumu için
> `main` branch'ine bak.

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

## Gereksinimler
Fedora Workstation (GNOME) bunların hepsini zaten kurulu getiriyor:
- `python3` (stdlib only, ek pip paketi gerekmiyor)
- `xdg-utils` (script'in tarayıcı açması için — `webbrowser` modülü bunu kullanır)
- `systemd` (arka plan timer'ı için)

rofi **gerekmiyor** — GNOME kendi app launcher'ını (Activities/Overview) kullanıyor.

## Dosyalar
- `news_digest.py` — asıl script (distro'dan bağımsız, değişmedi)
- `news-digest.desktop` — XDG autostart girişi; GNOME `~/.config/autostart`'ı
  native okuduğu için ekstra bir şey yapmana gerek yok (Hyprland'ın aksine)
- `news-digest-app.desktop` — app-launcher girişi: GNOME Activities/Overview'da
  "News Digest" olarak arayıp açabilirsin
- `news-digest-rofi.sh` — opsiyonel, sadece rofi kuruluysa `install.sh`
  tarafından kurulur; GNOME'da kurulmaz, dokunmana gerek yok
- `news-digest.service` + `news-digest.timer` — arka planda sessizce her 3
  saatte bir içeriği tazeleyen systemd user timer
- `install.sh` — hepsini yerine kopyalayıp aktif eden script

## Kurulum

```bash
git clone -b fedora-gnome git@github.com:Eraybeylik/news-digest.git
cd news-digest
chmod +x install.sh
./install.sh
```

Bu işlem:
1. `news_digest.py`'yi `~/.local/bin/`'a koyar
2. `news-digest.desktop`'ı `~/.config/autostart/`'a koyar → GNOME oturum
   açılışında otomatik çalıştırır, ekstra config gerekmez
3. `news-digest-app.desktop`'ı `~/.local/share/applications/news-digest.desktop`
   olarak koyar → GNOME Activities/Overview'da "News Digest" diye aratılabilir
4. `systemctl --user enable --now news-digest.timer` ile arka planda 3 saatte
   bir içeriği sessizce yeniler

## GNOME'da kullanmak
- **Otomatik açılış:** Kurulumdan sonra oturum açtığında digest otomatik
  üretilip tarayıcıda açılır (GNOME `~/.config/autostart`'ı native destekler,
  Hyprland'daki gibi manuel satır eklemene gerek yok).
- **Activities/Overview'dan manuel açmak:** Süper tuşuna bas (ya da Activities'e
  tıkla), "News Digest" yaz, Enter — digest'i üretip tarayıcıda açar.
- **Görünmezse:** GNOME Shell bazen app cache'ini geç yeniler; `Alt+F2` → `r`
  (X11'de) ile shell'i restart edebilir veya oturumu kapatıp açabilirsin
  (Wayland'da restart kısayolu yok).

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
