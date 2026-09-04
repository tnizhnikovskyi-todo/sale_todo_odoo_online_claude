#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Правки за аналізом калькулятора 04.09.2026 — пункти 2, 5, 6, 7.

    2 — пояснення багатоцільової залежності друкується в КП клієнта, тому з нього
        йде службова назва модуля (project_forecast)
    5 — кількість користувачів з'являється в ознаках Бази: гейт скринінгу обіцяв
        «понад 20 користувачів — рівень 2–3», а в прайсі цього не було. Години не
        змінюються: вони гіпотеза до замірів фази 0
    6 — need у чек-листі може нести рівень: {on, lv}, а не тільки id позиції
    7 — з ознаки «Управлінського обліку» р.3 йде переоцінка валют: на стенді не
        перевірена, а ознаку сейл читає клієнту

Запуск: python3 docs/аналіз-прайсу/скрипти/apply_fixes_2026-09-04.py
"""
import io, json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PRICE = os.path.join(ROOT, 'data', 'price.json')
QUAL = os.path.join(ROOT, 'data', 'qualification.json')

price = json.loads(io.open(PRICE, encoding='utf-8').read(), object_pairs_hook=collections.OrderedDict)
BY = {it['id']: it for g in price['групи'] for it in g['items']}

# ---- 2: КП клієнта без службових назв ----
pln = BY['pln']
dep = [d for d in pln['dep'] if isinstance(d['on'], list)][0]
old = "«планування за проєктами» — зв'язок зміни з проєктом (project_forecast); потрібні Проєкти або Виїзні роботи"
assert dep['why'] == old, dep['why']
dep['why'] = ('щоб планувати зміни під конкретні роботи, зміна має посилатися на проєкт або наряд: '
              'потрібна одна з двох позицій')

# ---- 5: користувачі в ознаках Бази ----
base = BY['base']
assert base['lv'][0][3] == 'усі бачать усе; ролі — штатні групи; одна юрособа'
base['lv'][0][3] = 'до 10 людей, усі бачать усе; ролі — штатні групи; одна юрособа'
assert base['lv'][1][3] == 'до 5 ролей з різним доступом до застосунків'
base['lv'][1][3] = '10–20 людей або до 5 ролей з різним доступом до застосунків'
assert base['lv'][2][3] == ('хтось має бачити лише свої записи або записи свого підрозділу; '
                            'різним ролям — різні форми')
base['lv'][2][3] = ('понад 20 людей, або хтось має бачити лише свої записи чи записи свого підрозділу; '
                    'різним ролям — різні форми')
assert base['q'] == 'Чи є люди, яким не можна бачити частину записів або застосунків?'
base['q'] = 'Скільком людям потрібен доступ і чи є серед них ті, кому не можна бачити частину записів?'

# ---- 7: переоцінка валют геть з ознаки ----
acc = BY['acc']
assert acc['lv'][2][3] == 'план-факт і бюджети, переоцінка валют або 2+ розрізи аналітики одночасно'
acc['lv'][2][3] = 'план-факт і бюджети або 2+ розрізи аналітики одночасно'

io.open(PRICE, 'w', encoding='utf-8').write(json.dumps(price, ensure_ascii=False, indent=2) + '\n')
print('price.json: КП без службових назв, користувачі в ознаках Бази, переоцінка валют геть з ознаки')

# ---- 6: need із рівнем ----
qual = json.loads(io.open(QUAL, encoding='utf-8').read(), object_pairs_hook=collections.OrderedDict)
scr = [b for b in qual['блоки'] if b['id'] == 'scr'][0]
byid = {q['id']: q for q in scr['питання']}

mig = byid['migrate']['a'][1]
assert mig.get('need') == ['mig'], mig.get('need')
mig['need'] = [collections.OrderedDict([('on', 'mig'), ('lv', 3)])]

size = byid['size']['a'][1]
assert 'need' not in size
size['need'] = [collections.OrderedDict([('on', 'base'), ('lv', 2)])]
size['note'] = ('Понад 20 користувачів — це вже роздільні права й окрема робота з ролями: '
                'База рівня 2 або 3. Сказати вголос до КП.')

qual['_схема']['відповідь'] = ('{t — формулювання відповіді, r: ok|warn|stop, note — що це означає для нас, '
                               'need — позиції прайсу, які відповідь робить обов\'язковими: id або '
                               '{on, lv} — з рівнем, не нижче якого позицію треба поставити}')
io.open(QUAL, 'w', encoding='utf-8').write(json.dumps(qual, ensure_ascii=False, indent=2) + '\n')
print('qualification.json: need несе рівень (migrate → Міграція р.3, size → База р.2)')
