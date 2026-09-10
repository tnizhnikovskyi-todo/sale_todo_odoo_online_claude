# -*- coding: utf-8 -*-
"""Негативні тести перевірок цілісності: кожна отрута мусить бути зловлена.

Навіщо окремий тест на перевірку. Перевірка, яка нічого не ловить, гірша за
відсутність перевірки: збірка друкує «OK», і на це «OK» починають покладатися.
Тому кожна з восьми перевірок `check_integrity` тут відтворюється навмисним псуванням
копії прайсу — а перед цим підтверджується, що на чистих даних вона молчить (інакше
тест проходив би на перевірці, яка кричить завжди).

Що перевіряється і чому саме це:

1. **Пункт прайсу без запису в журналі.** `check_verify` стежить за зворотним боком —
   запис журналу мусить вести на живий пункт. Цей бік був відкритий: `build_kb`
   позицію без журналу просто пропускав, тому нова обіцянка зникала з усіх звітів.
2. **Дубль тексту пункту.** Журнал адресує пункт текстом у межах рівня — два однакові
   тексти роблять запис неоднозначним, і галочка стає не на той пункт.
3. **Однакова ціна двох рівнів.** Години перевіряються на зростання, але ціна
   округлюється до 50: 20 і 21 година дають ту саму 1 000 евро.
4. **Однакові ознаки рівнів.** Рівень вибирають саме за ознакою.
5. **`home` поза `apps`.** На `home` тримається попередження «тягнеш чужий модуль без
   dep»; названий, але відсутній власник робить те попередження фіктивним.
6. **Цикл у жорстких залежностях.** Калькулятор додає їх сам, процедура збірки шукає
   порядок сортуванням — цикл ламає обидва.
7. **Хибне підтвердження у звірці.** «знайшли» посилається на іншу перевірку, а «є»
   стоїть true. 10.09.2026 таких записів було 11 і чотири з них виявились неправдою —
   переліки властивостей у базі були порожні. Тут три випадки, бо правило мусить
   ловити лінивий опис і НЕ чіпати опис із власним доказом.

Запуск: python3 tools/test_integrity.py
"""
import copy, io, json, sys, os
sys.path.insert(0, 'tools')
import importlib.util
spec = importlib.util.spec_from_file_location('bc', 'tools/build_calculator.py')
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)

P = json.load(io.open('data/price.json', encoding='utf-8'))
V = json.load(io.open('data/verify.json', encoding='utf-8'))

def find(groups, pid):
    for g in groups:
        for it in g['items']:
            if it['id'] == pid: return it

def run(name, poison_price, poison_vrfy, want, expect_err=True):
    g = copy.deepcopy(P['групи']); v = copy.deepcopy(V)
    if poison_price: poison_price(g)
    if poison_vrfy: poison_vrfy(v)
    errs, warns = bc.check_integrity(g, v)
    pool = errs if expect_err else warns
    hit = [m for m in pool if want in m]
    kind = 'помилка' if expect_err else 'попередження'
    print(('  ok     ' if hit else '  ПРОВАЛ ') + name + ' → ' + kind +
          (': ' + hit[0][:110] if hit else ' НЕ ЗНАЙДЕНО (усього %d/%d)' % (len(errs), len(warns))))
    return bool(hit)

# ── Класифікація залишку за видом роботи ─────────────────────────────────────
# Правило `kind()` зі звіту рецептів двічі помилялося, і обидва рази це показала
# вибірка, а не логіка. Тому тут закріплені саме ті випадки, на яких воно ламалося:
# щоб наступна «оптимізація» правила не повернула стару брехню.

def check_kind():
    import importlib.util
    spec = importlib.util.spec_from_file_location('rg', 'tools/report_recipe_gaps.py')
    rg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rg)
    cases = [
        # (моделі, звірка «є», позиція) → очікуваний вид, чому саме так
        (([], False, 'trn'), 'послуга',
         'запис сесії: звірка сказала «в базі немає» — це єдина надійна ознака послуги'),
        (([], True, 'crm'), 'без адреси в карті',
         'автоматичні активності за стадіями: правило створене й перевірене ділом, '
         'просто карта не знає адреси. Перша версія правила звала це послугою — і брехала'),
        ((['sale.order', 'account.move'], True, 'mig'), 'штатна поведінка',
         'тільки документні моделі: записувати нічого, перевіряємо застосунок'),
        ((['res.company'], True, 'rnt'), 'конфігурація',
         'поле компанії — є що записати'),
        ((['spreadsheet.dashboard'], True, 'dsh'), 'конфігурація',
         'дашборд ми створюємо: усе неперелічене в DOCS вважається конфігурацією — '
         'безпечніший бік помилки'),
        (([], True, 'diag'), 'не в базі: інструмент сейла',
         'експрес-діагностика живе в калькуляторі, рецепта для неї не буде ніколи'),
    ]
    # Пункт з адресою-МОДУЛЕМ («застосунок data_cleaning») — це конфігурація, а не
    # «без адреси»: щоб він працював, модуль має бути в базі. Перевіряється окремо,
    # бо аргумент інший.
    mod_case = rg.kind([], True, 'mig', ['data_cleaning'])
    out = []
    for (models, has, pid), want, why in cases:
        got = rg.kind(models, has, pid)
        out.append((got == want, '%-28s ← %s' % (got, why[:74])))
    out.append((mod_case == 'конфігурація',
                '%-28s ← %s' % (mod_case, 'адреса-модуль — це конфігурація, а не «без '
                                          'адреси»: модуль мусить бути в базі')))
    return out


# ── Розбір адрес у пробі переперевірки ───────────────────────────────────────
# Проба (`tools/probe_audit.py`) двічі тихо брехала, і обидва рази однаково: слово
# збігалося з назвою моделі, запис із таким id у базі був, і проба «підтверджувала»
# твердження, якого не перевіряла. Хибне підтвердження гірше за відсутність перевірки,
# бо закриває питання. Тут закріплені саме ті дві фрази.

def check_probe():
    import importlib.util
    spec = importlib.util.spec_from_file_location('pa', 'tools/probe_audit.py')
    pa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pa)
    out = []

    site = 'вкладеність: «Кава та чай» (меню 12) під «Про компанію» (меню 7) у меню сайту 4'
    got = set(m for _, m, _ in pa.pairs(site) if 'menu' in m)
    out.append((got == {'website.menu'},
                'меню сайту: %s — у записі про сайт голі «меню N» це website.menu, '
                'а ir.ui.menu 7 і 12 існують («General Settings», «Automation») і дали б '
                'хибне підтвердження' % (','.join(got) or '—')))

    seq = 'у сьогоднішніх нарядів послідовність 1 і 2'
    got2 = [m for _, m, _ in pa.pairs(seq)]
    out.append(('ir.sequence' not in got2,
                'послідовність як значення поля: адрес %d — це поле sequence, а не записи '
                'ir.sequence; запис 1 у базі є («Lead Mining Request») і проба підтвердила б '
                'порядок нарядів, якого не дивилась' % len(got2)))

    amb = 'бланк — шаблон 4897, дія 1355, роль 39'
    got3 = [w for w, _, _ in pa.pairs(amb) if w in pa.AMBIGUOUS]
    out.append((len(got3) == 3,
                'неоднозначні слова відсіяні: %s — «шаблон», «дія», «роль» означають різні '
                'моделі, тому в пробу не йдуть' % ','.join(got3)))
    return out


good = bc.check_integrity(copy.deepcopy(P['групи']), copy.deepcopy(V))
print('  ok     чисті дані: %d помилок, %d попереджень' % (len(good[0]), len(good[1])))
res = [not good[0] and not good[1]]

# ── 9. Залік діагностики проти найдешевшого можливого проєкту ────────────────
# Діагностика оплачується окремо, і частина суми зараховується у вартість проєкту.
# Поки залік був повним, існував набір, у якому він зʼїдав проєкт цілком: діагностика
# рівня 3 (€1 000) при «тільки Базі» рівня 1 (€800). Рішення 10.09.2026 — половина;
# але це не назавжди: досить підняти години діагностики або опустити години Бази.
# Тому перевіряється ІНВАРІАНТ (залік < найдешевший проєкт), а не число.
_справж_credit = bc.DIAG_CREDIT
try:
    bc.DIAG_CREDIT = 1.0
    _e9a, _ = bc.check_integrity(copy.deepcopy(P['групи']), copy.deepcopy(V))
finally:
    bc.DIAG_CREDIT = _справж_credit
res.append(any('залік діагностики' in m for m in _e9a))
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'залік: повний залік (100 %) спіймано')

_g9 = copy.deepcopy(P['групи'])
find(_g9, 'diag')['lv'][2][1] = 40          # +20 год діагностики = залік €1 000
_e9b, _ = bc.check_integrity(_g9, copy.deepcopy(V))
res.append(any('залік діагностики' in m for m in _e9b))
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'залік: підняті години діагностики теж спіймано')

_g9c = copy.deepcopy(P['групи'])
find(_g9c, 'base')['lv'][0][1] = 10         # −6 год Бази = проєкт €500
_e9c, _ = bc.check_integrity(_g9c, copy.deepcopy(V))
res.append(any('залік діагностики' in m for m in _e9c))
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'залік: опущені години Бази — той самий випадок з іншого боку')

_e9d, _ = bc.check_integrity(copy.deepcopy(P['групи']), copy.deepcopy(V))
res.append(not any('залік діагностики' in m for m in _e9d))
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'залік: на чинних даних правило мовчить')

# Частка заліку живе у ДВОХ місцях неминуче: Python перевіряє, JS показує. Тому
# вони звіряються між собою — інакше перевірка стерегла б не те, що бачить клієнт.
_html9 = io.open('artifacts/calculator.html', encoding='utf-8').read()
res.append(bc.check_diag_credit_const(_html9) == [])
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'залік: частка в коді сторінки збігається з тією, якою рахує перевірка')
res.append(bc.check_diag_credit_const(
    _html9.replace('var DIAG_CREDIT = 0.5;', 'var DIAG_CREDIT = 1;', 1)) != [])
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'залік: розсинхрон двох копій частки спіймано')

# ── 8. Число в пояснені чек-листа проти прайсу ───────────────────────────────
# Пояснення гейта про бюджет називає «обовʼязковий мінімум» конкретною сумою, а це
# ПОХІДНА від прайсу («База» р.1 + «Рахунки та оплати» р.1). Поправте години Бази —
# і сейл почне казати клієнтові неправду, бо число живе в тексті, а не в даних.
# Отрути дві, бо розійтися можна з обох боків: правкою тексту й правкою прайсу.
Q = json.load(io.open('data/qualification.json', encoding='utf-8'))

def _нота_з_мінімумом(blocks, заміна=None):
    for b in blocks:
        for x in b.get('питання') or []:
            for a_ in x.get('a') or []:
                н = a_.get('note') or ''
                if 'мінімум' in н.lower() and '€' in н:
                    if заміна:
                        a_['note'] = заміна(н)
                    return True
    return False

_бл = copy.deepcopy(Q['блоки'])
res.append(_нота_з_мінімумом(_бл))
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'мінімум: у чек-листі взагалі є нота з сумою мінімуму (інакше тест порожній)')

_бл1 = copy.deepcopy(Q['блоки'])
_нота_з_мінімумом(_бл1, lambda н: н.replace('€1 100', '€900'))
_e8, _ = bc.check_integrity(copy.deepcopy(P['групи']), copy.deepcopy(V), _бл1)
res.append(any('відвʼязалося від джерела' in m for m in _e8))
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'мінімум: правку числа в тексті спіймано')

_g8 = copy.deepcopy(P['групи'])
find(_g8, 'base')['lv'][0][1] += 2          # +2 години Бази = +€100 до мінімуму
_e8b, _ = bc.check_integrity(_g8, copy.deepcopy(V), copy.deepcopy(Q['блоки']))
res.append(any('відвʼязалося від джерела' in m for m in _e8b))
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'мінімум: правку ПРАЙСУ при незмінному тексті теж спіймано')

_e8c, _ = bc.check_integrity(copy.deepcopy(P['групи']), copy.deepcopy(V),
                             copy.deepcopy(Q['блоки']))
res.append(not any('відвʼязалося від джерела' in m for m in _e8c))
print(('  ok     ' if res[-1] else '  ПРОВАЛ ')
      + 'мінімум: на чинних даних правило мовчить')


res.append(run('1. новий пункт прайсу без запису в журналі',
    lambda g: find(g, 'base')['inc'].append('нова обіцянка без перевірки'),
    None, 'без запису в журналі', expect_err=False))

res.append(run('2. той самий текст пункту на двох рівнях',
    lambda g: find(g, 'base')['lv'][1][4].append(find(g, 'base')['inc'][0]),
    None, 'повторюється'))

res.append(run('3. округлення дало однакову ціну на двох рівнях',
    lambda g: find(g, 'base')['lv'][1].__setitem__(1, 16),
    None, 'за ті самі гроші'))

res.append(run('4. ознаки двох рівнів однакові',
    lambda g: find(g, 'base')['lv'][1].__setitem__(3, find(g, 'base')['lv'][0][3]),
    None, 'ознаки рівнів повторюються'))

res.append(run('5. свій застосунок не серед власних apps',
    lambda g: find(g, 'crm')['home'].append('mrp_plm'),
    None, 'власник фіктивний'))

def cycle(g):
    # sal уже потрібен prj жорстко; додамо зворотну жорстку — цикл
    find(g, 'sal').setdefault('dep', []).append(
        {'on': 'prj', 'type': 'hard', 'from_lv': 1, 'why': 'навмисний цикл для тесту'})
res.append(run('6. цикл у жорстких залежностях', cycle, None, 'цикл у жорстких залежностях'))

# 7. Хибне підтвердження. Дві отрути й одна протиотрута, бо правило мусить не просто
# кричати на слово «раніше», а відрізняти лінивий опис із доказом від опису без нього.
def лише_посилання(v):
    rec = v['позиції']['base']['1']['пункти']['компанія з реквізитами']
    rec['звірка'] = {'дата': '2026-09-10', 'дивились': 'реквізити компанії',
                     'знайшли': 'перевірено раніше', 'є': True}
res.append(run('7а. «знайшли» — лише посилання на іншу перевірку', None, лише_посилання,
    'не називає жодного доказу'))

def посилання_без_доказу_довше(v):
    rec = v['позиції']['base']['1']['пункти']['компанія з реквізитами']
    rec['звірка'] = {'дата': '2026-09-10', 'дивились': 'реквізити компанії',
                     'знайшли': 'те саме, що вище — усе заповнено', 'є': True}
res.append(run('7б. «те саме, що вище» без жодного доказу', None, посилання_без_доказу_довше,
    'не називає жодного доказу'))

def посилання_з_доказом(v):
    # Протиотрута: посилання на попередню перевірку ДОЗВОЛЕНЕ, якщо поруч стоїть
    # власний доказ. Без цього випадку правило кричало б на сім записів із живими
    # артефактами — а перевірка, яка кричить на правильні дані, живе до першої правки.
    rec = v['позиції']['base']['1']['пункти']['компанія з реквізитами']
    rec['звірка'] = {'дата': '2026-09-10', 'дивились': 'res.company id 1',
                     'знайшли': 'перевірено раніше; сьогодні бачив id 1 з назвою «Тодо»',
                     'є': True}
g7 = __import__('copy').deepcopy(P['групи']); v7 = __import__('copy').deepcopy(V)
посилання_з_доказом(v7)
e7, w7 = bc.check_integrity(g7, v7)
тихо = not [m for m in e7 if 'не називає жодного доказу' in m]
print(('  ok     ' if тихо else '  ПРОВАЛ ')
      + '7в. посилання РАЗОМ із власним доказом помилкою не вважається')
res.append(тихо)

for okk, note in check_kind():
    print(('  ok     ' if okk else '  ПРОВАЛ ') + 'вид роботи: ' + note)
    res.append(okk)

def check_subst():
    """Підстановка складеного значення в середину рядка.

    Спіймано дорого й тихо: рецепт написали як «$клієнт.контроль_міграції.назва»,
    підстановка розпізнала лише перший сегмент (вкладених шляхів мова не має),
    віддала весь словник, і str() від нього поїхав у arch подання разом із
    фігурними дужками. Валідатор рецептів мовчав — поле в профілі справді є,
    а емітер не падав. Одне око на плані — і все.
    """
    import importlib.util
    sp = importlib.util.spec_from_file_location('ec', 'tools/emit_config_calls.py')
    ec = importlib.util.module_from_spec(sp); sp.loader.exec_module(ec)
    out = []

    # отрута: словник у середину рядка
    m = []
    ec.subst('назва.$клієнт.складене.підполе', {'складене': {'назва': 'X'}}, m)
    out.append((any('складене значення' in x for x in m),
                'словник у середину рядка → сказано вголос'))
    # отрута: список так само
    m = []
    ec.subst('перелік: $клієнт.перелік', {'перелік': [1, 2]}, m)
    out.append((any('складене значення' in x for x in m),
                'список у середину рядка → сказано вголос'))
    # протиотрута 1: складене значення ЦІЛИМ рядком — законно (так передають опції)
    m = []
    r = ec.subst('$клієнт.перелік', {'перелік': [1, 2]}, m)
    out.append((r == [1, 2] and not m,
                'складене значення цілим рядком лишається складеним'))
    # протиотрута 2: звичайна скалярна підстановка в середину рядка
    m = []
    r = ec.subst('назва: $клієнт.назва!', {'назва': 'ТОВ'}, m)
    out.append((r == 'назва: ТОВ!' and not m, 'скаляр у середину рядка працює як був'))

    # $елемент УСЕРЕДИНІ рядка. Довго не підставлявся, і це мовчки ламало розмітку:
    # у базу йшло подання з буквальним «$елемент.назва» в заголовку. Помилки немає,
    # arch валідний, видно тільки очима. Знайдено прогоном плану по базі.
    m = []
    r = ec.subst('<list string="$елемент.назва"><field name="x"/></list>', {}, m,
                 elem={'назва': 'Воронка керівника'}, idx=1)
    out.append(('Воронка керівника' in r and '$елемент' not in r,
                '$елемент.поле в середині рядка підставляється'))
    # і те саме для $індекс, який теж бував лише цілим рядком
    m = []
    r = ec.subst('стадія $індекс', {}, m, elem='X', idx=3)
    out.append((r == 'стадія 3', '$індекс у середині рядка підставляється'))
    # протиотрута: складене значення в середину рядка так само заборонене
    m = []
    ec.subst('поля: $елемент.опції', {}, m, elem={'опції': [1, 2]}, idx=1)
    out.append((any('складене значення' in x for x in m),
                'складений $елемент у середину рядка → сказано вголос'))

    # Сторож усього плану: жодної незамінемої підстановки в готовому плані.
    # Вимикаємо заміну $елемент усередині рядка — тобто повертаємо поведінку,
    # яка мовчки клала «$елемент.назва» в arch подання, — і перевіряємо, що
    # емітер тепер відмовляється друкувати такий план.
    import re as _re, contextlib as _cx
    справжній_item = ec.ITEM_IN
    буф = io.StringIO()
    try:
        ec.ITEM_IN = _re.compile(r'(?!x)x')
        with _cx.redirect_stdout(буф):
            код = ec.main(['x', 'data/client-profile-example.json', '--всі'])
    finally:
        ec.ITEM_IN = справжній_item
    out.append((код != 0 and 'НЕЗАМІНЕНА ПІДСТАВКА' in буф.getvalue(),
                'план із незаміненою підставкою емітер друкувати відмовляється'))
    буф2 = io.StringIO()
    with _cx.redirect_stdout(буф2):
        код2 = ec.main(['x', 'data/client-profile-example.json', '--всі'])
    out.append((код2 == 0, 'на чистому плані сторож мовчить'))

    # «Перевірити» без жодного очікування: гілка-запобіжник, яка на нинішніх
    # рецептах не спрацьовує жодного разу. Саме тому їй потрібен тест — невживана
    # гілка інакше згниє непоміченою, і наступний рецепт із голою перевіркою
    # поїде до виконавця з невисловленою умовою.
    import tempfile as _tf, os as _os
    _d = _tf.mkdtemp()
    prof_t = json.load(io.open('data/client-profile-example.json', encoding='utf-8'))
    prof_t['набір'] = {'base': 1}
    rec_t = json.load(io.open('data/recipes.json', encoding='utf-8'))
    rec_t['позиції']['base']['1']['компанія з реквізитами']['кроки'] = [
        {'дія': 'перевірити', 'модель': 'res.company', 'домен': [['id', '=', 1]]}]
    пп = _os.path.join(_d, 'prof_bare.json'); рр = _os.path.join(_d, 'rec_bare.json')
    json.dump(prof_t, io.open(пп, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(rec_t, io.open(рр, 'w', encoding='utf-8'), ensure_ascii=False)
    справж = ec.RECIPES
    буфб = io.StringIO()
    try:
        ec.RECIPES = рр
        with _cx.redirect_stdout(буфб):
            ec.main(['x', пп])
    finally:
        ec.RECIPES = справж
    out.append(('за замовчуванням: запис мусить існувати' in буфб.getvalue(),
                'гола «перевірити» друкує свою умову явно'))
    return out

def check_coverage():
    """Режим «--всі» емітера: чи справді він бачить позиції ПОЗА набором прикладу.

    Дірка, яку він закриває, була тиха й велика: профіль-приклад описує реальний
    набір клієнта, і рецепти позицій поза ним («Друковані форми», «Управлінський
    облік», «Виробництво») емітер не бачив ніколи. А саме емітер ловить помилки
    підстановки — валідатор їх не бачить, бо поле профілю формально існує. Тобто
    ціла позиція могла лежати з неробочими рецептами при зелених перевірках.

    Отрута ставиться в «Друковані форми» — позицію, якої в наборі прикладу немає.
    Файли репозиторію не чіпаються: емітеру підсовується копія в тимчасовому каталозі.
    """
    import importlib.util, tempfile, os, copy as _copy
    sp = importlib.util.spec_from_file_location('ec2', 'tools/emit_config_calls.py')
    ec = importlib.util.module_from_spec(sp); sp.loader.exec_module(ec)
    out = []
    свіжі = json.load(io.open('data/recipes.json', encoding='utf-8'))
    отруєні = _copy.deepcopy(свіжі)
    отруєні['позиції']['prt']['1']['перевірка друку']['кроки'].insert(
        0, {'дія': 'послуга', 'опис': 'отрута $клієнт.поля_якого_точно_немає'})
    d = tempfile.mkdtemp()
    шлях_отрути = os.path.join(d, 'poison.json')
    json.dump(отруєні, io.open(шлях_отрути, 'w', encoding='utf-8'), ensure_ascii=False)
    справжній = ec.RECIPES
    try:
        ec.RECIPES = шлях_отрути
        код_набір = ec.main(['x', 'data/client-profile-example.json'])
        код_всі = ec.main(['x', 'data/client-profile-example.json', '--всі'])
    finally:
        ec.RECIPES = справжній
    out.append((код_набір == 0,
                'звичайний план отрути в позиції поза набором НЕ бачить (це й є дірка)'))
    out.append((код_всі != 0, '«--всі» отруту бачить і падає'))
    чисто = ec.main(['x', 'data/client-profile-example.json', '--всі'])
    out.append((чисто == 0, 'на чистих рецептах «--всі» проходить'))
    return out

def check_validator():
    """Валідатор рецептів: чи ловить він крок «записати» БЕЗ адреси.

    Дірка була така: обовʼязковими для «записати» вважались лише «модель» і
    «значення». Я написав неіснуюче поле «ціль_домен» замість «ціль», валідатор
    пропустив, емітер надрукував крок без жодної адреси — і виконавець отримав би
    «записати res.users нікуди». Крок при цьому виглядає цілком нормально.
    """
    import importlib.util, tempfile, os, copy as _copy
    sp = importlib.util.spec_from_file_location('cr2', 'tools/check_recipes.py')
    cr = importlib.util.module_from_spec(sp); sp.loader.exec_module(cr)
    out = []
    свіжі = json.load(io.open('data/recipes.json', encoding='utf-8'))
    отруєні = _copy.deepcopy(свіжі)
    крок = {'дія': 'записати', 'модель': 'res.users',
            'ціль_домен': [['login', '=', 'x@example.com']],
            'значення': {'signature': 'x'}}
    отруєні['позиції']['base']['2']['шаблони листів і підписи']['кроки'].append(крок)
    d = tempfile.mkdtemp()
    отрута = os.path.join(d, 'poison.json')
    json.dump(отруєні, io.open(отрута, 'w', encoding='utf-8'), ensure_ascii=False)
    справжній = cr.RECIPES
    try:
        cr.RECIPES = отрута
        код_отрути = cr.main()
    finally:
        cr.RECIPES = справжній
    out.append((код_отрути != 0, '«записати» без «ціль» валідатор ловить'))

    # Апостроф: за проєкт зʼїдав пошук ЧОТИРИ рази. Перевірка не в тому, що валідатор
    # відхилить текст (це він і так робив), а в тому, що він НАЗВЕ ПРИЧИНУ: два рядки
    # виглядають однаково, і без підказки людина шукає розбіжність очима.
    отр2 = _copy.deepcopy(свіжі)
    ц = [t for t in отр2['позиції']['rnt']['3'] if t.startswith('технологічна пауза')][0]
    отр2['позиції']['rnt']['3'][ц.replace('\u2019', '\u02bc')] = \
        отр2['позиції']['rnt']['3'].pop(ц)
    отрута2 = os.path.join(d, 'poison_apos.json')
    json.dump(отр2, io.open(отрута2, 'w', encoding='utf-8'), ensure_ascii=False)
    буфер = io.StringIO()
    try:
        cr.RECIPES = отрута2
        import contextlib as _c
        with _c.redirect_stdout(буфер):
            код_апос = cr.main()
    finally:
        cr.RECIPES = справжній
    out.append((код_апос != 0 and 'АПОСТРОФ' in буфер.getvalue(),
                'підміну апострофа валідатор не просто ловить, а називає причину'))

    # Пошук «рівно один» за назвою, якої ніхто не створює. Клас, знайдений пробою
    # доменів 10.09.2026: на демо-базі запис є (заводили руками), у клієнта немає.
    отр3 = _copy.deepcopy(свіжі)
    отр3['позиції']['hlp']['1']['одна черга заявок']['кроки'][0] = {
        'дія': 'знайти', 'модель': 'helpdesk.team',
        'домен': [['name', '=', '$клієнт.черга_заявок_назва']],
        'один': True, 'назвати': 'черга'}
    отрута3 = os.path.join(d, 'poison_named.json')
    json.dump(отр3, io.open(отрута3, 'w', encoding='utf-8'), ensure_ascii=False)
    буф3 = io.StringIO()
    try:
        cr.RECIPES = отрута3
        with _c.redirect_stdout(буф3):
            cr.main()
    finally:
        cr.RECIPES = справжній
    out.append(('жоден рецепт такого запису не створює' in буф3.getvalue(),
                'пошук за назвою, якої ніхто не створює, названо вголос'))
    # Протиотрута: на чистих рецептах правило МОВЧИТЬ. Перша його версія давала
    # 20 попереджень із двох справжніх — перевірка, яка кричить на правильні дані,
    # живе до першої правки.
    буф4 = io.StringIO()
    with _c.redirect_stdout(буф4):
        cr.main()
    out.append(('жоден рецепт такого запису не створює' not in буф4.getvalue(),
                'на чистих рецептах правило мовчить'))

    # Двойники: латинська «i» серед кирилиці. Знайдено в профілі — «Квалiфiкований»
    # ніколи не збігався з базою, і мовчки.
    проф = json.load(io.open('data/client-profile-example.json', encoding='utf-8'))
    проф['стадії_воронки'] = ['Новий лід', 'Квал\u0069ф\u0069кований']
    отрута5 = os.path.join(d, 'poison_homoglyph.json')
    json.dump(проф, io.open(отрута5, 'w', encoding='utf-8'), ensure_ascii=False)
    справжній_проф = cr.PROFILE
    буф5 = io.StringIO()
    try:
        cr.PROFILE = отрута5
        with _c.redirect_stdout(буф5):
            код5 = cr.main()
    finally:
        cr.PROFILE = справжній_проф
    out.append((код5 != 0 and 'латинськ' in буф5.getvalue(),
                'латиниця серед кирилиці спіймана й названа'))

    # Рецепт, який тільки перевіряє. Знайдено звітом «кроки проти годин»:
    # «Склад» показав 48 годин при 4 кроках-послугах, і причина була не в ціні,
    # а в чотирьох рецептах із єдиного «перевірити».
    отр6 = _copy.deepcopy(свіжі)
    б = отр6['позиції']['stk']['1']['прихід від постачальника']
    б['кроки'] = [x for x in б['кроки'] if x.get('дія') != 'послуга']
    отрута6 = os.path.join(d, 'poison_thin.json')
    json.dump(отр6, io.open(отрута6, 'w', encoding='utf-8'), ensure_ascii=False)
    буф6 = io.StringIO()
    try:
        cr.RECIPES = отрута6
        with _c.redirect_stdout(буф6):
            cr.main()
    finally:
        cr.RECIPES = справжній
    out.append(('тільки перевіряє' in буф6.getvalue(),
                'рецепт без запису й без передачі названо вголос'))
    буф7 = io.StringIO()
    with _c.redirect_stdout(буф7):
        cr.main()
    out.append(('тільки перевіряє' not in буф7.getvalue(),
                'на чистих рецептах правило про «тільки перевіряє» мовчить'))
    # ПЕРИМЕТР. Три отрути, кожна — окремий спосіб вийти за межі непомітно, і
    # жодна з них не виглядає підозріло в JSON. Четверта перевірка — протиотрута:
    # ЧИТАННЯ ir.cron у справжніх рецептах є (перевіряємо, що штатне розписання
    # Odoo живе), і правило мусить його пропускати. Заборонений саме запис.
    отрути_периметра = [
        ({'дія': 'створити', 'модель': 'ir.cron',
          'значення': {'name': 'нічне перерахування'}},
         'cron у базі клієнта', 'створення cron'),
        ({'дія': 'створити', 'модель': 'ir.actions.server',
          'значення': {'name': 'x', 'state': 'code', 'code': 'record.write({})'}},
         'Python у базі клієнта', 'сервер-дія з Python'),
        ({'дія': 'створити', 'модель': 'ir.actions.server',
          'значення': {'name': 'x', 'state': 'webhook'}},
         'вебхуки', 'сервер-дія з вебхуком'),
        ({'дія': 'створити', 'модель': 'ir.model.fields',
          'значення': {'name': 'x_разом', 'compute': "for r in self: r.x = 1"}},
         'обчислюване поле', 'обчислюване поле'),
        ({'дія': 'створити', 'модель': 'account.tax',
          'значення': {'name': 'ПДВ 20%'}},
         'ставки податків', 'ставка податку'),
    ]
    for i, (крок_отрути, слово, підпис) in enumerate(отрути_периметра):
        отрп = _copy.deepcopy(свіжі)
        отрп['позиції']['base']['2']['шаблони листів і підписи']['кроки'].append(крок_отрути)
        шп = os.path.join(d, 'poison_perim%d.json' % i)
        json.dump(отрп, io.open(шп, 'w', encoding='utf-8'), ensure_ascii=False)
        буфп = io.StringIO()
        try:
            cr.RECIPES = шп
            with _c.redirect_stdout(буфп):
                кодп = cr.main()
        finally:
            cr.RECIPES = справжній
        out.append((кодп != 0 and слово in буфп.getvalue(),
                    'периметр: %s спіймано й названо' % підпис))
    буф8 = io.StringIO()
    with _c.redirect_stdout(буф8):
        cr.main()
    out.append(('cron у базі клієнта' not in буф8.getvalue(),
                'периметр: ЧИТАННЯ штатного cron правило пропускає'))

    # Незвірене ім'я батьківського подання. Це ЄДИНА перевірка, яка ловить не
    # помилку, а НЕЗНАННЯ: ім'я може бути правильним, але поки його ніхто не
    # прочитав із бази, воно не має права їхати до клієнта. Приводом стало те,
    # що ім'я «maintenance.equipment.form» повернулося в шаблон уже ПІСЛЯ того,
    # як журнал записав правильне «equipment.form».
    отр9 = _copy.deepcopy(свіжі)
    отр9['шаблони']['власне_поле']  # шаблон мусить існувати
    ш = отр9['позиції']['mnt']['1']
    ключ9 = list(ш)[0]
    ш[ключ9]['кроки'].append({'дія': 'знайти', 'модель': 'ir.ui.view',
                              'домен': [['name', '=', 'maintenance.equipment.form'],
                                        ['type', '=', 'form'], ['inherit_id', '=', False]],
                              'один': True, 'назвати': 'подання_вигадане'})
    отрута9 = os.path.join(d, 'poison_view.json')
    json.dump(отр9, io.open(отрута9, 'w', encoding='utf-8'), ensure_ascii=False)
    буф9 = io.StringIO()
    try:
        cr.RECIPES = отрута9
        with _c.redirect_stdout(буф9):
            код9 = cr.main()
    finally:
        cr.RECIPES = справжній
    out.append((код9 != 0 and 'не звірене з базою' in буф9.getvalue(),
                'незвірене ім\'я батьківського подання валить збірку'))

    # Незвірений зовнішній id — той самий сторож, що для імен подань. Помилка тут
    # так само тиха: «знайти_xmlid» не впаде на перевірці, він упаде на прогоні
    # в клієнта.
    отр10 = _copy.deepcopy(свіжі)
    ш10 = отр10['позиції']['mnt']['1']
    ш10[list(ш10)[0]]['кроки'].append(
        {'дія': 'знайти_xmlid', 'модуль': 'maintenance',
         "ім'я": 'group_equipment_manager_вигаданий', 'назвати': 'роль_вигадана'})
    отрута10 = os.path.join(d, 'poison_xmlid.json')
    json.dump(отр10, io.open(отрута10, 'w', encoding='utf-8'), ensure_ascii=False)
    буф10 = io.StringIO()
    try:
        cr.RECIPES = отрута10
        with _c.redirect_stdout(буф10):
            код10 = cr.main()
    finally:
        cr.RECIPES = справжній
    out.append((код10 != 0 and 'не звірене з базою' in буф10.getvalue(),
                'незвірений зовнішній id валить збірку'))

    # Форма значення для x2many. Обидві отрути виглядають у JSON нормально —
    # саме тому правило й потрібне. Третя перевірка — протиотрута: у нинішніх
    # рецептах 14 полів пишуться командами, і правило мусить їх пропускати.
    отрути_форми = [
        ({'дія': 'записати', 'модель': 'res.users', 'ціль': '$продавці',
          'значення': {'group_ids': '$група_продажі_свої'}},
         'пишеться скаляр', 'скаляр у x2many'),
        ({'дія': 'записати', 'модель': 'res.users', 'ціль': '$продавці',
          'значення': {'notification_type': [[6, False, [1]]]}},
         'команда x2many', 'команда x2many у звичайному полі'),
    ]
    for i, (крок_ф, слово, підпис) in enumerate(отрути_форми):
        отрф = _copy.deepcopy(свіжі)
        отрф['позиції']['base']['2']['шаблони листів і підписи']['кроки'].append(крок_ф)
        шф = os.path.join(d, 'poison_form%d.json' % i)
        json.dump(отрф, io.open(шф, 'w', encoding='utf-8'), ensure_ascii=False)
        буфф = io.StringIO()
        try:
            cr.RECIPES = шф
            with _c.redirect_stdout(буфф):
                кодф = cr.main()
        finally:
            cr.RECIPES = справжній
        out.append((кодф != 0 and слово in буфф.getvalue(),
                    'форма значень: %s спіймано' % підпис))
    буф11 = io.StringIO()
    with _c.redirect_stdout(буф11):
        cr.main()
    out.append(('пишеться скаляр' not in буф11.getvalue()
                and 'команда x2many' not in буф11.getvalue(),
                'форма значень: на 14 законних командах правило мовчить'))

    # Дзеркало правила про пошуки: перевірка «рівно N» на записі, якого план ніде
    # не створює. Отрута ставиться в позицію, де такий крок був би правдоподібним.
    отр11 = _copy.deepcopy(свіжі)
    ш11 = отр11['позиції']['crm']['1']
    к11 = [t for t in ш11 if t.startswith('картка клієнта')][0]
    ш11[к11]['кроки'].append(
        {'дія': 'перевірити', 'модель': 'crm.team',
         'домен': [['name', '=', 'Команда, якої ніхто не створює']],
         'очікувати_кількість': 1})
    отрута11 = os.path.join(d, 'poison_check.json')
    json.dump(отр11, io.open(отрута11, 'w', encoding='utf-8'), ensure_ascii=False)
    буф12 = io.StringIO()
    try:
        cr.RECIPES = отрута11
        with _c.redirect_stdout(буф12):
            cr.main()
    finally:
        cr.RECIPES = справжній
    out.append(('якого план ніде не створює' in буф12.getvalue(),
                'перевірка «рівно N» без створення названа вголос'))
    # Протиотрути: правило мовчить і на чинних рецептах, і на двох законних формах —
    # «ir.model» (моделі не створюють) та значенні-списку в домені (створює цикл).
    буф13 = io.StringIO()
    with _c.redirect_stdout(буф13):
        cr.main()
    out.append(('якого план ніде не створює' not in буф13.getvalue(),
                'правило мовчить на «ir.model» і на значенні-списку в домені'))

    out.append((cr.main() == 0, 'на чистих рецептах валідатор мовчить'))
    return out

def check_claude_md():
    """CLAUDE.md проти даних: чи ловиться застаріле число.

    Це інструкція, яку читає кожна наступна сесія перед першою дією, і 10.09.2026
    девʼять її чисел уже не збігалися з даними — частину зістарив я сам того ж дня
    (додав поле в анкету, додав тести). Клас відтворюється щоразу, коли правиш
    дані й не перечитуєш інструкцію, тому правило потрібне саме тут.
    """
    import importlib.util, tempfile, os, contextlib as _cc
    sp = importlib.util.spec_from_file_location('cmd', 'tools/check_claude_md.py')
    cm = importlib.util.module_from_spec(sp); sp.loader.exec_module(cm)
    md = io.open('CLAUDE.md', encoding='utf-8').read()
    буф = io.StringIO()
    with _cc.redirect_stdout(буф):
        код = cm.main()
    out = [(код == 0, 'CLAUDE.md: на чинному тексті перевірка мовчить'),
           ('19 похідних чисел' in буф.getvalue(),
            'CLAUDE.md: перевірка справді дивиться на 19 чисел, а не на нуль')]
    d = tempfile.mkdtemp()
    справж = cm.MD
    for було, стало, підпис in [
        ('банк питань на 84 позиці', 'банк питань на 80 позиці', 'застаріле число'),
        ('фільтрує по всіх 549 рядках', 'фільтрує по всіх 539 рядках', 'стара сума рядків'),
    ]:
        assert було in md, було
        ш = os.path.join(d, 'poison_md_%s.md' % abs(hash(було)))
        io.open(ш, 'w', encoding='utf-8').write(md.replace(було, стало, 1))
        буф2 = io.StringIO()
        try:
            cm.MD = ш
            with _cc.redirect_stdout(буф2):
                код2 = cm.main()
        finally:
            cm.MD = справж
        out.append((код2 != 0 and 'а в даних' in буф2.getvalue(),
                    'CLAUDE.md: %s спіймано' % підпис))
    # Протиотрута на саму прив’язку: якщо текст навколо числа перепишуть, правило
    # мусить сказати «твердження не знайдено», а не тихо пройти.
    ш3 = os.path.join(d, 'poison_md_gone.md')
    io.open(ш3, 'w', encoding='utf-8').write(md.replace('банк питань на 84 позиці',
                                                        'банк питань', 1))
    буф3 = io.StringIO()
    try:
        cm.MD = ш3
        with _cc.redirect_stdout(буф3):
            код3 = cm.main()
    finally:
        cm.MD = справж
    out.append((код3 != 0 and 'не знайдено' in буф3.getvalue(),
                'CLAUDE.md: зникле твердження назване, а не пропущене'))
    return out


for okk, note in check_claude_md():
    print(('  ok     ' if okk else '  ПРОВАЛ ') + note)
    res.append(okk)


def check_concept():
    """Концепція: чи ловиться Studio без заперечення, чужа ціна і стоп-слово.

    Приводом стала не гіпотетична загроза: 10.09.2026 концепція **двадцять разів**
    називала Studio нашим способом впровадження — через день після рішення від неї
    відмовитись. Документ правлять руками, рішення лягають в інший файл, і розрив
    ніхто не бачить, бо жодна збірка концепцію не читала.
    """
    import importlib.util, tempfile, os, contextlib as _c
    sp = importlib.util.spec_from_file_location('cc', 'tools/check_concept.py')
    cc = importlib.util.module_from_spec(sp); sp.loader.exec_module(cc)
    out = []
    чистий = io.open('artifacts/concept.html', encoding='utf-8').read()
    d = tempfile.mkdtemp()
    отрути = [
        (чистий.replace('а не на рівні швидких рук у конфігураторі',
                        'а не на рівні швидких рук у Studio'),
         'без заперечення', 'Studio як бажана навичка'),
        (чистий.replace('<tr><td>CRM</td><td class="num">14</td>',
                        '<tr><td>CRM</td><td class="num">15</td>', 1),
         'а в прайсі', 'години позиції, яких немає в прайсі'),
        (чистий.replace('Бухгалтерського, податкового', 'ПРРО, бухгалтерського, податкового'),
         'знято з контуру', 'стоп-слово знятої теми'),
    ]
    справж = cc.HTML
    for i, (текст, слово, підпис) in enumerate(отрути):
        ш = os.path.join(d, 'poison_concept%d.html' % i)
        io.open(ш, 'w', encoding='utf-8').write(текст)
        буф = io.StringIO()
        try:
            cc.HTML = ш
            with _c.redirect_stdout(буф):
                код = cc.main()
        finally:
            cc.HTML = справж
        out.append((код != 0 and слово in буф.getvalue(),
                    'концепція: %s спіймано' % підпис))
    # Головні числа моделі — одне значення у двох документах. Отрути дві, бо
    # розійтися можна з обох боків; правило не рахує модель, воно лише вимагає,
    # щоб концепція й відкриті питання називали одне й те саме.
    відкриті = io.open('docs/відкриті-питання.md', encoding='utf-8').read()
    справж_open = cc.OPEN
    for було, стало, слово, підпис in [
        ('**три проєкти щомісяця**', '**чотири проєкти щомісяця**',
         'проєкти щомісяця', 'розбіжність у проєктах на місяць'),
        ('маржа з клієнта **€5 786**', 'маржа з клієнта **€5 526**',
         'маржа з клієнта', 'розбіжність у маржі з клієнта'),
    ]:
        assert було in відкриті, було
        шо = os.path.join(d, 'poison_open_%s.md' % abs(hash(було)))
        io.open(шо, 'w', encoding='utf-8').write(відкриті.replace(було, стало, 1))
        буфо = io.StringIO()
        try:
            cc.OPEN = шо
            with _c.redirect_stdout(буфо):
                кодо = cc.main()
        finally:
            cc.OPEN = справж_open
        out.append((кодо != 0 and слово in буфо.getvalue(),
                    'числа моделі: %s спіймано' % підпис))

    буф = io.StringIO()
    with _c.redirect_stdout(буф):
        код = cc.main()
    out.append((код == 0, 'концепція: на чинному документі перевірка мовчить'))
    # Перевірка мусить БАЧИТИ всі рядки: строгий шаблон мовчки пропускав три
    # позиції з пʼятнадцяти, і «OK» означало «я подивилась на 12 із 15».
    out.append(('15 позицій економіки' in буф.getvalue() and '5 наборів' in буф.getvalue(),
                'концепція: перевірка бачить усі 15 позицій і 5 наборів'))
    return out


for okk, note in check_concept():
    print(('  ok     ' if okk else '  ПРОВАЛ ') + note)
    res.append(okk)

import contextlib
with contextlib.redirect_stdout(io.StringIO()):
    _cov = check_coverage()
    _val = check_validator()
for okk, note in _val:
    print(('  ok     ' if okk else '  ПРОВАЛ ') + 'валідатор: ' + note)
    res.append(okk)
for okk, note in _cov:
    print(('  ok     ' if okk else '  ПРОВАЛ ') + 'покриття: ' + note)
    res.append(okk)

for okk, note in check_subst():
    print(('  ok     ' if okk else '  ПРОВАЛ ') + 'підстановка: ' + note)
    res.append(okk)

def check_client_text():
    """Стоп-слова знятих тем у клієнтському тексті калькулятора.

    Прайс від них захищений давно, а статична проза — «що не входить», умови,
    приймання, опис рівнів — не перевірялася ніяк, хоча живе в тому самому файлі,
    правиться руками і йде КЛІЄНТОВІ.
    """
    html = io.open('artifacts/calculator.html', encoding='utf-8').read()
    out = [(bc.check_client_text(html) == [], 'на чинному тексті КП правило мовчить')]
    отрути = [
        ('Платформа: підписка Odoo Online (план Custom)',
         'Платформа: ПРРО й підписка Odoo Online (план Custom)',
         'ПРРО', 'знята тема в КП'),
        ('робиться штатними засобами, Studio ми не відкриваємо',
         'робиться в Studio',
         'без заперечення', 'Studio без заперечення в описі рівня'),
    ]
    for було, стало, слово, підпис in отрути:
        assert було in html, було[:40]
        помилки = bc.check_client_text(html.replace(було, стало, 1))
        out.append((any(слово in e for e in помилки), 'КП: %s спіймано' % підпис))
    # Протиотрута, без якої правило вбило б журнал: у нотатках VERIFY Studio
    # згадується законно — це історія перевірки для аналітика, не текст клієнту.
    out.append(('Studio' in html.split('var VERIFY')[1],
                'КП: у нотатках журналу Studio лишається (правило туди не дивиться)'))
    return out


for okk, note in check_client_text():
    print(('  ok     ' if okk else '  ПРОВАЛ ') + note)
    res.append(okk)


def check_render():
    """Чи друкує план ВСЕ, що потрібно для виконання кроку.

    Дірка, знайдена 10.09.2026: дію «властивість» додали пізніше за рендер, і він
    її не навчився. У плані стояло «**властивість** `project.task`» — і більше
    нічого: ні назви поля, ні типу, ні батьківського запису, у якому лежить
    визначення. Виконати такий крок неможливо, а виглядає він рядком серед інших,
    тому й прожив непоміченим. Валідатор мовчав: рецепт цілий, поламаний ДРУК.

    Тест дивиться на надрукований план, а не на рецепт: перевіряти треба саме те,
    що бачить виконавець.
    """
    import importlib.util, contextlib as _cc
    sp = importlib.util.spec_from_file_location('ec3', 'tools/emit_config_calls.py')
    ec = importlib.util.module_from_spec(sp); sp.loader.exec_module(ec)
    буф = io.StringIO()
    with _cc.redirect_stdout(буф):
        ec.main(['x', 'data/client-profile-example.json', '--всі'])
    рядки = буф.getvalue().splitlines()
    кроки = [i for i, l in enumerate(рядки) if '**властивість**' in l]
    out = [(len(кроки) > 0, 'у плані взагалі є кроки «властивість» (інакше тест порожній)')]
    цілі = all('- поле `' in рядки[i + 1] and 'визначення лежить у' in рядки[i + 2]
               for i in кроки if i + 2 < len(рядки))
    out.append((цілі, 'кожна «властивість» друкує поле, тип і батьківський запис'))
    # Ціна дії: читання визначень + запис + читання назад. За замовчуванням
    # рахувалась одиниця, і замір фази 0 занижував би вартість пункту втричі.
    out.append((ec.CALLS_ВЛАСТИВІСТЬ == 3, '«властивість» коштує трьох викликів, не одного'))
    return out


for okk, note in check_render():
    print(('  ok     ' if okk else '  ПРОВАЛ ') + 'друк: ' + note)
    res.append(okk)

for okk, note in check_probe():
    print(('  ok     ' if okk else '  ПРОВАЛ ') + 'проба: ' + note)
    res.append(okk)

print()
print('пройшло %d із %d' % (sum(1 for r in res if r), len(res)))
sys.exit(0 if all(res) else 1)
