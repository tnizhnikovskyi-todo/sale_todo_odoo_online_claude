# -*- coding: utf-8 -*-
"""Збирає docs/setup-runbook.md — процедуру збірки бази клієнта.

Це не переказ прайсу. Прайс каже, ЩО куплено; runbook каже, В ЯКОМУ ПОРЯДКУ це
робиться в базі й ЗА ЯКОЮ АДРЕСОЮ кожен пункт лежить. Порядок рахується з жорстких
залежностей прайсу (поле dep, type=hard) топологічним сортуванням: позиція не може
йти раніше за ту, без якої вона технічно неможлива.

Джерела: data/price.json (позиції, рівні, залежності, застосунки) і
data/config-map.json (моделі, поля, шлях у меню — генерується build_config_map.py).

Запуск: python3 tools/build_config_map.py && python3 tools/build_runbook.py
"""

import collections
import io
import json
import sys

PRICE = 'data/price.json'
CMAP = 'data/config-map.json'
OUT = 'docs/setup-runbook.md'


def fmt_dep(grp, names):
    """Один запис залежності: одна позиція або «одна з» кількох."""
    got = [names.get(x, x) for x in grp]
    if len(got) == 1:
        return got[0]
    return 'одна з: ' + ', '.join(got)


def topo(items, deps):
    """Топологічний порядок за жорсткими залежностями, стабільний до порядку прайсу."""
    order, seen, stack = [], set(), set()

    def visit(pid, chain):
        if pid in seen:
            return
        if pid in stack:
            order.append(('ЦИКЛ', ' → '.join(chain + [pid])))
            return
        stack.add(pid)
        for grp in deps.get(pid, []):
            for on in grp:
                if on in items:
                    visit(on, chain + [pid])
        stack.discard(pid)
        seen.add(pid)
        order.append(pid)

    for pid in items:
        visit(pid, [])
    return order


def main():
    price = json.load(io.open(PRICE, encoding='utf-8'))
    cmap = json.load(io.open(CMAP, encoding='utf-8'))

    items, names, hard, soft, group_of = [], {}, {}, {}, {}
    for g in price['групи']:
        for it in g['items']:
            pid = it['id']
            items.append(pid)
            names[pid] = it['n']
            group_of[pid] = g['g']
            # «on» буває рядком або переліком альтернатив («одна з»)
            seen_h = set()
            hard[pid] = []
            for d in it.get('dep', []):
                if d.get('type') != 'hard':
                    continue
                grp = d['on'] if isinstance(d['on'], list) else [d['on']]
                sig = tuple(grp)
                if sig in seen_h:      # той самий звʼязок з різних рівнів — показати раз
                    continue
                seen_h.add(sig)
                hard[pid].append(grp)
            soft[pid] = [(d['on'] if isinstance(d['on'], list) else [d['on']],
                          d.get('why', ''))
                         for d in it.get('dep', []) if d.get('type') == 'soft']

    order = [p for p in topo(items, hard) if not isinstance(p, tuple)]
    cycles = [p for p in topo(items, hard) if isinstance(p, tuple)]

    L = []
    w = L.append
    w('# Процедура збірки бази клієнта')
    w('')
    w('**Згенеровано** `tools/build_runbook.py` з `data/price.json` і `data/config-map.json`.')
    w('Руками не правити — правити джерела й перезібрати.')
    w('')
    w('Цей документ відповідає на два питання, на які прайс не відповідає: **у якому порядку**')
    w('налаштовувати куплені позиції і **за якою адресою в Odoo** лежить кожен пункт складу')
    w('робіт. Що саме куплено — видно в калькуляторі; персональний чек-лист по пунктах —')
    w('на четвертій сторінці калькулятора.')
    w('')
    w('## Перед початком')
    w('')
    w('1. **План підписки — Custom.** Не тому, що ми користуємось Studio (не користуємось), а')
    w('   тому, що налаштування виконується через зовнішнє API, а воно є **тільки на Custom**.')
    w('   Мультикомпанійність — теж лише там. Підписку оформлює клієнт сам.')
    w('2. **Ключ API** просимо зі строком дії на час робіт. У репозиторії ключ не зберігається.')
    w('3. **Українська локалізація стане сама** разом із застосунком рахунків: план `ua_psbo`,')
    w('   близько 700 рахунків і ставки ПДВ. Ми їх **не налаштовуємо й не супроводжуємо** —')
    w('   сказати клієнтові вголос до того, як він це побачить.')
    w('4. **Обліку, податків і зарплати в базі не робимо.** Це межа контуру, не обмеження Odoo.')
    w('')
    w('## Порядок позицій')
    w('')
    w('Порядок порахований із жорстких залежностей прайсу: позиція не може йти раніше за ту,')
    w('без якої вона технічно неможлива. Позиції, яких клієнт не купив, просто пропускаються —')
    w('порядок решти від цього не змінюється.')
    w('')
    if cycles:
        w('> **УВАГА: у залежностях знайдено цикл** — %s. Це помилка в `data/price.json`.'
          % '; '.join(c[1] for c in cycles))
        w('')
    w('| № | Позиція | Група | Іде після |')
    w('|---:|---|---|---|')
    for i, pid in enumerate(order, 1):
        after = '; '.join(fmt_dep(grp, names) for grp in hard.get(pid, [])) or '—'
        w('| %d | **%s** | %s | %s |' % (i, names[pid], group_of[pid], after))
    w('')

    w('## Що робити в кожній позиції')
    w('')
    for pid in order:
        blk = cmap['позиції'].get(pid, {})
        w('### %s' % names[pid])
        w('')
        apps = blk.get('застосунки') or {}
        allapps = []
        for lv in ('1', '2', '3'):
            for a in apps.get(lv, []):
                if a not in allapps:
                    allapps.append(a)
        if allapps:
            w('**Застосунки (усі рівні):** %s' % ', '.join('`%s`' % a for a in allapps))
        if hard.get(pid):
            w('**Спершу має бути:** %s'
              % '; '.join(fmt_dep(grp, names) for grp in hard[pid]))
        for grp, why in soft.get(pid, []):
            w('**Попередити:** без «%s» — %s' % (fmt_dep(grp, names), why))
        w('')
        for lk in ('1', '2', '3'):
            rows = blk.get('рівні', {}).get(lk, [])
            if not rows:
                continue
            w('#### Рівень %s' % lk)
            w('')
            lv_apps = apps.get(lk, [])
            if lv_apps:
                w('Доставити застосунки: %s' % ', '.join('`%s`' % a for a in lv_apps))
                w('')
            w('| Пункт | Де в Odoo | Шлях у меню |')
            w('|---|---|---|')
            for r in rows:
                addr = ', '.join('`%s`' % m for m in r['моделі']) or '—'
                if r['поля']:
                    addr += '<br>поля: ' + ', '.join('`%s`' % f for f in r['поля'][:4])
                path = r['шлях'] or ''
                w('| %s | %s | %s |' % (r['пункт'], addr, path))
            w('')

    no_addr = cmap.get('без машинної адреси', [])
    w('## Пункти без машинної адреси — %d' % len(no_addr))
    w('')
    w('Тут карта нічим не допоможе: це або послуга (сесія, виїзд, показ), або дія в')
    w('інтерфейсі, яка не лишає окремого запису. Робота по них береться з журналу')
    w('`docs/журнал-налаштування-edu-online-todo.md`.')
    w('')
    for row in no_addr:
        w('- %s' % row)
    w('')

    s = cmap['зведення']
    w('## Чого бракує для `apply-config`')
    w('')
    w('Карта дає **адресу** пункту (%d із %d пунктів мають модель), але не дає **рецепта**:'
      % (s['з моделями'], s['пунктів']))
    w('яких значень набути полям і в якому порядку викликати створення всередині пункту.')
    w('Поки рецепта немає, автоматична збірка неможлива, і це чесна межа інструмента.')
    w('')
    w('Щоб рецепт зʼявився, у `data/verify.json` кожному пункту потрібне окреме поле')
    w('`рецепт` — перелік кроків виду:')
    w('')
    w('```json')
    w('"рецепт": [')
    w(' {"дія": "create", "модель": "ir.filters",')
    w('  "значення": {"name": "…", "model_id": "sale.order", "domain": "…", "sort": "[]"},')
    w('  "назвати": "фільтр_сегмента"},')
    w(' {"дія": "create", "модель": "ir.ui.menu",')
    w('  "значення": {"name": "…", "parent_id": 336, "action": "act_window,$дія_сегмента"}}')
    w(']')
    w('```')
    w('')
    w('Три речі, які рецепт мусить уміти, інакше він не працюватиме на живій базі:')
    w('')
    w('1. **Посилання на щойно створений запис** (`$назва`) — інакше подання, дію й меню')
    w('   не звʼязати.')
    w('2. **Пошук замість жорсткого id** — `parent_id` кореневого меню або id ролі на кожній')
    w('   базі свій, тому в рецепті має стояти пошук за ознакою, а не число.')
    w('3. **Перевірку після кроку** — конектор повідомляє помилку й тоді, коли дія відбулася')
    w('   (перевірено дорого, див. базу знань), тому кожен крок закінчується перечитуванням.')
    w('')
    w('Оцінка обсягу: рецепти потрібні для %d пунктів із моделями. Писати їх варто не всі '
      'відразу, а по позиціях — починаючи з «Бази» і «Проєктів», бо саме на них міряється '
      'окупність інструментарію у фазі 0.' % s['з моделями'])
    w('')

    # самоперевірка: жодна позиція не стоїть раніше за свою жорстку залежність
    pos = {pid: i for i, pid in enumerate(order)}
    broken = []
    for pid in order:
        for grp in hard.get(pid, []):
            known = [x for x in grp if x in pos]
            if known and min(pos[x] for x in known) > pos[pid]:
                broken.append('%s раніше за %s' % (names[pid], fmt_dep(grp, names)))
    if broken:
        print('ПОМИЛКА порядку: ' + '; '.join(broken))
        return 1
    if len(order) != len(items):
        print('ПОМИЛКА: у порядку %d позицій, у прайсі %d' % (len(order), len(items)))
        return 1

    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('OK: %s — %d позицій у порядку залежностей, %d пунктів, %d без адреси'
          % (OUT, len(order), s['пунктів'], len(no_addr)))
    if cycles:
        print('    УВАГА: цикл у залежностях — %s' % '; '.join(c[1] for c in cycles))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
