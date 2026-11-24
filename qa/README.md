Run from the project folder: `heavy python3 -I qa/check_site.py` (serves the site itself on a free local port) or pass a URL: `heavy python3 -I qa/check_site.py https://example.vercel.app`.
It prints a PASS/WARN/FAIL table (console errors, broken requests/links/images, overflow, alt text, leftover TODO/PENDING text, duplicate ids, form labels, tap targets, menu/booking/form tests, image sizes) and exits 1 on any FAIL.
Full-page screenshots land in `qa/shots/<page>-375.png` and `qa/shots/<page>-1280.png`.
