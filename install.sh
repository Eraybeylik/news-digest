#!/usr/bin/env bash
# Installs the news digest: script + login autostart + app-launcher entry
# (shows up in rofi drun / your themed app menu) + optional 3-hourly refresh timer.
# Run from the folder containing all the news-digest-* files.
set -euo pipefail

mkdir -p "$HOME/.local/bin" "$HOME/.config/autostart" "$HOME/.config/systemd/user" "$HOME/.local/share/applications"

cp -f news_digest.py "$HOME/.local/bin/news_digest.py"
chmod +x "$HOME/.local/bin/news_digest.py"

cp -f news-digest.desktop "$HOME/.config/autostart/news-digest.desktop"

# App launcher entry (shows up in rofi drun / your themed app menu, same as other apps)
if [ -f news-digest-app.desktop ]; then
  cp -f news-digest-app.desktop "$HOME/.local/share/applications/news-digest.desktop"
  # Rofi's drun mode caches the app list; clear it so the new entry shows up immediately.
  rm -rf "$HOME/.cache/rofi"* 2>/dev/null || true
fi

if [ -f news-digest-rofi.sh ]; then
  cp -f news-digest-rofi.sh "$HOME/.local/bin/news-digest-rofi.sh"
  chmod +x "$HOME/.local/bin/news-digest-rofi.sh"
fi

cp -f news-digest.service "$HOME/.config/systemd/user/news-digest.service"
cp -f news-digest.timer "$HOME/.config/systemd/user/news-digest.timer"

systemctl --user daemon-reload
systemctl --user enable --now news-digest.timer

echo "Installed."
echo "- Opens automatically at login: add 'exec-once = /usr/bin/python3 ~/.local/bin/news_digest.py' to hyprland.conf"
echo "- Shows up in your themed app launcher (rofi drun) as 'News Digest'"
echo "- Refreshes silently every 3h in the background: systemctl --user status news-digest.timer"
echo "- Run manually any time:  python3 ~/.local/bin/news_digest.py"
