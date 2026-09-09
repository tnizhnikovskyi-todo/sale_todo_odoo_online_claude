# -*- coding: utf-8 -*-
"""Перевіряє data/recipes.json — щоб зламаний рецепт не доїхав до бази клієнта.

Що перевіряється:

1. Тексти пунктів слово в слово збігаються з прайсом. Перейменування позиції в
   price.json ламає перевірку — так само, як у verify.json.
2. Дія кожного кроку — з дозволеного переліку, і в неї є обов'язкові поля.
3. Модель кожного кроку є в карті налаштування (`data/config-map.json`), тобто
   існує на живій базі. Виняток — моделі з ALLOW_EXTRA нижче: вони не трапляються
   в полі «де», але потрібні рецептам (наприклад res.country для пошуку країни).
4. Кожне посилання $ім'я визначене раніше, ніж використане. Це найчастіша помилка:
   крок посилається на запис, якого ще немає.
5. Кожне $клієнт.поле є в профілі-прикладі. Інакше рецепт мовчки підставить порожнє.
6. Після кожної дії, що змінює базу, є крок «перевірити». Без цього ми віримо
   відмовам конектора, а він повідомляє помилку й тоді, коли дія відбулася.

Запуск: python3 tools/check_recipes.py
"""

import io
import json
import re
import sys

RECIPES = 'data/recipes.json'
PRICE = 'data/price.json'
CMAP = 'data/config-map.json'
PROFILE = 'data/client-profile-example.json'

ACTIONS = {
    'знайти': ['модель', 'домен'],
    'знайти_xmlid': ['модуль', "ім'я", 'назвати'],
    'створити': ['модель', 'значення'],
    'записати': ['модель', 'значення'],
    'параметр': ['ключ', 'значення_параметра'],
    'перевірити': [],
    'послуга': ['опис'],
    'для_кожного': ['перелік', 'крок'],
    'шаблон': ['назва', 'аргументи'],
}
CHANGING = ('створити', 'записати', 'параметр')

# Моделі, потрібні рецептам, але відсутні в полі «де» журналу.
# Усі три звірені з ir.model живої бази 09.09.2026 — просто не трапляються
# в полі «де», бо там про них не писали.
ALLOW_EXTRA = {'res.country', 'res.partner.category', 'ir.model.data', 'res.currency',
               'ir.model'}
# ir.model потрібен для перевірки «застосунок стоїть»: на свіжій базі документів ще
# немає, тому «щонайменше одна угода» падало б законно — перевіряємо не документ,
# а наявність моделі, яку приносить застосунок

REF = re.compile(r'^\$([^.]+)$')
CLIENT = re.compile(r'\$клієнт\.([\wа-яіїєґ_]+)', re.I | re.U)


def walk_values(v):
    """Усі рядки всередині значень кроку, включно з переліками й словниками."""
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            for y in walk_values(x):
                yield y
    elif isinstance(v, (list, tuple)):
        for x in v:
            for y in walk_values(x):
                yield y


def main():
    rec = json.load(io.open(RECIPES, encoding='utf-8'))
    price = json.load(io.open(PRICE, encoding='utf-8'))
    cmap = json.load(io.open(CMAP, encoding='utf-8'))
    prof = json.load(io.open(PROFILE, encoding='utf-8'))
    templates = rec.get('шаблони') or {}
    errs_early = []

    # Апостроф в імені аргумента чи поля профілю ламає підстановку молча:
    # регулярка збирає ім'я з літер і підкреслень і обірветься на апострофі.
    apos = [c for c in ("'", '\u2019')]
    for name in prof:
        if any(a in name for a in apos):
            errs_early.append('поле профілю «%s» містить апостроф — підстановка обірветься'
                              % name)
    for tname, tpl in templates.items():
        if tname.startswith('_') or not isinstance(tpl, dict):
            continue          # службові ключі розділу, як «_нащо»
        for a in (tpl.get('аргументи') or []):
            if any(x in a for x in apos):
                errs_early.append('шаблон «%s»: аргумент «%s» містить апостроф'
                                  % (tname, a))

    known_models = set(ALLOW_EXTRA)
    for blk in cmap['позиції'].values():
        for rows in blk.get('рівні', {}).values():
            for r in rows:
                known_models.update(r['моделі'])

    price_items = {}
    names = {}
    for g in price['групи']:
        for it in g['items']:
            names[it['id']] = it['n']
            # lv = [назва, години, економія, ознака, додані на цьому рівні пункти]
            # рівень 1 = inc + додані на 1-му; рівні 2 і 3 — тільки свої додані,
            # так само як у verify.json
            acc = {'1': set(it['inc']) | set(it['lv'][0][4])}
            acc['2'] = set(it['lv'][1][4])
            acc['3'] = set(it['lv'][2][4])
            price_items[it['id']] = acc

    errs, warns = list(errs_early), []
    n_items = n_steps = 0

    for pid, levels in rec['позиції'].items():
        if pid not in price_items:
            errs.append('позиції «%s» немає в прайсі' % pid)
            continue
        for lk, items in levels.items():
            for txt, body in items.items():
                n_items += 1
                if txt not in price_items[pid].get(lk, set()):
                    errs.append('%s р.%s: пункту немає в прайсі слово в слово — «%s»'
                                % (pid, lk, txt))
                bound = set()
                steps = body.get('кроки', [])
                if not steps:
                    errs.append('%s р.%s «%s»: немає кроків' % (pid, lk, txt))
                for i, st in enumerate(steps, 1):
                    n_steps += 1
                    where = '%s р.%s «%s» крок %d' % (pid, lk, txt[:34], i)
                    act = st.get('дія')
                    if act not in ACTIONS:
                        errs.append('%s: невідома дія «%s»' % (where, act))
                        continue
                    if act == 'шаблон':
                        tname = st.get('назва')
                        tpl = templates.get(tname)
                        if not tpl:
                            errs.append('%s: шаблону «%s» немає в розділі «шаблони»'
                                        % (where, tname))
                        else:
                            need = set(tpl.get('аргументи') or [])
                            got = set((st.get('аргументи') or {}).keys())
                            for miss in sorted(need - got):
                                errs.append('%s: шаблон «%s» вимагає аргумент «%s»'
                                            % (where, tname, miss))
                            for extra in sorted(got - need):
                                errs.append('%s: шаблон «%s» не має аргументу «%s»'
                                            % (where, tname, extra))
                        if st.get('назвати'):
                            bound.add(st['назвати'])
                        continue
                    if act == 'для_кожного':
                        src = st.get('перелік', '')
                        mm = CLIENT.fullmatch(src.strip()) if isinstance(src, str) else None
                        if not mm:
                            errs.append('%s: «перелік» має бути $клієнт.поле' % where)
                        elif mm.group(1) not in prof:
                            errs.append('%s: у профілі немає переліку «%s»'
                                        % (where, mm.group(1)))
                        elif not isinstance(prof[mm.group(1)], list):
                            errs.append('%s: «%s» у профілі не перелік' % (where, mm.group(1)))
                        inner = st.get('крок') or {}
                        if inner.get('дія') not in ACTIONS or inner.get('дія') == 'для_кожного':
                            errs.append('%s: вкладений крок має звичайну дію' % where)
                        imdl = inner.get('модель')
                        if imdl and imdl not in known_models:
                            errs.append('%s: моделі «%s» немає в карті налаштування'
                                        % (where, imdl))
                        if inner.get('назвати'):
                            errs.append('%s: у вкладеному кроці «назвати» не має сенсу — '
                                        'записів буде кілька' % where)
                        if st.get('назвати'):
                            bound.add(st['назвати'])
                        continue
                    for f in ACTIONS[act]:
                        if f not in st:
                            errs.append('%s: у дії «%s» немає поля «%s»' % (where, act, f))
                    mdl = st.get('модель')
                    if mdl and mdl not in known_models:
                        errs.append('%s: моделі «%s» немає в карті налаштування' % (where, mdl))
                    # посилання
                    for s in walk_values({k: v for k, v in st.items() if k != 'назвати'}):
                        m = REF.match(s.strip()) if isinstance(s, str) else None
                        if m and m.group(1) not in bound:
                            errs.append('%s: посилання $%s ще не визначене'
                                        % (where, m.group(1)))
                        for cm in CLIENT.finditer(s if isinstance(s, str) else ''):
                            if cm.group(1) not in prof:
                                errs.append('%s: у профілі немає поля «%s»'
                                            % (where, cm.group(1)))
                    if st.get('назвати'):
                        bound.add(st['назвати'])
                # перевірка після змін
                acts = [s.get('дія') for s in steps]
                for i, a in enumerate(acts):
                    if a in CHANGING:
                        if 'перевірити' not in acts[i + 1:]:
                            warns.append('%s р.%s «%s»: після «%s» немає кроку «перевірити»'
                                         % (pid, lk, txt[:40], a))
                            break

    for w in warns:
        print('  ! %s' % w)
    for e in errs:
        print('  • %s' % e)

    cov = []
    for pid, levels in rec['позиції'].items():
        for lk, items in levels.items():
            total = len(price_items.get(pid, {}).get(lk, set()))
            cov.append('%s р.%s — %d із %d пунктів' % (names.get(pid, pid), lk, len(items), total))

    if errs:
        print('ПОМИЛКА: рецепти не проходять перевірку (%d помилок, %d попереджень)'
              % (len(errs), len(warns)))
        return 1
    print('OK: рецепти — %d пунктів, %d кроків, %d попереджень' % (n_items, n_steps, len(warns)))
    for c in cov:
        print('    покриття: %s' % c)
    return 0


if __name__ == '__main__':
    sys.exit(main())
