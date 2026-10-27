import base64
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

BUILDER = Path(__file__).resolve().parents[1] / 'scripts' / 'build.py'
PANDOC = shutil.which('pandoc')

@unittest.skipUnless(PANDOC, 'Pandoc is required for integration tests')
class OfflineDocsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='offline-docs-test-')
        self.root = Path(self.temp.name)
        self.docs = self.root / 'docs'
        self.docs.mkdir()
        (self.docs / 'index.md').write_text('# Hello world\n\nStart at [features](features.md#interfaces).\n\n## Start\n\nHello offline.\n', encoding='utf8')
        (self.docs / 'features.md').write_text('# Features\n\n## Interfaces\n\nThe browser is searchable.\n', encoding='utf8')

    def tearDown(self):
        self.temp.cleanup()

    def run_build(self, *flags, env=None, check=True):
        cmd = [sys.executable, str(BUILDER), '--docs', str(self.docs), '--title', 'Test Docs', *flags]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if check and result.returncode != 0:
            raise AssertionError(f'code {result.returncode}: {result.stdout}\n{result.stderr}')
        return result

    def test_single_output_and_rewritten_links(self):
        original = (self.docs / 'index.md').read_bytes()
        self.run_build()
        output = (self.docs / 'index.html').read_text(encoding='utf8')
        self.assertIn('id="search-overlay"', output)
        self.assertIn('offline-docs-signature', output)
        self.assertIn('id="toc-items"', output)
        self.assertNotIn('src="https://', output)
        self.assertRegex(output, r'href="#doc-features-md-[a-z0-9]+--interfaces"')
        self.assertEqual((self.docs / 'index.md').read_bytes(), original)
        self.assertEqual({x.name for x in self.docs.iterdir()}, {'index.md', 'features.md', 'index.html'})

    def test_unchanged_build_skips(self):
        self.run_build()
        file = self.docs / 'index.html'
        before = file.stat().st_mtime_ns
        result = self.run_build()
        self.assertIn('No changes', result.stdout)
        self.assertEqual(file.stat().st_mtime_ns, before)
        (self.docs / 'features.md').write_text('# Features\n\nUpdated details.\n', encoding='utf8')
        result = self.run_build()
        self.assertIn('Built:', result.stdout)
        self.assertIn('Updated details.', file.read_text(encoding='utf8'))

    def test_do_not_overwrite_user_created_html(self):
        output = self.docs / 'index.html'
        output.write_text('MANUAL HTML', encoding='utf8')
        result = self.run_build(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_text(encoding='utf8'), 'MANUAL HTML')
        self.run_build('--overwrite-existing')
        self.assertIn('offline-docs-version', output.read_text(encoding='utf8'))

    def test_nested_docs_and_embedded_image(self):
        nested = self.docs / 'systems'
        nested.mkdir()
        # Small valid PNG.
        pixel = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==')
        (nested / 'pixel.png').write_bytes(pixel)
        (nested / 'usage.md').write_text('# Usage\n\n![pixel](pixel.png)\n', encoding='utf8')
        self.run_build()
        html = (self.docs / 'index.html').read_text(encoding='utf8')
        self.assertIn('data:image/png;base64,', html)
        self.assertIn('Usage', html)

    def test_missing_mermaid_cli_is_explicit(self):
        (self.docs / 'index.md').write_text('# Diagram\n\n```mermaid\ngraph LR\nA-->B\n```\n', encoding='utf8')
        path_env = os.environ.copy()
        # To ensure predictable absence without hiding Pandoc, test an environment with a shim pandoc.
        if shutil.which('mmdc'):
            self.skipTest('mmdc already installed; missing CLI scenario not applicable')
        result = self.run_build(env=path_env, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('mmdc', result.stderr)
        self.assertFalse((self.docs / 'index.html').exists())

    @unittest.skipIf(os.name == 'nt', 'Fake Mermaid CLI integration currently uses POSIX executable')
    def test_mermaid_rendering_embeds_svg(self):
        (self.docs / 'index.md').write_text('# Diagram\n\n```mermaid\ngraph LR\nA-->B\n```\n', encoding='utf8')
        fake_dir = self.root / 'fake-bin'
        fake_dir.mkdir()
        fake = fake_dir / 'mmdc'
        fake.write_text('#!/bin/sh\nwhile [ "$#" -gt 0 ]; do\n  if [ "$1" = "-o" ]; then shift; echo \'<svg xmlns="http://www.w3.org/2000/svg"><text>Diagram OK</text></svg>\' > "$1"; exit 0; fi\n  shift\ndone\nexit 2\n', encoding='utf8')
        fake.chmod(0o755)
        env = os.environ.copy()
        env['PATH'] = str(fake_dir) + os.pathsep + env.get('PATH', '')
        self.run_build(env=env)
        html = (self.docs / 'index.html').read_text(encoding='utf8')
        self.assertIn('data:image/svg+xml;base64,', html)
        self.assertIn('class="diagram"', html)
        self.assertNotIn('graph LR', html)

if __name__ == '__main__':
    unittest.main()
