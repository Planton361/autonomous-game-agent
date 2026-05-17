#!/usr/bin/env bash
set -euo pipefail

tmp="$(mktemp --suffix=.png)"
trap 'rm -f "$tmp"' EXIT

spectacle --background --nonotify --activewindow --output "$tmp" >/dev/null
magick "$tmp" -alpha off -depth 8 ppm:-
