#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вшиває data/price.json у artifacts/calculator.html.

Джерело правди для прайсу — data/price.json. Калькулятор публікується як
Artifact і не може підвантажувати зовнішні файли, тому дані вшиваються в HTML.

Порядок роботи:
    1. правиш data/price.json
    2. python3 tools/build_calculator.py
    3. публікуєш artifacts/calculator.html через Artifact

Скрипт перевіряє структуру перед записом і падає, якщо вона зламана.
"""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'price.json')
HTML = os.path.join(ROOT, 'artifacts', 'calculator.html')

def check(groups):
    errs = []
    ids = set()
    for gr in groups:
        if not gr.get('g') or not isinstance(gr.get('items'), list):
            errs.append('група без назви або без items'); continue
        for it in gr['items']:
            iid = it.get('id')
            if not iid: errs.append('позиція без id у групі %s' % gr['g']); continue
            if iid in ids: errs.append('дубль id: %s' % iid)
            ids.add(iid)
            if len(it.get('inc', [])) < 1:
                errs.append('%s: порожній inc' % iid)
            lv = it.get('lv', [])
            if len(lv) != 3:
                errs.append('%s: має бути рівно 3 рівні, а не %d' % (iid, len(lv)))
                continue
            for i, l in enumerate(lv):
                if len(l) != 5:
                    errs.append('%s рівень %d: очікується 5 елементів [назва, години, економія, ознака, додані]' % (iid, i+1))
                    continue
                name, hours, sav, sig, add = l
                if not isinstance(hours, int) or hours <= 0:
                    errs.append('%s рівень %d: години мусять бути додатнім цілим' % (iid, i+1))
                if not (0 <= sav <= 90):
                    errs.append('%s рівень %d: економія поза межами 0..90' % (iid, i+1))
                if not sig:
                    errs.append('%s рівень %d: немає ознаки для вибору' % (iid, i+1))
                if i == 0 and add:
                    errs.append('%s: у першого рівня список доданих мусить бути порожнім' % iid)
            hrs = [l[1] for l in lv]
            if hrs != sorted(hrs):
                errs.append('%s: години не зростають за рівнями: %s' % (iid, hrs))
    return errs

def main():
    payload = json.load(io.open(DATA, encoding='utf-8'))
    groups = payload['групи']
    errs = check(groups)
    if errs:
        print('СТРУКТУРА ЗЛАМАНА, збірку скасовано:')
        for e in errs: print('  •', e)
        return 1

    html = io.open(HTML, encoding='utf-8').read()
    # межі блоку даних шукаємо стійко: від 'var GROUPS = ' до ';' перед 'var MODS'
    a = html.index('var GROUPS = ')
    m = html.index('var MODS', a)
    end = html.rindex(';', a, m)          # ';' що закриває масив
    indent = html[html.rindex('\n', 0, a) + 1:a]
    block = indent + 'var GROUPS = ' + json.dumps(
        groups, ensure_ascii=False, indent=2).replace('\n', '\n' + indent)
    html = html[:html.rindex('\n', 0, a) + 1] + block + html[end:]
    io.open(HTML, 'w', encoding='utf-8').write(html)

    pos = sum(len(g['items']) for g in groups)
    pts = sum(len(it['inc']) + sum(len(it['lv'][k][4]) for k in (1, 2))
              for g in groups for it in g['items'])
    print('OK: %d груп, %d позицій, %d пунктів складу вшито в calculator.html' % (len(groups), pos, pts))
    return 0

if __name__ == '__main__':
    sys.exit(main())
