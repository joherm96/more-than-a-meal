#!/usr/bin/env python3
"""QA harness for the More Than a Meal static site.

Usage:  python3 -I qa/check_site.py [BASE_URL]

With no BASE_URL a local http.server is started on a free port (in a thread)
serving the project directory. Screenshots go to qa/shots/<page>-<width>.png.
Prints a PASS / WARN / FAIL table and exits 1 if anything FAILs.
"""
import glob
import functools
import http.server
import os
import re
import socket
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

# `python3 -I` ignores PYTHONPATH, so find the installed playwright package if needed.
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    _candidates = [
        "/Applications/Loom.app/Contents/Resources/runtime/site-packages",
        *glob.glob(os.path.expanduser("~/Library/Python/*/lib/python/site-packages")),
        *glob.glob("/opt/homebrew/lib/python3*/site-packages"),
    ]
    for _c in _candidates:
        if os.path.isdir(os.path.join(_c, "playwright")) and _c not in sys.path:
            sys.path.append(_c)
    from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "qa", "shots")
PAGES = ["index", "story", "classes", "teachers", "farms", "book", "thanks"]
IMAGE_WARN_BYTES = 400 * 1024
BANNED_WORDS = re.compile(r"\b(PENDING|TODO|lorem|placeholder)\b", re.I)
FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")

MOBILE = dict(viewport={"width": 375, "height": 812}, device_scale_factor=2,
              is_mobile=True, has_touch=True)
DESKTOP = dict(viewport={"width": 1280, "height": 800})

results = []  # (status, page, view, check, detail)


def add(status, page, view, check, detail=""):
    results.append((status, page, view, check, detail))


def ok_or_fail(problems, page, view, check, ok_detail="", warn=False):
    if problems:
        shown = "; ".join(problems[:6]) + (f"; (+{len(problems) - 6} more)" if len(problems) > 6 else "")
        add("WARN" if warn else "FAIL", page, view, check, shown)
    else:
        add("PASS", page, view, check, ok_detail)


# --------------------------------------------------------------------------- server

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def start_server():
    handler = functools.partial(QuietHandler, directory=ROOT)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def online():
    try:
        socket.create_connection(("fonts.googleapis.com", 443), timeout=3).close()
        return True
    except OSError:
        return False


def url_status(url):
    """HTTP status for a URL (GET, small read); 0 on connection failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "site-qa"})
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read(1)
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


# --------------------------------------------------------------------------- in-page JS

JS_OVERFLOW = """() => ({sw: document.scrollingElement.scrollWidth, iw: window.innerWidth,
  culprits: [...document.querySelectorAll('body *')].filter(e => {
     const r = e.getBoundingClientRect(); return r.width > 0 && r.right > window.innerWidth + 1;
  }).slice(0, 5).map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
     (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/).join('.') : ''))})"""

JS_IMAGES = """() => [...document.images].map(i => ({src: i.currentSrc || i.getAttribute('src') || '',
  alt: i.getAttribute('alt'), complete: i.complete, nw: i.naturalWidth}))"""

JS_LINKS = """() => {
  const out = [];
  const push = (el, attr, v) => { if (v) out.push({tag: el.tagName.toLowerCase(), attr, v}); };
  document.querySelectorAll('[href]').forEach(e => push(e, 'href', e.getAttribute('href')));
  document.querySelectorAll('[src]').forEach(e => push(e, 'src', e.getAttribute('src')));
  document.querySelectorAll('[srcset]').forEach(e => e.getAttribute('srcset').split(',').forEach(
     s => push(e, 'srcset', s.trim().split(/\\s+/)[0])));
  document.querySelectorAll('form[action]').forEach(e => push(e, 'action', e.getAttribute('action')));
  return out;
}"""

JS_IDS = """() => { const c = {}; document.querySelectorAll('[id]').forEach(e => c[e.id] = (c[e.id] || 0) + 1);
  return Object.entries(c).filter(([k, n]) => n > 1).map(([k, n]) => k + ' x' + n); }"""

JS_LABELS = """() => [...document.querySelectorAll('input, select, textarea')].filter(e => {
    const t = (e.getAttribute('type') || '').toLowerCase();
    if (['hidden', 'submit', 'button', 'reset', 'image'].includes(t)) return false;
    if (e.name === '_honey') return false;   // honeypot is meant to be invisible
    return true;
  }).filter(e => {
    const hasLabel = e.labels && [...e.labels].some(l => l.textContent.trim());
    const lb = e.getAttribute('aria-labelledby');
    const hasLb = lb && lb.split(/\\s+/).some(id => { const x = document.getElementById(id); return x && x.textContent.trim(); });
    return !(hasLabel || hasLb || (e.getAttribute('aria-label') || '').trim());
  }).map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.name ? '[name=' + e.name + ']' : ''))"""

JS_TAPS = """() => {
  const vis = e => { const s = getComputedStyle(e);
     return s.display !== 'none' && s.visibility !== 'hidden' && e.getClientRects().length > 0; };
  const out = [];
  document.querySelectorAll('a, button, input, select').forEach(e => {
    const t = (e.getAttribute('type') || '').toLowerCase();
    if (e.tagName === 'INPUT' && t === 'hidden') return;
    if (e.name === '_honey') return;
    if (!vis(e)) return;
    let r = e.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) return;           // visually-hidden (e.g. skip link)
    let w = r.width, h = r.height;
    if (['checkbox', 'radio'].includes(t) && e.labels) {   // a label enlarges the hit area
      for (const l of e.labels) { const lr = l.getBoundingClientRect();
        w = Math.max(w, lr.width); h = Math.max(h, lr.height); }
    }
    const after = getComputedStyle(e, '::after');            // stretched-link pattern
    if (after.content !== 'none' && after.position === 'absolute' && after.inset === '0px') {
      let c = e.parentElement;
      while (c && getComputedStyle(c).position === 'static') c = c.parentElement;
      if (c) { const cr = c.getBoundingClientRect(); w = Math.max(w, cr.width); h = Math.max(h, cr.height); }
    }
    if (w >= 40 && h >= 40) return;
    const inline = e.tagName === 'A' && getComputedStyle(e).display.startsWith('inline') &&
       !!e.closest('p, li p, figcaption, blockquote, address, small, td, dd');
    const label = (e.innerText || e.value || e.getAttribute('aria-label') || e.getAttribute('href') || '').trim()
       .replace(/\\s+/g, ' ').slice(0, 30);
    out.push({desc: e.tagName.toLowerCase() + ' "' + label + '" ' + (Math.round(w*10)/10) + 'x' + (Math.round(h*10)/10), inline});
  });
  return out;
}"""


# --------------------------------------------------------------------------- page checks

def check_page(ctx, base, name, view, is_online, seen_local):
    page = ctx.new_page()
    console_errs, bad_reqs = [], []
    page.on("console", lambda m: console_errs.append(m.text[:160]) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errs.append("pageerror: " + str(e)[:160]))

    def font(url):
        return any(h in url for h in FONT_HOSTS)

    def on_failed(req):
        if font(req.url) and not is_online:
            return
        bad_reqs.append(f"{req.url} ({req.failure})")

    def on_response(resp):
        if resp.status >= 400 and not (font(resp.url) and not is_online):
            bad_reqs.append(f"{resp.url} -> {resp.status}")

    page.on("requestfailed", on_failed)
    page.on("response", on_response)

    url = f"{base}/{name}.html"
    try:
        resp = page.goto(url, wait_until="load", timeout=20000)
    except Exception as e:
        add("FAIL", name, view, "page loads", f"{url}: {e}".splitlines()[0])
        page.close()
        return
    if resp is None or resp.status >= 400:
        add("FAIL", name, view, "page loads", f"{url} -> {resp.status if resp else 'no response'}")
        page.close()
        return
    add("PASS", name, view, "page loads")
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    # trigger lazy images, then return to top
    page.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += 400) {
        window.scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); } window.scrollTo(0, 0); }""")
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass

    w = 375 if view == "mobile" else 1280
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, f"{name}-{w}.png"), full_page=True)

    # 1. console + requests (page-level resource 404s land in bad_reqs)
    ok_or_fail(console_errs, name, view, "console errors")
    ok_or_fail(sorted(set(r for r in bad_reqs if not r.startswith(url + " "))), name, view, "failed requests")

    # 2. horizontal overflow
    ov = page.evaluate(JS_OVERFLOW)
    ok_or_fail([f"scrollWidth {ov['sw']} > innerWidth {ov['iw']}; wide: {', '.join(ov['culprits'])}"]
               if ov["sw"] > ov["iw"] + 1 else [], name, view, "no horizontal overflow")

    # 3. images
    probs = []
    for im in page.evaluate(JS_IMAGES):
        short = im["src"].replace(base + "/", "")
        if im["alt"] is None or not im["alt"].strip():
            probs.append(f"{short}: missing/empty alt")
        if im["nw"] == 0:
            probs.append(f"{short}: naturalWidth 0 (broken or not loaded)")
    ok_or_fail(probs, name, view, "images: alt + loaded")

    # 4. text, ids, links: only once per page (desktop pass) to avoid duplicate rows
    if view == "desktop":
        text = page.evaluate("() => document.body ? document.body.innerText : ''")
        hits = []
        for line in text.splitlines():
            if BANNED_WORDS.search(line):
                hits.append(repr(line.strip()[:80]))
        ok_or_fail(hits, name, "-", "no PENDING/TODO/lorem/placeholder text")

        ok_or_fail(page.evaluate(JS_IDS), name, "-", "unique element ids")

        probs = []
        ids_here = set(page.evaluate("() => [...document.querySelectorAll('[id]')].map(e => e.id)"))
        names_here = set(page.evaluate("() => [...document.querySelectorAll('a[name]')].map(e => e.name)"))
        for ln in page.evaluate(JS_LINKS):
            v = ln["v"].strip()
            if re.match(r"^(mailto:|tel:|sms:|javascript:|data:)", v, re.I):
                continue
            if v.startswith("#"):
                frag = urllib.parse.unquote(v[1:])
                if frag and frag not in ids_here and frag not in names_here:
                    probs.append(f"{ln['tag']}[{ln['attr']}]={v}: no element with that id")
                continue
            absu = urllib.parse.urljoin(url, v)
            pu, pb = urllib.parse.urlparse(absu), urllib.parse.urlparse(base)
            if pu.netloc != pb.netloc:
                continue  # external
            target = urllib.parse.urlunparse(pu._replace(fragment=""))
            if target not in seen_local:
                seen_local[target] = url_status(target)
            st = seen_local[target]
            if not (200 <= st < 400):
                probs.append(f"{ln['tag']}[{ln['attr']}]={v} -> {st or 'unreachable'}")
        ok_or_fail(probs, name, "-", "local href/src resolve")

        if name == "book":
            ok_or_fail(page.evaluate(JS_LABELS), name, "-", "form controls have labels")

    # 5. tap targets (mobile)
    if view == "mobile":
        taps = page.evaluate(JS_TAPS)
        hard = [t["desc"] for t in taps if not t["inline"]]
        soft = [t["desc"] for t in taps if t["inline"]]
        ok_or_fail(hard, name, view, "tap targets >= 40x40")
        if soft:
            ok_or_fail(soft, name, view, "tap targets (inline text links)", warn=True)
    page.close()


# --------------------------------------------------------------------------- interactions

def test_interactions(ctx, base):
    page = ctx.new_page()
    v = "mobile"

    # hamburger
    try:
        r = page.goto(f"{base}/index.html", wait_until="load")
        if not r or r.status >= 400:
            raise RuntimeError("index.html did not load")
        toggle = page.locator(".nav-toggle, button[aria-controls][aria-expanded]").first
        if toggle.count() == 0:
            raise RuntimeError("no hamburger button (.nav-toggle / button[aria-expanded])")
        if not toggle.is_visible():
            raise RuntimeError("hamburger button not visible at 375px")
        before = toggle.get_attribute("aria-expanded")
        toggle.click()
        opened = toggle.get_attribute("aria-expanded")
        nav_id = toggle.get_attribute("aria-controls")
        nav_vis = page.locator(f"#{nav_id}").is_visible() if nav_id else None
        page.keyboard.press("Escape")
        closed = toggle.get_attribute("aria-expanded")
        probs = []
        if before != "false":
            probs.append(f"initial aria-expanded={before!r}")
        if opened != "true":
            probs.append(f"after click aria-expanded={opened!r}")
        if nav_id and not nav_vis:
            probs.append(f"#{nav_id} not visible when open")
        if closed != "false":
            probs.append(f"after Escape aria-expanded={closed!r}")
        ok_or_fail(probs, "index", v, "hamburger opens / Escape closes")
    except Exception as e:
        add("FAIL", "index", v, "hamburger opens / Escape closes", str(e).splitlines()[0])

    # "Book this class" -> book.html with option selected
    try:
        r = page.goto(f"{base}/book.html", wait_until="load")
        if not r or r.status >= 400:
            raise RuntimeError("book.html did not load")
        original = page.evaluate("""() => { const s = document.querySelector('select#class');
            return s ? [...s.options].map(o => [o.value, o.textContent]) : null; }""")
        if original is None:
            raise RuntimeError("book.html has no select#class")
        r = page.goto(f"{base}/classes.html", wait_until="load")
        if not r or r.status >= 400:
            raise RuntimeError("classes.html did not load")
        link = page.get_by_role("link", name=re.compile(r"book this class", re.I)).first
        if link.count() == 0:
            raise RuntimeError('no "Book this class" link on classes.html')
        href = link.get_attribute("href") or ""
        wanted = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("class", [""])[0]
        link.scroll_into_view_if_needed()
        link.click()
        page.wait_for_url(re.compile(r"/book\.html"), timeout=10000)
        page.wait_for_load_state("load")
        sel = page.evaluate("""() => { const s = document.querySelector('select#class');
            const o = s && s.selectedOptions[0]; return o ? [o.value, o.textContent] : null; }""")
        norm = lambda s: re.sub(r"\s+", " ", (s or "").strip()).lower()
        probs = []
        if not wanted:
            probs.append(f"link href {href!r} has no ?class= value")
        elif not sel or norm(wanted) not in (norm(sel[0]), norm(sel[1])):
            probs.append(f"wanted {wanted!r}, selected {sel!r}")
        elif not any(norm(wanted) in (norm(a), norm(b)) for a, b in original):
            probs.append(f"{wanted!r} is not a real option in select#class (main.js had to inject it)")
        ok_or_fail(probs, "classes", v, '"Book this class" preselects class',
                   f"{href} -> selected {sel[1].strip() if sel else ''!r}")
    except Exception as e:
        add("FAIL", "classes", v, '"Book this class" preselects class', str(e).splitlines()[0])

    # booking form wiring + validation
    try:
        r = page.goto(f"{base}/book.html", wait_until="load")
        if not r or r.status >= 400:
            raise RuntimeError("book.html did not load")
        info = page.evaluate("""() => { const f = document.querySelector('form[action*="formsubmit"]') || document.querySelector('form');
          if (!f) return null;
          const g = n => { const e = f.querySelector(`[name="${n}"]`); if (!e) return null;
             const s = getComputedStyle(e);
             return {type: (e.getAttribute('type') || '').toLowerCase(), value: e.value,
                     hidden: e.type === 'hidden' || s.display === 'none' || s.visibility === 'hidden' ||
                             !!e.closest('[hidden], [aria-hidden="true"]') || e.getClientRects().length === 0 ||
                             (() => { let p = e; while (p) { const c = getComputedStyle(p);
                                if (c.display === 'none' || (c.position === 'absolute' && parseFloat(c.left) < -1000)) return true;
                                p = p.parentElement; } return false; })()}; };
          return {action: f.getAttribute('action') || '', method: (f.getAttribute('method') || 'get').toLowerCase(),
                  honey: g('_honey'), next: g('_next'), valid: f.checkValidity(),
                  required: f.querySelectorAll('[required]').length}; }""")
        if info is None:
            raise RuntimeError("no <form> on book.html")
        probs = []
        if not info["action"].startswith("https://formsubmit.co/"):
            probs.append(f"action={info['action']!r}")
        if info["method"] != "post":
            probs.append(f"method={info['method']!r} (should be POST)")
        if not info["honey"]:
            probs.append("missing _honey field")
        elif not info["honey"]["hidden"]:
            probs.append("_honey field is visible")
        if not info["next"]:
            probs.append("missing _next field")
        else:
            if info["next"]["type"] != "hidden":
                probs.append(f"_next type={info['next']['type']!r}")
            if "thanks" not in (info["next"]["value"] or ""):
                probs.append(f"_next value={info['next']['value']!r} (expected .../thanks.html)")
        ok_or_fail(probs, "book", v, "form: formsubmit action, _honey, _next", info["action"])

        probs = []
        if info["required"] == 0:
            probs.append("no [required] fields")
        if info["valid"]:
            probs.append("form.checkValidity() is true with empty fields")
        # Clicking submit must not navigate (formsubmit requests are blocked anyway)
        before = page.url
        btn = page.locator('form button[type="submit"], form input[type="submit"], form button:not([type])').first
        if btn.count():
            btn.scroll_into_view_if_needed()
            btn.click()
            page.wait_for_timeout(700)
            if page.url != before:
                probs.append(f"empty submit navigated to {page.url}")
        else:
            probs.append("no submit button")
        ok_or_fail(probs, "book", v, "empty submit blocked by validation", f"{info['required']} required fields")
    except Exception as e:
        add("FAIL", "book", v, "form checks", str(e).splitlines()[0])
    page.close()


# --------------------------------------------------------------------------- image weights

def image_weights():
    rows = []
    for dirpath, _, files in os.walk(os.path.join(ROOT, "images")):
        for f in sorted(files):
            if f.startswith("."):
                continue
            p = os.path.join(dirpath, f)
            rows.append((os.path.relpath(p, ROOT), os.path.getsize(p)))
    return rows


# --------------------------------------------------------------------------- main

def main():
    httpd = None
    if len(sys.argv) > 1:
        base = sys.argv[1].rstrip("/")
    else:
        httpd, base = start_server()
    is_online = online()
    print(f"Base URL: {base}   (network {'online' if is_online else 'OFFLINE: Google Fonts failures ignored'})")

    seen_local = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for view, opts in (("mobile", MOBILE), ("desktop", DESKTOP)):
            ctx = browser.new_context(**opts)
            ctx.route(re.compile(r"https?://(www\.)?formsubmit\.co/.*"), lambda route: route.abort())
            for name in PAGES:
                try:
                    check_page(ctx, base, name, view, is_online, seen_local)
                except Exception as e:
                    add("FAIL", name, view, "harness error", str(e).splitlines()[0][:200])
            if view == "mobile":
                test_interactions(ctx, base)
            ctx.close()
        browser.close()

    for path, size in image_weights():
        kb = size / 1024
        add("WARN" if size > IMAGE_WARN_BYTES else "PASS", "images", "-", f"weight {path}", f"{kb:.0f} KB")

    if httpd:
        httpd.shutdown()

    # table
    w1 = max(len(r[1]) for r in results)
    w3 = max(len(r[3]) for r in results)
    print(f"\n{'RESULT':6}  {'PAGE':{w1}}  {'VIEW':7}  {'CHECK':{w3}}  DETAIL")
    print("-" * (6 + w1 + w3 + 30))
    for st, pg, vw, ck, dt in results:
        print(f"{st:6}  {pg:{w1}}  {vw:7}  {ck:{w3}}  {dt}")
    counts = {k: sum(1 for r in results if r[0] == k) for k in ("PASS", "WARN", "FAIL")}
    print(f"\n{counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL   screenshots: {os.path.relpath(SHOTS, ROOT)}/")
    sys.exit(1 if counts["FAIL"] else 0)


if __name__ == "__main__":
    main()
