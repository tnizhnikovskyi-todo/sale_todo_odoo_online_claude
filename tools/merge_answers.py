#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Зливає відповіді агентів у data/questions.json.

Агенти пишуть кожен у СВІЙ файл `<тека>/<sid>.json` — спільний реєстр вони не
чіпають. Інакше 336 паралельних записів у той самий файл затирали б одне одного.
Цей скрипт зводить їх в один реєстр і рахує, скільки позицій справді закрито.

    python3 tools/merge_answers.py <тека_findings> <тека_answers>
"""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEST = os.path.join(ROOT, 'data', 'questions.json')


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    fdir, adir = sys.argv[1], sys.argv[2]
    Q = json.load(io.open(QUEST, encoding='utf-8'))
    поз = Q['позиції']
    нових_ф, нових_в, чужі = 0, 0, []

    for sid in list(поз):
        f = os.path.join(fdir, sid + '.json')
        if os.path.exists(f):
            try:
                d = json.load(io.open(f, encoding='utf-8'))
            except Exception as e:
                чужі.append('%s: findings нечитабельні (%s)' % (sid, e)); continue
            if поз[sid].get('знайдено') is None:
                нових_ф += 1
            поз[sid]['знайдено'] = d
            if поз[sid]['стан'] == 'pending':
                поз[sid]['стан'] = 'explored'
        a = os.path.join(adir, sid + '.json')
        if os.path.exists(a):
            try:
                d = json.load(io.open(a, encoding='utf-8'))
            except Exception as e:
                чужі.append('%s: answers нечитабельні (%s)' % (sid, e)); continue
            пит = d.get('питання') or []
            погані = [q for q in пит if not q.get('q') or not q.get('ставить')]
            if not пит:
                чужі.append('%s: файл відповідей без питань' % sid); continue
            if погані:
                чужі.append('%s: %d питань без формулювання або без «що ставить»' % (sid, len(погані))); continue
            if not поз[sid].get('питання'):
                нових_в += 1
            поз[sid]['питання'] = пит
            поз[sid]['стан'] = 'done'

    io.open(QUEST, 'w', encoding='utf-8').write(json.dumps(Q, ensure_ascii=False, indent=1))
    всього = len(поз)
    expl = sum(1 for r in поз.values() if r['стан'] in ('explored', 'done'))
    done = sum(1 for r in поз.values() if r['стан'] == 'done')
    пит = sum(len(r.get('питання') or []) for r in поз.values())
    print('Долито: досліджень +%d, наборів питань +%d' % (нових_ф, нових_в))
    print('Реєстр: досліджено %d/%d · питання записано %d/%d · усього питань %d'
          % (expl, всього, done, всього, пит))
    print('Звітів разом: %d із 672' % (expl + done))
    if чужі:
        print('НЕ ЗАРАХОВАНО (%d):' % len(чужі))
        for c in чужі[:20]:
            print('  •', c)
    return 0


if __name__ == '__main__':
    sys.exit(main())
