# asus-zenbook-fan-driver

Keep this repository standalone. Never import private desktop configuration,
private Git history, ASUS binaries, DLLs, Windows drivers or firmware.
Use GPL-3.0-or-later SPDX headers for authored source and 0BSD for packaging.
Do not access hardware or run maximum tests without explicit authorization.
Only the service worker may access EC; ordinary monitoring must never write
mode/PWM. Keep the exact model/version checks. Fan labels are Fan 1 / Fan 2.
Run `make check` and staged install after changes. Keep source archives stable:
packaging is export-ignored so checksums do not depend on themselves.
Public repository conversion, release upload and AUR push require owner approval.
