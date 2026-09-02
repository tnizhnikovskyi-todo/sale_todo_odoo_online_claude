#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Перевірка залежностей між позиціями прайсу.

Читає data/price.json (як build_calculator.py) і поля apps/home/dep/mult —
або вже вшиті в позиції, або з окремого фрагмента (аргумент 2, для проби).
Друкує помилки (збірку треба скасувати), попередження (ознаки поганого
скоупінгу) і закриття кількох контрольних наборів із цінами.
"""
import io, json, sys

RATE = 50
def price(it, lv_idx):                       # так само, як у калькуляторі
    return round(it['lv'][lv_idx][1] * RATE / 50) * 50

def load(price_path, frag_path=None):
    payload = json.load(io.open(price_path, encoding='utf-8'))
    items = {it['id']: it for g in payload['групи'] for it in g['items']}
    if frag_path:
        frag = json.load(io.open(frag_path, encoding='utf-8'))['позиції']
        for iid, extra in frag.items():
            if iid not in items:
                raise SystemExit('фрагмент посилається на невідому позицію: %s' % iid)
            items[iid].update(extra)
    return items

def as_list(x):
    return x if isinstance(x, list) else [x]

def check_deps(items):
    errs, warns = [], []
    roots = {iid for iid, it in items.items() if it.get('req')}
    home_of = {}
    for iid, it in items.items():
        for m in it.get('home', []):
            if m in home_of:
                errs.append('модуль %s є home одразу у %s і %s' % (m, home_of[m], iid))
            home_of[m] = iid
    for iid, it in items.items():
        apps = it.get('apps', {})
        deps = it.get('dep', [])
        if not isinstance(apps, dict) or set(apps) - {'1', '2', '3'}:
            errs.append('%s: apps мусить бути об’єктом з ключами "1","2","3"' % iid)
            apps = {}
        for d in deps:
            ons = as_list(d.get('on'))
            for o in ons:
                if o not in items: errs.append('%s: dep на невідому позицію %s' % (iid, o))
                if o == iid: errs.append('%s: залежність від самої себе' % iid)
                if o in roots: errs.append('%s: залежність від обов’язкової %s зайва — вона неявна' % (iid, o))
            if d.get('type') not in ('hard', 'soft'):
                errs.append('%s → %s: type мусить бути hard або soft' % (iid, ons))
            if d.get('from_lv') not in (1, 2, 3):
                errs.append('%s → %s: from_lv мусить бути 1..3' % (iid, ons))
            if d.get('min_lv', 1) not in (1, 2, 3):
                errs.append('%s → %s: min_lv мусить бути 1..3' % (iid, ons))
            if not d.get('why'):
                errs.append('%s → %s: порожнє why' % (iid, ons))
            if len(ons) > 1 and d.get('type') == 'hard':
                warns.append('%s → %s: hard-залежність «одна з» — калькулятор не додасть сам, лише зупинить із підказкою' % (iid, ons))
            # сигнал завищення: примусова позиція дорожча за ту, що її тягне
            if d.get('type') == 'hard' and len(ons) == 1 and ons[0] in items:
                tgt = items[ons[0]]
                if price(tgt, d.get('min_lv', 1) - 1) > price(it, d['from_lv'] - 1):
                    warns.append('%s (рівень %d, €%d) тягне %s рівня %d за €%d — примусова позиція дорожча за саму позицію'
                                 % (iid, d['from_lv'], price(it, d['from_lv'] - 1), ons[0], d.get('min_lv', 1), price(tgt, d.get('min_lv', 1) - 1)))
        # apps → home: усе, що позиція тягне, або її власне, або має dep
        for lv, mods in apps.items():
            for m in mods:
                owner = home_of.get(m)
                if not owner or owner == iid: continue
                if owner in roots:
                    continue
                if iid in roots:
                    warns.append('база тягне %s — домашній модуль позиції %s: дубль роботи між Базою і %s' % (m, owner, owner))
                    continue
                ok = any(owner in as_list(d.get('on')) and d.get('from_lv', 9) <= int(lv) for d in deps)
                if not ok:
                    errs.append('%s тягне модуль %s (домашній для %s) з рівня %s, а dep на %s немає або починається пізніше' % (iid, m, owner, lv, owner))
    # цикли жорстких залежностей — не помилка, а ознака кривого скоупінгу
    hard = {iid: {o for d in it.get('dep', []) if d.get('type') == 'hard' for o in as_list(d.get('on')) if len(as_list(d.get('on'))) == 1}
            for iid, it in items.items()}
    for a in hard:
        for b in hard[a]:
            if a in hard.get(b, set()):
                warns.append('взаємна жорстка залежність %s ↔ %s — ознака, що пункт треба перенести в одну з позицій' % (a, b))
    return errs, sorted(set(warns))

def resolve(items, sel):
    """sel: {id: lv_idx 0..2}. Повертає (sel_після, автододані, зауваження)."""
    sel = dict(sel)
    for iid, it in items.items():
        if it.get('req') and iid not in sel: sel[iid] = 0
    auto, notes = {}, []
    changed = True
    while changed:
        changed = False
        for iid, lv in list(sel.items()):
            for d in items[iid].get('dep', []):
                if d['from_lv'] - 1 > lv: continue
                ons = as_list(d['on']); need = d.get('min_lv', 1) - 1
                have = [o for o in ons if o in sel]
                if d['type'] == 'hard':
                    if not have:
                        if len(ons) == 1:
                            sel[ons[0]] = need; auto[ons[0]] = '%s: %s' % (items[iid]['n'], d['why']); changed = True
                        else:
                            notes.append('СТОП %s: потрібна одна з %s — %s' % (items[iid]['n'], ons, d['why']))
                    else:
                        for o in have:
                            if sel[o] < need:
                                sel[o] = need; changed = True
                                notes.append('рівень %s піднято до %d через %s' % (items[o]['n'], need + 1, items[iid]['n']))
                elif not have:
                    notes.append('УВАГА %s без %s — %s' % (items[iid]['n'], '/'.join(items[o]['n'] for o in ons) if len(ons) <= 3 else 'позиції з даними', d['why']))
    return sel, auto, sorted(set(notes))

def total(items, sel):
    return sum(price(items[i], lv) for i, lv in sel.items())

def main():
    price_path = sys.argv[1] if len(sys.argv) > 1 else 'data/price.json'
    frag = sys.argv[2] if len(sys.argv) > 2 else None
    items = load(price_path, frag)
    errs, warns = check_deps(items)
    print('ПОМИЛКИ: %d' % len(errs))
    for e in errs: print('  •', e)
    print('ПОПЕРЕДЖЕННЯ: %d' % len(warns))
    for w in warns: print('  •', w)
    demos = {
        'Каса, рівень Стандарт': {'pos': 1},
        'Оренда, рівень Стандарт': {'rnt': 1},
        'Підписки, рівень Базовий': {'sub': 0},
        'Виробництво, рівень Базовий': {'mrp': 0},
        'Інтернет-магазин, рівень Базовий': {'shop': 0},
        'Виїзні роботи, рівень Розширений': {'fsm': 2},
        'Проєкти, рівень Стандарт': {'prj': 1},
        'Сайт, рівень Базовий': {'web': 0},
        'Склад, рівень Стандарт': {'stk': 1},
        'Мультикомпанійність, рівень 3 + Управлінський облік рівень 1': {'mco': 2, 'acc': 0},
        'Планування, рівень Стандарт': {'pln': 1},
        'Торгівля: База+CRM+Продажі+Закупівлі+Склад(2)+Облік(2)+Бланки': {'crm': 1, 'sal': 1, 'pur': 1, 'stk': 1, 'acc': 1, 'prt': 1},
    }
    print('\nКОНТРОЛЬНІ НАБОРИ (ціна до → після закриття залежностей)')
    for name, sel in demos.items():
        base_sel = dict(sel); 
        for iid, it in items.items():
            if it.get('req'): base_sel.setdefault(iid, 0)
        after, auto, notes = resolve(items, sel)
        print('\n%s: €%d → €%d' % (name, total(items, base_sel), total(items, after)))
        for k, v in auto.items(): print('   + додано %s (рівень %d) ← %s' % (items[k]['n'], after[k] + 1, v))
        for n in notes: print('   ', n)
    return 1 if errs else 0

if __name__ == '__main__':
    sys.exit(main())
