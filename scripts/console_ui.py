"""Shared Bootstrap navigation for the local TAK management console."""

from __future__ import annotations

from html import escape


PAGES = (
    ("/", "檔案分享"),
    ("/provision", "引導式佈建"),
    ("/media", "MediaMTX 管理"),
    ("/mumble", "Mumble 管理"),
    ("/certificates", "用戶端憑證"),
    ("/settings/groups", "小隊與群組"),
)


def active_page(path: str) -> str:
    for prefix in ("/provision", "/media", "/mumble", "/certificates", "/settings/groups"):
        if path == prefix or path.startswith(prefix + "/"):
            return prefix
    return "/"


def navbar(path: str) -> str:
    active = active_page(path)
    links = []
    for href, label in PAGES:
        current = href == active
        css = "nav-link active" if current else "nav-link"
        aria = ' aria-current="page"' if current else ""
        links.append(f'<li class="nav-item"><a class="{css}"{aria} href="{href}">{escape(label)}</a></li>')
    return (
        '<nav class="navbar navbar-expand-lg portal-navbar" aria-label="控制台頁面">'
        '<div class="container-fluid">'
        '<a class="navbar-brand" href="/">TAK 控制台</a>'
        '<button class="navbar-toggler" type="button" data-bs-toggle="collapse" '
        'data-bs-target="#portal-navbar-links" aria-controls="portal-navbar-links" '
        'aria-expanded="false" aria-label="切換導覽選單">'
        '<span class="navbar-toggler-icon" aria-hidden="true">&#9776;</span></button>'
        '<div class="collapse navbar-collapse" id="portal-navbar-links">'
        f'<ul class="navbar-nav ms-auto mb-2 mb-lg-0">{"".join(links)}</ul>'
        '</div></div></nav>'
    )


def breadcrumb(items: list[tuple[str, str | None]]) -> str:
    if not items:
        return ""
    crumbs = []
    for label, href in items:
        text = escape(str(label))
        content = f'<a href="{escape(href, quote=True)}">{text}</a>' if href else text
        current = ' aria-current="page"' if not href else ""
        crumbs.append(f'<li class="breadcrumb-item{" active" if not href else ""}"{current}>{content}</li>')
    return '<nav aria-label="階層位置"><ol class="breadcrumb">' + "".join(crumbs) + '</ol></nav>'
