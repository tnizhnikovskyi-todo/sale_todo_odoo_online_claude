# -*- coding: utf-8 -*-
"""Витягує з плану всі пошуки «рівно один» — щоб перевірити їх однією пачкою.

Навіщо. Найчастіша поломка рецепта — не помилка в мові, а **домен, який знаходить не
те**. Двічі за одну сесію: пошук проєкту за назвою (на базі проєктів «Виїзне
обслуговування» ДВА), пошук батьківського подання за іменем (подань `sale.order.form`
ТРИ, бо успадковані носять імʼя батька). Обидва рази валідатор молчав — він перевіряє
цілість рецепта, а не правдивість домену.

Крок із `один: true` каже: «очікую рівно один запис». Це перевірна обіцянка, і
перевіряється вона одним читанням на кожен домен. Скрипт збирає їх із **розгорнутого
плану** (тобто вже з підставленими значеннями профілю) і друкує так, щоб можна було
прогнати пачкою й порівняти з очікуваним.

Скрипт **не звертається до Odoo**: ключ API в репозиторії не зберігається. Він готує
пробу — читає той, у кого є конектор.

Запуск:
    python3 tools/probe_recipes.py <профіль.json>
    python3 tools/probe_recipes.py <профіль.json> --json проба.json
    python3 tools/probe_recipes.py <профіль.json> --всі        # усі 27 позицій
"""

import collections
import io
import json
import subprocess
import sys
import tempfile

EMIT = 'tools/emit_config_calls.py'


def main(argv):
    if len(argv) < 2:
        print('вжиток: python3 tools/probe_recipes.py <профіль.json> '
              '[--json проба.json] [--всі]')
        return 2
    prof = argv[1]
    with tempfile.NamedTemporaryFile('r', suffix='.json', delete=False) as f:
        plan_path = f.name
    # «--всі» прокидається в емітер, і це не зручність. Без нього проба бачить
    # лише позиції з набору профілю — тобто рівно ті рецепти, які й так найбільше
    # прогнані. Домени позицій поза набором («Виробництво», «Друковані форми»,
    # «Управлінський облік») не перевірялися жодного разу.
    cmd = ['python3', EMIT, prof, '--json', plan_path]
    if '--всі' in argv:
        cmd.append('--всі')
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print('емітер упав:\n%s' % (r.stderr or r.stdout))
        return 1
    plan = json.load(io.open(plan_path, encoding='utf-8'))

    # Пошук «рівно один» небезпечний не завжди. Якщо ЦЕЙ САМИЙ план раніше створює
    # такий запис («створити» з тим самим полем і значенням), то пара «створити →
    # знайти» самодостатня: на свіжій базі запис зʼявиться, і пошук його знайде.
    # Ризик — тільки в пошуках записів, які мусять існувати ДО плану: контрагент,
    # товар, штатна стадія, штатне подання. Без цього поділу проба кричала б на
    # половину пошуків: перший же прогін дав чотири «відсутні» записи, з яких два
    # план створює сам.
    made = set()
    for st in plan['кроки']:
        if st.get('дія') != 'створити':
            continue
        vals = st.get('значення') or {}
        for f, v in list(vals.items()) + [tuple(c[:1] + c[2:]) if False else (c[0], c[2])
                                          for c in (st.get('якщо_немає') or [])
                                          if isinstance(c, list) and len(c) == 3]:
            if isinstance(v, (str, int, float, bool)):
                made.add((st.get('модель'), f, v))

    # Неявні створення: Odoo сама створює один запис разом з іншим. Проба про це знати
    # не може — це семантика платформи, тому пари перелічені руками. Без них проба
    # кричить на пошук `product.product`, хоча план створив `product.template`, а
    # варіант зʼявився разом із ним.
    IMPLICIT = {'product.product': ['product.template']}

    def creates_it(model, domain):
        """Чи створює план запис, який задовольнить цей домен (прямо або неявно)."""
        if not isinstance(domain, list):
            return False
        for m in [model] + IMPLICIT.get(model, []):
            for c in domain:
                if isinstance(c, list) and len(c) == 3 and (m, c[0], c[2]) in made:
                    return True
        return False

    strict, loose, checks, safe = [], [], [], []
    for st in plan['кроки']:
        act = st.get('дія')
        if act == 'знайти':
            row = collections.OrderedDict([
                ('модель', st.get('модель')),
                ('домен', st.get('домен')),
                ('очікую', 'рівно один' if st.get('один') else 'будь-скільки'),
                ('пункт', '%s р.%s · %s' % (st.get('_позиція'), st.get('_рівень'),
                                            st.get('_пункт'))),
            ])
            if not st.get('один'):
                loose.append(row)
            elif creates_it(st.get('модель'), st.get('домен')):
                row['примітка'] = 'план сам створює цей запис раніше'
                safe.append(row)
            else:
                strict.append(row)
        elif act == 'перевірити' and st.get('домен'):
            n = st.get('очікувати_кількість')
            m = st.get('щонайменше')
            checks.append(collections.OrderedDict([
                ('модель', st.get('модель')),
                ('домен', st.get('домен')),
                ('очікую', ('рівно %s' % n) if n is not None
                           else ('щонайменше %s' % m) if m is not None else '—'),
                ('пункт', '%s р.%s · %s' % (st.get('_позиція'), st.get('_рівень'),
                                            st.get('_пункт'))),
            ]))

    if '--json' in argv:
        i = argv.index('--json') + 1
        if i >= len(argv):
            print('після «--json» треба вказати файл')
            return 2
        io.open(argv[i], 'w', encoding='utf-8').write(json.dumps(
            {'рівно один': strict, 'створюється планом': safe,
             'будь-скільки': loose, 'перевірки': checks},
            ensure_ascii=False, indent=1) + '\n')
        print('проба записана: %s' % argv[i])
        return 0

    print('# Проба рецептів: домени, які обіцяють «рівно один»')
    print()
    print('Пошуків «рівно один», які вимагають ГОТОВОГО запису: **%d**' % len(strict))
    print('Пошуків «рівно один», запис для яких створює сам план: %d' % len(safe))
    print('Пошуків без обмеження: %d · перевірок із кількістю: %d'
          % (len(loose), len(checks)))
    print()
    print('«Рівно один» — це обіцянка домену. Якщо запис не один, рецепт зупиниться')
    print('(добре) або перейменує не той запис (погано). Перевіряти треба саме перші:')
    print('пара «створити → знайти» всередині плану самодостатня, а ось запис, який')
    print('мусить існувати ДО плану, і є справжнім ризиком.')
    print()
    by_model = collections.defaultdict(list)
    for row in strict:
        by_model[row['модель']].append(row)
    for m in sorted(by_model, key=lambda x: -len(by_model[x])):
        print('## %s — %d' % (m, len(by_model[m])))
        seen = set()
        for row in by_model[m]:
            key = json.dumps(row['домен'], ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            print('- `%s`' % key)
            print('  · %s' % row['пункт'][:96])
        print()
    if checks:
        print('## Перевірки з очікуваною кількістю')
        print()
        for row in checks:
            print('- %s `%s` → %s' % (row['модель'],
                                      json.dumps(row['домен'], ensure_ascii=False),
                                      row['очікую']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
