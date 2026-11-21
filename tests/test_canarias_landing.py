"""Verifica que la landing distingue distribución permanente y candidatos de CI."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
REPO='/atreyu1968/EvaluaFPCanarias'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            self.hrefs.extend(v for k,v in attrs if k=='href' and v)


class CanaryLandingTests(unittest.TestCase):
    def test_downloads_come_from_current_repository(self):
        html=(ROOT/'docs'/'index.html').read_text(encoding='utf-8')
        self.assertIn('id="descargas"',html)
        section=html.split('id="descargas"',1)[1].split('</section>',1)[0]
        links=Links()
        links.feed(section)
        downloads=[]
        for href in links.hrefs:
            url=urlsplit(href)
            if '/actions/runs/' not in url.path and '/releases' not in url.path:
                continue
            self.assertEqual(url.scheme,'https')
            self.assertEqual(url.hostname,'github.com')
            self.assertTrue(url.path.startswith(REPO+'/'))
            if re.fullmatch(REPO+r'/actions/runs/\d+/artifacts/\d+',url.path):
                downloads.append(url.path)
        # Un único flujo puede producir las cuatro arquitecturas.
        self.assertEqual(len(set(downloads)),4)
        self.assertIn('https://github.com'+REPO+'/releases',links.hrefs)
        for label in ('Windows 10/11','Linux · x64','macOS · Intel','macOS · Apple Silicon'):
            self.assertIn(label,section)
        self.assertIn('sin firma',section)
        self.assertIn('beta.4',section)
        self.assertNotIn('Versión 1.0.6',html)


if __name__=='__main__':
    unittest.main()
