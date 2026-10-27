# Установка Geralt Voice: Codex, GPT и Claude

Версия ядра: **3.0.0-rc.3**. Три ZIP собираются из одних исходников. Формат плагина и формат навыка различаются.

## Окно «Новый плагин» на скриншоте

1. Скачай [Geralt Voice Codex.zip](../Geralt%20Voice%20Codex.zip).
2. В окне добавления плагина выбери **этот ZIP целиком**, не распаковывая.
3. После установки включи плагин и попроси: «Используй Geralt Voice, ответь моим голосом: …».

Архив содержит непосредственно в корне:

```text
.codex-plugin/plugin.json
README.md
skills/
  geralt-voice/
    SKILL.md
    VERSION
    agents/openai.yaml
    references/...
```

Прежний `Geralt Voice 3.0.0-rc.zip` содержит `geralt-voice/SKILL.md` и предназначен для загрузки навыка. В нём нет манифеста плагина и корневого `skills/`. Именно это объясняет показанную ошибку установщика. Переименовать файл недостаточно: исправлена структура нового пакета.

## Claude: плагин

Скачай [Geralt Voice Claude.zip](../Geralt%20Voice%20Claude.zip). В совместимом окне установки плагинов выбери ZIP целиком. Для локальной проверки в Claude Code можно распаковать архив в отдельную папку и запустить:

```bash
claude --plugin-dir /absolute/path/to/unpacked-geralt-plugin
```

Навык плагина в Claude Code доступен под пространством имён плагина, например `/geralt-voice:geralt-voice`; его также можно попросить применить обычным текстом.

Структура:

```text
.claude-plugin/plugin.json
README.md
skills/
  geralt-voice/
    SKILL.md
    VERSION
    references/...
```

В Claude ZIP отсутствуют `.codex-plugin/` и `agents/openai.yaml`. Содержимое ядра и справочников сохраняется без переписывания под другую модель. Конкретная подача может отличаться между моделями; одинаковый пакет не гарантирует одинаковые ответы.

## Claude: именно навык

Если интерфейс предлагает добавление **навыка / custom skill**, используй [ZIP навыка](../Geralt%20Voice%203.0.0-rc.zip). Он содержит одну папку `geralt-voice/` с `SKILL.md`. Не путай этот путь с установкой плагина; поддержка навыков зависит от продукта и настроек аккаунта.

## GPT и Claude в обычном чате

Для среды без установки плагинов используй [инструкцию GPT](../prompts/GPT.md), [инструкцию Claude](../prompts/CLAUDE.md) или [компактное ядро](../prompts/QUICK.md). Текст можно применить в поддерживаемом поле инструкций или явно задать для текущего чата. Это не устанавливает плагин и не меняет веса модели.

## Проверка пакетов

Сборка создаёт три версионных ZIP в `dist/` и три ссылки на скачивание в корне репозитория. [SHA256SUMS](../dist/SHA256SUMS) содержит контрольные суммы трёх текущих версионных ZIP. Все манифесты получают версию из `VERSION`.

```bash
python3 scripts/build.py
python3 scripts/check.py --archive
python3 -m unittest discover -s tests -v
```

Тесты проверяют наличие манифеста без внешней папки, `skills/geralt-voice/SKILL.md`, идентичность справочников источникам, относительные ссылки, отсутствие проверочных данных в ZIP и воспроизводимость всех трёх архивов. Повреждение или удаление манифеста обнаруживается негативными тестами.

Дополнительно распакованный Claude-пакет проверен официальным Claude Code **2.1.311**:

```bash
claude plugin validate /absolute/path/to/unpacked-geralt-plugin --strict --json
```

Результат проверки манифеста: `success: true`, ошибок и предупреждений манифеста нет. Эта команда вернула пустой раздел `contents`: содержание навыка, его ссылки и соответствие исходникам проверяются нашими тестами отдельно. Проверка требований публичного каталога плагинов не входила в эту задачу.

Структурная проверка не означает подтверждённую установку в аккаунте пользователя: окно со скриншота недоступно из этой сессии. После загрузки нового ZIP интерфейс может предъявить дополнительные требования; результат установки здесь не заявляется.

## На какие официальные примеры опирается структура

Проверено через GitHub 27.10.2026. Официальные сайты документации в этой среде отвечали 403; вместо них прочитаны исходные примеры разработчиков:

- [OpenAI plugins, README](https://github.com/openai/plugins/blob/0722921d5542fc593105c27bd52630babd8b8c2a/README.md): `.codex-plugin/plugin.json` и `skills/`.
- [Манифест плагина OpenAI](https://github.com/openai/plugins/blob/0722921d5542fc593105c27bd52630babd8b8c2a/plugins/build-web-apps/.codex-plugin/plugin.json): `name`, `version`, `skills`, `interface`.
- [Anthropic, структура плагина](https://github.com/anthropics/claude-plugins-official/blob/41f619d61b999adec1a1c8deb97d1a5b6ac35bb6/README.md): `.claude-plugin/plugin.json` и `skills/`.
- [Anthropic, справочник манифеста](https://github.com/anthropics/claude-plugins-official/blob/41f619d61b999adec1a1c8deb97d1a5b6ac35bb6/plugins/plugin-dev/skills/plugin-structure/references/manifest-reference.md).
