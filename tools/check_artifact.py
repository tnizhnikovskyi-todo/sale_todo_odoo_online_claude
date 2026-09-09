# -*- coding: utf-8 -*-
"""Звірка опублікованого артефакту з репозиторієм.

Навіщо. Калькулятор правлять **з двох боків**: тут через `data/*.json` і збірку, а
також прямо на сторінці артефакту. Тому опублікована версія може бути новішою за
репозиторій — і навпаки. Досі це звірялося очима: прочитати артефакт, знайти `var
GROUPS`, подивитися. На 690 КБ такий спосіб знаходить хіба що зникнення цілого блоку.

Скрипт звіряє **дані й код окремо**, бо це різні поломки з різними наслідками:

* **Дані** — пʼять вшитих блоків (`GROUPS`, `QUAL`, `PROBES`, `FORM`, `VERIFY`) —
  порівнюються з джерелами правди (`data/*.json`), а не з HTML у репозиторії.
  Так одна перевірка ловить обидві біди: «на сторінці правили прайс, а в репозиторій
  не перенесли» і «прайс правили тут, а сторінку не перепублікували».
* **Код** — усе, що поза блоками даних: розмітка, стилі, JS. Тут будь-яка різниця
  означає, що сторінку правили в артефакті, і ця правка **зникне при наступній
  публікації з репозиторію**.

Порівняння даних — за розібраним JSON, а не за текстом: відступи, порядок ключів і
екранування нічого не значать, значить лише зміст.

Запуск:

    python3 tools/check_artifact.py <файл-артефакту.html>

Файл артефакту беруть із результату `Artifact` (`action: "read"`) — інструмент
зберігає повний HTML на диск і друкує шлях. Скрипт сам відрізає обгортку, яку
додає публікація (doctype, head зі скиданням стилів).

Коди: 0 — усе збігається; 1 — є різниця; 2 — файл не заданий або не читається.
"""

import io
import json
import os
import re
import sys

BLOCKS = [
    # (імʼя блоку в HTML, файл-джерело, ключ усередині файлу або None = весь файл)
    ('GROUPS', 'data/price.json', 'групи'),
    ('QUAL', 'data/qualification.json', 'блоки'),
    ('PROBES', 'data/qualification.json', 'глибина'),
    ('FORM', 'data/client-form.json', None),
    ('VERIFY', 'data/verify.json', None),
]
REPO_HTML = 'artifacts/calculator.html'


def plural(n, one, few, many):
    """«1 місце», «2 місця», «5 місць» — інакше звіт читається як машинний переклад."""
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def human(path, groups):
    """До адреси на кшталт GROUPS[1].items[0].lv[0][1] додає людську підказку.

    Адреса потрібна, щоб знайти місце в JSON; назва — щоб зрозуміти, про що йдеться,
    не відкриваючи файл. Без цього звіт про розбіжність доводиться розшифровувати.
    """
    m = re.match(r'GROUPS\[(\d+)\](?:\.items\[(\d+)\])?', path)
    if not m:
        return path
    try:
        gr = groups[int(m.group(1))]
    except (IndexError, KeyError):
        return path
    bits = [gr.get('g', '?')]
    if m.group(2) is not None:
        try:
            bits.append('«%s»' % gr['items'][int(m.group(2))]['n'])
        except (IndexError, KeyError):
            pass
    lv = re.search(r'\.lv\[(\d)\]', path)
    if lv:
        bits.append('рівень %d' % (int(lv.group(1)) + 1))
    return '%s  (%s)' % (path, ' · '.join(bits))


def extract(html, name):
    """Тіло `var NAME = …;` — тим самим балансом дужок, що в збірці."""
    marker = 'var ' + name + ' = '
    a = html.find(marker)
    if a < 0:
        return None, None
    body = a + len(marker)
    depth, i, n = 0, body, len(html)
    while i < n:
        c = html[i]
        if c in '[{':
            depth += 1
        elif c in ']}':
            depth -= 1
            if depth == 0:
                i += 1
                break
        i += 1
    return html[body:i], (a, i)


def walk(a, b, path=''):
    """Список розбіжностей двох структур — адресами, а не діфом.

    Діф на 690 КБ нечитабельний, тому кажемо шлях до місця: «GROUPS[3].items[2].lv[1]».
    Глибше за перше розходження не спускаємось — інакше одна перейменована позиція
    дає сотні рядків.
    """
    if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return ['%s: тип %s ≠ %s' % (path or '·', type(a).__name__, type(b).__name__)]
    if isinstance(a, dict):
        out = []
        for k in [k for k in a if k not in b]:
            out.append('%s.%s: є в репозиторії, немає в артефакті' % (path, k))
        for k in [k for k in b if k not in a]:
            out.append('%s.%s: є в артефакті, немає в репозиторії' % (path, k))
        for k in [k for k in a if k in b]:
            out += walk(a[k], b[k], '%s.%s' % (path, k))
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return ['%s: довжина %d ≠ %d' % (path or '·', len(a), len(b))]
        out = []
        for i in range(len(a)):
            out += walk(a[i], b[i], '%s[%d]' % (path, i))
        return out
    if a != b:
        sa, sb = json.dumps(a, ensure_ascii=False), json.dumps(b, ensure_ascii=False)
        cut = lambda s: s if len(s) <= 90 else s[:87] + '…'
        return ['%s:\n      репозиторій: %s\n      артефакт:    %s' % (path or '·', cut(sa), cut(sb))]
    return []


def skeleton(html):
    """HTML без блоків даних: те, що є код сторінки, а не її вміст."""
    parts, pos = [], 0
    spans = []
    for name, _, _ in BLOCKS:
        _, span = extract(html, name)
        if span:
            spans.append((span[0], span[1], name))
    for a, b, name in sorted(spans):
        parts.append(html[pos:a])
        parts.append('«блок ' + name + '»')
        pos = b
    parts.append(html[pos:])
    return ''.join(parts)


def main(argv):
    if len(argv) < 2:
        print('Вкажіть файл артефакту: python3 tools/check_artifact.py <файл.html>')
        print('Файл дає інструмент Artifact із action: "read" — він друкує шлях.')
        return 2
    path = argv[1]
    if not os.path.exists(path):
        print('Файл не знайдено: %s' % path)
        return 2

    art = io.open(path, encoding='utf-8').read()
    repo = io.open(REPO_HTML, encoding='utf-8').read()
    print('артефакт    %s (%d символів)' % (path, len(art)))
    print('репозиторій %s (%d символів)' % (REPO_HTML, len(repo)))
    print()

    bad = []
    srcs = {}
    for name, src, key in BLOCKS:
        if src not in srcs:
            srcs[src] = json.load(io.open(src, encoding='utf-8'))
        want = srcs[src][key] if key else srcs[src]
        raw, _ = extract(art, name)
        if raw is None:
            bad.append('блок %s в артефакті не знайдено — сторінку перебудували інакше' % name)
            continue
        try:
            got = json.loads(raw)
        except ValueError as e:
            bad.append('блок %s в артефакті не розбирається як JSON: %s' % (name, e))
            continue
        diff = walk(want, got, name)
        if diff:
            if name == 'GROUPS':
                diff = [human(d.split(':')[0], want) + d[len(d.split(':')[0]):] for d in diff]
            bad.append('блок %s розійшовся з %s — %d %s:\n    %s'
                       % (name, src, len(diff),
                          plural(len(diff), 'місце', 'місця', 'місць'),
                          '\n    '.join(diff[:12])
                          + ('\n    … і ще %d' % (len(diff) - 12) if len(diff) > 12 else '')))
        else:
            print('  ok  %-8s = %s%s' % (name, src, (' → «%s»' % key) if key else ''))

    # Код сторінки. Обгортку публікації знімаємо з двох боків: спереду — doctype і
    # head зі скиданням стилів (шукаємо початок самого фрагмента), позаду — закриття
    # </body></html>. Хвіст ріжемо саме шаблоном обгортки, а не «до кінця файлу
    # репозиторію»: інакше справжня правка в останніх рядках сховалася б за різанням.
    head = repo[:60]
    at = art.find(head)
    if at < 0:
        bad.append('початок фрагмента не знайдено в артефакті — порівняти код не можу')
    else:
        frag = re.sub(r'\s*</body>\s*</html>\s*$', '', art[at:])
        # rstrip з двох боків: різання обгортки зʼїдає перенос рядка перед </body>,
        # тому «зайвий \n у кінці файлу» — артефакт різання, а не правка сторінки
        sk_art, sk_repo = skeleton(frag).rstrip(), skeleton(repo).rstrip()
        if sk_art == sk_repo:
            print('  ok  код      розмітка, стилі й JS однакові (%d символів)' % len(sk_repo))
        else:
            # перший рядок, що відрізняється, — щоб було з чого починати
            la, lr = sk_art.splitlines(), sk_repo.splitlines()
            n = 0
            while n < min(len(la), len(lr)) and la[n] == lr[n]:
                n += 1
            det = 'рядків %d проти %d' % (len(lr), len(la))
            if n < min(len(la), len(lr)) or len(la) != len(lr):
                det += ', перша різниця на рядку %d:' % (n + 1)
                det += '\n      репозиторій: %s' % (lr[n][:120] if n < len(lr) else '(кінець)')
                det += '\n      артефакт:    %s' % (la[n][:120] if n < len(la) else '(кінець)')
            else:
                # рядки збігаються всі, а тексти різні — різниця в пробілах усередині
                i = 0
                while i < min(len(sk_art), len(sk_repo)) and sk_art[i] == sk_repo[i]:
                    i += 1
                det += ', рядки збігаються — різниця в пробілах на символі %d:' % i
                det += '\n      репозиторій: %s' % repr(sk_repo[max(0, i - 40):i + 20])
                det += '\n      артефакт:    %s' % repr(sk_art[max(0, i - 40):i + 20])
            bad.append('код сторінки розійшовся — правки в артефакті зникнуть при '
                       'наступній публікації з репозиторію.\n    ' + det)
        if at > 0:
            print('      (обгортка публікації: %d символів перед фрагментом)' % at)

    print()
    if bad:
        print('РОЗІЙШЛОСЯ:')
        for b in bad:
            print('  • %s' % b)
        print()
        print('Що робити: якщо новіший артефакт — перенести правку в data/*.json і')
        print('перезібрати; якщо новіший репозиторій — опублікувати заново тим самим URL.')
        return 1
    print('Артефакт збігається з репозиторієм: дані з джерел правди, код без правок.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
