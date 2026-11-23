#!/usr/bin/env python3
"""Read-only regression checks for the plan hub's guide-to-sample path."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDES = {'/how-many-days-to-run/', '/easy-run-pace/', '/running-plan-without-watch/'}


class Hub(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.start = self.end = self.first_plan = None
        self.position = 0
        self.current = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.position += 1
        attrs = dict(attrs)
        if tag == 'section' and attrs.get('aria-labelledby') == 'before-choosing':
            self.start = self.position
        if tag == 'a':
            href = attrs.get('href', '')
            self.current = [href, '', self.position]
            if href.startswith('/training-plans/') and href != '/training-plans/' and self.first_plan is None:
                self.first_plan = self.position

    def handle_data(self, text):
        if self.current is not None:
            self.current[1] += text

    def handle_endtag(self, tag):
        self.position += 1
        if tag == 'a' and self.current is not None:
            self.links.append(self.current)
            self.current = None
        if tag == 'section' and self.start is not None and self.end is None:
            self.end = self.position


class HubTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / 'training-plans/index.html').read_text()
        self.hub = Hub(self.text)

    def test_guides_precede_sample_choices(self):
        h = self.hub
        self.assertIsNotNone(h.start)
        self.assertIsNotNone(h.end)
        self.assertLess(h.start, h.end)
        self.assertLess(h.end, h.first_plan)
        links = [(url, label) for url, label, pos in h.links if h.start < pos < h.end]
        self.assertEqual({url for url, _ in links}, GUIDES)
        for url, label in links:
            self.assertGreater(len(label.strip().split()), 3, url)
            self.assertTrue((ROOT / url.strip('/') / 'index.html').is_file())

    def test_all_22_sample_destinations_remain(self):
        expected = {'/' + str(p.parent.relative_to(ROOT)) + '/' for p in (ROOT / 'training-plans').glob('*/index.html')}
        self.assertEqual(len(expected), 22)
        actual = {url for url, _, _ in self.hub.links if url.startswith('/training-plans/') and url != '/training-plans/'}
        self.assertEqual(actual, expected)

    def test_play_destination_and_referrer_unchanged(self):
        links = [url for url, _, _ in self.hub.links if url.startswith('https://play.google.com/')]
        self.assertEqual(links, ['https://play.google.com/store/apps/details?id=com.dk.paceline&referrer=ref%3Dseo-hub%26utm_source%3Dseo%26utm_medium%3Dhub'])
        self.assertNotIn('<script', self.text.lower())

    def test_sample_scope_and_existing_guidance_remain(self):
        for phrase in ['not a personal workout prescription', '/what-is-a-taper/', '/missed-weeks-training-plan/', 'Check each page']:
            self.assertIn(phrase, self.text)


if __name__ == '__main__':
    unittest.main()
