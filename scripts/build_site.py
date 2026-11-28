#!/usr/bin/env python3
"""Render the static pages with the standard library. Pages publishes the checked-in output."""

import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from content import CASES, CATEGORIES, DOMAIN, GITHUB, LINKEDIN, PROJECTS, TELEGRAM


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("ru", "en")
ASSETS = {
    file: f"/{file}?v={sha256((ROOT / file).read_bytes()).hexdigest()[:12]}"
    for file in ("style.css", "site.js")
}
THEME_BOOTSTRAP = (ROOT / "theme.js").read_text(encoding="utf-8").rstrip()


def localized(value, lang):
    return escape(value[LANGUAGES.index(lang)] if isinstance(value, tuple) else value)


def home_url(lang):
    return "/en/" if lang == "en" else "/"


def case_url(slug, lang):
    return f"{home_url(lang)}cases/{slug}/"


def layout(lang, routes, title, description, body, *, home=False, image="assets/portfolio-social.jpg"):
    def t(ru, en):
        return localized((ru, en), lang)

    base = home_url(lang)
    other = "en" if lang == "ru" else "ru"
    person = t("Костя Базров", "Kostia Bazrov")
    metadata = '<meta name="robots" content="noindex">'
    schema = ""
    if routes:
        canonical = f"{DOMAIN}{routes[lang]}"
        metadata = f'''<link rel="canonical" href="{canonical}">
    <link rel="alternate" hreflang="ru" href="{DOMAIN}{routes['ru']}">
    <link rel="alternate" hreflang="en" href="{DOMAIN}{routes['en']}">
    <link rel="alternate" hreflang="x-default" href="{DOMAIN}{routes['ru']}">
    <meta property="og:type" content="{'website' if home else 'article'}">
    <meta property="og:locale" content="{t('ru_RU', 'en_US')}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:image" content="{DOMAIN}/{image}">
    <meta name="twitter:card" content="summary_large_image">'''
        if home:
            person_data = {
                "@context": "https://schema.org",
                "@type": "Person",
                "name": "Kostia Bazrov",
                "alternateName": "Костя Базров",
                "url": DOMAIN + "/",
                "jobTitle": "Frontend Engineer",
                "sameAs": [GITHUB, LINKEDIN],
            }
            schema = f'\n    <script type="application/ld+json">{json.dumps(person_data, ensure_ascii=False)}</script>'

    return f'''<!doctype html>
<html lang="{lang}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="dark light">
    <title>{title}</title>
    <meta name="description" content="{description}">
    {metadata}
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <script>
{THEME_BOOTSTRAP}
    </script>
    <link rel="stylesheet" href="{ASSETS['style.css']}">
    <script src="{ASSETS['site.js']}" defer></script>{schema}
  </head>
  <body id="top">
    <a class="skip" href="#main">{t('К содержимому', 'Skip to content')}</a>
    <header class="site-header">
      <div class="wrap header-inner">
        <a class="brand" href="{base}">
          <span class="brand-mark" aria-hidden="true">kb.</span>
          <span>{person}</span>
        </a>
        <nav class="site-nav" aria-label="{t('Навигация', 'Main navigation')}">
          <a href="{base}#work">{t('Кейсы', 'Case studies')}</a>
          <a href="{base}#projects">{t('Проекты', 'Projects')}</a>
          <a href="{base}#about">{t('Обо мне', 'About')}</a>
        </nav>
        <div class="header-controls">
          <a class="language-link" href="{routes[other] if routes else home_url(other)}" lang="{other}" hreflang="{other}" aria-label="{t('EN (Read in English)', 'RU (Читать на русском)')}">{other.upper()}</a>
          <label class="theme-control" data-theme-control hidden>
            <span aria-hidden="true">◐</span>
            <select data-theme-select aria-label="{t('Тема сайта', 'Color theme')}">
              <option value="system">{t('Авто', 'Auto')}</option>
              <option value="dark">{t('Тёмная', 'Dark')}</option>
              <option value="light">{t('Светлая', 'Light')}</option>
            </select>
          </label>
        </div>
      </div>
    </header>
{body}
    <footer id="contact" class="site-footer">
      <div class="wrap">
        <div class="contact">
          <div>
            <h2>{t('Обсудим задачу', 'Let’s talk about your project')}</h2>
            <p>{t('Разработка интерфейсов, модернизация сайтов и автоматизация.', 'Frontend development, website modernization and automation.')}</p>
          </div>
          <a class="button button-primary" href="{TELEGRAM}">{t('Написать в Telegram', 'Message on Telegram')} <span aria-hidden="true">↗</span></a>
        </div>
        <div class="footer-bottom">
          <span>© {person}</span>
          <nav aria-label="{t('Профили и навигация', 'Profiles and navigation')}">
            <a href="{GITHUB}">GitHub</a>
            <a href="{LINKEDIN}">LinkedIn</a>
            <a href="#top">{t('Наверх', 'Back to top')} <span aria-hidden="true">↑</span></a>
          </nav>
        </div>
      </div>
    </footer>
  </body>
</html>
'''


def case_card(case, lang):
    name = localized(case["name"], lang)
    label = localized(("Смотреть кейс", "Read case study"), lang)
    image = case["image"]
    return f'''          <article class="case-card case-card--{case['image']}">
            <div class="case-media">
              <img src="/assets/{image}-small.webp" srcset="/assets/{image}-small.webp 720w, /assets/{image}.webp 1240w" sizes="auto, (max-width: 760px) calc(100vw - 40px), 52vw" alt="" width="1240" height="827" loading="lazy" decoding="async">
            </div>
            <div class="case-card-copy">
              <p class="case-category">{localized(case['category'], lang)}</p>
              <h3>{name}</h3>
              <p>{localized(case['summary'], lang)}</p>
              <a class="case-cta" href="{case_url(case['slug'], lang)}" aria-label="{label} {name}">{label} <span aria-hidden="true">→</span></a>
            </div>
          </article>'''


def project_row(project, lang):
    name, category, destination, stack, description = project
    element = "div"
    href = ""
    arrow = ""
    if destination:
        external = destination.startswith("https://")
        if external:
            url = destination
        elif destination.startswith("/"):
            url = home_url(lang) + destination.lstrip("/")
        else:
            url = case_url(destination, lang)
        element = "a"
        href = f' href="{escape(url)}"'
        arrow = f'\n              <span class="project-arrow" aria-hidden="true">{"↗" if external else "→"}</span>'
    return f'''          <li data-project="{category}">
            <{element} class="project-row"{href}>
              <div class="project-copy">
                <h3>{localized(name, lang)}</h3>
                <p>{localized(description, lang)}</p>
              </div>
              <span class="project-stack">{localized(stack, lang)}</span>{arrow}
            </{element}>
          </li>'''


def render_home(lang):
    def t(ru, en):
        return localized((ru, en), lang)

    cards = "\n".join(case_card(case, lang) for case in CASES)
    rows = "\n".join(project_row(project, lang) for project in PROJECTS)
    filter_items = {"all": ("Все", "All"), **CATEGORIES}
    filters = "\n".join(
        f'          <button type="button" data-filter="{key}" aria-pressed="{str(key == "all").lower()}" aria-controls="project-list">{localized(label, lang)}</button>'
        for key, label in filter_items.items()
    )

    body = f'''    <main id="main" tabindex="-1">
      <section class="hero wrap" aria-labelledby="hero-title">
        <div class="hero-copy">
          <p class="hero-role">{t('Frontend Engineer', 'Frontend Engineer')}</p>
          <h1 id="hero-title">{t('Костя', 'Kostia')}<br>{t('Базров', 'Bazrov')}</h1>
          <p class="hero-intro">{t('Разрабатываю интерфейсы для складов, интернет-магазинов и сервисов с AI.', 'I build interfaces for warehouse operations, online stores and AI tools.')}</p>
          <div class="hero-actions">
            <a class="button button-primary" href="#work">{t('Смотреть кейсы', 'Explore case studies')} <span aria-hidden="true">↓</span></a>
            <a class="button button-secondary" href="#contact">{t('Связаться', 'Get in touch')}</a>
          </div>
        </div>
        <div class="hero-media">
          <img src="/assets/hero.webp" srcset="/assets/hero-small.webp 640w, /assets/hero.webp 1100w" sizes="(max-width: 760px) calc(100vw - 40px), (max-width: 1280px) 50vw, 640px" alt="" width="1100" height="825" fetchpriority="high">
        </div>
      </section>

      <section class="wrap section" id="work" aria-labelledby="work-title">
        <div class="section-heading">
          <h2 id="work-title">{t('Избранные кейсы', 'Selected case studies')}</h2>
          <p>{t('Какие задачи решал и что получилось.', 'The problems I worked on and the results.')}</p>
        </div>
        <div class="case-grid">
{cards}
        </div>
      </section>

      <section class="wrap section" id="projects" aria-labelledby="projects-title">
        <div class="section-heading">
          <h2 id="projects-title">{t('Проекты', 'Projects')}</h2>
          <a class="text-link" href="{GITHUB}?tab=repositories">{t('Все репозитории на GitHub', 'All repositories on GitHub')} <span aria-hidden="true">↗</span></a>
        </div>
        <div class="project-toolbar" data-project-toolbar hidden>
          <div class="project-filters" role="group" aria-label="{t('Фильтр проектов', 'Filter projects')}">
{filters}
          </div>
          <p class="project-count" data-project-count role="status"></p>
        </div>
        <ul class="project-list" id="project-list" role="list">
{rows}
        </ul>
      </section>

      <section class="section about" id="about" aria-labelledby="about-title">
        <div class="wrap about-inner">
          <h2 id="about-title">{t('Обо мне', 'About me')}</h2>
          <div>
            <p class="about-lead">{t('Больше восьми лет в коммерческой frontend-разработке.', 'Over eight years in commercial frontend engineering.')}</p>
            <p>{t('В последних проектах работаю с Vue и TypeScript. Разбираю пользовательский сценарий и API-контракт, собираю компоненты, проверяю основные сценарии и довожу изменения до релиза.', 'In recent projects I’ve worked with Vue and TypeScript. I trace user journeys and API contracts, build components, test key flows and take changes through to release.')}</p>
            <p>{t('В своих проектах делаю статические сайты, интеграции и инструменты на базе локальных моделей. Люблю, когда интерфейс понятен с первого действия, а код можно развивать без лишней сложности.', 'In my own projects I build static websites, integrations and tools that use local models. I care about interfaces that make the first step clear and code that’s straightforward to extend.')}</p>
          </div>
        </div>
      </section>
    </main>'''
    return layout(
        lang,
        {locale: home_url(locale) for locale in LANGUAGES},
        t("Костя Базров | Frontend Engineer", "Kostia Bazrov | Frontend Engineer"),
        t("Портфолио Кости Базрова. Кейсы frontend-разработки для складских систем, интернет-магазинов и сервисов с AI.",
          "Kostia Bazrov’s frontend engineering portfolio. Case studies for warehouse operations, online stores and AI tools."),
        body,
        home=True,
    )


def render_case(case, next_case, lang):
    def t(ru, en):
        return localized((ru, en), lang)

    section_titles = (("Задача", "The problem"), ("Мой вклад", "My contribution"), ("Результат", "The outcome"))
    sections = "\n".join(
        f'          <section><h2>{localized(title, lang)}</h2><p>{localized(paragraph, lang)}</p></section>'
        for title, paragraph in zip(section_titles, case["sections"])
    )
    steps = "\n".join(f'          <li>{localized(step, lang)}</li>' for step in case["steps"])
    links = "\n".join(
        f'            <a class="button button-secondary" href="{escape(url)}">{localized(text, lang)} <span aria-hidden="true">↗</span></a>'
        for url, text in case["links"]
    )
    links = f'\n          <div class="case-links">\n{links}\n          </div>' if links else ""

    title = localized(case["name"], lang)
    summary = localized(case["summary"], lang)
    example = ""
    if case["image"] == "warehouse":
        example = f'''
        <section class="scan-example" aria-labelledby="scan-example-title">
          <h2 id="scan-example-title">{t('Что видит оператор', 'What the operator sees')}</h2>
          <p>{t('Пример с тестовым номером.', 'Example using a sample serial number.')}</p>
          <div class="scan-states">
            <div>
              <h3>{t('Первый скан', 'First scan')}</h3>
              <code>SN-DEMO-01</code>
              <p>{t('Товар добавлен в список.', 'Item added to the list.')}</p>
            </div>
            <div>
              <h3>{t('Повторный скан', 'Repeat scan')}</h3>
              <code>SN-DEMO-01</code>
              <p>{t('Повтор подсвечен. В списке одна запись.', 'Duplicate flagged. The list still contains one item.')}</p>
            </div>
          </div>
        </section>'''
    body = f'''    <main id="main" tabindex="-1" class="wrap case-main">
      <article class="case-story case-story--{case['image']}">
        <a class="text-link case-back" href="{home_url(lang)}#work"><span aria-hidden="true">←</span> {t('Все кейсы', 'All case studies')}</a>
        <header class="case-intro">
          <p class="case-category">{localized(case['category'], lang)}</p>
          <h1>{title}</h1>
          <p class="case-summary">{summary}</p>
        </header>
        <dl class="case-facts">
          <div><dt>{t('Моя роль', 'My role')}</dt><dd>{localized(case['role'], lang)}</dd></div>
          <div><dt>{t('Технологии', 'Technology')}</dt><dd>{localized(case['stack'], lang)}</dd></div>
          <div><dt>{t('Что проверено', 'Evidence')}</dt><dd>{localized(case['state'], lang)}</dd></div>
        </dl>
        <figure class="case-cover">
          <img src="/assets/{case['image']}.webp" alt="" width="1240" height="827" fetchpriority="high">
          <figcaption>{t('Иллюстрация к кейсу', 'Case study illustration')}</figcaption>
        </figure>
        <div class="case-flow">
          <h2>{t('Как это работает', 'How it works')}</h2>
          <ol>
{steps}
          </ol>
        </div>{example}
        <div class="case-narrative">
{sections}{links}
        </div>
      </article>
      <nav class="case-next" aria-label="{t('Следующий кейс', 'Next case study')}">
        <a href="{case_url(next_case['slug'], lang)}">
          <span>{t('Следующий кейс', 'Next case study')}</span>
          <strong>{localized(next_case['name'], lang)}</strong>
          <span class="next-arrow" aria-hidden="true">→</span>
        </a>
      </nav>
    </main>'''
    return layout(
        lang,
        {locale: case_url(case["slug"], locale) for locale in LANGUAGES},
        f"{title} | {t('Костя Базров', 'Kostia Bazrov')}",
        summary,
        body,
        image=f"assets/{case['image']}-social.jpg",
    )


def render_ayugram_sync(lang):
    def t(ru, en):
        return localized((ru, en), lang)

    routes = {locale: home_url(locale) + "ayugram-sync/" for locale in LANGUAGES}
    download = "/ayugram-sync/ayugram-sync-0.1-preview.zip"
    source = f"{GITHUB}/kostia7alania.github.io/tree/main/ayugram-sync"
    guide = f"{GITHUB}/kostia7alania.github.io/blob/main/ayugram-sync/README.md"
    description = t(
        "Перенеси сохранённые правки и удаления из копии AyuGram Desktop в свой архив. Его можно открыть и на втором компьютере.",
        "Move saved edits and deletions from an AyuGram Desktop backup to your own archive. You can open it on a second computer.",
    )
    body = f'''    <main id="main" tabindex="-1" class="wrap case-main">
      <article class="case-story">
        <a class="text-link case-back" href="{home_url(lang)}#projects"><span aria-hidden="true">←</span> {t('Все проекты', 'All projects')}</a>
        <header class="case-intro">
          <p class="case-category">{t('Версия 0.1 · превью', 'Version 0.1 · preview')}</p>
          <h1>AyuGram Sync</h1>
          <p class="case-summary">{description}</p>
          <div class="hero-actions">
            <a class="button button-primary" href="{download}" download>{t('Скачать ZIP', 'Download ZIP')}</a>
            <a class="button button-secondary" href="{guide}" hreflang="ru">{t('Открыть инструкцию', 'Open setup guide (Russian)')}</a>
          </div>
        </header>
        <div class="case-narrative">
          <section>
            <h2>{t('Попробовать на примере', 'Try sample data')}</h2>
            <div>
              <p>{t('Распакуй ZIP, открой терминал в этой папке и запусти проверку. Нужен Python 3.9 или новее.', 'Unzip the download, open a terminal in its folder and run the check. You need Python 3.9 or newer.')}</p>
              <p>macOS / Linux<br><code>python3 -B test_roundtrip.py -v</code></p>
              <p>Windows PowerShell<br><code>py -3 -B test_roundtrip.py -v</code></p>
              <p>{t('Пример создаст тестовую правку и удаление, передаст их двум архивам и выведет OK.', 'The demo generates a sample edit and deletion, sends both to two archives and prints OK.')}</p>
            </div>
          </section>
          <section>
            <h2>{t('Что умеет превью', 'What the preview supports')}</h2>
            <p>{t('Можно посмотреть, по каким личным чатам есть записи, вручную импортировать один чат и открыть его сохранённый текст. Архив запускается на своём компьютере. Фоновый сбор, Android и вложения пока не поддерживаются.', 'List private chats with saved records, import one chat at a time and read its saved text. The archive runs on your own computer. Background capture, Android and attachments are outside this preview.')}</p>
          </section>
          <section>
            <h2>{t('Фикс ленты Desktop', 'Desktop chat history fix')}</h2>
            <div>
              <p>{t('Отдельный патч возвращает сохранённый удалённый текст в обычную ленту личного чата. Патч проверен на macOS arm64. Статус выпуска указан в PR.', 'A separate patch restores saved deleted text to the regular private chat history. It was tested on macOS arm64. See the PR for release status.')}</p>
              <p><a class="text-link" href="https://github.com/AyuGram/AyuGramDesktop/pull/530">{t('Патч в AyuGram Desktop #530', 'AyuGram Desktop patch #530')}</a></p>
            </div>
          </section>
          <div class="case-links">
            <a class="button button-secondary" href="{source}">{t('Исходники и проверка', 'Source and test')} <span aria-hidden="true">↗</span></a>
          </div>
        </div>
      </article>
    </main>'''
    return layout(lang, routes, "AyuGram Sync | " + t("Костя Базров", "Kostia Bazrov"), description, body)


def render_not_found():
    body = '''    <main id="main" tabindex="-1" class="wrap not-found">
      <p class="hero-role">404</p>
      <h1>Страница не найдена</h1>
      <p lang="en">Page not found.</p>
      <div class="hero-actions">
        <a class="button button-primary" href="/">На главную</a>
        <a class="button button-secondary" href="/en/" lang="en">English homepage</a>
      </div>
    </main>'''
    return layout("ru", None, "Страница не найдена | Костя Базров", "Page not found.", body)


def render_files():
    pages = {"404.html": render_not_found()}
    urls = []
    for lang in LANGUAGES:
        home = home_url(lang)
        pages[home.lstrip("/") + "index.html"] = render_home(lang)
        urls.append(home)
        sync = home + "ayugram-sync/"
        pages[sync.lstrip("/") + "index.html"] = render_ayugram_sync(lang)
        urls.append(sync)
        for index, case in enumerate(CASES):
            url = case_url(case["slug"], lang)
            pages[url.lstrip("/") + "index.html"] = render_case(case, CASES[(index + 1) % len(CASES)], lang)
            urls.append(url)

    sitemap = "\n".join(f"  <url><loc>{DOMAIN}{url}</loc></url>" for url in urls)
    pages["sitemap.xml"] = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{sitemap}
</urlset>
'''
    return pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check the committed output for drift")
    args = parser.parse_args()
    stale = []
    for name, output in render_files().items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != output:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output, encoding="utf-8")

    if stale:
        parser.exit(1, "Regenerate the site: " + ", ".join(stale) + "\n")


if __name__ == "__main__":
    main()
