# -*- coding: utf-8 -*-
"""Негативні тести перевірок цілісності: кожна отрута мусить бути зловлена.

Навіщо окремий тест на перевірку. Перевірка, яка нічого не ловить, гірша за
відсутність перевірки: збірка друкує «OK», і на це «OK» починають покладатися.
Тому кожна з шести перевірок `check_integrity` тут відтворюється навмисним псуванням
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

good = bc.check_integrity(copy.deepcopy(P['групи']), copy.deepcopy(V))
print('  ok     чисті дані: %d помилок, %d попереджень' % (len(good[0]), len(good[1])))
res = [not good[0] and not good[1]]

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

print()
print('пройшло %d із %d' % (sum(1 for r in res if r), len(res)))
sys.exit(0 if all(res) else 1)
