import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from build import build
from check import validate


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='geralt-voice-test-')
        self.root = Path(self.temp.name)
        for name in ['geralt-voice','docs','prompts','evaluation','VERSION','README.md','CHANGELOG.md','BENCHMARK.md','AGENTS.md','CLAUDE.md','requirements-dev.txt']:
            source, target = ROOT/name, self.root/name
            if source.is_dir():
                shutil.copytree(source, target, ignore=shutil.ignore_patterns('local','__pycache__'))
            else:
                shutil.copy2(source,target)
        build(self.root)
    def tearDown(self):
        self.temp.cleanup()
    def edit(self,name,fn):
        p=self.root/name
        p.write_text(fn(p.read_text()))
    def fails(self,part,**kwargs):
        errors=validate(self.root,**kwargs)
        self.assertTrue(any(part in x for x in errors), errors)
    def test_clean_package(self):
        self.assertEqual(validate(self.root,archive=True),[])
    def test_reproducible_zip(self):
        p=build(self.root)
        first=hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(first,hashlib.sha256(build(self.root).read_bytes()).hexdigest())
    def test_archive_single_skill_root(self):
        with zipfile.ZipFile(build(self.root)) as z:
            self.assertTrue(all(n.startswith('geralt-voice/') for n in z.namelist()))
            self.assertIn('geralt-voice/VERSION',z.namelist())
    def test_unexpected_installable_file(self):
        (self.root/'geralt-voice/private-log.txt').write_text('private synthetic marker')
        self.fails('unexpected installable file')
    def test_invalid_yaml(self):
        self.edit('geralt-voice/SKILL.md',lambda s:s.replace('name: geralt-voice','name: [unclosed'))
        self.fails('invalid YAML')
    def test_duplicate_yaml_key(self):
        self.edit('geralt-voice/SKILL.md',lambda s:s.replace('name: geralt-voice','name: geralt-voice\nname: duplicate'))
        self.fails('invalid YAML')
    def test_markdown_missing_file(self):
        self.edit('README.md',lambda s:s+'\n[missing](missing.md)\n')
        self.fails('broken link')
    def test_wrong_directory_same_basename(self):
        self.edit('README.md',lambda s:s+'\n[missing](wrong/SKILL.md)\n')
        self.fails('broken link')
    def test_missing_anchor(self):
        self.edit('README.md',lambda s:s+'\n[missing](CHANGELOG.md#not-a-heading)\n')
        self.fails('broken anchor')
    def test_html_link(self):
        self.edit('README.md',lambda s:s+'\n<a href="missing.md">missing</a>\n')
        self.fails('broken link')
    def test_readme_version(self):
        version=(self.root/'VERSION').read_text().strip()
        self.edit('README.md',lambda s:s.replace(version,'9.9.9'))
        self.fails('release version')
    def test_empty_example_output(self):
        p=self.root/'geralt-voice/references/examples.jsonl'
        rows=[json.loads(x) for x in p.read_text().splitlines()]
        rows[0]['output']=''
        p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
        self.fails('empty or nontext field')
    def test_deleted_rendered_examples(self):
        self.edit('geralt-voice/references/examples.md',lambda s:s.replace('**Вариант:**','**removed:**'))
        self.fails('generated file drift')
    def test_duplicate_example_id(self):
        p=self.root/'geralt-voice/references/examples.jsonl'
        rows=p.read_text().splitlines()
        p.write_text('\n'.join(rows+[rows[0]])+'\n')
        self.fails('duplicate ids')
    def test_long_duplicate_bullet(self):
        line='\n- '+('Повторённое нормативное правило для проверки валидатора. '*4)+'\n'
        for name in ['editing','conversation']:
            self.edit(f'geralt-voice/references/{name}.md',lambda s:s+line)
        self.fails('duplicate long rule')
    def test_missing_numbered_section(self):
        self.edit('geralt-voice/references/editing.md',lambda s:s+'\nСм. раздел 999 в `conversation.md`.\n')
        self.fails('broken numbered section')
    def test_generated_prompt_drift(self):
        self.edit('prompts/GPT.md',lambda s:s+'\nextra\n')
        self.fails('generated file drift')
    def test_claude_xml(self):
        self.edit('prompts/CLAUDE.md',lambda s:s+'<broken>')
        self.fails('well-formed XML')
    def test_archive_tamper(self):
        p=next((self.root/'dist').glob('*.zip'))
        p.write_bytes(b'not a zip')
        self.fails('archive error',archive=True)
    def test_checksum_tamper(self):
        self.edit('dist/SHA256SUMS',lambda s:s.replace(s[:64],'0'*64))
        self.fails('checksum mismatch',archive=True)
    def test_data_leakage(self):
        p=self.root/'evaluation/cases.jsonl'
        cases=[json.loads(x) for x in p.read_text().splitlines()]
        cases[0]['input']=json.loads((self.root/'geralt-voice/references/examples.jsonl').read_text().splitlines()[0])['input']
        p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in cases))
        self.fails('leaked into examples')
    def test_false_user_acceptance(self):
        self.edit('geralt-voice/references/examples.jsonl',lambda s:s.replace('"user_accepted": false','"user_accepted": true',1))
        self.fails('must not claim user acceptance')
    def test_format_contract(self):
        p=self.root/'geralt-voice/references/examples.jsonl'
        rows=[json.loads(x) for x in p.read_text().splitlines()]
        rows[0]['output']='Привет.'
        p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
        self.fails('pc format violation')


if __name__=='__main__':
    unittest.main()
