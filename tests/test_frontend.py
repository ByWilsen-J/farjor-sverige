"""Regression: an unknown arrival must not become an arrival on departure day."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


class FrontendArrivalTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js required')
    def test_unknown_arrival_is_not_a_dated_arrival_event(self):
        html = (Path(__file__).resolve().parents[1] / 'index.html').read_text()
        script = html.split('<script>')[-1].split('</script>')[0]
        script = script.rsplit('init();', 1)[0]
        assertions = '''
        DATA = {meta:{}, avgangar_datum:{}, fartyg_datum:{}};
        const row = bygRad({rederi:'Test', avghamn:'Rostock', ankhamn:'Trelleborg', avgtid:'12:00', anktid:''}, 'Test', '', new Date(2026,9,21));
        if(row._arrDate !== '' || Number.isFinite(row._sortAnk)) throw new Error('Unknown arrival became a dated event');
        const known = bygRad({rederi:'Test', avghamn:'Rostock', ankhamn:'Trelleborg', avgtid:'12:00', anktid:'18:00'}, 'Test', '', new Date(2026,9,21));
        if(known._arrDate !== '2026-10-21') throw new Error('Known arrival lost its date');
        '''
        runner = 'const vm=require("node:vm"); vm.runInNewContext(' + json.dumps(script + assertions) + ', {console, setTimeout,clearTimeout,AbortController});'
        result = subprocess.run(['node', '-e', runner], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
