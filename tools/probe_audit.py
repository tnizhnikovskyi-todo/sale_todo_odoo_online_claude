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
CMAP = 'data/config-map.json'

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


# ── Проба за назвою ───────────────────────────────────────────────────────────
# Адресних записів лише 9 %. Решта описує знахідку назвою: «папка «Договори з
# клієнтами»», «роль «Аналітик»», «шаблон «Договір постачання»». Такі теж можна
# перевірити читанням — але модель тут НЕ витягується з тексту.
#
# Причина в тій самій пастці, на якій проба вже двічі збрехала: слово в тексті
# збігається з назвою моделі рідко й ненадійно. Тому модель береться з **карти
# налаштування** (`config-map.json`), тобто з поля «де», яке писала людина, а назва —
# з лапок у тексті звірки. Пара «модель із карти + назва з тексту» не вгадується.
#
# Що це не робить: не гарантує, що знайдений запис і є той, про який мова. Запис із
# такою назвою може існувати з іншої причини, тому проба друкує фразу-джерело, а
# звіряти треба відповідність, не існування.

QUOTED = re.compile(r'«([^»]{3,60})»')
# назви, які не є назвами записів: наші ж терміни й значення полів
NOT_NAMES = {
    'є', 'немає', 'штатно', 'так', 'ні', 'Studio', 'Властивості', 'не входить',
    'Клієнт', 'Постачальник',
}
# у цих моделях шукати за назвою немає сенсу: назви немає або вона службова
NO_NAME_SEARCH = {'ir.model.fields', 'ir.rule', 'ir.config_parameter', 'properties.base.definition',
                  'ir.model.data', 'res.groups.privilege'}


def looks_like_name(t):
    """Чи схоже це на назву запису, а не на фразу зі звірки.

    Перший прогін показав шум: у лапках стоять і назви записів («Воронка керівника»),
    і значення полів («DAP Київ, склад покупця»), і мої ж фрази («рядки переміщення
    конектор не пише»). Проба, яка це змішує, дає купу «не знайдено» там, де запис
    правильний, — і тоді її перестають читати.

    Фільтр грубий і навмисно такий: назви записів у нас короткі. Довга фраза або
    щось із дієсловом — це опис, а не назва.
    """
    w = t.split()
    if len(w) > 5:
        return False
    if re.search(r'\b(не|конектор|пише|немає|через|лишається)\b', t, re.I | re.U):
        return False
    return True


def by_name(found, models):
    """Пари (модель, назва) — КАНДИДАТИ на читання за назвою.

    Це кандидати, а не адреси: модель узята з карти (поле «де», яке писала людина),
    назва — з лапок. Пара не вгадана, але й не доведена: запис із такою назвою може
    існувати з іншої причини, а може лежати в сусідній моделі. Тому «не знайдено» тут
    означає «подивитися», а не «поломка».
    """
    names = [n for n in QUOTED.findall(found)
             if n not in NOT_NAMES and looks_like_name(n)]
    ms = [m for m in models if m not in NO_NAME_SEARCH]
    if not names or not ms:
        return []
    # модель беремо першу з карти: вона й є головною адресою пункту
    return [(ms[0], n) for n in names[:3]]

def main(argv):
    V = json.load(io.open(VERIFY, encoding='utf-8'))
    C = json.load(io.open(CMAP, encoding='utf-8'))
    addr_of = {}
    for pid, b in C['позиції'].items():
        for lk, rws in b.get('рівні', {}).items():
            for r in rws:
                addr_of[(pid, lk, r['пункт'])] = r['моделі']
    by_model = collections.defaultdict(set)
    names_by_model = collections.defaultdict(set)
    named = 0
    amb = collections.Counter()
    rows, named_rows, total, addressed = [], [], 0, 0
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
                else:
                    nm = by_name(found, addr_of.get((pid, lk, txt)) or [])
                    if nm:
                        named += 1
                        for m, n in nm:
                            names_by_model[m].add(n)
                        named_rows.append((pid, lk, txt, nm))
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
        print()
        print('# Проба за назвою: модель із карти налаштування, назва з тексту')
        print()
        nplan = collections.defaultdict(set)
        for pid, lk, txt, nm in named_rows:
            for m, n in nm:
                nplan[m].add(n)
        for m in sorted(nplan, key=lambda x: -len(nplan[x])):
            print('%s' % m)
            for n in sorted(nplan[m]):
                print('    «%s»' % n)
        return 0

    print('записів «є в базі»            %d' % total)
    print('з них адресних (модель + id)  %d  (%d %%)' % (addressed, round(100.0 * addressed / total)))
    print('кандидатів за назвою          %d  (%d %%)' % (named, round(100.0 * named / total)))
    print('лишається на очі              %d  (%d %%)'
          % (total - addressed - named, round(100.0 * (total - addressed - named) / total)))
    print()
    print('«Адресні» — модель і номер запису: тут «не знайдено» означає поломку.')
    print('«Кандидати за назвою» — модель із карти, назва з лапок: пара не доведена,')
    print('тому «не знайдено» означає «подивитися», а не «зламано».')
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
