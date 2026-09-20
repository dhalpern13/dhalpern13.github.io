import copy
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import yaml

from server import Conflict, PublicationStore, make_handler

ROOT = Path(__file__).resolve().parents[1]


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ('_data', '_resume', 'files'):
            shutil.copytree(ROOT / directory, self.root / directory)
        shutil.copy2(ROOT / 'compile-data.py', self.root / 'compile-data.py')
        self.store = PublicationStore(self.root)

    def change(self, **request):
        return self.store.change({'revision': self.store.state()['revision'], **request})

    def assert_rendered_labels_unique(self):
        papers = yaml.safe_load((self.root / '_data/papers.yml').read_text())
        ids = [p['paper_id'] for p in papers]
        self.assertEqual(len(ids), len(set(ids)))

    def test_crud_stable_labels_and_pdf_preservation(self):
        original = self.store.state()['data']['conference']
        paper = copy.deepcopy(original[0])
        paper['title'] = 'A dashboard test paper'
        resume = (self.root / 'files/resume.pdf').read_bytes()
        result = self.change(action='save', category='conference', index=None, paper=paper)
        self.assertEqual(result['data']['conference'][0]['paper_id'], f'C{len(original)+1}')
        self.assertEqual(result['data']['conference'][1]['paper_id'], f'C{len(original)}')
        self.assertIn('A dashboard test paper', (self.root / '_data/papers.yml').read_text())
        self.assertEqual(resume, (self.root / 'files/resume.pdf').read_bytes())
        self.change(action='delete', category='conference', index=0)
        result = self.change(action='save', category='conference', index=None, paper=paper)
        self.assertEqual(result['data']['conference'][0]['paper_id'], f'C{len(original)+2}')
        self.assertTrue((self.root / 'files' / (paper['link'] + '.pdf')).exists())
        self.assert_rendered_labels_unique()
        self.assertTrue(list((self.root / '_publication_admin/backups').iterdir()))

    def test_edit_retains_unknown_metadata_and_other_sections(self):
        source = self.store.source.read_text().replace("link: 'prophet-p-mean'", "link: 'prophet-p-mean'\n    custom-note: 'Keep me'")
        self.store.source.write_text(source)
        original = self.store.state()['data']
        paper = copy.deepcopy(original['working'][0])
        paper.pop('custom-note')
        paper['title'] = 'Edited working paper'
        result = self.change(action='save', category='working', index=0, paper=paper)
        self.assertEqual(result['data']['working'][0]['custom-note'], 'Keep me')
        self.assertEqual(result['data']['coauthors'], original['coauthors'])
        self.assertTrue(self.store.source.read_text().startswith(source.split('working:')[0]))

    def test_move_working_paper_to_conference(self):
        data = self.store.state()['data']
        paper = copy.deepcopy(data['working'][0])
        paper.update(conference='EC', citation='ACM Conference on Economics and Computation', year='2027')
        result = self.change(action='save', category='conference', originalCategory='working', index=0, paper=paper)
        self.assertEqual(len(result['data']['working']), len(data['working'])-1)
        self.assertEqual(result['data']['conference'][0]['title'], paper['title'])
        self.assertEqual(result['data']['working'][0]['paper_id'], f'W{len(data["working"])-1}')
        self.assert_rendered_labels_unique()

    def test_single_author_thesis_and_new_collaborator(self):
        before = (self.root / '_resume/publications.tex').read_bytes()
        author = {'key': 'example', 'long': 'Example Author', 'short': 'E. Author', 'website': 'https://example.org'}
        self.change(action='collaborator', author=author)
        paper = {'title': 'Another thesis', 'link': 'thesis', 'institution': 'Harvard University', 'year': '2025', 'authors': ['example']}
        self.change(action='save', category='theses', index=None, paper=paper)
        papers = yaml.safe_load((self.root / '_data/papers.yml').read_text())
        thesis = next(p for p in papers if p['title'] == 'Another thesis')
        self.assertEqual(thesis['authors'], '[Example Author](https://example.org)')
        self.assertEqual(before, (self.root / '_resume/publications.tex').read_bytes())

    def test_stale_revision_and_bad_file_do_not_write(self):
        raw = self.store.source.read_bytes()
        with self.assertRaises(Conflict):
            self.store.change({'revision': 'old', 'action': 'delete', 'category': 'working', 'index': 0})
        paper = copy.deepcopy(self.store.state()['data']['working'][0])
        for bad in ('../files/thesis', 'missing-file'):
            paper['link'] = bad
            with self.assertRaises(ValueError):
                self.change(action='save', category='working', index=0, paper=paper)
        self.assertEqual(raw, self.store.source.read_bytes())

    def test_failed_generation_does_not_write(self):
        raw = self.store.source.read_bytes()
        (self.root / 'compile-data.py').write_text('raise RuntimeError("Test failure")')
        paper = self.store.state()['data']['working'][0]
        with self.assertRaisesRegex(ValueError, 'Nothing was saved'):
            self.change(action='save', category='working', index=0, paper=paper)
        self.assertEqual(raw, self.store.source.read_bytes())

    def test_delete_only_thesis(self):
        result = self.change(action='delete', category='theses', index=0)
        self.assertEqual(result['data']['theses'], [])
        self.assertNotIn('paper_id: T1', (self.root / '_data/papers.yml').read_text())

    def test_optional_collaborator_website(self):
        self.change(action='collaborator', author={'key': 'example', 'long': 'Example Author', 'short': 'E. Author', 'website': ''})
        paper = {'title': 'Test paper', 'authors': ['example'], 'link': 'thesis'}
        self.change(action='save', category='working', index=None, paper=paper)
        papers = yaml.safe_load((self.root / '_data/working-papers.yml').read_text())
        self.assertEqual(papers[0]['authors'], 'Example Author')
        self.assertIn('E. Author', (self.root / '_resume/working.tex').read_text())
        self.assertNotIn('\\link{}', (self.root / '_resume/working.tex').read_text())

    def test_write_failure_rolls_back(self):
        import server
        original_write = server.atomic_write
        original = {name: (self.root / name).read_bytes() for name in ['_data/publication-data.yml', *server.OUTPUTS]}
        failed = False

        def fail_once(path, contents):
            nonlocal failed
            if path == self.root / '_data/working-papers.yml' and not failed:
                failed = True
                raise OSError('Test write failure')
            original_write(path, contents)

        paper = copy.deepcopy(self.store.state()['data']['working'][0])
        paper['title'] = 'This should roll back'
        with patch('server.atomic_write', side_effect=fail_once):
            with self.assertRaisesRegex(OSError, 'Test write failure'):
                self.change(action='save', category='working', index=0, paper=paper)
        for name, contents in original.items():
            self.assertEqual(contents, (self.root / name).read_bytes(), name)

    def test_http_guard_and_read_state(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.store, 'test-token', 0))
        port = server.server_port
        server.RequestHandlerClass = make_handler(self.store, 'test-token', port)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f'http://127.0.0.1:{port}'
        with urlopen(url + '/api/state') as response:
            self.assertEqual(json.load(response)['token'], 'test-token')
        for headers in ({}, {'X-Editor-Token': 'test-token', 'Origin': 'https://example.org'}, {'Host': 'evil.example'}):
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(url + '/api/change', data=b'{}', headers=headers))
            self.assertEqual(error.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
