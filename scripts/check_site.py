#!/usr/bin/env python3
"""Dependency-free structural HTML and same-site link checks.

This is a focused static-site check, not a full HTML conformance validator.
It makes no network requests and never deploys or modifies site files.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

VOID = set('area base br col embed hr img input link meta param source track wbr'.split())
SITE = 'pacelinerun.com'


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.links, self.ids = [], [], [], set()
        self.doctype = False
        self.titles = self.h1s = 0
        self.in_title = False
        self.title_text = ''
        self.lang = self.charset = False
        self.feed(text)
        self.close()
        if self.stack:
            self.errors.append('unclosed tags: ' + ', '.join(self.stack))
        if not self.doctype:
            self.errors.append('missing HTML doctype')
        if not self.lang:
            self.errors.append('missing html lang')
        if not self.charset:
            self.errors.append('missing charset')
        if self.titles != 1 or not self.title_text.strip():
            self.errors.append('expected one nonempty title')

    def handle_decl(self, decl):
        self.doctype |= decl.lower() == 'doctype html'

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if len(attrs) != len(a):
            self.errors.append('duplicate attribute on ' + tag)
        if tag == 'html':
            self.lang = bool(a.get('lang'))
        if tag == 'meta' and a.get('charset'):
            self.charset = True
        if tag == 'title':
            self.titles += 1
            self.in_title = True
        if tag == 'h1':
            self.h1s += 1
        if a.get('id'):
            if a['id'] in self.ids:
                self.errors.append('duplicate id: ' + a['id'])
            self.ids.add(a['id'])
        for key in ('href', 'src'):
            if a.get(key):
                self.links.append(a[key])
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag in VOID:
            self.errors.append('closing void tag: ' + tag)
        elif not self.stack or self.stack[-1] != tag:
            self.errors.append('unexpected closing tag: ' + tag)
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self.in_title:
            self.title_text += data


def resolve(root, source, href):
    url = urlsplit(href)
    if url.scheme and url.scheme not in ('https', 'http'):
        return None
    if url.netloc and url.hostname != SITE:
        return None
    rel = unquote(url.path)
    target = (root / rel.lstrip('/')) if rel.startswith('/') else source.parent / rel
    if not rel:
        target = source
    target = target.resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('link escapes site root')
    if target.is_dir() or rel.endswith('/'):
        target /= 'index.html'
    return target, unquote(url.fragment)


def check(root):
    root = Path(root).resolve()
    errors = []
    pages = {}
    for source in sorted(root.rglob('*.html')):
        if any(part.startswith('.') for part in source.relative_to(root).parts):
            continue
        try:
            page = Page(source.read_text(encoding='utf-8'))
            pages[source] = page
            errors.extend(f'{source.relative_to(root)}: {e}' for e in page.errors)
        except (UnicodeError, ValueError) as e:
            errors.append(f'{source.relative_to(root)}: {e}')
    for source, page in pages.items():
        for href in page.links:
            try:
                dest = resolve(root, source, href)
                if dest is None:
                    continue
                target, fragment = dest
                if not target.is_file():
                    errors.append(f'{source.relative_to(root)}: missing target {href}')
                elif fragment and target in pages and fragment not in pages[target].ids:
                    errors.append(f'{source.relative_to(root)}: missing anchor {href}')
            except ValueError as e:
                errors.append(f'{source.relative_to(root)}: {e}')
    sitemap = root / 'sitemap.xml'
    if sitemap.exists():
        try:
            tree = ET.parse(sitemap)
            seen = set()
            for item in tree.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                url = item.text or ''
                if url in seen:
                    errors.append('sitemap.xml: duplicate URL ' + url)
                seen.add(url)
                if urlsplit(url).scheme != 'https' or urlsplit(url).hostname != SITE:
                    errors.append('sitemap.xml: unexpected origin ' + url)
                    continue
                dest = resolve(root, root / 'index.html', url)
                if not dest or not dest[0].is_file():
                    errors.append('sitemap.xml: missing target ' + url)
        except ET.ParseError as e:
            errors.append('sitemap.xml: ' + str(e))
    return pages, errors


class SelfTests(unittest.TestCase):
    def test_valid_html_and_broken_structure(self):
        self.assertFalse(Page('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>OK</title></head><body><p>Text</p></body></html>').errors)
        self.assertTrue(Page('<html><head><title></title></head><body><div></body></html>').errors)

    def test_links_and_fragments(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Test</title></head><body>{}</body></html>'
            file = root / 'index.html'
            file.write_text(base.format('<h1 id="ok">OK</h1><a href="#ok">here</a>'))
            self.assertFalse(check(root)[1])
            file.write_text(base.format('<a href="/missing/">missing</a><a href="#absent">bad</a>'))
            self.assertEqual(len(check(root)[1]), 2)
            self.assertIsNone(resolve(root, file, 'https://example.com/'))
            with self.assertRaises(ValueError):
                resolve(root, file, '../outside')

    def test_sitemap_missing_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://pacelinerun.com/missing/</loc></url></urlset>')
            self.assertTrue(check(root)[1])


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        unittest.main(argv=[sys.argv[0]])
    else:
        root = Path(__file__).resolve().parents[1]
        pages, errors = check(root)
        for error in errors:
            print(error)
        print(f'Checked {len(pages)} HTML files; {len(errors)} error(s).')
        sys.exit(bool(errors))
