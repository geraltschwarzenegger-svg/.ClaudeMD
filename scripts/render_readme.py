#!/usr/bin/env python3
"""Render local README diagrams and descriptive counts from saved paired outputs."""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'docs/assets'
COLORS = ['#ff9b8f', '#a2caff', '#b7dda3']


def text(x, y, value, size=23, color='#f1f3f8', weight='400'):
    return f'<text x="{x}" y="{y}" font-family="DejaVu Sans,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(value)}</text>'


def frame(title, subtitle, height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" viewBox="0 0 1280 {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc><rect width="1280" height="{height}" rx="24" fill="#111622"/>', text(48,60,title,32,weight='700'),text(48,100,subtitle,20,'#abb8ce')]


def cards(name,title,subtitle,items):
    rows=(len(items)+2)//3
    svg=frame(title,subtitle,140+rows*215)
    for i,(heading,lines) in enumerate(items):
        x=48+(i%3)*402; y=135+(i//3)*215; color=COLORS[i%3]
        svg += [f'<rect x="{x}" y="{y}" width="378" height="190" rx="16" fill="#1c2433"/>',text(x+22,y+38,heading,23,color,'700')]
        svg += [text(x+22,y+80+j*31,line,20) for j,line in enumerate(lines)]
    svg.append('</svg>'); (ASSETS/name).write_text('\n'.join(svg)+'\n')


def render():
    ASSETS.mkdir(parents=True,exist_ok=True)
    cards('firmware.svg','Что здесь называется прошивкой','Версия 3.0.0-rc.3 · инструкции для модели, справочники и примеры',[
        ('01 / Ядро',['SKILL.md задаёт приоритеты','Смысл, факты, условия','Один готовый ответ']),
        ('02 / Твой голос',['Профиль и формат как с ПК','24 ситуативные роли','Теплота и напор отдельно']),
        ('03 / Справочники',['Редактура, юмор, поддержка','Йохан и Аянокоджи','Глубина и личная переписка']),
        ('04 / Примеры',['120 синтетических примеров','Иллюстрируют подачу','Не факты о пользователе']),
        ('05 / Экспорты',['GPT, Claude, короткое ядро','Генерируются из исходников','ZIP с папкой geralt-voice']),
        ('06 / Проверка',['76 отдельных задания','Тесты структуры и архива','Обратная связь пользователя'])])
    cards('request-flow.svg','Как запрос становится ответом','Схема поведения по инструкциям · внутренние шаги не выводятся в чат',[
        ('01 / Разобрать вход',['Твой черновик или цитата','Что уже было отправлено','Чего нет во вложениях']),
        ('02 / Выбрать задачу',['Исправить или переписать','Ответить или придумать','Учитывать область правки']),
        ('03 / Настроить подачу',['Адресат и формат','Теплота, напор, юмор','Роль только по ситуации']),
        ('04 / Написать',['Использовать данные факты','Сохранить твою позицию','Не сочинять обязательства']),
        ('05 / Проверить',['Отрицания и неизвестное','Уместность и точный URL','Исполнение твоей просьбы']),
        ('06 / Вернуть',['Один копируемый текст','Варианты по запросу','Разбор, если он нужен'])])
    cards('install-map.svg','Выбери способ подключения','Поддержка инструкций и памяти зависит от конкретного продукта',[
        ('GPT',['Открыть prompts/GPT.md','Добавить как инструкцию','Прислать контекст и задачу']),
        ('Claude',['Открыть prompts/CLAUDE.md','Использовать поле инструкций','Дать материал для ответа']),
        ('Плагины',['Codex: ZIP Codex','Claude: ZIP Claude','Манифест и skills/ в корне'])])
    cards('persona-map.svg','Три ориентира, разные задачи','Авторские профили подачи · не подлинные цитаты и не измеренная имитация',[
        ('Йохан Либерт',['Данное наблюдение','Точное расхождение','Спокойная твёрдая позиция']),
        ('Киётака Аянокоджи',['Факт отдельно от гипотезы','Решение по цели','Понятный следующий шаг']),
        ('Жёсткий разнос',['Аргументный нажим','80 авторских заготовок','Разгон и мат по запросу'])])
    cards('quality-map.svg','Что проверяет качество','Разные уровни доказательств отвечают на разные вопросы',[
        ('Структура',['32 unit-теста','Ссылки, YAML, XML, ZIP','Это не оценка естественности']),
        ('Авторские пробы',['12 новых текстов rc.3','24 исторических текста rc.2','Автор видит свои критерии']),
        ('Что ещё нужно',['Независимые запуски','Слепой выбор пользователя','Нет измеренного победителя'])])
    cards('package-map.svg','Что внутри скачанного ZIP','Навык и два плагина · одно ядро 3.0.0-rc.3',[
        ('ZIP навыка',['geralt-voice/SKILL.md','VERSION и references/','Для загрузки навыка']),
        ('ZIP плагинов',['Манифест нужной среды','skills/geralt-voice/SKILL.md','Справочники и версия']),
        ('Остаётся в репозитории',['Экспорты GPT и Claude','Бенчмарк, задания и тесты','README и его картинки'])])
    rows=[json.loads(s) for s in (ROOT/'evaluation/probes/compare-2.2-vs-3.0.jsonl').read_text().splitlines()]
    both=[r for r in rows if r['copyable_2_2_0'] is not None]
    metrics=[('Полный выход · 12 пар',sum(len(r['output_2_2_0']) for r in rows)/len(rows),sum(len(r['output_3_0_0_rc_2']) for r in rows)/len(rows)),('Только сообщение · 11 пар',sum(len(r['copyable_2_2_0']) for r in both)/len(both),sum(len(r['output_3_0_0_rc_2']) for r in both)/len(both))]
    svg=frame('2.2.0 и 3.0 · средняя длина авторских текстов','Символы с пробелами, не токены · длина не является оценкой качества',540)
    scale=700/max(v for _,a,b in metrics for v in [a,b])
    for i,(label,a,b) in enumerate(metrics):
        y=155+i*170;svg.append(text(48,y,label,23,weight='700'))
        for j,(version,value) in enumerate([('2.2.0',a),('3.0 rc.2',b)]):
            by=y+25+j*47
            svg += [text(48,by+25,version,20),f'<rect x="220" y="{by}" width="{value*scale:.2f}" height="31" rx="5" fill="{COLORS[j]}"/>',text(240+value*scale,by+25,f'{value:.1f}',21)]
    svg += [text(48,505,'Открытая авторская реконструкция · не независимый A/B · победитель не установлен',20,'#abb8ce'),'</svg>']
    (ASSETS/'benchmark-length.svg').write_text('\n'.join(svg)+'\n')
    return metrics


if __name__ == '__main__':
    for label,a,b in render():print(f'{label}: 2.2.0={a:.1f}, 3.0 rc.2={b:.1f} characters')
