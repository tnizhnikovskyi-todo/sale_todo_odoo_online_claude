#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вшиває data/price.json і data/qualification.json у artifacts/calculator.html.

Джерело правди для прайсу — data/price.json, для чек-листа кваліфікації
(друга сторінка калькулятора) — data/qualification.json. Калькулятор публікується
як Artifact і не може підвантажувати зовнішні файли, тому дані вшиваються в HTML.

Порядок роботи:
    1. правиш data/price.json або data/qualification.json
    2. python3 tools/build_calculator.py
    3. публікуєш artifacts/calculator.html через Artifact

Скрипт перевіряє структуру перед записом і падає, якщо вона зламана:
3 рівні, зростання годин, ознаки, поля q/bounds/dep, стоп-слова периметра
(«доопрацювання», «доробка», «лише в XML», «умовні блоки», «обчислювані поля»
без застереження); у чек-листі — вид блоку, наслідки r, посилання need на
відомі позиції прайсу, пояснення при r=warn/stop.
"""
import io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'price.json')
QUAL = os.path.join(ROOT, 'data', 'qualification.json')
FORM = os.path.join(ROOT, 'data', 'client-form.json')
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
                # багатоцільова жорстка залежність друкується в КП клієнта («потребує однієї з
                # позицій»), тому службові назви модулів у її пояснення потрапити не можуть
                elif d.get('type') == 'hard' and isinstance(d.get('on'), list) and len(d['on']) > 1:
                    tech = re.findall(r'\b[a-z][a-z_.]{3,}\b', d['why'])
                    if tech:
                        errs.append('%s: пояснення багатоцільової залежності друкується в КП — '
                                    'службові назви %s звідти прибрати' % (iid, tech))
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

def check_qual(blocks, known):
    """Перевіряє чек-лист кваліфікації. known — id позицій прайсу для посилань need."""
    errs, warns = [], []
    ids = set()
    for b in blocks:
        bid = b.get('id')
        if not bid: errs.append('блок чек-листа без id'); continue
        if bid in ids: errs.append('дубль id блоку чек-листа: %s' % bid)
        ids.add(bid)
        if not b.get('назва'): errs.append('%s: блок без назви' % bid)
        if b.get('вид') not in ('питання', 'чеклист'):
            errs.append('%s: вид блоку мусить бути «питання» або «чеклист»' % bid)
            continue
        if not b.get('під'): warns.append('%s: блок без підзаголовка (під)' % bid)
        if b['вид'] == 'чеклист':
            if not b.get('пункти'): errs.append('%s: чеклист без пунктів' % bid)
            for p in b.get('пункти', []):
                if not p.get('id') or not p.get('t'):
                    errs.append('%s: пункт чек-листа без id або тексту' % bid)
                if not p.get('note'):
                    warns.append('%s/%s: пункт без пояснення, чим загрожує незакритий' % (bid, p.get('id')))
            continue
        if not b.get('питання'): errs.append('%s: блок питань без питань' % bid)
        for q in b.get('питання', []):
            qid = '%s/%s' % (bid, q.get('id'))
            if not q.get('id'): errs.append('%s: питання без id' % bid)
            if not q.get('q'): errs.append('%s: питання без формулювання' % qid)
            elif has_stop(q['q']): errs.append('%s: питання обіцяє те, що поза периметром' % qid)
            ans = q.get('a') or []
            if len(ans) < 2: errs.append('%s: у питання мусить бути щонайменше дві відповіді' % qid)
            for a in ans:
                if not a.get('t'): errs.append('%s: відповідь без формулювання' % qid)
                if a.get('r') not in ('ok', 'warn', 'stop'):
                    errs.append('%s: наслідок відповіді (r) мусить бути ok, warn або stop' % qid)
                if a.get('r') in ('warn', 'stop') and not a.get('note'):
                    errs.append('%s: відповідь «%s» без пояснення note' % (qid, a.get('r')))
                if a.get('note') and has_stop(a['note']):
                    errs.append('%s: note обіцяє те, що поза периметром: «%s»' % (qid, a['note']))
                for t in a.get('need', []) or []:
                    # need — id позиції або {on, lv}: рівень, не нижче якого її треба поставити
                    on, lv = (t.get('on'), t.get('lv')) if isinstance(t, dict) else (t, None)
                    if on not in known: errs.append('%s: need на невідому позицію %s' % (qid, on))
                    if lv is not None and lv not in (1, 2, 3):
                        errs.append('%s: need.lv мусить бути 1..3, а не %r' % (qid, lv))
            if not any(a.get('r') == 'ok' for a in ans):
                warns.append('%s: немає відповіді без наслідків — питання не розділяє лідів' % qid)
    return errs, warns

REF = re.compile(r'«([^»]+)»\s*рівня\s*(\d)')

def check_refs(text, where, pos_names, errs, warns):
    """Посилання «Назва» рівня N у «що слухати» мусить вести на живу позицію прайсу.
    Позиції перейменовують — без цієї перевірки чек-лист тихо починає називати те,
    чого в прайсі вже немає."""
    for m in REF.finditer(text or ''):
        nm, lv = m.group(1), int(m.group(2))
        if not 1 <= lv <= 3:
            errs.append('%s: посилання на рівень %d — рівнів три' % (where, lv))
        if nm in pos_names:
            continue
        hit = [n for n in pos_names if n.startswith(nm)]
        if len(hit) == 1:
            warns.append('%s: «%s» — скорочена назва позиції «%s»' % (where, nm, hit[0]))
        elif hit:
            errs.append('%s: «%s» підходить кільком позиціям: %s' % (where, nm, ', '.join(hit)))
        else:
            errs.append('%s: посилання на позицію «%s», якої в прайсі немає' % (where, nm))

def check_probes(probes, group_names, pos_names=()):
    """Перевіряє питання на глибину: ключ = назва групи прайсу, 5-7 питань, є «що слухати»."""
    errs, warns = [], []
    for grp, items in (probes or {}).items():
        if grp not in group_names:
            errs.append('глибина: невідома група «%s» (ключ мусить збігатися з назвою групи в прайсі)' % grp)
            continue
        if not isinstance(items, list) or not items:
            errs.append('глибина/%s: порожній список питань' % grp); continue
        if not (8 <= len(items) <= 14):
            warns.append('глибина/%s: %d питань, а треба 8-14' % (grp, len(items)))
        ids = set()
        for it in items:
            pid = '%s/%s' % (grp, it.get('id'))
            if not it.get('id'): errs.append('глибина/%s: питання без id' % grp)
            elif it['id'] in ids: errs.append('глибина: дубль id %s' % pid)
            else: ids.add(it['id'])
            if not it.get('q'): errs.append('глибина/%s: питання без формулювання' % pid)
            elif has_stop(it['q']): errs.append('глибина/%s: питання обіцяє те, що поза периметром' % pid)
            if not it.get('hear'): errs.append('глибина/%s: немає «що слухати» (hear)' % pid)
            elif has_stop(it['hear']): errs.append('глибина/%s: «що слухати» обіцяє те, що поза периметром' % pid)
            else: check_refs(it['hear'], 'глибина/%s' % pid, pos_names, errs, warns)
    missing = [g for g in group_names if g not in (probes or {})]
    for g in missing: warns.append('глибина: для групи «%s» питань немає' % g)
    return errs, warns

def check_form(form, known):
    """Перевіряє анкету клієнта: типи полів, унікальність id, посилання на позиції прайсу.

    Аудиторія анкети — клієнт, тому окремо ловимо внутрішню лексику: рівнів, цін,
    «стопів» і слова «контур» у питаннях до клієнта бути не має.
    """
    errs, warns = [], []
    INNER = ['рівень', 'рівня', 'стоп-', 'наш контур', 'прайс', 'маржа', '€', 'дискваліф']
    TYPES = ('текст', 'абзац', 'вибір')
    seen = set()
    if not form.get('вступ'): warns.append('анкета: немає вступу для клієнта')

    def fields(where, items):
        for f in items:
            fid = '%s/%s' % (where, f.get('id'))
            if not f.get('id'): errs.append('%s: поле без id' % where)
            elif fid in seen: errs.append('анкета: дубль поля %s' % fid)
            else: seen.add(fid)
            if not f.get('q'): errs.append('%s: поле без питання' % fid)
            elif has_stop(f['q']): errs.append('%s: питання обіцяє те, що поза периметром' % fid)
            else:
                low = f['q'].lower()
                for w in INNER:
                    if w in low: errs.append('%s: у питанні до клієнта внутрішня лексика «%s»' % (fid, w))
            if f.get('тип') not in TYPES:
                errs.append('%s: тип мусить бути %s' % (fid, ' / '.join(TYPES)))
            if f.get('тип') == 'вибір' and len(f.get('опції') or []) < 2:
                errs.append('%s: у полі-виборі мусить бути щонайменше дві опції' % fid)
            if f.get('тип') != 'вибір' and f.get('опції'):
                errs.append('%s: опції має тільки поле-вибір' % fid)

    secs = (form.get('розділи') or []) + (form.get('розділи2') or [])
    if not secs: errs.append('анкета: немає постійних розділів')
    for sec in secs:
        if not sec.get('id') or not sec.get('назва'):
            errs.append('анкета: розділ без id або назви'); continue
        if not sec.get('поля'): errs.append('анкета/%s: розділ без полів' % sec['id'])
        fields(sec['id'], sec.get('поля') or [])
    procs = form.get('процеси') or []
    if not procs: errs.append('анкета: немає блоків процесів')
    for pr in procs:
        pid = pr.get('id')
        if not pid or not pr.get('назва'):
            errs.append('анкета: процес без id або назви'); continue
        if not pr.get('питання'): errs.append('анкета/%s: процес без питань' % pid)
        for t in pr.get('позиції') or []:
            if t not in known: errs.append('анкета/%s: посилання на невідому позицію прайсу %s' % (pid, t))
        if not pr.get('позиції'): warns.append('анкета/%s: процес не зіставлений із позиціями прайсу' % pid)
        fields(pid, pr.get('питання') or [])
    return errs, warns

def inject(html, name, value):
    """Замінює тіло `var NAME = …;` у HTML на value, зберігаючи відступ рядка."""
    a = html.index('var ' + name + ' = ')
    body = a + len('var ' + name + ' = ')
    depth, i, n = 0, body, len(html)
    while i < n:                      # шукаємо кінець літерала за балансом дужок
        c = html[i]
        if c in '[{': depth += 1
        elif c in ']}':
            depth -= 1
            if depth == 0: i += 1; break
        i += 1
    end = html.index(';', i)
    line = html.rindex('\n', 0, a) + 1
    indent = html[line:a]
    block = indent + 'var ' + name + ' = ' + json.dumps(
        value, ensure_ascii=False, indent=2).replace('\n', '\n' + indent)
    return html[:line] + block + html[end:]

def main():
    payload = json.load(io.open(DATA, encoding='utf-8'))
    groups = payload['групи']
    errs, warns = check(groups)
    known = set(it.get('id') for gr in groups for it in gr.get('items', []))
    qpayload = json.load(io.open(QUAL, encoding='utf-8'))
    qual = qpayload['блоки']
    probes = qpayload.get('глибина') or {}
    qe, qw = check_qual(qual, known)
    errs += qe; warns += qw
    pe, pw = check_probes(probes, [g['g'] for g in groups],
                          [it['n'] for g in groups for it in g['items']])
    errs += pe; warns += pw
    formdata = json.load(io.open(FORM, encoding='utf-8'))
    fe, fw = check_form(formdata, known)
    errs += fe; warns += fw
    for w in warns: print('  ⚠', w)
    if errs:
        print('СТРУКТУРА ЗЛАМАНА, збірку скасовано:')
        for e in errs: print('  •', e)
        return 1

    html = io.open(HTML, encoding='utf-8').read()
    html = inject(html, 'GROUPS', groups)
    html = inject(html, 'QUAL', qual)
    html = inject(html, 'PROBES', probes)
    html = inject(html, 'FORM', formdata)
    io.open(HTML, 'w', encoding='utf-8').write(html)

    pos = sum(len(g['items']) for g in groups)
    pts = sum(len(it['inc']) + sum(len(it['lv'][k][4]) for k in (1, 2))
              for g in groups for it in g['items'])
    bnd = sum(len(it.get('bounds', [])) for g in groups for it in g['items'])
    dps = sum(len(it.get('dep', [])) for g in groups for it in g['items'])
    qq = sum(len(b.get('питання', [])) for b in qual)
    qp = sum(len(b.get('пункти', [])) for b in qual)
    print('OK: %d груп, %d позицій, %d пунктів складу, %d рядків «не входить», %d залежностей вшито в calculator.html' % (len(groups), pos, pts, bnd, dps))
    pr = sum(len(v) for v in probes.values())
    print('    чек-лист кваліфікації: %d блоків, %d питань скринінгу, %d пунктів готовності, %d питань на глибину' % (len(qual), qq, qp, pr))
    fq = (sum(len(x.get('поля') or []) for x in (formdata.get('розділи') or []) + (formdata.get('розділи2') or []))
          + sum(len(x.get('питання') or []) for x in formdata.get('процеси') or []))
    print('    анкета клієнта: %d розділів, %d блоків процесів, %d полів' % (
        len((formdata.get('розділи') or []) + (formdata.get('розділи2') or [])),
        len(formdata.get('процеси') or []), fq))
    return 0

if __name__ == '__main__':
    sys.exit(main())
