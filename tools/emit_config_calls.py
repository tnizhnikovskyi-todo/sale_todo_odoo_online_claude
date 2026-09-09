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


def load_topo():
    spec = importlib.util.spec_from_file_location('rb', 'tools/build_runbook.py')
    rb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rb)
    return rb.topo


def subst(v, prof, missing, elem=None, idx=None):
    """Підставляє $клієнт.поле, $скільки(...), $елемент і $індекс.

    $ім'я (посилання на створений запис) лишає виконавцеві — підставити його
    можна тільки під час виконання.
    """
    if isinstance(v, str):
        t = v.strip()
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
            return str(prof[mm.group(1)])
        return CLIENT.sub(rep, v)
    if isinstance(v, dict):
        return {k: subst(x, prof, missing, elem, idx) for k, x in v.items()}
    if isinstance(v, list):
        return [subst(x, prof, missing, elem, idx) for x in v]
    return v


def unroll(st, prof, missing):
    """Розгортає «для_кожного» у конкретні кроки: профіль уже відомий, тому цикл
    не потрібен під час виконання — виконавець отримує готовий перелік."""
    if st.get('дія') != 'для_кожного':
        return [{k: subst(v, prof, missing) for k, v in st.items()}]
    src = st.get('перелік', '')
    m = CLIENT.fullmatch(src.strip()) if isinstance(src, str) else None
    if not m:
        missing.append('для_кожного: «перелік» має бути $клієнт.поле, а не «%s»' % src)
        return []
    if m.group(1) not in prof:
        missing.append(m.group(1))
        return []
    out = []
    for i, elem in enumerate(prof[m.group(1)], 1):
        inner = st.get('крок') or {}
        out.append({k: subst(v, prof, missing, elem, i) for k, v in inner.items()})
    return out


def main(argv):
    if len(argv) < 2:
        print('вжиток: python3 tools/emit_config_calls.py <профіль.json> [--json план.json]')
        return 2
    prof_path = argv[1]
    out_json = None
    if '--json' in argv:
        out_json = argv[argv.index('--json') + 1]

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
                    for step in unroll(st, prof, missing):
                        step['_позиція'] = names[pid]
                        step['_рівень'] = lk
                        step['_пункт'] = txt
                        if step.get('дія') == 'послуга':
                            services.append('%s р.%s · %s' % (names[pid], lk, txt))
                            continue
                        plan.append(step)

    if missing:
        print('ПОМИЛКА: у профілі бракує полів: %s' % ', '.join(sorted(set(missing))))
        return 1

    # читаний план
    print('# План збірки — %s' % prof.get('назва', '(без назви)'))
    print()
    print('Куплено: %s' % ', '.join('%s р.%s' % (names[p], bought[p])
                                    for p in order if p in bought))
    print('Кроків до виконання: %d' % len(plan))
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
        if st.get('очікувати_кількість') is not None:
            print('   - очікувати кількість: %s' % st['очікувати_кількість'])
        if st.get('очікувати_щонайменше') is not None:
            print('   - очікувати щонайменше: %s' % st['очікувати_щонайменше'])
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
