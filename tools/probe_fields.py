# -*- coding: utf-8 -*-
"""Які пари (модель, поле) план узагалі пише — щоб звірити їх із живою базою.

НАВІЩО. Рецепти писалися за журналом перевірки, а журнал пише поле словами:
«maintenance.equipment.location». Такого поля в базі немає — справжнє зветься
`location_id` і посилається на `stock.location`. Рецепт при цьому виглядав
бездоганно, валідатор мовчав (поле профілю є, модель у карті є), і зламався б
він лише на живій базі, посеред прогону.

ЩО РОБИТЬ ЦЕЙ СКРИПТ. Витягає з готового плану всі пари «модель + поле», які
план справді пише або перевіряє, і друкує їх переліком, придатним для одного
запиту до `ir.model.fields`. Сам він у базу НЕ ХОДИТЬ і ходити не буде: ключа
API в репозиторії немає й не буде.

ЯК КОРИСТУВАТИСЯ. Запустити, узяти перелік моделей і полів, зробити один запит
на кожну партію й звірити. Знайдене «немає в базі» — привід дивитися, а не
вирок: у батьківських моделей поле може зватися інакше, а деякі поля приносять
модулі, яких на цій базі не встановлено.

Перший прогін 10.09.2026: **140 пар у 39 моделях, одна помилка** —
`maintenance.equipment.location` замість `location_id`. Одна на 140 — саме та
щільність, заради якої перевірку варто робити перед прогоном, а не після.

Запуск: python3 tools/probe_fields.py [профіль.json]
"""

import collections
import io
import json
import os
import subprocess
import sys
import tempfile

# Поля, які є в кожній моделі Odoo: перевіряти їх немає сенсу, вони лише
# роздувають перелік і ховають справжні кандидати.
СКРІЗЬ = {'id', 'name', 'active', 'sequence', 'company_id', 'create_date',
          'write_date', 'display_name'}


def main(argv):
    профіль = argv[1] if len(argv) > 1 else 'data/client-profile-example.json'
    tmp = os.path.join(tempfile.mkdtemp(), 'plan.json')
    r = subprocess.run(['python3', 'tools/emit_config_calls.py', профіль,
                        '--всі', '--json', tmp], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write('емітер не склав план:\n%s\n' % (r.stderr or r.stdout))
        return 1
    план = json.load(io.open(tmp, encoding='utf-8'))

    пари = collections.defaultdict(set)
    де = {}
    for st in план['кроки']:
        м = st.get('модель')
        if not м:
            continue
        for ключ in ('значення', 'очікувати', 'поля'):
            v = st.get(ключ)
            if isinstance(v, dict):
                for поле in v:
                    пари[м].add(поле)
                    де.setdefault((м, поле), '%s · %s'
                                  % (st.get('_позиція'), (st.get('_пункт') or '')[:40]))
        for дом in (st.get('домен') or []) + (st.get('якщо_немає') or []):
            if isinstance(дом, list) and len(дом) == 3 and isinstance(дом[0], str):
                поле = дом[0].split('.')[0]
                пари[м].add(поле)
                де.setdefault((м, поле), '%s · %s'
                              % (st.get('_позиція'), (st.get('_пункт') or '')[:40]))

    цікаві = {м: (поля - СКРІЗЬ) for м, поля in пари.items()}
    цікаві = {м: поля for м, поля in цікаві.items() if поля}
    усього = sum(len(v) for v in цікаві.values())

    print('# Поля, які пише план — звірити з ir.model.fields')
    print()
    print('Моделей %d, пар (модель, поле) %d. Поля, що є в кожній моделі '
          '(%s), у перелік не входять.' % (len(цікаві), усього, ', '.join(sorted(СКРІЗЬ))))
    print()
    print('Скрипт у базу НЕ ХОДИТЬ: ключа API в репозиторії немає. Перелік '
          'нижче — для запиту руками.')
    print()
    for м in sorted(цікаві):
        print('%-34s %s' % (м, ', '.join(sorted(цікаві[м]))))
    print()
    print('## Звідки кожне поле — щоб знайти рецепт, коли поля в базі не виявиться')
    print()
    for (м, поле), джерело in sorted(де.items()):
        if поле in СКРІЗЬ:
            continue
        print('- `%s.%s` — %s' % (м, поле, джерело))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
