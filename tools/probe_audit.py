# -*- coding: utf-8 -*-
"""Готує пробу для переперевірки звірки: з тексту «знайшли» витягує адреси записів.

Навіщо. Звірка каже «343 із 360 знайдено в базі», і кожен запис описує знахідку
словами: «подання 4889», «меню 804 з роллю 99», «фільтр 32», «контрагент 13».
Переперевіряти це вибірками по двадцять — надовго: 343 записи.

Але більшість таких тверджень **адресні**: у них є модель і номер запису. Цей скрипт
витягує пари «модель → id» з тексту й групує їх, щоб переперевірка стала пачкою
читань, а не читанням журналу очима.

Чого скрипт НЕ робить: не звертається до Odoo. Ключ API в репозиторії не зберігається,
та й доступ до бази є лише в конектора. Скрипт готує пробу — читання виконує той, у кого
є конектор, і результат порівнює з тим, що тут написано.

Запуск:
    python3 tools/probe_audit.py            # зведення: що можна перевірити адресно
    python3 tools/probe_audit.py --plan     # проба: модель і перелік id для читання
    python3 tools/probe_audit.py --json f   # те саме машинно

Слова, за якими впізнаються моделі, узяті з наших же формулювань — вони стабільні,
бо журнал писався одним стилем. Якщо формулювання зміниться, скрипт це покаже
падінням покриття, а не тихою помилкою.
"""

import collections
import io
import json
import re
import sys

VERIFY = 'data/verify.json'

# «слово в журналі» → модель Odoo. Порядок важливий: довші назви перші, інакше
# «меню сайту» впізнається як «меню».
WORDS = [
    ('меню сайту', 'website.menu'),
    ('сторінка сайту', 'website.page'),
    ('подання', 'ir.ui.view'),
    ('меню', 'ir.ui.menu'),
    ('фільтр', 'ir.filters'),
    ('дія сервера', 'ir.actions.server'),
    ('дія', 'ir.actions.act_window'),
    ('звіт', 'ir.actions.report'),
    ('шаблон', 'ir.ui.view'),
    ('контрагент', 'res.partner'),
    ('компанія', 'res.company'),
    ('дашборд', 'spreadsheet.dashboard'),
    ('таблиця', 'documents.document'),
    ('журнал', 'account.journal'),
    ('правило', 'ir.rule'),
    ('категорія погоджень', 'approval.category'),
    ('роль', 'res.groups'),
    ('група', 'res.groups'),
]
# Неоднозначні слова у пробу не йдуть. Дві причини, і друга небезпечніша:
#
# 1. Слово означає різні моделі: «шаблон» — це і QWeb-бланк, і шаблон листа, і шаблон
#    Sign; «дія» — і вікно, і дія сервера; «роль»/«група» — і група доступу, і роль
#    планування.
# 2. Слово означає **значення поля, а не запис**. На цьому проба тихо збрехала:
#    «у сьогоднішніх нарядів послідовність 1 і 2» — це поле `sequence` зі значеннями
#    1 і 2, а не записи `ir.sequence` з такими id. А `ir.sequence` 1 у базі є («Lead
#    Mining Request», штатний Odoo), тому проба прочитала б його, знайшла б — і
#    підтвердила твердження про порядок нарядів, якого не перевіряла.
#
# Тому «послідовність» прибрано з розбору повністю: у наших текстах воно частіше
# значення поля, ніж модель.
AMBIGUOUS = {'шаблон', 'звіт', 'дія', 'роль', 'група'}


def pairs(text):
    """Пари (слово, id) з тексту: «подання 4889», «меню 804», «фільтр 32».

    ПАСТКА, на якій перша версія тихо збрехала. Запис про структуру сайту каже
    «меню 12 лежить під меню 7», і це **меню сайту** (`website.menu`). Наївний розбір
    відносив їх до `ir.ui.menu` — а записи з такими id там теж є («General Settings» і
    «Automation»). Проба відзвітувала б «знайдено» й **підтвердила твердження, якого
    не перевіряла**. Хибне підтвердження гірше за відсутність перевірки: воно закриває
    питання.

    Тому контекст самого запису має право перевизначити модель: якщо в тексті згадано
    «меню сайту», то й голі «меню N» у ньому — це меню сайту.
    """
    out = []
    site = bool(re.search(r'меню\s+сайту', text, re.I | re.U))
    for word, model in WORDS:
        if word == 'меню' and site:
            model = 'website.menu'
        for m in re.finditer(word + r'[а-яіїєґ]*\s+(\d{1,6})\b', text, re.I | re.U):
            out.append((word, model, int(m.group(1))))
    return out


def main(argv):
    V = json.load(io.open(VERIFY, encoding='utf-8'))
    by_model = collections.defaultdict(set)
    amb = collections.Counter()
    rows, total, addressed = [], 0, 0
    for pid, lvs in V['позиції'].items():
        for lk, rec in lvs.items():
            for txt, st in (rec.get('пункти') or {}).items():
                z = st.get('звірка') or {}
                if z.get('є') is not True:
                    continue
                total += 1
                found = z.get('знайшли') or ''
                got = pairs(found)
                clean = [(w, m, i) for w, m, i in got if w not in AMBIGUOUS]
                if clean:
                    addressed += 1
                    for w, m, i in clean:
                        by_model[m].add(i)
                    rows.append((pid, lk, txt, clean))
                for w, m, i in got:
                    if w in AMBIGUOUS:
                        amb[w] += 1

    if '--plan' in argv or '--json' in argv:
        plan = collections.OrderedDict(
            (m, sorted(ids)) for m, ids in sorted(by_model.items(), key=lambda x: -len(x[1])))
        if '--json' in argv:
            i = argv.index('--json') + 1
            if i >= len(argv):
                print('після «--json» треба вказати файл')
                return 2
            io.open(argv[i], 'w', encoding='utf-8').write(
                json.dumps({'проба': plan, 'записи': [
                    {'позиція': p, 'рівень': l, 'пункт': t,
                     'адреси': [{'модель': m, 'id': i2} for _, m, i2 in c]}
                    for p, l, t, c in rows]}, ensure_ascii=False, indent=1) + '\n')
            print('проба записана: %s' % argv[i])
            return 0
        print('# Проба переперевірки: що читати')
        print()
        for m, ids in plan.items():
            print('%-28s %s' % (m, ', '.join(str(i) for i in ids)))
        print()
        print('# Звідки взялася кожна адреса')
        print()
        print('Проба друкує джерело навмисно: id без фрази, з якої він узятий, перевірити')
        print('неможливо — саме на цьому вона двічі помилялася («меню 12» виявилося меню')
        print('сайту, «послідовність 1» — значенням поля, а не записом). Читаючи пробу,')
        print('звіряйте не існування запису, а те, що запис відповідає фразі.')
        print()
        for pid, lk, txt, clean in rows:
            addrs = ', '.join('%s %d' % (m, i) for _, m, i in clean)
            print('- **%s р.%s** %s' % (pid, lk, txt[:60]))
            print('  %s' % addrs)
        return 0

    print('записів «є в базі»            %d' % total)
    print('з них адресних (модель + id)  %d  (%d %%)' % (addressed, round(100.0 * addressed / total)))
    print('різних моделей у пробі        %d' % len(by_model))
    print('записів до перечитування      %d' % sum(len(v) for v in by_model.values()))
    print()
    print('найбільші групи:')
    for m, ids in sorted(by_model.items(), key=lambda x: -len(x[1]))[:8]:
        print('  %-28s %d' % (m, len(ids)))
    if amb:
        print()
        print('неоднозначні слова (у пробу не йдуть, бо означають різні моделі):')
        for w, n in amb.most_common():
            print('  «%s» — %d згадок' % (w, n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
