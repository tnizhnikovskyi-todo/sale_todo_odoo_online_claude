# -*- coding: utf-8 -*-
"""Одна перевірка на весь репозиторій: чи все згенероване актуальне.

У проєкті багато похідних файлів: калькулятор, дві бази знань, журнал звірки,
карта налаштування, процедура збірки, зразок плану. Кожен збирається зі своїх
джерел правди. Найтихіша й найпідліша поломка тут — **правка похідного файлу
руками** або забутий перезбір: джерело каже одне, документ показує інше, і
помітити це можна тільки випадково.

Ця перевірка:

1. Запускає всі генератори (кожен сам валідує свої джерела й падає, якщо зламано).
2. Порівнює те, що вийшло, з тим, що лежить у git: якщо генератор змінив файл,
   значить у коміті лежала стара версія. Це помилка, і вона називається вголос.
3. Прогоняє валідатор рецептів і негативні тести перевірок цілісності
   (перевірка, яка нічого не ловить, гірша за відсутність перевірки).
4. Прогоняє перевірку калькулятора в браузері, якщо в системі є playwright-core
   і Chromium. Немає — крок позначається «не перевірено» і не валить збірку:
   «зламано» і «не перевірено» — різні відповіді, і плутати їх не можна.

Запуск: python3 tools/check_all.py
Повертає 0, якщо все чисте; 1 — якщо щось не так.

Файли лишаються перезібраними, тому після падіння достатньо переглянути `git diff`
і закомітити оновлене.
"""

import subprocess
import sys

GENERATORS = [
    ('tools/build_calculator.py', ['artifacts/calculator.html']),
    ('tools/build_kb.py', ['docs/база-знань-блоки.md']),
    ('tools/build_audit.py', ['docs/звірка-бази-2026-09-09.md']),
    ('tools/build_config_map.py', ['data/config-map.json']),
    ('tools/build_runbook.py', ['docs/setup-runbook.md']),
    ('tools/report_recipe_gaps.py', ['docs/рецепти-що-лишилось.md']),
    # Артефакт аналізу прайсу теж похідний — від docs/аналіз-прайсу.md. У переліку
    # його не було, тому 10.09.2026 правка документа не потрапила в артефакт і
    # збірка сказала «чисто». Рівно та поломка, від якої цей скрипт існує.
    ('tools/build_analysis.py', ['artifacts/price-analysis.html']),
]
# Звіт «кроки проти годин» пише в stdout, як і план — тому збирається окремо,
# тим самим способом, що PLAN нижче.
STEPS = ('tools/report_plan_vs_price.py', 'docs/кроки-проти-годин.md')
# Перелік полів плану — теж у stdout. Сам він у базу не ходить (ключа API
# в репозиторії немає), але мусить лишатися актуальним: рецепт правлять,
# поле міняється, а перелік для звірки застаріває мовчки.
FIELDS = ('tools/probe_fields.py', 'docs/поля-плану-для-звірки.md')
VALIDATORS = ['tools/check_recipes.py', 'tools/check_concept.py',
              'tools/test_integrity.py']
# Перевірка в браузері: код 2 означає «немає чим перевіряти», а не «зламано».
BROWSER = ['node', 'tools/test_calculator_ui.js']
# Зразок плану збирається з профілю-прикладу окремою командою.
PLAN = ('tools/emit_config_calls.py', 'data/client-profile-example.json',
        'docs/план-збірки-приклад.md')


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def run_raw(cmd):
    """Як run, але віддає stdout байт у байт — для генераторів, що пишуть у файл
    через перенаправлення. Інакше перевірка сама створює різницю в останньому рядку."""
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr.strip()


def dirty(paths):
    """Які з файлів відрізняються від закоміченого стану."""
    # core.quotepath=false обовʼязково: інакше git екранує кириличні імена
    # («docs/\320\261...»), і порівняння шляхів молча не збігається — а таких
    # імен у цьому репозиторії більшість
    code, out = run(['git', '-c', 'core.quotepath=false',
                     'diff', '--name-only', '--'] + paths)
    if code != 0:
        return []
    return [p for p in out.splitlines() if p.strip()]


def verdict(gen, outs, dirty_before):
    """Що сталося з похідними файлами генератора.

    Різниця після перезбору = у коміті лежала стара версія (джерело правили, а
    перезбір забули). Різниця тільки ДО перезбору = файл правили руками, і
    перезбір цю правку щойно затер — про це треба сказати, бо людина могла
    вважати ту правку роботою.
    """
    out_bad = []
    after = set(dirty(outs))
    for path in outs:
        if path in after:
            out_bad.append('%s: у коміті стара версія — джерело змінили, перезбір забули '
                           '(%s)' % (gen, path))
        elif path in dirty_before:
            out_bad.append('%s: файл правили руками, і перезбір цю правку затер (%s). '
                           'Похідні файли не правлять — правлять джерело' % (gen, path))
    return out_bad


def main():
    bad = []
    skipped = []

    # Стан ДО перезбору. Похідний файл, змінений до перевірки, — це або правка
    # руками, або забутий перезбір. Обидва випадки треба назвати, а не затерти.
    all_outs = [o for _, outs in GENERATORS for o in outs] + [PLAN[2], STEPS[1], FIELDS[1]]
    dirty_before = set(dirty(all_outs))

    for gen, outs in GENERATORS:
        code, out = run(['python3', gen])
        if code != 0:
            bad.append('генератор %s упав:\n%s' % (gen, out))
            continue
        bad += verdict(gen, outs, dirty_before)
        print('  ok  %-30s %s' % (gen, out.splitlines()[0] if out else ''))

    # зразок плану
    gen, prof, out_path = PLAN
    code, out, err = run_raw(['python3', gen, prof])
    if code != 0:
        bad.append('%s упав:\n%s' % (gen, err or out))
    else:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(out)
        bad += verdict(gen, [out_path], dirty_before)
        print('  ok  %-30s %d рядків плану' % (gen, len(out.splitlines())))

    for gen, out_path in (STEPS, FIELDS):
        code, out, err = run_raw(['python3', gen])
        if code != 0:
            bad.append('%s упав:\n%s' % (gen, err or out))
            continue
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(out)
        bad += verdict(gen, [out_path], dirty_before)
        перший = [l for l in out.splitlines() if l.startswith('| **Разом**')
                  or l.startswith('Моделей ')]
        print('  ok  %-30s %s' % (gen, (перший[0][:70] if перший else '')))

    # План на ВСІ позиції — перевірка покриття, а не документ. Потрібна тому, що
    # профіль-приклад описує реальний набір клієнта, і позиції поза цим набором
    # емітер ніколи не бачить. Саме емітер ловить помилки підстановки, яких не бачить
    # валідатор рецептів (поле профілю формально є, а значення складене) — тому
    # рецепти позицій поза набором лежали б неперевіреними. Результат нікуди не
    # пишеться: перевіряємо, що план узагалі складається без «бракує полів».
    code, out, err = run_raw(['python3', PLAN[0], PLAN[1], '--всі'])
    if code != 0:
        bad.append('план на всі позиції не складається:\n%s' % (err or out)[:2000])
    else:
        head = [l for l in out.splitlines() if l.startswith('Кроків')]
        print('  ok  %-30s %s' % ('emit --всі (покриття)', head[0] if head else ''))

    # Перевірка в браузері — після генераторів: вона читає щойно перезібраний
    # artifacts/calculator.html, тобто перевіряє те, що зараз у репозиторії.
    code, out = run(BROWSER)
    if code == 2:
        skipped.append('перевірка калькулятора в браузері не запускалась: %s'
                       % (out.splitlines()[0] if out else 'немає playwright-core або Chromium'))
    elif code != 0:
        bad.append('перевірка калькулятора в браузері не пройшла:\n%s' % out)
    else:
        last = [l for l in out.splitlines() if l.strip()]
        print('  ok  %-30s %s' % ('tools/test_calculator_ui.js', last[-1] if last else ''))

    # Генератор рецептів «штатної поведінки» ЗАПУСКАТИ ТУТ НЕ ТРЕБА: він пише в
    # data/recipes.json — джерело правди, а не похідний файл. Автоматично мутувати
    # джерело означало б, що склад рецептів змінюється сам, без рішення людини.
    # Тому перевірка лише питає «--dry»: чи зʼявилися нові пункти цього виду.
    code, out = run(['python3', 'tools/gen_standard_recipes.py', '--dry'])
    if code != 0:
        bad.append('генератор «штатної поведінки» упав:\n%s' % out)
    else:
        first = out.splitlines()[0] if out else ''
        n = 0
        try:
            n = int(first.split('рецептів:')[1].split('(')[0].strip())
        except (IndexError, ValueError):
            pass
        if n:
            skipped.append('зʼявилося %d пунктів виду «штатна поведінка» без рецепта — '
                           'дописати: python3 tools/gen_standard_recipes.py' % n)
        else:
            print('  ok  %-30s нових пунктів «штатної поведінки» немає'
                  % 'gen_standard_recipes.py')

    for v in VALIDATORS:
        code, out = run(['python3', v])
        if code != 0:
            bad.append('валідатор %s не пройшов:\n%s' % (v, out))
        else:
            print('  ok  %-30s %s' % (v, out.splitlines()[0] if out else ''))

    print()
    for s_ in skipped:
        print('  НЕ ПЕРЕВІРЕНО: %s' % s_)
    if skipped:
        print()
    if bad:
        print('НЕ ЧИСТО:')
        for b in bad:
            print('  • %s' % b)
        print()
        print('Файли перезібрані — подивіться `git diff` і закомітьте оновлене.')
        return 1
    print('Усе згенероване актуальне, валідатори пройшли.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
