#!/usr/bin/env python3
"""Check the general home, the FDE and graphics portfolios, their project pages, and redirects after the Hugo build."""
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.tags = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def count(self, name):
        return sum(tag == name for tag, _ in self.tags)

    @property
    def ids(self):
        return {attrs["id"] for _, attrs in self.tags if "id" in attrs}


root = Path(sys.argv[1] if len(sys.argv) > 1 else "public").resolve()
paths = [root / "index.html", root / "graphics/index.html", root / "404.html"]
projects_dir = root / "graphics"
slugs = sorted(p.parent.name for p in projects_dir.glob("*/index.html"))
paths.extend(projects_dir / slug / "index.html" for slug in slugs)
# The FDE portfolio and its case studies live under /fde/; the home page lists every project.
fde_slugs = ("onegoal", "omnimed3d", "webserv", "ft_transcendence", "mini-engine")
home_slugs = fde_slugs + ("minirt",)
paths.append(root / "fde/index.html")
paths.extend(root / "fde" / slug / "index.html" for slug in fde_slugs)
errors = []
for retired in ("vulkan-study-log", "archives", "series", "tags", "categories", "search"):
    if (root / retired).exists():
        errors.append(f"{retired}/: retired section is still published (see /legacy/ snapshot)")
# Old /portfolio/ links must keep working after the move to /graphics/.
for slug in [""] + slugs:
    old = root / "portfolio" / slug / "index.html"
    if not old.is_file() or f"/graphics/{slug + '/' if slug else ''}\"" not in old.read_text(encoding="utf-8"):
        errors.append(f"{old.relative_to(root)}: expected a redirect to /graphics/{slug}")
# The portfolio is shared as /FDE/, and GitHub Pages paths are case-sensitive.
fde_alias = root / "FDE/index.html"
if not fde_alias.is_file() or '/fde/"' not in fde_alias.read_text(encoding="utf-8"):
    errors.append("FDE/index.html: expected a redirect to /fde/")
cache = {}


def read(path):
    if path not in cache:
        cache[path] = Page(path)
    return cache[path]


for path in paths:
    label = str(path.relative_to(root))
    if not path.is_file():
        errors.append(f"{label}: missing page")
        continue
    page = read(path)
    for tag in ("h1", "main", "title"):
        if page.count(tag) != 1:
            errors.append(f"{label}: expected one {tag}, found {page.count(tag)}")
    if path == root / "graphics/index.html":
        for anchor in ("intro-title", "projects", "about", "profile", "contact"):
            if anchor not in page.ids:
                errors.append(f"{label}: missing portfolio section #{anchor}")
        groups = [attrs for _, attrs in page.tags if "competency-group" in attrs.get("class", "").split()]
        if len(groups) != 2:
            errors.append(f"{label}: core expertise and working knowledge must both render")
    if path == root / "index.html":
        for anchor in ("intro-title", "projects", "portfolios", "about", "profile", "contact"):
            if anchor not in page.ids:
                errors.append(f"{label}: missing home section #{anchor}")
        for slug in home_slugs:
            if f"project-{slug}" not in page.ids:
                errors.append(f"{label}: missing project #{f'project-{slug}'}")
        for portfolio in ("/fde/", "/graphics/"):
            if not any(tag == "a" and attrs.get("href") == portfolio for tag, attrs in page.tags):
                errors.append(f"{label}: missing link to the {portfolio} portfolio")
        groups = [attrs for _, attrs in page.tags if "competency-group" in attrs.get("class", "").split()]
        if len(groups) != 2:
            errors.append(f"{label}: both technology groups must render")
    if path == root / "fde/index.html":
        for anchor in ("intro-title", "projects", "about", "profile", "contact"):
            if anchor not in page.ids:
                errors.append(f"{label}: missing portfolio section #{anchor}")
        for slug in fde_slugs:
            if f"project-{slug}" not in page.ids:
                errors.append(f"{label}: missing project #{f'project-{slug}'}")
        groups = [attrs for _, attrs in page.tags if "competency-group" in attrs.get("class", "").split()]
        if len(groups) != 2:
            errors.append(f"{label}: both technology groups must render")
    if path.parent.parent.name == "fde":
        for anchor in ("brief-title", "lineage-title"):
            if anchor not in page.ids:
                errors.append(f"{label}: missing case study section #{anchor}")
    if path.parent.name in ("omnimed3d", "mini-engine", "onegoal") and "architecture-title" not in page.ids:
        errors.append(f"{label}: missing project architecture overview")
    for tag, attrs in page.tags:
        if tag == "img" and "alt" not in attrs:
            errors.append(f"{label}: image without alt attribute")
        link = attrs.get("href") if tag in ("a", "link") else attrs.get("src")
        if not link:
            continue
        url = urlsplit(link)
        if url.scheme and url.scheme not in ("http", "https"):
            continue
        if url.netloc and url.netloc != "nowead.github.io":
            continue
        local = unquote(url.path)
        target = (root / local.lstrip("/")) if local.startswith("/") else (path.parent / local if local else path)
        if target.is_dir():
            target /= "index.html"
        if not target.is_file():
            errors.append(f"{label}: missing local target {link}")
        elif url.fragment and target.suffix == ".html" and unquote(url.fragment) not in read(target).ids:
            errors.append(f"{label}: missing anchor {link}")

home = root / "graphics/index.html"
if home.is_file():
    projects = [attrs for _, attrs in read(home).tags if "data-project" in attrs]
    if len(projects) < 5:
        errors.append("graphics: expected all five existing projects to render")
    for slug in ("omnimed3d", "mini-engine"):
        if not (root / f"graphics/{slug}/index.html").is_file():
            errors.append(f"graphics: missing featured project {slug}")

for name, index, expected in (("home", root / "index.html", home_slugs), ("fde", root / "fde/index.html", fde_slugs)):
    if index.is_file():
        projects = [attrs for _, attrs in read(index).tags if "data-project" in attrs]
        if len(projects) != len(expected):
            errors.append(f"{name}: expected {len(expected)} projects, found {len(projects)}")

if errors:
    print("Site validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    sys.exit(1)
print(f"Validated {len(paths)} pages: page structure, portfolio sections, projects, local links, anchors, and assets.")
