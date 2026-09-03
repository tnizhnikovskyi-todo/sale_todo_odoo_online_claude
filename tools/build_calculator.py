#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вшиває data/price.json у artifacts/calculator.html.

Джерело правди для прайсу — data/price.json. Калькулятор публікується як
Artifact і не може підвантажувати зовнішні файли, тому дані вшиваються в HTML.

Порядок роботи:
    1. правиш data/price.json
    2. python3 tools/build_calculator.py
    3. публікуєш artifacts/calculator.html через Artifact

Скрипт перевіряє структуру перед записом і падає, якщо вона зламана:
3 рівні, зростання годин, ознаки, поля q/bounds/dep, стоп-слова периметра
(«доопрацювання», «доробка», «лише в XML», «умовні блоки», «обчислювані поля»
без застереження).
"""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'price.json')
HTML = os.path.join(ROOT, 'artifacts', 'calculator.html')

STOP = ['доопрацюван', 'доробк', 'лише в XML', 'умовні блоки', 'обчислювані поля']
NEG = ['немає', 'не робимо', 'поза периметром', 'замість']

def has_stop(text):
    t = text.lower()
    return any(w in t for w in STOP) and not any(n in t for n in NEG)

def check(groups):
    errs, warns = [], []
    ids = set()
    allitems = [it for gr in groups for it in gr.get('items', [])]
    known = set(it.get('id') for it in allitems)
    home = {}
    for it in allitems:
        for mod in it.get('home', []) or []:
            home[mod] = it.get('id')
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
                elif has_stop(sig):
                    errs.append('%s рівень %d: ознака обіцяє те, що поза периметром: «%s»' % (iid, i+1, sig))
                if i == 0 and add:
                    errs.append('%s: у першого рівня список доданих мусить бути порожнім' % iid)
                for t in add:
                    if has_stop(t):
                        errs.append('%s рівень %d: пункт поза периметром без застереження: «%s»' % (iid, i+1, t))
            for t in it.get('inc', []):
                if has_stop(t):
                    errs.append('%s: базовий пункт поза периметром без застереження: «%s»' % (iid, t))
            hrs = [l[1] for l in lv]
            if hrs != sorted(hrs):
                errs.append('%s: години не зростають за рівнями: %s' % (iid, hrs))
            # нові поля
            if not it.get('q'): warns.append('%s: немає питання сейла (q)' % iid)
            if not it.get('bounds'): warns.append('%s: немає переліку «не входить» (bounds)' % iid)
            for d in it.get('dep', []) or []:
                ons = d.get('on') if isinstance(d.get('on'), list) else [d.get('on')]
                for t in ons:
                    if t not in known: errs.append('%s: dep на невідому позицію %s' % (iid, t))
                    if t == iid: errs.append('%s: dep на саму себе' % iid)
                if d.get('type') not in ('hard', 'soft'):
                    errs.append('%s: dep.type мусить бути hard або soft' % iid)
                if d.get('from_lv', 1) not in (1, 2, 3) or d.get('min_lv', 1) not in (1, 2, 3):
                    errs.append('%s: dep.from_lv / min_lv мусять бути 1..3' % iid)
                if not d.get('why'): errs.append('%s: dep без пояснення why' % iid)
            # тягнеш чужий модуль — мусиш мати dep на його власника (попередження)
            deps_to = set()
            for d in it.get('dep', []) or []:
                for t in (d['on'] if isinstance(d['on'], list) else [d['on']]): deps_to.add(t)
            for lvk, mods in (it.get('apps') or {}).items():
                for mod in mods:
                    owner = home.get(mod)
                    if owner and owner != iid and owner != 'base' and owner not in deps_to:
                        warns.append('%s: тягне %s (власник — %s), але dep на %s немає' % (iid, mod, owner, owner))
    return errs, warns

def main():
    payload = json.load(io.open(DATA, encoding='utf-8'))
    groups = payload['групи']
    errs, warns = check(groups)
    for w in warns: print('  ⚠', w)
    if errs:
        print('СТРУКТУРА ЗЛАМАНА, збірку скасовано:')
        for e in errs: print('  •', e)
        return 1

    html = io.open(HTML, encoding='utf-8').read()
    marker = '  var GROUPS = '
    a = html.index(marker)
    b = html.index(';\n\n  var MODS = [], BYID = {};')
    block = marker + json.dumps(groups, ensure_ascii=False, indent=2).replace('\n', '\n  ')
    html = html[:a] + block + html[b:]
    io.open(HTML, 'w', encoding='utf-8').write(html)

    pos = sum(len(g['items']) for g in groups)
    pts = sum(len(it['inc']) + sum(len(it['lv'][k][4]) for k in (1, 2))
              for g in groups for it in g['items'])
    bnd = sum(len(it.get('bounds', [])) for g in groups for it in g['items'])
    dps = sum(len(it.get('dep', [])) for g in groups for it in g['items'])
    print('OK: %d груп, %d позицій, %d пунктів складу, %d рядків «не входить», %d залежностей вшито в calculator.html' % (len(groups), pos, pts, bnd, dps))
    return 0

if __name__ == '__main__':
    sys.exit(main())
