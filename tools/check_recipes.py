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
VERIFY = 'data/verify.json'
PROFILE = 'data/client-profile-example.json'

ACTIONS = {
    'знайти': ['модель', 'домен'],
    'знайти_xmlid': ['модуль', "ім'я", 'назвати'],
    'створити': ['модель', 'значення'],
    # «ціль» обовʼязкова, і це не формальність: запис без адреси НІКУДИ не піде,
    # а виглядає крок цілком нормально. Спіймано на собі 10.09.2026 — я написав
    # неіснуюче поле «ціль_домен», валідатор пропустив, емітер надрукував крок
    # без жодної адреси, і виконавець отримав би «записати res.users нікуди».
    'записати': ['модель', 'значення', 'ціль'],
    'параметр': ['ключ', 'значення_параметра'],
    'перевірити': [],
    'послуга': ['опис'],
    'для_кожного': ['перелік', 'крок'],
    'шаблон': ['назва', 'аргументи'],
    'властивість': ['модель', 'батько_модель', 'батько_поле', 'батько_домен',
                    'назва', 'підпис', 'тип'],
}
# Дії, після яких потрібен окремий крок «перевірити»: конектор повідомляє помилку й
# тоді, коли дія відбулася, тому вірити його відмові не можна.
#
# «властивість» тут НАВМИСНО відсутня, і це не послаблення правила. Дія за своїм
# контрактом — читання-зміна-**читання назад**: виконавець перечитує перелік визначень
# і переконується, що рядок у ньому є. Окремий «перевірити» після неї перевіряв би те
# саме вдруге — тобто був би театром, а не перевіркою. Правило лишається там, де воно
# має сенс: після дій, які лише пишуть.
CHANGING = ('створити', 'записати', 'параметр')

# Де лежить ВИЗНАЧЕННЯ властивостей для кожної моделі. Пара не вгадується: у
# контрагента це спільний запис, у решти — різні батьки (угода → команда продажів,
# задача → проєкт, товар → категорія). Звірено з ir.model.fields живої бази
# 09.09.2026 по ttype properties / properties_definition. Валідатор порівнює з
# цією таблицею, бо помилка тут тиха: властивість ляже не туди, де її шукає Odoo,
# і в картці не зʼявиться.
PROP_PARENT = {
    'res.partner': ('properties.base.definition', 'properties_definition'),
    'res.users': ('properties.base.definition', 'properties_definition'),
    'helpdesk.ticket': ('helpdesk.team', 'ticket_properties'),
    'crm.lead': ('crm.team', 'lead_properties_definition'),
    'project.task': ('project.project', 'task_properties_definition'),
    'product.template': ('product.category', 'product_properties_definition'),
    'product.product': ('product.category', 'product_properties_definition'),
    'stock.lot': ('product.product', 'lot_properties_definition'),
    'stock.quant': ('product.product', 'lot_properties_definition'),
    'stock.move.line': ('product.product', 'lot_properties_definition'),
    'stock.picking': ('stock.picking.type', 'picking_properties_definition'),
    'maintenance.equipment': ('maintenance.equipment.category',
                              'equipment_properties_definition'),
    'hr.employee': ('res.company', 'employee_properties_definition'),
    'approval.request': ('approval.category', 'approval_properties_definition'),
    'planning.slot': ('planning.role', 'slot_properties_definition'),
    # Пʼять пар, дописаних 10.09.2026: таблицю знято ЦІЛКОМ із живої бази
    # (ir.model.fields, ttype=properties → 20 моделей-носіїв, ttype=properties_definition
    # → 15 моделей-власників опису), а не доповнено здогадами. Дві з них ламають
    # інтуїцію «опис живе на батьківському довіднику»: у статті бази знань і в активу
    # опис лежить на ЗАПИСІ ТОГО САМОГО ТИПУ (батьківська стаття, батьківський актив),
    # а в позики — на журналі.
    'knowledge.article': ('knowledge.article', 'article_properties_definition'),
    'account.asset': ('account.asset', 'asset_properties_definition'),
    'account.loan': ('account.journal', 'loan_properties_definition'),
    'hr.resume.line': ('hr.resume.line.type', 'resume_line_type_properties_definition'),
    'properties.base.definition.mixin': ('properties.base.definition',
                                         'properties_definition'),
}
# Моделей із полем «Властивості» рівно 20; тут 20 ключів. Якщо в базі клієнта
# застосунків менше — частини моделей просто не буде, і це не помилка таблиці.
PROP_TYPES = {'char', 'text', 'boolean', 'integer', 'float', 'date', 'datetime',
              'selection', 'tags', 'many2one', 'many2many', 'separator'}

# Моделі, потрібні рецептам, але відсутні в полі «де» журналу.
# Усі три звірені з ir.model живої бази 09.09.2026 — просто не трапляються
# в полі «де», бо там про них не писали.
ALLOW_EXTRA = {'res.country', 'res.partner.category', 'ir.model.data', 'res.currency',
               'ir.model', 'properties.base.definition', 'crm.team', 'planning.role',
               'maintenance.equipment.category', 'stock.picking.type', 'helpdesk.team',
               'ir.model.fields.selection', 'base.automation', 'res.groups',
               'ir.module.module', 'res.currency.rate', 'ir.ui.view'}
# ir.model потрібен для перевірки «застосунок стоїть»: на свіжій базі документів ще
# немає, тому «щонайменше одна угода» падало б законно — перевіряємо не документ,
# а наявність моделі, яку приносить застосунок.
# ir.module.module — щоб рецепт зупинявся, коли застосунку позиції ще не поставили:
# без модуля Inter-Company полів міжкомпанійності на res.company просто не існує,
# і запис у них упав би незрозумілою помилкою замість зрозумілої зупинки.

REF = re.compile(r'^\$([^.]+)$')
# Змінні циклу «для_кожного»: вони не «посилання на створений запис», а підстановки
# емітера. Без цього переліку валідатор вимагав би визначити $індекс кроком «назвати».
LOOP_VARS = {'елемент', 'індекс'}
# $ім'я.поле — поле знайденого запису; розвʼязує виконавець. Валідатор мусить бачити
# базове імʼя, інакше описка в посиланні («$компаня.partner_id») проїде молча.
DEREF = re.compile(r'^\$([^.$]+)\.([\w]+)$')
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



def base_facts(rec):
    """Значення, які валідатор перевірити НЕ МОЖЕ, — їх звіряють на базі.

    Навіщо це друкувати. Валідатор бачить структуру: посилання, поля профілю, тексти
    пунктів. Але «подання_батько: hr.expense.form» він прийме, хоча в базі подання
    зветься `hr.expense.view.form`, — і рецепт упаде на прогоні, а не тут. За цю
    помилку я платив двічі: спершу вписав xmlid-и замість імен подань
    (`base.view_partner_form` проти `res.partner.form`), потім вигадав
    `hr.expense.form`.

    Тому валідатор тепер друкує перелік того, чого не знає: імена батьківських
    подань, зовнішні id меню й ролей, назви стадій і типів активності. Це не
    попередження — це список на одну звірку з базою, після якої він більше не
    потрібен. Мовчати про такі значення гірше: тоді «OK» валідатора виглядає як
    «рецепт правильний», а він означає лише «рецепт цілий».
    """
    views, xmlids, others = set(), set(), set()

    def walk(o):
        if isinstance(o, dict):
            a = o.get('аргументи') or {}
            if isinstance(a, dict):
                v = a.get('подання_батько')
                if isinstance(v, str) and not v.startswith('$'):
                    views.add(v)
                for mod, nm in (('меню_батько_xmlid_модуль', 'меню_батько_xmlid_назва'),
                                ('роль_xmlid_модуль', 'роль_xmlid_назва')):
                    if isinstance(a.get(mod), str) and isinstance(a.get(nm), str) \
                            and not a[mod].startswith('$'):
                        xmlids.add('%s.%s' % (a[mod], a[nm]))
                for k in ('тип_активності', 'модель_стадії'):
                    if isinstance(a.get(k), str) and not a[k].startswith('$'):
                        others.add('%s: %s' % (k, a[k]))
            if o.get('дія') == 'знайти_xmlid' and isinstance(o.get('модуль'), str) \
                    and not o['модуль'].startswith('$'):
                xmlids.add('%s.%s' % (o['модуль'], o.get("ім'я")))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(rec)
    return views, xmlids, others


def stale_generated(rec, cmap, vrfy):
    """Згенеровані рецепти, які вже не відповідають своєму виду.

    Рецепт виду «штатна поведінка» каже: конфігурації тут немає, лише перевірка
    застосунку й показ процесу. Якщо пункт згодом став конфігураційним — наприклад
    у журнал дописали адресу, і карта побачила модель — такий рецепт **занижує
    роботу**: план виглядає повним, а налаштування ніхто не зробить. Тому вид
    перечитується щоразу, і розбіжність називається вголос.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location('rg', 'tools/report_recipe_gaps.py')
    rg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rg)
    bad = []
    for pid, lvs in rec['позиції'].items():
        for lk, items in lvs.items():
            for txt, body in items.items():
                if not (isinstance(body, dict) and body.get('джерело')):
                    continue
                rows = (cmap['позиції'].get(pid, {}).get('рівні', {}) or {}).get(lk, [])
                row = next((r for r in rows if r['пункт'] == txt), None)
                if not row:
                    continue
                st = ((vrfy['позиції'].get(pid) or {}).get(lk) or {}).get('пункти', {})
                z = (st.get(txt) or {}).get('звірка') or {}
                kind = rg.kind(row['моделі'], z.get('є'), pid, row.get('модулі'))
                # Вид, під який рецепт згенерували, записаний у ньому самому. Раніше
                # тут стояло жорстке «штатна поведінка» — і щойно генератор навчився
                # другого виду, перевірка почала кричати на цілком правильні рецепти.
                # Порівнювати треба з тим, що записано, а не з тим, що я памʼятаю.
                was = body.get('вид') or 'штатна поведінка'
                if kind != was:
                    bad.append('%s р.%s «%s»: рецепт згенерований як «%s», а пункт тепер '
                               '«%s» — згенерований рецепт занижує роботу, його треба '
                               'замінити рукописним' % (pid, lk, txt[:44], was, kind))
    return bad


def named_but_not_created(rec, prof):
    """Пошук «рівно один» за назвою, яку жоден рецепт не створює.

    Клас помилок, знайдений 10.09.2026 пробою доменів — сім штук за один прохід,
    усі в щойно написаних рецептах. Форма завжди та сама:

        {"дія": "знайти", "модель": "helpdesk.team",
         "домен": [["name", "=", "$клієнт.черга_заявок_назва"]], "один": true}

    На демо-базі такий запис Є — ми його заводили руками, і журнал це чесно
    описує. На базі клієнта його немає, і рецепт зупиниться на першому ж кроці.

    ЯК ЦЕ НЕ ПЕРЕТВОРИТИСЯ НА КРИК. Перша версія правила порівнювала САМІ РЯДКИ
    «$клієнт.поле» — і дала 20 попереджень, із яких справжніх було два. Причини
    обидві структурні: більшість записів створюється всередині «для_кожного»
    (там ім'я — «$елемент.назва», а не «$клієнт.черга»), а половина шуканих —
    штатні записи Odoo, яких ніхто й не мусить створювати.

    Тому правило працює на ЗНАЧЕННЯХ, а не на іменах полів: профіль відомий,
    отже і перелік назв, які план створить, і назва, яку він шукає, — конкретні
    рядки. І звужене двома умовами, кожна з яких прибирає цілий клас шуму:

      • шукана назва мусить містити КИРИЛИЦЮ. Штатні записи Odoo названі
        латиницею («UA», «kg», «EUR», «Call», «Solved», «Order Confirmation»,
        «Wire Transfer») — їх ніхто не створює й не мусить;
      • моделі людей і контрагентів (res.partner, res.users, hr.employee)
        не перевіряються: ці записи приносить міграція або сам клієнт.

    Лишається попередженням, а не помилкою: рецепт може спиратися на запис,
    який заводить сусідня позиція поза набором прикладу.
    """
    ЛЮДИ = {'res.partner', 'res.users', 'hr.employee'}
    КИРИЛИЦЯ = re.compile(r'[а-яіїєґА-ЯІЇЄҐ]')

    def значення(v):
        """Конкретний рядок замість $клієнт.поле — профіль відомий."""
        if not isinstance(v, str):
            return None
        m = re.fullmatch(r'\$клієнт\.([\wа-яіїєґ_]+)', v.strip(), re.I | re.U)
        if m:
            з = prof.get(m.group(1))
            return з if isinstance(з, str) else None
        return None if v.startswith('$') else v

    створює = set()

    def збір(steps, елемент=None):
        for st in steps:
            if not isinstance(st, dict):
                continue
            if st.get('дія') == 'для_кожного':
                перелік = st.get('перелік')
                m = re.fullmatch(r'\$клієнт\.([\wа-яіїєґ_]+)',
                                 перелік.strip(), re.I | re.U) if isinstance(перелік, str) else None
                рядки = prof.get(m.group(1)) if m else None
                for e in (рядки if isinstance(рядки, list) else [None]):
                    збір([st.get('крок') or {}], e)
                continue
            if st.get('дія') != 'створити':
                continue
            for поле in ('name', 'code', 'login'):
                v = (st.get('значення') or {}).get(поле)
                if not isinstance(v, str):
                    continue
                mi = re.fullmatch(r'\$елемент(?:\.([\wа-яіїєґ_]+))?', v.strip(), re.I | re.U)
                if mi:
                    if isinstance(елемент, dict) and mi.group(1):
                        з = елемент.get(mi.group(1))
                    elif isinstance(елемент, str) and not mi.group(1):
                        з = елемент
                    else:
                        з = None
                    if isinstance(з, str):
                        створює.add(з)
                    continue
                з = значення(v)
                if з:
                    створює.add(з)

    for pid, lvs in rec['позиції'].items():
        for lk, items in lvs.items():
            for txt, body in items.items():
                збір(body.get('кроки') or [])

    warns = []
    for pid, lvs in rec['позиції'].items():
        for lk, items in lvs.items():
            for txt, body in items.items():
                for st in body.get('кроки') or []:
                    if not isinstance(st, dict) or st.get('дія') != 'знайти':
                        continue
                    if not st.get('один') or st.get('модель') in ЛЮДИ:
                        continue
                    for умова in st.get('домен') or []:
                        if not (isinstance(умова, list) and len(умова) == 3):
                            continue
                        if умова[0] not in ('name', 'code', 'login'):
                            continue
                        шукане = значення(умова[2])
                        if not шукане or not КИРИЛИЦЯ.search(шукане):
                            continue
                        if шукане in створює:
                            continue
                        warns.append('%s р.%s «%s»: шукає «рівно один» %s з назвою '
                                     '«%s», але жоден рецепт такого запису не '
                                     'створює. На демо-базі він є, бо заводили '
                                     'руками; у клієнта рецепт зупиниться'
                                     % (pid, lk, txt[:34], st.get('модель'), шукане))
    return warns


def main():
    rec = json.load(io.open(RECIPES, encoding='utf-8'))
    price = json.load(io.open(PRICE, encoding='utf-8'))
    cmap = json.load(io.open(CMAP, encoding='utf-8'))
    prof = json.load(io.open(PROFILE, encoding='utf-8'))
    templates = rec.get('шаблони') or {}
    errs_early = []
    vrfy = json.load(io.open(VERIFY, encoding='utf-8'))
    errs_early += stale_generated(rec, cmap, vrfy)
    warns_early = named_but_not_created(rec, prof)

    known_models = set(ALLOW_EXTRA)
    for blk in cmap['позиції'].values():
        for rows in blk.get('рівні', {}).values():
            for r in rows:
                known_models.update(r['моделі'])


    # Апостроф в імені аргумента чи поля профілю ламає підстановку молча:
    # регулярка збирає ім'я з літер і підкреслень і обірветься на апострофі.
    apos = [c for c in ("'", '\u2019')]
    for name in prof:
        if any(a in name for a in apos):
            errs_early.append('поле профілю «%s» містить апостроф — підстановка обірветься'
                              % name)

    # ДВОЙНИКИ. Цей проєкт уже вп'яте втрачає час на символи, що виглядають однаково:
    # апостроф U+2019 проти U+02BC (чотири рази) і латинська «i» всередині
    # «Квалiфiкований» у профілі (знайдено 10.09.2026 — стадія просто ніколи
    # не збігалася з базою).
    #
    # ПЕРША ВЕРСІЯ ПРАВИЛА КРИЧАЛА НА ПРАВИЛЬНІ ДАНІ — 20+ рядків на розмітці
    # («name="Про», «class="container"><h1>Про») і шляхах («WH/Запаси»), де змішані
    # алфавіти абсолютно законні. Тому правило звужене двома умовами, і кожна
    # прибирає цілий клас шуму:
    #   • слово складається ТІЛЬКИ з літер — розмітка, шляхи й формати відпадають;
    #   • латинські літери в ньому — ЛИШЕ ДВОЙНИКИ кириличних (i, o, a, c, e, p, x,
    #     y, T, H, B, M, K…). Слово на кшталт «Odoo19укр» не чіпаємо: там латиниця
    #     осмислена, а не переплутана.
    ДВОЙНИКИ = set('iIoOaAcCeEpPxXyYTHBMKlm')
    СЛОВО = re.compile(r'[^\W\d_]{3,}', re.U)

    def двойники(текст, де):
        for сл in СЛОВО.findall(текст or ''):
            кир = [c for c in сл if '\u0400' <= c <= '\u04ff']
            лат = [c for c in сл if 'a' <= c.lower() <= 'z']
            if not кир or not лат:
                continue
            if not all(c in ДВОЙНИКИ for c in лат):
                continue
            errs_early.append('%s: у слові «%s» латинські «%s» серед кирилиці — '
                              'майже напевно описка (порівняйте «і» U+0456 і «i» '
                              'U+0069). Пошук за таким рядком мовчки не знаходить '
                              'нічого' % (де, сл, ''.join(sorted(set(лат)))))

    for name, знач in prof.items():
        рядки = [знач] if isinstance(знач, str) else (
            [x for x in знач if isinstance(x, str)] if isinstance(знач, list) else [])
        for рядок in рядки:
            двойники(рядок, 'профіль «%s»' % name)
    for tname, tpl in templates.items():
        if tname.startswith('_') or not isinstance(tpl, dict):
            continue          # службові ключі розділу, як «_нащо»
        declared = set(tpl.get('аргументи') or [])
        for a in declared:
            if any(x in a for x in apos):
                errs_early.append('шаблон «%s»: аргумент «%s» містить апостроф'
                                  % (tname, a))
        # Кроки шаблону — такі самі кроки, і перевіряти їх треба так само.
        # Без цього зламаний шаблон проїжджає: перевірка аргументів нічого не каже
        # про те, що всередині.
        bound_t = set()
        for i, st in enumerate(tpl.get('кроки') or [], 1):
            where = 'шаблон «%s» крок %d' % (tname, i)
            act = st.get('дія')
            if act not in ACTIONS:
                errs_early.append('%s: невідома дія «%s»' % (where, act))
                continue
            mdl = st.get('модель')
            if isinstance(mdl, str) and mdl.startswith('$арг.'):
                if mdl[5:] not in declared:
                    errs_early.append('%s: модель узята з аргумента «%s», якого немає '
                                      'в переліку аргументів' % (where, mdl[5:]))
            elif mdl and mdl not in known_models:
                errs_early.append('%s: моделі «%s» немає в карті налаштування'
                                  % (where, mdl))
            for v in walk_values({k: x for k, x in st.items() if k != 'назвати'}):
                if not isinstance(v, str):
                    continue
                for mm in re.finditer(r'\$арг\.([\wа-яіїєґ_]+)', v, re.I | re.U):
                    if mm.group(1) not in declared:
                        errs_early.append('%s: аргумент «%s» не оголошений'
                                          % (where, mm.group(1)))
                m = REF.match(v.strip())
                if m and m.group(1) in LOOP_VARS:
                    continue
                if m and m.group(1) not in bound_t:
                    errs_early.append('%s: посилання $%s ще не визначене'
                                      % (where, m.group(1)))
            if st.get('назвати'):
                bound_t.add(st['назвати'])

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

    errs, warns = list(errs_early), list(warns_early)
    n_items = n_steps = 0

    for pid, levels in rec['позиції'].items():
        if pid not in price_items:
            errs.append('позиції «%s» немає в прайсі' % pid)
            continue
        for lk, items in levels.items():
            for txt, body in items.items():
                n_items += 1
                if txt not in price_items[pid].get(lk, set()):
                    # За проєкт цей апостроф зʼїдав пошук ЧОТИРИ рази: у прайсі стоїть
                    # U+2019 (’), а з клавіатури й з інших документів приходить U+02BC (ʼ)
                    # або звичайний U+0027. Тексти виглядають однаково, збіг не працює.
                    # Тому коли єдина різниця саме в ньому — кажемо це прямо, а не
                    # лишаємо людину гадати над двома однаковими на вигляд рядками.
                    def _норм(t):
                        return t.replace('\u02bc', '\u2019').replace("'", '\u2019')
                    близькі = [c for c in price_items[pid].get(lk, set())
                               if _норм(c) == _норм(txt)]
                    if близькі:
                        errs.append('%s р.%s: текст пункту збігається з прайсом усім, '
                                    'КРІМ АПОСТРОФА. У прайсі U+2019 (’), у рецепті '
                                    'інший — скопіювати текст із data/price.json, '
                                    'а не набирати: «%s»' % (pid, lk, txt))
                    else:
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
                            # «опції» потрібні лише полю-переліку. Робити їх
                            # обовʼязковими завжди означало б писати «опції: []» у
                            # кожному виклику — шум, який перестають читати. А от
                            # перелік БЕЗ опцій — справжня тиха поломка: поле є,
                            # вибрати нічого.
                            if tname == 'власне_поле':
                                # «опції» передаються завжди (мова не має умовних
                                # кроків, і цикл у шаблоні мусить отримати список),
                                # але для переліку вони мусять бути НЕПОРОЖНІ: поле
                                # без варіантів створюється, а вибрати в ньому нічого.
                                ttype = (st.get('аргументи') or {}).get('тип')
                                opts = (st.get('аргументи') or {}).get('опції')
                                if ttype == 'selection' and opts == []:
                                    errs.append('%s: поле-перелік з порожніми «опції» — '
                                                'воно створиться без варіантів' % where)
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
                        # ВКЛАДЕНИЙ КРОК ПЕРЕВІРЯВСЯ ВПОЛОВИНУ, і це знайшлося на собі
                        # 10.09.2026: усередині циклу стояв виклик шаблону, якого в
                        # розділі «шаблони» ще не було, — валідатор промовчав, бо
                        # перевіряв тільки дію й модель. Той самий пропуск стосувався
                        # й обовʼязкових полів: вкладене «створити» без «значення»
                        # проїхало б так само.
                        if inner.get('дія') == 'шаблон':
                            itn = inner.get('назва')
                            itpl = templates.get(itn)
                            if not itpl:
                                errs.append('%s: у вкладеному кроці шаблону «%s» немає '
                                            'в розділі «шаблони»' % (where, itn))
                            else:
                                ineed = set(itpl.get('аргументи') or [])
                                igot = set((inner.get('аргументи') or {}).keys())
                                if ineed - igot:
                                    errs.append('%s: вкладеному шаблону «%s» бракує '
                                                'аргументів: %s'
                                                % (where, itn, ', '.join(sorted(ineed - igot))))
                                if igot - ineed:
                                    errs.append('%s: вкладеному шаблону «%s» передані '
                                                'зайві аргументи: %s'
                                                % (where, itn, ', '.join(sorted(igot - ineed))))
                        elif inner.get('дія') in ACTIONS:
                            for f in ACTIONS[inner['дія']]:
                                if f not in inner:
                                    errs.append('%s: у вкладеній дії «%s» немає поля «%s»'
                                                % (where, inner['дія'], f))
                        if st.get('назвати'):
                            bound.add(st['назвати'])
                        continue
                    for f in ACTIONS[act]:
                        if f not in st:
                            errs.append('%s: у дії «%s» немає поля «%s»' % (where, act, f))
                    mdl = st.get('модель')
                    if mdl and mdl not in known_models:
                        errs.append('%s: моделі «%s» немає в карті налаштування' % (where, mdl))
                    if act == 'властивість':
                        # Найтихіша помилка властивостей: визначення записане не на той
                        # батьківський запис. Odoo просто не покаже властивість у картці,
                        # помилки не буде. Тому пара звіряється з таблицею, знятою з бази.
                        want = PROP_PARENT.get(mdl)
                        if not want:
                            errs.append('%s: для моделі «%s» невідомо, де лежить визначення '
                                        'властивостей — доповнити PROP_PARENT із живої бази'
                                        % (where, mdl))
                        else:
                            got = (st.get('батько_модель'), st.get('батько_поле'))
                            if got != want:
                                errs.append('%s: властивості «%s» визначаються в %s.%s, а в '
                                            'рецепті стоїть %s.%s — Odoo шукає визначення '
                                            'саме на батькові, тому властивість просто не '
                                            'зʼявиться' % (where, mdl, want[0], want[1],
                                                           got[0], got[1]))
                        if st.get('тип') not in PROP_TYPES:
                            errs.append('%s: тип властивості «%s» невідомий — можна %s'
                                        % (where, st.get('тип'), ', '.join(sorted(PROP_TYPES))))
                        if st.get('тип') == 'selection' and not st.get('опції'):
                            errs.append('%s: властивість-перелік без «опції»' % where)
                        if st.get('тип') in ('many2one', 'many2many') \
                                and not st.get('модель_посилання'):
                            errs.append('%s: властивість-посилання без «модель_посилання»'
                                        % where)
                    # посилання
                    for s in walk_values({k: v for k, v in st.items() if k != 'назвати'}):
                        d = DEREF.match(s.strip()) if isinstance(s, str) else None
                        if d and not d.group(1).startswith(('клієнт', 'арг', 'елемент')):
                            if d.group(1) not in bound:
                                errs.append('%s: посилання «$%s.%s» на невизначений запис'
                                            % (where, d.group(1), d.group(2)))
                        m = REF.match(s.strip()) if isinstance(s, str) else None
                        if m and m.group(1) in LOOP_VARS:
                            continue
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
    views, xmlids, others = base_facts(rec)
    print('Звірити з базою (валідатор цього не бачить):')
    print('  батьківські подання (шукаються за ІМЕНЕМ, не за xmlid): %s'
          % ', '.join(sorted(views)))
    print('  зовнішні id: %s' % ', '.join(sorted(xmlids)))
    if others:
        print('  назви, що приходять штатними (часто англійські): %s'
              % ', '.join(sorted(others)))
    print()
    print('OK: рецепти — %d пунктів, %d кроків, %d попереджень' % (n_items, n_steps, len(warns)))
    for c in cov:
        print('    покриття: %s' % c)
    return 0


if __name__ == '__main__':
    sys.exit(main())
