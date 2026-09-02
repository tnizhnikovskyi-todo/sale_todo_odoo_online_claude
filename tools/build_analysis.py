#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Збирає artifacts/price-analysis.html із docs/аналіз-прайсу.md.

Зведений аналіз прайсу пишеться в markdown (джерело правди — docs/аналіз-прайсу.md);
для публікації через Artifact він перетворюється на HTML-фрагмент у стилі концепції
та калькулятора (ті самі токени кольорів і шрифти).

    python3 tools/build_analysis.py

Підтримується підмножина markdown, якою написано документ: заголовки ##/###,
абзаци, таблиці, нумеровані й марковані списки (з переносами рядків усередині
пункту), **жирний**, _курсив_, `код`, горизонтальні лінії.
"""
import io, os, re, sys, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'docs', 'аналіз-прайсу.md')
OUT = os.path.join(ROOT, 'artifacts', 'price-analysis.html')

NAV = {  # номер розділу -> короткий підпис у навігації
    '0': 'Головне', '1': 'Периметр', '2': 'Залежності', '3': 'Сегмент UA', '4': 'Години й економіка',
    '5': 'Ризики фікса', '6': 'Склад робіт', '7': 'Механізм dep', '8': 'Ринок', '9': 'Розходження',
    '10': 'Стенд', '11': 'Пріоритети',
}

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![\w`])_([^_]+?)_(?![\w`])', r'<em>\1</em>', t)
    t = re.sub(r'(?<![\w>])\*([^*]+?)\*(?![\w<])', r'<em>\1</em>', t)
    # позначки критичності — у пілюлі
    t = re.sub(r'\b(критично|вибуховий|токсичн[аі])\b', r'<span class="chip bad">\1</span>', t)
    return t

def table(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    head, body = cells[0], cells[2:]
    out = ['<div class="tbl"><table>', '<thead><tr>']
    out += ['<th>%s</th>' % inline(c) for c in head]
    out.append('</tr></thead><tbody>')
    for r in body:
        out.append('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in r) + '</tr>')
    out.append('</tbody></table></div>')
    return '\n'.join(out)

def convert(md):
    lines = md.split('\n')
    out, i, sec = [], 0, None
    def flush_para(buf):
        if buf:
            out.append('<p>%s</p>' % inline(' '.join(x.strip() for x in buf)))
            buf[:] = []
    buf = []
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('# '):
            i += 1; continue  # заголовок документа малюється в шапці
        if ln.startswith('## '):
            flush_para(buf)
            if sec is not None: out.append('</section>')
            title = ln[3:].strip()
            m = re.match(r'^(\d+)\.\s*(.*)$', title)
            num, txt = (m.group(1), m.group(2)) if m else (None, title)
            sec = num or 'x'
            out.append('<section id="s%s">' % sec)
            if num is not None:
                out.append('<h2><span class="num">%s</span>%s</h2>' % (num, inline(txt)))
            else:
                out.append('<h2>%s</h2>' % inline(txt))
            i += 1; continue
        if ln.startswith('### '):
            flush_para(buf)
            out.append('<h3>%s</h3>' % inline(re.sub(r'^\d+\.\d+\.\s*', '', ln[4:].strip())))
            i += 1; continue
        if ln.strip() == '---':
            flush_para(buf); i += 1; continue
        if ln.startswith('|'):
            flush_para(buf)
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i]); i += 1
            out.append(table(rows)); continue
        m = re.match(r'^(\d+)\.\s+(.*)$', ln)
        if m or re.match(r'^- ', ln):
            flush_para(buf)
            ordered = bool(m)
            items = []
            while i < len(lines):
                l2 = lines[i]
                mm = re.match(r'^(\d+)\.\s+(.*)$', l2) if ordered else re.match(r'^- (.*)$', l2)
                if mm:
                    items.append([mm.group(2) if ordered else mm.group(1)]); i += 1
                elif l2.startswith('   ') or l2.startswith('  ') and l2.strip() and items:
                    items[-1].append(l2.strip()); i += 1
                else:
                    break
            tag = 'ol' if ordered else 'ul'
            start = ' start="%s"' % m.group(1) if ordered and m.group(1) != '1' else ''
            out.append('<%s%s>' % (tag, start))
            for it in items:
                out.append('<li>%s</li>' % inline(' '.join(it)))
            out.append('</%s>' % tag)
            continue
        if ln.startswith('> '):
            flush_para(buf); out.append('<blockquote>%s</blockquote>' % inline(ln[2:])); i += 1; continue
        if not ln.strip():
            flush_para(buf); i += 1; continue
        if sec is None and not buf and ln.startswith('Дата:'):
            # перший абзац документа дублює шапку сторінки — пропускаємо його цілком
            while i < len(lines) and lines[i].strip(): i += 1
            continue
        buf.append(ln); i += 1
    flush_para(buf)
    if sec is not None: out.append('</section>')
    return '\n'.join(out)

STYLE = """<title>Аналіз прайсу калькулятора</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;0,7..72,700;1,7..72,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --ground:#FBF9FA; --surface:#FFFFFF; --surface-2:#F4F0F2;
  --ink:#1D181C; --ink-2:#463E45; --muted:#6C6270;
  --line:#E2DADF; --line-strong:#CDC1C9;
  --accent:#6D4462; --accent-soft:#F2E9EF;
  --allow:#0F6E68; --allow-soft:#E6F1EF;
  --deny:#A63D2E; --deny-soft:#F8EAE7;
  --escalate:#8A6009; --escalate-soft:#F7EFDC;
  --shadow:0 1px 2px rgba(29,24,28,.05), 0 8px 24px -16px rgba(29,24,28,.18);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#171317; --surface:#1F1A1F; --surface-2:#272029;
    --ink:#F1EAEE; --ink-2:#D2C7CE; --muted:#9C909A;
    --line:#332B33; --line-strong:#4A3F4A;
    --accent:#C994B8; --accent-soft:#2C2029;
    --allow:#5CBFB2; --allow-soft:#172A29;
    --deny:#E28A78; --deny-soft:#2E1E1B;
    --escalate:#D9AC4E; --escalate-soft:#2B2317;
    --shadow:0 1px 2px rgba(0,0,0,.3), 0 8px 24px -16px rgba(0,0,0,.6);
  }
}
:root[data-theme="dark"]{
  --ground:#171317; --surface:#1F1A1F; --surface-2:#272029;
  --ink:#F1EAEE; --ink-2:#D2C7CE; --muted:#9C909A;
  --line:#332B33; --line-strong:#4A3F4A;
  --accent:#C994B8; --accent-soft:#2C2029;
  --allow:#5CBFB2; --allow-soft:#172A29;
  --deny:#E28A78; --deny-soft:#2E1E1B;
  --escalate:#D9AC4E; --escalate-soft:#2B2317;
  --shadow:0 1px 2px rgba(0,0,0,.3), 0 8px 24px -16px rgba(0,0,0,.6);
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;font-size:15.5px;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--accent)}
code{font-family:"IBM Plex Mono",Menlo,Consolas,monospace;font-size:.88em;background:var(--surface-2);padding:.05em .35em;border-radius:4px;color:var(--ink-2)}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px 80px}
header.top{padding:44px 0 20px;border-bottom:1px solid var(--line)}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:500;margin:0 0 10px}
h1{font-family:Literata,Georgia,serif;font-weight:600;font-size:clamp(28px,4vw,40px);line-height:1.15;margin:0 0 14px;text-wrap:balance;letter-spacing:-.01em}
.lede{font-size:17px;color:var(--ink-2);max-width:68ch;margin:0}
.meta{display:flex;flex-wrap:wrap;gap:10px 22px;margin-top:18px;font-size:13px;color:var(--muted)}
.meta b{color:var(--ink-2);font-weight:500}
/* зріз периметра */
.split{margin:26px 0 0;padding:18px 20px;background:var(--surface);border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow)}
.split .cap{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.split .cap h2{margin:0;font-size:15px;font-weight:600;font-family:"IBM Plex Sans",sans-serif}
.split .cap span{font-size:13px;color:var(--muted)}
.bar{display:flex;height:22px;border-radius:6px;overflow:hidden;border:1px solid var(--line-strong)}
.bar i{display:block;height:100%}
.bar .a{background:var(--allow)} .bar .b{background:var(--accent)} .bar .d{background:var(--escalate)} .bar .c{background:var(--deny)}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:10px;font-size:13px;color:var(--ink-2)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.legend b{font-family:"IBM Plex Mono",monospace;font-weight:500;font-variant-numeric:tabular-nums}
/* навігація */
nav.toc{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--ground) 92%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);margin:0 -24px;padding:0 24px}
nav.toc ol{list-style:none;margin:0;padding:8px 0;display:flex;gap:2px 4px;flex-wrap:wrap}
nav.toc a{display:inline-block;padding:5px 9px;border-radius:6px;font-size:13px;color:var(--ink-2);text-decoration:none;white-space:nowrap}
nav.toc a:hover,nav.toc a:focus-visible{background:var(--accent-soft);color:var(--accent);outline:none}
nav.toc a .n{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--muted);margin-right:5px}
/* текст */
section{padding:30px 0 6px;border-bottom:1px solid var(--line)}
section:last-of-type{border-bottom:0}
h2{font-family:Literata,Georgia,serif;font-weight:600;font-size:26px;line-height:1.2;margin:0 0 14px;text-wrap:balance;display:flex;gap:14px;align-items:baseline}
h2 .num{font-family:"IBM Plex Mono",monospace;font-size:14px;font-weight:500;color:var(--accent);background:var(--accent-soft);padding:2px 8px;border-radius:5px;letter-spacing:.02em}
h3{font-family:"IBM Plex Sans",sans-serif;font-weight:600;font-size:17px;margin:26px 0 8px;color:var(--ink);text-wrap:balance}
p,li{max-width:76ch}
p{margin:0 0 12px}
ol,ul{margin:0 0 14px;padding-left:1.4em}
li{margin:0 0 7px}
li::marker{color:var(--muted);font-family:"IBM Plex Mono",monospace;font-size:.9em}
#s0 > ol > li{padding:6px 0 6px 6px;border-left:2px solid var(--line-strong);margin-left:-1.4em;padding-left:1.6em;list-style-position:inside}
#s0 > ol > li::marker{color:var(--accent);font-weight:500}
blockquote{margin:0 0 14px;padding:8px 14px;border-left:3px solid var(--accent);background:var(--accent-soft);color:var(--ink-2);border-radius:0 6px 6px 0}
strong{font-weight:600;color:var(--ink)}
.chip{display:inline-block;font-size:12px;font-weight:500;padding:1px 7px;border-radius:999px;border:1px solid;line-height:1.5;vertical-align:1px}
.chip.bad{color:var(--deny);background:var(--deny-soft);border-color:var(--deny)}
/* таблиці */
.tbl{overflow-x:auto;margin:6px 0 18px;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13.5px;line-height:1.45}
th,td{padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
th{background:var(--surface-2);font-weight:600;font-size:12.5px;letter-spacing:.01em;color:var(--ink-2);white-space:nowrap}
tbody tr:last-child td{border-bottom:0}
td{font-variant-numeric:tabular-nums}
td:first-child{font-weight:500;color:var(--ink)}
tbody tr:hover td{background:color-mix(in srgb,var(--surface-2) 60%,transparent)}
footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
@media (max-width:640px){body{font-size:15px} .wrap{padding:0 16px 60px} nav.toc{margin:0 -16px;padding:0 16px} h2{font-size:22px}}
@media (prefers-reduced-motion: reduce){*{scroll-behavior:auto!important}}
html{scroll-behavior:smooth;scroll-padding-top:56px}
</style>
"""

def main():
    md = io.open(SRC, encoding='utf-8').read()
    body = convert(md)
    # навігація з розділів
    nums = re.findall(r'<section id="s(\d+)">', body)
    nav = ['<nav class="toc" aria-label="Розділи"><ol>']
    for n in nums:
        nav.append('<li><a href="#s%s"><span class="n">%s</span>%s</a></li>' % (n, n, NAV.get(n, n)))
    nav.append('</ol></nav>')
    # зріз периметра: підсумки лінзи A по 343 пунктах (розділ 1 документа)
    A, B, C, D = 249, 62, 6, 26
    tot = A + B + C + D
    pct = lambda v: '%.1f%%' % (v * 100.0 / tot)
    split = ('<div class="split"><div class="cap"><h2>Здійсненність 343 пунктів складу робіт у периметрі «штатна конфігурація + Studio»</h2>'
             '<span>лінза A, Odoo Online 19</span></div>'
             '<div class="bar" role="img" aria-label="Штатно %d, Studio %d, сумнівно %d, поза периметром %d">'
             '<i class="a" style="width:%s"></i><i class="b" style="width:%s"></i><i class="d" style="width:%s"></i><i class="c" style="width:%s"></i></div>'
             '<div class="legend"><span><i style="background:var(--allow)"></i>штатна конфігурація <b>%d</b></span>'
             '<span><i style="background:var(--accent)"></i>потребує Studio <b>%d</b></span>'
             '<span><i style="background:var(--escalate)"></i>сумнівно, слово ширше за механіку <b>%d</b></span>'
             '<span><i style="background:var(--deny)"></i>поза периметром <b>%d</b></span></div></div>'
             % (A, B, D, C, pct(A), pct(B), pct(D), pct(C), A, B, D, C))
    head = ('<div class="wrap"><header class="top"><p class="eyebrow">Департамент odoo.com · робочий документ</p>'
            '<h1>Аналіз прайсу калькулятора</h1>'
            '<p class="lede">26 позицій × 3 рівні, 343 пункти складу робіт, 78 оцінок годин — розібрано за сімома лінзами: '
            'периметр, години й економіка, сегмент UA, якість складу робіт, ризики фікса, залежності, ринок. '
            'Тут — зведення і пріоритети; повні звіти — у <code>docs/аналіз-прайсу/</code>.</p>'
            '<div class="meta"><span>Дата <b>02.09.2026</b></span><span>Предмет <b>data/price.json</b></span>'
            '<span>Джерело цього документа <b>docs/аналіз-прайсу.md</b></span></div>'
            + split + '</header>')
    foot = ('<footer>Позначки: <b>факт</b> — стенд (аудит) або документація 19.0 через пошук; <b>гіпотеза</b> — експертна оцінка до заміру у фазі 0. '
            'Усі числа про години, P80 і ринок — гіпотези або сніпети зовнішніх джерел. Зібрано з <code>docs/аналіз-прайсу.md</code> скриптом <code>tools/build_analysis.py</code>.</footer></div>')
    page = STYLE + head + '\n'.join(nav) + '\n<main>\n' + body + '\n</main>\n' + foot + '\n'
    io.open(OUT, 'w', encoding='utf-8').write(page)
    print('OK: %d розділів, %d байт -> %s' % (len(nums), len(page.encode('utf-8')), os.path.relpath(OUT, ROOT)))
    return 0

if __name__ == '__main__':
    sys.exit(main())
