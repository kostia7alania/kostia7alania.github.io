# Kostia Bazrov — personal website

Personal portfolio in Russian and English. Source repository:
https://github.com/kostia7alania/kostia7alania.github.io

Plain HTML, CSS and a small language switcher. No build step, third-party fonts,
analytics, cookies or remote runtime dependencies. The three featured projects
link to their public source repositories. Artwork is illustrative SVG and CSS.

## Local preview

```sh
python3 -m http.server 8080
```

## Publication

GitHub Pages publishes the root of `main` automatically after each push.
Cloudflare manages DNS for `kostia7alania.ru`; no VPS is used.
The custom domain must be set in repository Settings → Pages, and its assigned
Cloudflare nameservers must be set at the domain registrar.

Keep `CNAME`, canonical links, `robots.txt`, sitemap and social metadata aligned
when changing the domain. The language preference is stored locally in the
visitor's browser. All main content is available without JavaScript.

Production DNS: `emerie.ns.cloudflare.com` and `gerald.ns.cloudflare.com`.
The apex and `www` are DNS-only CNAME records pointing to
`kostia7alania.github.io` (Cloudflare flattens the apex CNAME).
GitHub Pages issues and renews the HTTPS certificate.

GitHub Pages enforces HTTPS and redirects `www` to the apex domain.
Certificate renewal is managed by Pages. The initial certificate setup is complete;
no separate HTTPS workflow or personal access token is needed.
