# Kostia Bazrov — personal website

Personal portfolio in Russian and English. Source repository:
https://github.com/kostia7alania/kostia7alania.github.io

Plain HTML, CSS and JavaScript. The Russian and English editions have separate
URLs with three editorial case studies and a filterable project index. Case
covers are generated illustrations. The theme follows the device by default
and supports a local override. No third-party fonts, analytics or runtime
dependencies.

## Local preview

```sh
python3 -m http.server 8080
```

Edit the public copy in `scripts/content.py`. After editing content or the page
templates, regenerate the checked-in HTML and sitemap with Python 3.

```sh
python3 scripts/build_site.py
python3 scripts/build_site.py --check
```

## Publication

GitHub Pages publishes the root of `main` automatically after each push.
Cloudflare manages DNS for `kostia7alania.ru`; no VPS is used.
The custom domain must be set in repository Settings → Pages, and its assigned
Cloudflare nameservers must be set at the domain registrar.

Keep `CNAME`, canonical links, `robots.txt`, sitemap and social metadata aligned
when changing the domain. Theme preferences are stored in the visitor's browser.
Both languages and the project index are available without JavaScript.

Production DNS: `emerie.ns.cloudflare.com` and `gerald.ns.cloudflare.com`.
The apex and `www` are DNS-only CNAME records pointing to
`kostia7alania.github.io` (Cloudflare flattens the apex CNAME).
GitHub Pages issues and renews the HTTPS certificate.

GitHub Pages enforces HTTPS and redirects `www` to the apex domain.
Certificate renewal is managed by Pages. The initial certificate setup is complete;
no separate HTTPS workflow or personal access token is needed.
