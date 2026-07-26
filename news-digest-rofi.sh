#!/usr/bin/env bash
# Rofi menu for the news digest: open it, or silently refresh the cached data.
# Bind a Hyprland hotkey to this script to trigger it.

OPEN="📰 Digest'i Aç"
REFRESH="🔄 Digest'i Yenile (arka planda)"

CHOICE=$(printf "%s\n%s" "$OPEN" "$REFRESH" | rofi -dmenu -i -p "News Digest")

case "$CHOICE" in
  "$OPEN")
    /usr/bin/python3 "$HOME/.local/bin/news_digest.py"
    ;;
  "$REFRESH")
    /usr/bin/python3 "$HOME/.local/bin/news_digest.py" --no-open
    command -v notify-send >/dev/null && notify-send "News Digest" "Yenilendi"
    ;;
esac
