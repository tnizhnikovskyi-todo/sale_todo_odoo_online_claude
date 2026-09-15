# -*- coding: utf-8 -*-
"""Перейменовує пункт складу робіт у ВСІХ файлах, де його текст є ключем.

Навіщо окремий інструмент. Текст пункту — не просто назва, а **ключ у трьох файлах**:
`data/price.json` (сама обіцянка), `data/verify.json` (журнал перевірки: що зроблено й
що справді є в базі) і `data/recipes.json` (рецепт збірки). Перейменувати треба скрізь
одночасно, інакше збірка падає — і це добре, бо інакше журнал тихо відстав би від прайсу.

Я робив це руками тричі за одну ніч і на третій раз забув рецепти: валідатор спіймав,
але хвилина пішла. Такі речі не запамʼятовують, їх автоматизують.

Що робить:
  • перевіряє, що старий текст є в прайсі рівно один раз (інакше зупиняється);
  • міняє його в прайсі, у журналі й у рецептах, зберігаючи порядок ключів;
  • дописує в ноту журналу причину перейменування — щоб через місяць було зрозуміло,
    чому обіцянка звучить інакше.

Чого НЕ робить: не міняє тексти в документах (`docs/*.md`) — вони або генеруються з
цих джерел, або є історією, яку переписувати не можна.

Запуск:
    python3 tools/rename_item.py "старий текст" "новий текст" "причина"
"""

import collections
import io
import json
import sys

OD = collections.OrderedDict
PRICE = 'data/price.json'
VERIFY = 'data/verify.json'
RECIPES = 'data/recipes.json'


def rename_in_ordered(d, old, new):
    """Міняє ключ, зберігаючи його місце в порядку."""
    out = OD()
    hit = False
    for k, v in d.items():
        if k == old:
            out[new] = v
            hit = True
        else:
            out[k] = v
    return out, hit


def main(argv):
    if len(argv) < 4:
        print('вжиток: python3 tools/rename_item.py "старий" "новий" "причина"')
        return 2
    old, new, why = argv[1], argv[2], argv[3]
    if old == new:
        # Здавалося б, нащо таке забороняти. Я перевіряв інструмент, передавши той
        # самий текст двічі, — і він слухняно дописав у ноту журналу «ФОРМУЛЮВАННЯ
        # ЗМІНЕНО: перевірка інструмента». Тобто нічого не перейменував, зате
        # засмітив журнал. Перейменування в себе — завжди описка.
        print('старий і новий тексти однакові — нічого не робимо')
        return 2

    P = json.load(io.open(PRICE, encoding='utf-8'), object_pairs_hook=OD)
    where = []
    for g in P['групи']:
        for it in g['items']:
            for i, t in enumerate(it.get('inc') or []):
                if t == old:
                    where.append((it, 1, it['inc'], i))
            for lv_i in (1, 2):
                for i, t in enumerate(it['lv'][lv_i][4]):
                    if t == old:
                        where.append((it, lv_i + 1, it['lv'][lv_i][4], i))
    if len(where) != 1:
        print('у прайсі знайдено %d входжень — перейменування скасовано. '
              'Однакові тексти в різних пунктах заборонені перевіркою цілісності, '
              'тому нуль означає описку, а більше одного — зламані дані.' % len(where))
        return 1
    it, lk, arr, idx = where[0]
    pid = it['id']
    arr[idx] = new

    V = json.load(io.open(VERIFY, encoding='utf-8'), object_pairs_hook=OD)
    rec = ((V['позиції'].get(pid) or {}).get(str(lk)) or {}).get('пункти')
    v_hit = False
    if rec is not None:
        fresh, v_hit = rename_in_ordered(rec, old, new)
        if v_hit:
            fresh[new]['нота'] = (fresh[new].get('нота') or '') + \
                ' ФОРМУЛЮВАННЯ ЗМІНЕНО: %s' % why
            V['позиції'][pid][str(lk)]['пункти'] = fresh

    R = json.load(io.open(RECIPES, encoding='utf-8'), object_pairs_hook=OD)
    items = ((R['позиції'].get(pid) or {}).get(str(lk)) or None)
    r_hit = False
    if items is not None:
        fresh, r_hit = rename_in_ordered(items, old, new)
        if r_hit:
            R['позиції'][pid][str(lk)] = fresh

    io.open(PRICE, 'w', encoding='utf-8').write(
        json.dumps(P, ensure_ascii=False, indent=1) + '\n')
    io.open(VERIFY, 'w', encoding='utf-8').write(
        json.dumps(V, ensure_ascii=False, indent=1) + '\n')
    io.open(RECIPES, 'w', encoding='utf-8').write(
        json.dumps(R, ensure_ascii=False, indent=1) + '\n')
    print('перейменовано %s р.%d' % (pid, lk))
    print('  прайс:   так')
    print('  журнал:  %s' % ('так' if v_hit else 'запису не було'))
    print('  рецепти: %s' % ('так' if r_hit else 'рецепта не було'))
    print('Далі: python3 tools/check_all.py')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
