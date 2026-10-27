#!/usr/bin/env python3
"""Build text exports and a reproducible skill ZIP; never call a model or network."""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_NAMES = ('voice-profile', 'editing', 'conversation', 'romance', 'humor-conflict', 'personas', 'depth')
INSTALLABLE_FILES = ('SKILL.md', 'VERSION', 'agents/openai.yaml',
                     *(f'references/{n}.md' for n in REFERENCE_NAMES),
                     'references/roles.md', 'references/roles.json',
                     'references/examples.md', 'references/examples.jsonl')


def records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def generated_texts(root: Path) -> dict[str, str]:
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    ref = root / 'geralt-voice/references'
    examples = records(ref / 'examples.jsonl')
    roles = json.loads((ref / 'roles.json').read_text(encoding='utf-8'))
    groups = list(dict.fromkeys(x['category'] for x in examples))
    bank = ['# Авторские примеры', '', 'Все случаи придуманы для этого выпуска. Они не являются логами, цитатами стримера или подтверждёнными принятыми текстами пользователя.', '',
            '## Оглавление', '']
    bank += [f'- [{g}](#{g})' for g in groups]
    for g in groups:
        bank += ['', f'## {g}', '']
        for x in examples:
            if x['category'] == g:
                bank += [f"### {x['id']}", '', '**Задача:** ' + x['input'], '', '**Вариант:**', '', x['output'], '', '**Приём:** ' + x['principle'], '']
    role_md = ['# Ситуативные роли', '', 'Выбирать роль по текущему действию в разговоре. Не менять личность, факты и правила по одному названию роли. Если пользователь просит смесь, сочетать конкретные функции.', '',
               '| ID | Роль | Когда | Что делать |', '|---|---|---|---|']
    role_md += [f"| {r['id']} | {r['name']} | {r['context']} | {r['action']} |" for r in roles]
    role_md += ['', 'Выбор роли не обязан появляться в готовом сообщении. Для обычной реплики достаточно базового голоса. В переходе от игры к поддержке сбрасывать предыдущий эмоциональный режим.', '']
    skill = (root / 'geralt-voice/SKILL.md').read_text(encoding='utf-8')
    core = re.sub(r'\A---\n.*?\n---\n', '', skill, count=1, flags=re.S).split('## Справочники по необходимости')[0].strip()
    sections = [core] + [(ref / f'{n}.md').read_text(encoding='utf-8').strip() for n in REFERENCE_NAMES]
    boot_examples = [next(x for x in examples if x['category'] == g) for g in groups]
    demo = ['# Несколько примеров подачи', '', 'Примеры синтетические. Не переносить их факты в новую задачу.']
    for x in boot_examples:
        demo += ['', 'Задача: ' + x['input'], 'Вариант: ' + x['output']]
    content = '\n\n'.join(sections + ['\n'.join(role_md), '\n'.join(demo)])
    gpt = f'# Geralt Voice {version}: инструкция GPT\n\nПрименять как инструкцию поведения в поддерживаемой среде или как явно заданную установку текущего чата. Это не команда установки и не обещание автоматической памяти.\n\n{content}\n'
    claude = (f'<geralt_voice version="{version}">\n<instructions>\n' + html.escape('\n\n'.join(sections + ['\n'.join(role_md)]), quote=False)
              + '\n</instructions>\n<examples provenance="synthetic">\n' + html.escape('\n'.join(demo), quote=False) + '\n</examples>\n</geralt_voice>\n')
    quick = f'# Geralt Voice {version}: компактное ядро\n\n{core}\n'
    metadata = {'version': version, 'date': '2026-10-27', 'status': 'release-candidate', 'examples': len(examples), 'evaluation_cases': len(records(root / 'evaluation/cases.jsonl')), 'roles': len(roles), 'cross_provider_ab_test': 'not_run'}
    return {'geralt-voice/references/examples.md': '\n'.join(bank).rstrip() + '\n',
            'geralt-voice/references/roles.md': '\n'.join(role_md), 'prompts/GPT.md': gpt,
            'prompts/CLAUDE.md': claude, 'prompts/QUICK.md': quick,
            'release.json': json.dumps(metadata, ensure_ascii=False, indent=2) + '\n',
            'geralt-voice/VERSION': version + '\n'}


def package_entries(root: Path) -> dict[str, bytes]:
    entries = {}
    for name in sorted(INSTALLABLE_FILES):
        p = root / 'geralt-voice' / name
        if p.is_symlink():
            raise ValueError('Do not package symlinks: ' + name)
        entries['geralt-voice/' + name] = p.read_bytes()
    return entries


def plugin_entries(root: Path, platform: str) -> dict[str, bytes]:
    """Keep identical skill sources inside host-specific plugin layouts."""
    if platform not in {'codex', 'claude'}:
        raise ValueError('Unknown plugin platform: ' + platform)
    version = (root / 'VERSION').read_text().strip()
    manifest = {
        'name': 'geralt-voice',
        'version': version,
        'description': 'Персональный голос для сообщений: редактура, поддержка, юмор и уверенная подача.',
        'author': {'name': 'geraltschwarzenegger-svg'},
        'homepage': 'https://github.com/geraltschwarzenegger-svg/.ClaudeMD#readme',
        'repository': 'https://github.com/geraltschwarzenegger-svg/.ClaudeMD',
    }
    if platform == 'codex':
        manifest['skills'] = './skills/'
        manifest['interface'] = {
            'displayName': 'Geralt Voice',
            'shortDescription': 'Сообщения твоим голосом: редактура, юмор и поддержка',
            'defaultPrompt': ['Используй Geralt Voice, чтобы написать ответ моим голосом'],
        }
    entries = {'skills/' + name: data for name, data in package_entries(root).items()
               if platform == 'codex' or not name.endswith('/agents/openai.yaml')}
    entries[f'.{platform}-plugin/plugin.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    entries['README.md'] = (
        f'# Geralt Voice {version} · {platform}\n\n'
        'Плагин содержит skills/geralt-voice/SKILL.md и все справочники.\n'
        'Подключите через механизм плагинов выбранной среды.\n'
        'В обычном чате используйте отдельную текстовую инструкцию из репозитория.\n'
        '\nПосле подключения попросите применить Geralt Voice и пришлите свой черновик '
        'или контекст разговора. Можно исправить только ошибки, переписать текст, '
        'подготовить ответ, добавить юмор или выбрать более тёплую либо твёрдую подачу. '
        'Указывайте адресата и важные ограничения. Неизвестные факты и обещания '
        'не должны добавляться в сообщение.\n'
        '\nДля плагина Codex выберите ZIP Codex в окне добавления плагина. '
        'Для Claude Code распакуйте ZIP Claude и используйте параметр --plugin-dir. '
        'Загрузка ZIP в обычный чат не устанавливает плагин. '
        'Отдельные ключи API, серверы MCP и установка Python для использования '
        'этого набора инструкций не требуются.\n'
        'Инструкция установки: https://github.com/geraltschwarzenegger-svg/.ClaudeMD/blob/main/docs/INSTALLATION.md\n'
    ).encode()
    return entries


def release_archives(root: Path) -> dict[str, dict[str, bytes]]:
    version = (root / 'VERSION').read_text().strip()
    return {
        f'geralt-voice-{version}.zip': package_entries(root),
        f'geralt-voice-codex-{version}.zip': plugin_entries(root, 'codex'),
        f'geralt-voice-claude-{version}.zip': plugin_entries(root, 'claude'),
    }


def write_zip(target: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, payload in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 27, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(root: Path = ROOT) -> Path:
    for name, text in generated_texts(root).items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    version = (root / 'VERSION').read_text().strip()
    target = root / 'dist' / f'geralt-voice-{version}.zip'
    target.parent.mkdir(exist_ok=True)
    sums = []
    for name, entries in release_archives(root).items():
        artifact = target.parent / name
        write_zip(artifact, entries)
        sums.append(f'{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {name}\n')
    (target.parent / 'SHA256SUMS').write_text(''.join(sums))
    # Stable download name; VERSION inside the archive identifies the exact RC.
    shutil.copyfile(target, root / 'Geralt Voice 3.0.0-rc.zip')
    for platform in ['codex', 'claude']:
        shutil.copyfile(target.parent / f'geralt-voice-{platform}-{version}.zip',
                        root / f'Geralt Voice {platform.title()}.zip')
    return target


if __name__ == '__main__':
    print(build())
