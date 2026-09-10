# -*- coding: utf-8 -*-
"""Складає план викликів для збірки бази конкретного клієнта.

Вхід — профіль клієнта (див. data/client-profile-example.json) з полем «набір»:
які позиції куплені й на якому рівні. Вихід — упорядкований, пронумерований план:
що викликати, у якій моделі й з якими значеннями. Виконує план Claude через
зовнішнє API; сам скрипт до бази не ходить і нічого в ній не міняє.

Порядок позицій — той самий топологічний, що в docs/setup-runbook.md: позиція
ніколи не стоїть раніше за ту, без якої вона технічно неможлива.

Підстановки: $клієнт.поле замінюється значенням із профілю прямо тут; $ім'я
лишається як є — це посилання на запис, який зʼявиться під час виконання, і
підставити його може тільки виконавець.

Запуск:
    python3 tools/emit_config_calls.py data/client-profile-example.json
    python3 tools/emit_config_calls.py profile.json --json plan.json
"""

import importlib.util
import io
import json
import os
import re
import sys

RECIPES = 'data/recipes.json'
PRICE = 'data/price.json'
CLIENT = re.compile(r'\$клієнт\.([\wа-яіїєґ_]+)', re.I | re.U)
COUNT = re.compile(r'\$скільки\(\$клієнт\.([\wа-яіїєґ_]+)\)', re.I | re.U)
ITEM = re.compile(r'\$елемент(?:\.([\wа-яіїєґ_]+))?$', re.I | re.U)
# $елемент УСЕРЕДИНІ рядка. Довго його не було, і це мовчки ламало розмітку:
# шаблон «робоче_місце» отримує поля списку рядком
# '<list string="$елемент.назва">…', і без цієї заміни в базу йшло подання
# з буквальним «$елемент.назва» в заголовку. Помилки при цьому НЕМАЄ —
# arch валідний, подання створюється, і видно тільки очима на екрані.
# Знайдено прогоном плану «Дашбордів» по базі 10.09.2026.
ITEM_IN = re.compile(r'\$елемент(?:\.([\wа-яіїєґ_]+))?', re.I | re.U)
ARG = re.compile(r'\$арг\.([\wа-яіїєґ_]+)', re.I | re.U)


def load_topo():
    spec = importlib.util.spec_from_file_location('rb', 'tools/build_runbook.py')
    rb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rb)
    return rb.topo


def subst(v, prof, missing, elem=None, idx=None, args=None):
    """Підставляє $клієнт.поле, $скільки(...), $елемент і $індекс.

    $ім'я (посилання на створений запис) лишає виконавцеві — підставити його
    можна тільки під час виконання.
    """
    if isinstance(v, str):
        t = v.strip()
        if args is not None:
            ma = ARG.fullmatch(t)
            if ma:
                if ma.group(1) not in args:
                    missing.append('арг.' + ma.group(1))
                    return v
                return args[ma.group(1)]

            def repa(mm):
                if mm.group(1) not in args:
                    missing.append('арг.' + mm.group(1))
                    return mm.group(0)
                return str(args[mm.group(1)])
            t2 = ARG.sub(repa, t)
            if t2 != t:
                return subst(t2, prof, missing, elem, idx, None)
        if elem is not None:
            mi = ITEM.fullmatch(t)
            if mi:
                if mi.group(1):
                    if not isinstance(elem, dict) or mi.group(1) not in elem:
                        missing.append('елемент.' + mi.group(1))
                        return v
                    return elem[mi.group(1)]
                return elem
            if t == '$індекс':
                return idx

            def repi(mm):
                if mm.group(1):
                    з = elem.get(mm.group(1)) if isinstance(elem, dict) else None
                    if з is None:
                        missing.append('елемент.' + mm.group(1))
                        return mm.group(0)
                else:
                    з = elem
                if isinstance(з, (dict, list)):
                    missing.append('елемент%s: складене значення підставляється '
                                   'в середину рядка «%s»'
                                   % ('.' + mm.group(1) if mm.group(1) else '', v[:60]))
                    return mm.group(0)
                return str(з)
            t3 = ITEM_IN.sub(repi, t)
            if t3 != t:
                return t3
            if '$індекс' in t:
                return t.replace('$індекс', str(idx))
        mc = COUNT.fullmatch(t)
        if mc:
            if mc.group(1) not in prof:
                missing.append(mc.group(1))
                return v
            return len(prof[mc.group(1)])
        m = CLIENT.fullmatch(t)
        if m:
            if m.group(1) not in prof:
                missing.append(m.group(1))
                return v
            return prof[m.group(1)]

        def rep(mm):
            if mm.group(1) not in prof:
                missing.append(mm.group(1))
                return mm.group(0)
            знач = prof[mm.group(1)]
            # Підстановка складеного значення В СЕРЕДИНУ рядка — завжди помилка.
            # Спіймано дорого: рецепт написали як «$клієнт.контроль_міграції.назва»,
            # підстановка розпізнала лише перший сегмент, віддала весь словник, і
            # str() від нього поїхав у arch подання разом із фігурними дужками.
            # Валідатор мовчав — поле «контроль_міграції» у профілі справді є.
            # Вкладених шляхів мова не має: профіль пласкии, як «рм_crm_назва».
            if isinstance(знач, (dict, list)):
                missing.append('%s: складене значення (%s) підставляється в середину '
                               'рядка «%s». Вкладених шляхів $клієнт.поле.підполе мова не '
                               'має — розкласти профіль на пласкі поля'
                               % (mm.group(1), type(знач).__name__, v[:60]))
                return mm.group(0)
            return str(знач)
        return CLIENT.sub(rep, v)
    if isinstance(v, dict):
        return {k: subst(x, prof, missing, elem, idx, args) for k, x in v.items()}
    if isinstance(v, list):
        return [subst(x, prof, missing, elem, idx, args) for x in v]
    return v


def unroll(st, prof, missing, templates=None):
    """Розгортає «для_кожного» у конкретні кроки: профіль уже відомий, тому цикл
    не потрібен під час виконання — виконавець отримує готовий перелік."""
    if st.get('дія') == 'шаблон':
        tpl = (templates or {}).get(st.get('назва'))
        if not tpl:
            missing.append('шаблон «%s» не описаний' % st.get('назва'))
            return []
        args = st.get('аргументи') or {}
        out = []
        for inner in tpl.get('кроки', []):
            out += unroll({k: subst(v, prof, missing, None, None, args)
                           for k, v in inner.items()}, prof, missing, templates)
        return out
    if st.get('дія') != 'для_кожного':
        return [{k: subst(v, prof, missing) for k, v in st.items()}]
    src = st.get('перелік', '')
    # «перелік» буває двох видів:
    #  • $клієнт.поле — звичайний випадок, значення беремо з профілю;
    #  • готовий список — так виходить, коли цикл стоїть УСЕРЕДИНІ шаблону й перелік
    #    прийшов його аргументом: до моменту розгортання аргумент уже підставлено.
    # Другий випадок спершу не приймався, і шаблон «власне_поле» з порожніми «опції»
    # валив емітер. Приймати його правильніше, ніж вимагати, щоб цикл у шаблоні
    # звертався до профілю навпростець: тоді шаблон перестав би бути шаблоном.
    if isinstance(src, list):
        items_src = src
    else:
        m = CLIENT.fullmatch(src.strip()) if isinstance(src, str) else None
        if not m:
            missing.append('для_кожного: «перелік» має бути $клієнт.поле або список, '
                           'а не «%s»' % src)
            return []
        if m.group(1) not in prof:
            missing.append(m.group(1))
            return []
        items_src = prof[m.group(1)]
    out = []
    for i, elem in enumerate(items_src, 1):
        inner = st.get('крок') or {}
        filled = {k: subst(v, prof, missing, elem, i) for k, v in inner.items()}
        # Шаблон усередині циклу треба розгорнути, а не віддати виконавцеві сирим
        # кроком «шаблон». Саме ця пара потрібна позиціям, де артефакт повторюється
        # під кожну роль: «окремі робочі місця під ролі» — це той самий шаблон
        # стільки разів, скільки ролей у профілі.
        #
        # Рекурсія лише для шаблонів: звичайний крок уже підставлений, і другий
        # прохід підстановки був би зайвим (а на значенні зі знаком $ ще й шкідливим).
        if filled.get('дія') == 'шаблон':
            out += unroll(filled, prof, missing, templates)
        else:
            out.append(filled)
    return out


CALLS_ВЛАСТИВІСТЬ = 3


def main(argv):
    if len(argv) < 2:
        print('вжиток: python3 tools/emit_config_calls.py <профіль.json> [--json план.json] [--всі]')
        print('  --всі: план на ВСІ позиції рівня 3 — перевірка покриття, а не план клієнта')
        return 2
    prof_path = argv[1]
    out_json = None
    if '--json' in argv:
        i = argv.index('--json') + 1
        if i >= len(argv):
            # без цього виходив IndexError із трасуванням — «--json» без шляху
            # виглядає як помилка інструмента, а це просто забутий аргумент
            print('після «--json» треба вказати файл, куди писати план')
            return 2
        out_json = argv[i]

    prof = json.load(io.open(prof_path, encoding='utf-8'))
    rec = json.load(io.open(RECIPES, encoding='utf-8'))
    price = json.load(io.open(PRICE, encoding='utf-8'))

    names, hard, items = {}, {}, []
    for g in price['групи']:
        for it in g['items']:
            items.append(it['id'])
            names[it['id']] = it['n']
            hard[it['id']] = [d['on'] if isinstance(d['on'], list) else [d['on']]
                              for d in it.get('dep', []) if d.get('type') == 'hard']

    topo = load_topo()
    order = [p for p in topo(items, hard) if not isinstance(p, tuple)]

    bought = prof.get('набір') or {}
    if '--всі' in argv:
        # Режим покриття, а не плану для клієнта. Потрібен тому, що профіль-приклад
        # описує РЕАЛЬНИЙ набір, і позиції поза ним емітер ніколи не бачить: рецепти
        # «Друкованих форм» і «Управлінського обліку» пролежали б неперевіреними, хоча
        # саме емітер ловить помилки підстановки — валідатор їх не бачить, бо поле
        # профілю формально є. Тому збірка окремо просить план на ВСІ позиції р.3.
        bought = {pid: 3 for pid in items}
    if not bought:
        print('У профілі немає поля «набір» — нічого збирати.')
        return 2

    plan, missing, no_recipe, services = [], [], [], []
    for pid in order:
        if pid not in bought:
            continue
        lvl = int(bought[pid])
        for lk in [str(x) for x in range(1, lvl + 1)]:
            body = rec['позиції'].get(pid, {}).get(lk)
            if not body:
                no_recipe.append('%s р.%s' % (names[pid], lk))
                continue
            for txt, item in body.items():
                for st in item.get('кроки', []):
                    for step in unroll(st, prof, missing,
                                       rec.get('шаблони')):
                        step['_позиція'] = names[pid]
                        step['_рівень'] = lk
                        step['_пункт'] = txt
                        if step.get('дія') == 'послуга':
                            services.append('%s р.%s · %s' % (names[pid], lk, txt))
                            continue
                        plan.append(step)

    # ОСТАННІЙ ЗАСІБ: жодної незамінемої підстановки в готовому плані.
    #
    # Обидві дірки в підстановці, що знайшлися 10.09.2026, давали ВАЛІДНИЙ план
    # із буквальним «$клієнт.поле.підполе» чи «$елемент.назва» всередині значення.
    # Емітер не падав, конектор не сварився, у базу йшов запис із текстом
    # підстановки в полі — і видно це було тільки очима на екрані.
    #
    # Тому план перечитується перед друком. Легальним лишається тільки «$імʼя» —
    # посилання на створений запис, яке розвʼязує ВИКОНАВЕЦЬ.
    ПЛЕЙС = re.compile(r'\$(клієнт|елемент|арг|індекс|скільки)\b', re.I | re.U)

    def лишки(v, шлях, крок):
        if isinstance(v, str):
            m = ПЛЕЙС.search(v)
            if m:
                missing.append('НЕЗАМІНЕНА ПІДСТАВКА $%s у «%s · %s», поле %s: «%s». '
                               'План виглядав би валідним, а в базу пішов би текст '
                               'підстановки'
                               % (m.group(1), крок.get('_позиція'),
                                  (крок.get('_пункт') or '')[:34], шлях, v[:70]))
        elif isinstance(v, dict):
            for k, x in v.items():
                лишки(x, '%s.%s' % (шлях, k), крок)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                лишки(x, '%s[%d]' % (шлях, i), крок)

    for крок in plan:
        for k, v in крок.items():
            if not k.startswith('_'):
                лишки(v, k, крок)

    if missing:
        print('ПОМИЛКА: у профілі бракує полів: %s' % ', '.join(sorted(set(missing))))
        return 1

    # читаний план
    print('# План збірки — %s' % prof.get('назва', '(без назви)'))
    print()
    print('Куплено: %s' % ', '.join('%s р.%s' % (names[p], bought[p])
                                    for p in order if p in bought))
    # Викликів конектора більше, ніж кроків: «створити» — це запис плюс обовʼязкове
    # перечитування, «послуга» не коштує жодного. Це число потрібне для заміру фази 0
    # (docs/процедура-заміру-фази-0.md): кроки — одиниця плану, виклики — одиниця часу.
    # «властивість» коштує ТРЬОХ викликів, а не одного: контракт дії —
    # прочитати перелік визначень у батька, дописати рядок, прочитати назад.
    # За замовчуванням тут стояла одиниця, і замір фази 0 занижував би вартість
    # кожного такого пункту втричі.
    CALLS = {'знайти': 1, 'знайти_xmlid': 1, 'створити': 2, 'записати': 1,
             'параметр': 1, 'перевірити': 1, 'послуга': 0,
             'властивість': CALLS_ВЛАСТИВІСТЬ}
    calls = sum(CALLS.get(st['дія'], 1) for st in plan)
    print('Кроків до виконання: %d · викликів конектора: %d' % (len(plan), calls))
    print()
    print('Виконує Claude через зовнішнє API. Після КОЖНОГО кроку, що змінює базу,')
    print('перечитати запис: конектор повідомляє помилку й тоді, коли дія відбулася.')
    print()
    cur = None
    for i, st in enumerate(plan, 1):
        head = '%s р.%s · %s' % (st['_позиція'], st['_рівень'], st['_пункт'])
        if head != cur:
            cur = head
            if i > 1:
                print()
            print('## %s' % head)
            print()
        act = st['дія']
        line = '%d. **%s**' % (i, act)
        if st.get('модель'):
            line += ' `%s`' % st['модель']
        if st.get('домен') is not None and act in ('знайти', 'перевірити'):
            line += ' домен `%s`' % json.dumps(st['домен'], ensure_ascii=False)
        if st.get('якщо_немає'):
            line += ' (тільки якщо немає `%s`)' % json.dumps(st['якщо_немає'], ensure_ascii=False)
        if st.get('ціль'):
            line += ' → ціль `%s`' % st['ціль']
        if st.get('назвати'):
            line += ' → назвати `$%s`' % st['назвати']
        print(line)
        for key in ('значення', 'очікувати', 'очікувати_містить'):
            if st.get(key):
                print('   - %s: `%s`' % (key, json.dumps(st[key], ensure_ascii=False)))
        if st.get('ключ'):
            print('   - параметр `%s` = `%s`' % (st['ключ'], st.get('значення_параметра')))
        # «Властивість» друкувалася ОДНІЄЮ МОДЕЛЛЮ — «властивість project.task» і
        # більше нічого. Дію додали пізніше за рендер, і він її не навчився: ні
        # назви поля, ні типу, ні батьківського запису, у якому лежить визначення.
        # Виконати такий крок неможливо, а виглядає він у плані як рядок серед інших.
        if st['дія'] == 'властивість':
            print('   - поле `%s` («%s»), тип `%s`%s'
                  % (st.get('назва'), st.get('підпис'), st.get('тип'),
                     (', опції: `%s`' % json.dumps(st['опції'], ensure_ascii=False))
                     if st.get('опції') else ''))
            print('   - визначення лежить у `%s.%s`, запис за доменом `%s`'
                  % (st.get('батько_модель'), st.get('батько_поле'),
                     json.dumps(st.get('батько_домен'), ensure_ascii=False)))
            print('   - контракт: прочитати перелік визначень, ДОПИСАТИ рядок '
                  '(запис замінює весь перелік), прочитати назад')
        if st.get('очікувати_кількість') is not None:
            print('   - очікувати кількість: %s' % st['очікувати_кількість'])
        if st.get('очікувати_щонайменше') is not None:
            print('   - очікувати щонайменше: %s' % st['очікувати_щонайменше'])
        # «Перевірити» без жодного очікування — це «запис існує», і так його й
        # виконують. Але НЕВИСЛОВЛЕНЕ очікування в перевірці — та сама дірка, що
        # перевірка, яка нічого не перевіряє: виконавець мусить здогадатися, що
        # порожня відповідь — це провал. Тому умова друкується явно.
        #
        # ЗАРАЗ ЦЯ ГІЛКА НЕ СПРАЦЬОВУЄ ЖОДНОГО РАЗУ, і це чесно сказано тут, щоб
        # її не сприйняли за опис наявного стану: у плані на весь прайс усі
        # перевірки мають явне очікування. Вона стоїть як запобіжник на майбутній
        # рецепт і закрита тестом — інакше невживана гілка тихо згниє.
        elif (st.get('дія') == 'перевірити'
              and not any(k in st for k in ('очікувати', 'очікувати_містить',
                                            'очікувати_кількість', 'щонайменше',
                                            'поля'))):
            print('   - очікувати щонайменше: 1 (за замовчуванням: запис мусить '
                  'існувати, порожня відповідь — провал кроку)')
        if st.get("модуль"):
            print('   - зовнішній id: `%s.%s`' % (st['модуль'], st["ім'я"]))
    print()
    if services:
        print('## Поза базою — робить людина')
        print()
        for s in services:
            print('- %s' % s)
        print()
    if no_recipe:
        print('## Рецепта ще немає — збирати руками за журналом')
        print()
        for s in no_recipe:
            print('- %s' % s)
        print()

    if out_json:
        io.open(out_json, 'w', encoding='utf-8').write(
            json.dumps({'клієнт': prof.get('назва'), 'кроки': plan,
                        'послуги': services, 'без рецепта': no_recipe},
                       ensure_ascii=False, indent=1) + '\n')
        print('(план у машинному вигляді: %s)' % out_json)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
