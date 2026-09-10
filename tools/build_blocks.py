#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Збирає artifacts/blocks.html — артефакт «Будова блоків».

ОКРЕМИЙ КОНТУР. Прайс, чек-лист, анкету клієнта й калькулятор не чіпає.

Джерела:
    data/blocks.json     граф залежностей і каталог налаштувань (знімок, не правиться руками)
    data/questions.json  четвертий ярус: питання до кожного налаштування (пишуть агенти)
    tools/blocks_template.html  розмітка

    python3 tools/build_blocks.py
"""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCKS = os.path.join(ROOT, 'data', 'blocks.json')
QUEST = os.path.join(ROOT, 'data', 'questions.json')
TPL = os.path.join(ROOT, 'tools', 'blocks_template.html')
OUT = os.path.join(ROOT, 'artifacts', 'blocks.html')

ЗАГОЛОВКИ = {'0': 'Фундамент', '1': 'Після фундаменту', '2': 'Після продажів',
             '3': 'Після робіт', '4': 'Збирачі'}


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def побудувати_svg(GR):
    N, E = GR['вузли'], GR['ребра']
    W, H, ШИР, ВИС = GR['W'], GR['H'], GR['ШИР'], GR['ВИС']

    def шлях(a, b):
        ax, ay = N[a]['x'], N[a]['y'] + ВИС / 2
        bx, by = N[b]['x'], N[b]['y'] + ВИС / 2
        if bx > ax:
            x1, x2 = ax + ШИР, bx
            d = max(28, (x2 - x1) * 0.45)
            return f'M{x1:.0f},{ay:.0f} C{x1+d:.0f},{ay:.0f} {x2-d:.0f},{by:.0f} {x2:.0f},{by:.0f}'
        if bx < ax:
            x1, x2 = ax, bx + ШИР
            d = max(28, (x1 - x2) * 0.45)
            return f'M{x1:.0f},{ay:.0f} C{x1-d:.0f},{ay:.0f} {x2+d:.0f},{by:.0f} {x2:.0f},{by:.0f}'
        x1, d = ax + ШИР, 46
        return f'M{x1:.0f},{ay:.0f} C{x1+d:.0f},{ay:.0f} {x1+d:.0f},{by:.0f} {x1:.0f},{by:.0f}'

    ч = []
    for k in sorted(ЗАГОЛОВКИ):
        if k not in GR['смуги']:
            continue
        x = N[GR['смуги'][k][0]]['x']
        ч.append(f'<text class="band" x="{x}" y="26">{esc(ЗАГОЛОВКИ[k].upper())}</text>')
        if k == '4':
            ч.append(f'<line class="split" x1="{x-30}" y1="14" x2="{x-30}" y2="{H-10}"/>')
    for e in sorted(E, key=lambda e: 0 if e['t'] == 'soft' else 1):
        cls = 'e ' + e['t'] + (' one' if e.get('одне') else '')
        mk = ' marker-end="url(#ar)"' if e['t'] == 'hard' else ''
        ч.append(f'<path class="{cls}" data-a="{e["a"]}" data-b="{e["b"]}" d="{шлях(e["a"], e["b"])}"{mk}/>')
    for pid, n in N.items():
        x, y = n['x'], n['y']
        хр = ' spine' if n['вхід'] >= 3 else ''
        ч.append(f'<g class="n{хр}" data-id="{pid}" tabindex="0" role="button" aria-label="{esc(n["n"])}">')
        ч.append(f'<rect x="{x}" y="{y}" width="{ШИР}" height="{ВИС}" rx="3"/>')
        if n['збирач']:
            всього = sum(c['n'] for c in n['збирач'])
            ч.append(f'<text class="badge" x="{x+ШИР-9}" y="{y+ВИС/2+4}" text-anchor="end">×{всього}</text>')
        elif n['вхід'] >= 2:
            ч.append(f'<text class="badge" x="{x+ШИР-9}" y="{y+ВИС/2+4}" text-anchor="end">{n["вхід"]}</text>')
        ч.append(f'<text class="lbl" x="{x+10}" y="{y+ВИС/2+4}">{esc(n["n"])}</text></g>')
    return ('<svg viewBox="0 0 %d %d" role="img" preserveAspectRatio="xMidYMid meet"\n'
            '   aria-label="Граф залежностей 25 блоків: жорсткі звʼязки утворюють смуги зліва направо; '
            'Рахунки та оплати, Склад і Продажі тримають більшість решти">\n'
            '  <defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0,1 L7,4 L0,7 z" fill="currentColor"/></marker></defs>\n'
            '  %s\n</svg>') % (W, H, '\n  '.join(ч))


def перевірити(CA, Q):
    """Кожне налаштування каталогу мусить мати запис у реєстрі питань, і навпаки."""
    errs = []
    у_каталозі = {p['sid'] for b in CA['блоки'].values() for p in b['пункти'] if p.get('sid')}
    без_sid = sum(1 for b in CA['блоки'].values() for p in b['пункти'] if not p.get('sid'))
    if без_sid:
        errs.append('у каталозі %d налаштувань без sid' % без_sid)
    у_реєстрі = set(Q['позиції'])
    if у_каталозі - у_реєстрі:
        errs.append('немає в реєстрі питань: %s' % sorted(у_каталозі - у_реєстрі)[:5])
    if у_реєстрі - у_каталозі:
        errs.append('у реєстрі є зайві: %s' % sorted(у_реєстрі - у_каталозі)[:5])
    for sid, r in Q['позиції'].items():
        if r['стан'] == 'done' and not r.get('питання'):
            errs.append('%s: стан done, але питань немає' % sid)
        for q in r.get('питання') or []:
            if not q.get('q') or not q.get('ставить'):
                errs.append('%s: питання без формулювання або без «що ставить»' % sid)
    return errs


def main():
    D = json.load(io.open(BLOCKS, encoding='utf-8'))
    CA, GR = D['каталог'], D['граф']
    Q = json.load(io.open(QUEST, encoding='utf-8'))

    errs = перевірити(CA, Q)
    if errs:
        print('СТРУКТУРА ЗЛАМАНА, збірку скасовано:')
        for e in errs:
            print('  •', e)
        return 1

    html = io.open(TPL, encoding='utf-8').read()
    html = (html.replace('__SVG__', побудувати_svg(GR))
                .replace('__GRAPH__', json.dumps(GR, ensure_ascii=False, separators=(',', ':')))
                .replace('__CAT__', json.dumps(CA, ensure_ascii=False, separators=(',', ':')))
                .replace('__Q__', json.dumps(Q['позиції'], ensure_ascii=False, separators=(',', ':'))))
    io.open(OUT, 'w', encoding='utf-8').write(html)

    всього = len(Q['позиції'])
    done = sum(1 for r in Q['позиції'].values() if r['стан'] == 'done')
    expl = sum(1 for r in Q['позиції'].values() if r['стан'] in ('explored', 'done'))
    пит = sum(len(r.get('питання') or []) for r in Q['позиції'].values())
    print('Зібрано: %d блоків · %d налаштувань · %d питань' % (len(CA['блоки']), всього, пит))
    print('Реєстр: досліджено %d/%d · записано питань %d/%d' % (expl, всього, done, всього))
    return 0


if __name__ == '__main__':
    sys.exit(main())
