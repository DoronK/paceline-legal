#!/usr/bin/env python3
"""Read-only regression for generated plan-page share metadata."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HAND_OWNED = {'10k-training-plan-beginner', 'half-marathon-training-plan-beginner'}


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.meta, self.canonical, self.title = {}, [], ''
        self.in_title = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta':
            key = a.get('property', a.get('name'))
            if key:
                self.meta.setdefault(key, []).append(a.get('content'))
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonical.append(a.get('href'))
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, text):
        if self.in_title:
            self.title += text


class MetadataTests(unittest.TestCase):
    def test_all_generated_page_identities(self):
        paths = [ROOT / 'training-plans/index.html'] + [
            p for p in (ROOT / 'training-plans').glob('*/index.html')
            if p.parent.name not in HAND_OWNED]
        self.assertEqual(len(paths), 21)
        for path in paths:
            with self.subTest(page=str(path.relative_to(ROOT))):
                head = Head(path.read_text())
                expected_url = 'https://pacelinerun.com/' + str(path.parent.relative_to(ROOT)) + '/'
                self.assertEqual(head.canonical, [expected_url])
                expected = {
                    'og:title': head.title,
                    'og:description': head.meta['description'][0],
                    'og:url': expected_url,
                    'og:type': 'website' if path.parent.name == 'training-plans' else 'article',
                    'og:site_name': 'Paceline',
                    'og:image': 'https://pacelinerun.com/img/paceline-icon.png',
                    'og:image:width': '192',
                    'og:image:height': '192',
                    'og:image:alt': 'Paceline app icon',
                    'twitter:card': 'summary',
                }
                for key, value in expected.items():
                    self.assertEqual(head.meta.get(key), [value], key)
                self.assertNotIn('?', expected_url)
                self.assertTrue((ROOT / 'img/paceline-icon.png').is_file())


if __name__ == '__main__':
    unittest.main()
