#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Збирає docs/звірка-бази-2026-09-09.md із data/verify.json.

Журнал звірки: по кожному пункту прайсу — що саме дивились у базі й що знайшли.
Свого змісту документ не має, це проєкція шару «звірка» з журналу перевірки.

    python3 tools/build_audit.py
"""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'price.json')
VRFY = os.path.join(ROOT, 'data', 'verify.json')
OUT = os.path.join(ROOT, 'docs', 'звірка-бази-2026-09-09.md')

def main():
    groups = json.load(io.open(DATA, encoding='utf-8'))['групи']
    vrfy = json.load(io.open(VRFY, encoding='utf-8'))
    pos = vrfy.get('позиції') or {}
    out, tot, yes = [], 0, 0
    rows = []

    for gr in groups:
        for item in gr['items']:
            rec = pos.get(item['id'])
            if not rec:
                continue
            y = n = 0
            for lk in ('1', '2', '3'):
                for st in ((rec.get(lk) or {}).get('пункти') or {}).values():
                    z = st.get('звірка')
                    if not z:
                        continue
                    n += 1
                    if z.get('є'):
                        y += 1
            rows.append((gr['g'], item, y, n))
            tot += n
            yes += y

    out.append('# Звірка з базою: що з записаного справді є в `%s`' % vrfy.get('база', '?'))
    out.append('')
    out.append('Згенеровано `python3 tools/build_audit.py` із `data/verify.json` — руками не правити.')
    out.append('')
    out.append('Порядок роботи був такий: беремо пункт прайсу, читаємо в журналі перевірки, що по ньому '
               'було зроблено і де це має бути, і йдемо в базу дивитися саме на це. У рядку пункту '
               'записано **що дивились** і **що знайшли** — без домислів: якщо артефакту немає, так і '
               'написано.')
    out.append('')
    out.append('Результат: **%d із %d пунктів знайдено в базі, %d немає**.' % (yes, tot, tot - yes))
    out.append('')
    out.append('«Немає» не означає «не працює». Це одна з трьох речей: послуга або документ, яких у базі '
               'не буває взагалі (сесія, інструкція, виїзд); перевірка механізму на іншій моделі, а не '
               'артефакт під цю позицію (подання, кнопка); або те, чого в цій демо-базі просто не '
               'заводили (бюджети, відпустки, рамкові договори).')
    out.append('')
    out.append('## Зведення по блоках')
    out.append('')
    out.append('| Блок | id | Є в базі | Немає |')
    out.append('|---|---|---|---|')
    for gn, item, y, n in rows:
        out.append('| %s | `%s` | %d / %d | %d |' % (item['n'], item['id'], y, n, n - y))
    out.append('')

    last = None
    for gn, item, y, n in rows:
        if gn != last:
            out.append('## %s' % gn)
            out.append('')
            last = gn
        out.append('### %s (`%s`) — знайдено %d із %d' % (item['n'], item['id'], y, n))
        out.append('')
        rec = pos[item['id']]
        for lk in ('1', '2', '3'):
            lrec = rec.get(lk) or {}
            pts = lrec.get('пункти') or {}
            if not pts:
                continue
            out.append('**Рівень %s «%s»**' % (lk, item['lv'][int(lk) - 1][0]))
            out.append('')
            for txt, st in pts.items():
                z = st.get('звірка')
                if not z:
                    out.append('- %s — звірку не робили' % txt)
                    continue
                mark = 'Є' if z.get('є') else 'НЕМАЄ'
                out.append('- **%s** — %s' % (txt, mark))
                out.append('  - дивились: %s' % z.get('дивились'))
                out.append('  - знайшли: %s' % z.get('знайшли'))
            out.append('')

    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(out).rstrip() + '\n')
    print('OK: %s — %d пунктів, %d знайдено, %d немає'
          % (os.path.relpath(OUT, ROOT), tot, yes, tot - yes))
    return 0

if __name__ == '__main__':
    sys.exit(main())
