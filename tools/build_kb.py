#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Збирає docs/база-знань-блоки.md із data/price.json і data/verify.json.

Тематична база знань (`docs/база-знань-налаштувань.md`) відповідає на питання
«де в Odoo 19 це налаштовується». Цей документ відповідає на інше питання:
«що саме входить у блок прайсу, який ми продали, і де це в базі клієнта».
Порядок — прайсовий: група → позиція → рівень → пункти складу робіт слово
в слово з прайсу, під кожним пунктом — що зроблено (нота журналу) і шлях у базі.

Це матеріал, з якого збираються письмові інструкції за ролями — пункт
«наповнена база знань за налаштованими блоками» в позиції «Навчання команди»,
рівень «Стандарт». Своїх даних документ не має: правити треба джерела.

    python3 tools/build_kb.py
"""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'price.json')
VRFY = os.path.join(ROOT, 'data', 'verify.json')
OUT = os.path.join(ROOT, 'docs', 'база-знань-блоки.md')
RATE = 50

MARK = {'ok': '', 'fail': ' — **відкрито**', 'move': ' — **інша позиція**',
        'skip': ' — **у базі не перевіряється**'}
WORD = {'ok': 'налаштовано', 'fail': 'відкрито', 'move': 'переїжджає',
        'skip': 'не в базі'}

def money(v):
    s = str(int(round(v)))
    out = ''
    while len(s) > 3:
        out = ' ' + s[-3:] + out
        s = s[:-3]
    return '€' + s + out

def price(hours):
    return int(round(hours * RATE / 50.0) * 50)

def own(item, lk):
    return item['inc'] if lk == '1' else item['lv'][int(lk) - 1][4]

def main():
    groups = json.load(io.open(DATA, encoding='utf-8'))['групи']
    vrfy = json.load(io.open(VRFY, encoding='utf-8'))
    pos = vrfy.get('позиції') or {}
    out, rows = [], []
    total = dict((s, 0) for s in WORD)

    for gr in groups:
        for item in gr['items']:
            rec = pos.get(item['id'])
            if not rec:
                continue
            cnt = dict((s, 0) for s in WORD)
            for lk in ('1', '2', '3'):
                for st in ((rec.get(lk) or {}).get('пункти') or {}).values():
                    cnt[st['с']] = cnt.get(st['с'], 0) + 1
                    total[st['с']] = total.get(st['с'], 0) + 1
            rows.append((gr['g'], item, cnt))

    out.append('# База знань за блоками прайсу')
    out.append('')
    out.append('Згенеровано `python3 tools/build_kb.py` із `data/price.json` і '
               '`data/verify.json` — руками не правити, правити джерела.')
    out.append('')
    out.append('Порядок — прайсовий: група → позиція → рівень → пункти складу робіт '
               'слово в слово з прайсу. Під кожним пунктом стоїть те, що записав журнал '
               'перевірки на живій базі: що саме зроблено і де це в базі. '
               'Тематичний зріз того самого знання — `docs/база-знань-налаштувань.md`; '
               'там відповідь на питання «де в Odoo 19 це налаштовується», тут — '
               '«що входить у блок, який ми продали».')
    out.append('')
    out.append('Це матеріал для письмових інструкцій за ролями: інструкція роли '
               'складається з тих блоків, які клієнт купив, а не з усього документа. '
               'Блоків, яких у наборі клієнта немає, у його інструкції бути не повинно.')
    out.append('')
    out.append('База перевірки — `%s`. Пунктів: %d налаштовано, %d відкрито, '
               '%d переїжджає, %d у базі не перевіряється.'
               % (vrfy.get('база', '—'), total['ok'], total['fail'],
                  total['move'], total['skip']))
    out.append('')
    out.append('## Зведення по блоках')
    out.append('')
    out.append('| Блок | id | Ціна | Налаштовано | Відкрито | Не в базі |')
    out.append('|---|---|---|---|---|---|')
    for gn, item, cnt in rows:
        lo, hi = price(item['lv'][0][1]), price(item['lv'][2][1])
        out.append('| %s | `%s` | %s–%s | %d | %d | %d |'
                   % (item['n'], item['id'], money(lo), money(hi),
                      cnt['ok'], cnt['fail'], cnt['skip'] + cnt['move']))
    out.append('')

    last = None
    for gn, item, cnt in rows:
        if gn != last:
            out.append('## %s' % gn)
            out.append('')
            last = gn
        rec = pos[item['id']]
        out.append('### %s (`%s`) — %s'
                   % (item['n'], item['id'], item.get('d') or ''))
        out.append('')
        if item.get('q'):
            out.append('Питання сейла: _%s_' % item['q'])
            out.append('')
        for lk in ('1', '2', '3'):
            lv = item['lv'][int(lk) - 1]
            lrec = rec.get(lk) or {}
            head = '#### Рівень %s «%s» — %s' % (lk, lv[0], money(price(lv[1])))
            if lk != '1':
                head += ' (додається до попереднього)'
            out.append(head)
            out.append('')
            out.append('Ознака вибору: %s.' % lv[3])
            if lrec.get('дата'):
                out.append('Перевірено на базі %s.' % lrec['дата'])
            out.append('')
            pts = lrec.get('пункти') or {}
            for txt in own(item, lk):
                st = pts.get(txt)
                if not st:
                    out.append('- **%s** — у журналі перевірки цього пункту ще немає' % txt)
                    out.append('')
                    continue
                out.append('- **%s**%s' % (txt, MARK.get(st['с'], '')))
                if st.get('нота'):
                    out.append('  %s' % st['нота'])
                if st.get('де'):
                    out.append('  Де: `%s`' % st['де'])
                out.append('')
        if item.get('bounds'):
            out.append('Не входить у блок (казати клієнту вголос):')
            out.append('')
            for b in item['bounds']:
                out.append('- %s' % b)
            out.append('')

    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(out).rstrip() + '\n')
    print('OK: %s — %d блоків, %d налаштовано, %d відкрито, %d не в базі'
          % (os.path.relpath(OUT, ROOT), len(rows), total['ok'], total['fail'],
             total['skip'] + total['move']))
    return 0

if __name__ == '__main__':
    sys.exit(main())
