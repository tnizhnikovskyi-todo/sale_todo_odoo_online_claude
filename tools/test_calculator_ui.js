// Перевірка калькулятора в справжньому браузері: сторінки 1–3.
//
// Навіщо. Збірка (`tools/build_calculator.py`) перевіряє **дані** — структуру прайсу,
// чек-листа й анкети. Вона нічого не знає про те, чи працює сторінка: чи додається
// жорстка залежність, чи збігається сума в КП із сумою на панелі, чи піднімається
// прапорець порога обмежень. Це перевіряється тільки натисканнями.
//
// Головне правило цього файлу: **очікування рахуються з `data/price.json`**, а не
// вписані числами. Інакше після кожної правки прайсу тест падав би на власних
// застарілих числах — і його б вимкнули.
//
// Запуск:  node tools/test_calculator_ui.js
// Потрібен playwright-core і Chromium. Якщо їх немає — тест каже це вголос і
// повертає 2 (не 1): «не перевірено» і «зламано» — різні речі.

const fs = require('fs');
const path = require('path');
const os = require('os');

const ROOT = path.resolve(__dirname, '..');
const RATE = 50;

// Пакет шукається в чотирьох місцях, і це не перестраховка: у цьому образі
// playwright стоїть ГЛОБАЛЬНО, а node глобальні модулі за замовчуванням не бачить.
// Через це перевірка одного разу мовчки перейшла в «НЕ ПЕРЕВІРЕНО» на цілком
// придатному оточенні — тобто найгірший режим: збірка зелена, а сторінку ніхто
// не натискав.
function loadChromium() {
  const ids = ['playwright-core', 'playwright'];
  const roots = [null];
  try {
    const cp = require('child_process');
    const g = cp.execSync('npm root -g', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    if (g) roots.push(g);
  } catch (e) { /* npm може бути відсутній — не привід падати */ }
  roots.push('/opt/node22/lib/node_modules', '/usr/lib/node_modules');
  for (const root of roots) {
    for (const id of ids) {
      try {
        const mod = require(root ? path.join(root, id) : id);
        if (mod && mod.chromium) return { chromium: mod.chromium, звідки: (root || 'проєкт') + '/' + id };
      } catch (e) { /* пробуємо наступне місце */ }
    }
  }
  return null;
}

const пакет = loadChromium();
if (!пакет) {
  console.error('playwright не знайдено — перевірка в браузері не запускалась.');
  console.error('Шукали playwright-core і playwright у проєкті, у `npm root -g` '
    + 'і в /opt/node22/lib/node_modules, /usr/lib/node_modules.');
  console.error('Поставити:  npm i playwright-core   (Chromium уже є в образі)');
  process.exit(2);
}
const chromium = пакет.chromium;

function findChromium() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  const cands = [];
  try {
    for (const d of fs.readdirSync(base)) {
      if (/^chromium/.test(d)) cands.push(path.join(base, d, 'chrome-linux', 'chrome'));
    }
  } catch (e) { /* каталогу немає — впадемо нижче з понятним текстом */ }
  cands.push(path.join(base, 'chromium', 'chrome-linux', 'chrome'), '/usr/bin/chromium');
  for (const c of cands) { if (fs.existsSync(c)) return c; }
  return null;
}

// --- очікування з прайсу ---------------------------------------------------
const price = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/price.json'), 'utf8'));
const EXP = {};
for (const g of price['групи']) {
  for (const it of g.items) {
    EXP[it.id] = {
      n: it.n,
      ціни: it.lv.map(l => Math.round(l[1] * RATE / 50) * 50),
      hard: (it.dep || []).filter(d => d.type === 'hard').map(d => d.on),
    };
  }
}

const out = [];
const ok = (name, cond, detail) =>
  out.push({ name, ok: !!cond, detail: detail === undefined ? '' : String(detail) });
const num = s => parseInt(String(s).replace(/[^\d]/g, ''), 10);

// Стан вибору читається з самого DOM: id позиції з «c-<id>», рівень — значення селекта
// (0/1/2). Так тест не тримає власної моделі стану, яка може розійтися зі сторінкою.
const READ = () => {
  const sel = [];
  for (const r of Array.from(document.querySelectorAll('#rows tr.item'))) {
    const cb = r.querySelector('input[type=checkbox]');
    if (!cb) continue;
    const s = document.getElementById('l-' + cb.id.replace(/^c-/, ''));
    sel.push({
      id: cb.id.replace(/^c-/, ''),
      on: /\bon\b/.test(r.className),
      lv: s ? parseInt(s.value, 10) : null,
      cls: r.className,
    });
  }
  return {
    sel,
    total: document.getElementById('t-price').textContent.trim(),
    count: document.getElementById('t-count').textContent.trim(),
    autos: (document.getElementById('autos') || {}).textContent.trim(),
  };
};

// Сума КП = сума вибраних позицій. Діагностика в підсумок не входить — вона
// оплачується окремо й зараховується у вартість (рішення 09.09.2026).
function expected(sel) {
  let sum = 0;
  const parts = [];
  for (const r of sel) {
    if (!r.on) continue;
    const e = EXP[r.id];
    if (!e) return { sum: null, parts: ['невідома позиція ' + r.id] };
    if (r.id === 'diag') { parts.push('diag пропущено'); continue; }
    sum += e.ціни[r.lv];
    parts.push(e.n + ' р.' + (r.lv + 1) + '=' + e.ціни[r.lv]);
  }
  return { sum, parts };
}

(async () => {
  const exe = findChromium();
  if (!exe) {
    console.error('Chromium не знайдено. Шукали в PLAYWRIGHT_BROWSERS_PATH і /usr/bin.');
    console.error('Вказати вручну:  CHROMIUM_PATH=/шлях/до/chrome node tools/test_calculator_ui.js');
    process.exit(2);
  }

  // Калькулятор — фрагмент для Artifact, без doctype: обгортаємо, як у CLAUDE.md.
  const frag = fs.readFileSync(path.join(ROOT, 'artifacts/calculator.html'), 'utf8');
  const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'calc-ui-')), 'preview.html');
  fs.writeFileSync(tmp, '<!doctype html><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width,initial-scale=1">' + frag);

  const b = await chromium.launch({ executablePath: exe });
  const p = await b.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  p.on('console', m => {
    if (m.type() === 'error' && !/ERR_CONNECTION|net::/.test(m.text())) errs.push('console: ' + m.text());
  });
  await p.goto('file://' + tmp);
  await p.waitForTimeout(1200);

  // --- 1. типовий стан: База обовʼязкова й уже на «Стандарті» --------------
  // Це не дрібниця: будь-який підсумок калькулятора вже містить 1 000 € Бази.
  let st = await p.evaluate(READ);
  const base = st.sel.find(r => r.id === 'base');
  ok('База позначена й обовʼязкова', base && base.on && /req/.test(base.cls), JSON.stringify(base));
  let e = expected(st.sel);
  ok('ціна типового стану = ' + e.sum, num(st.total) === e.sum, st.total + ' | ' + e.parts.join(', '));

  // --- 2. рівні: ціна кожного рівня збігається з прайсом -------------------
  for (const lv of [0, 1, 2]) {
    await p.evaluate(v => {
      const s = document.getElementById('l-base');
      s.value = String(v);
      s.dispatchEvent(new Event('change', { bubbles: true }));
    }, lv);
    await p.waitForTimeout(200);
    st = await p.evaluate(READ);
    e = expected(st.sel);
    ok('База р.' + (lv + 1) + ': підсумок = ' + e.sum, num(st.total) === e.sum, st.total);
  }

  // --- 3. жорсткі залежності додаються самі --------------------------------
  const hardOfPrj = EXP.prj.hard.flat();
  await p.evaluate(() => document.getElementById('c-prj').click());
  await p.waitForTimeout(500);
  st = await p.evaluate(READ);
  const on = st.sel.filter(r => r.on).map(r => r.id);
  ok('prj сам додав ' + hardOfPrj.join(' і '), hardOfPrj.every(x => on.includes(x)), on.join(','));
  ok('додані позначені як «потрібна для»', /потрібна для/.test(st.autos), st.autos.slice(0, 90));
  e = expected(st.sel);
  ok('ціна з залежностями = ' + e.sum, num(st.total) === e.sum, st.total + ' | ' + e.parts.join(', '));

  // --- 4. мʼяка залежність попереджає, але позиції не додає -----------------
  await p.evaluate(() => document.getElementById('c-dsh').click());
  await p.waitForTimeout(400);
  const soft = await p.evaluate(() => ({
    warns: (document.getElementById('warns') || {}).textContent.trim(),
    cardHidden: (document.getElementById('warns-card') || {}).hidden,
  }));
  ok('мʼяка залежність дає попередження, а не додає позицію',
     !soft.cardHidden && soft.warns.length > 10, soft.warns.slice(0, 100));

  // --- 5. КП: збирається, містить «не входить», та сама сума ---------------
  st = await p.evaluate(READ);
  e = expected(st.sel);
  await p.click('#sum-btn');
  await p.waitForTimeout(400);
  const kp = await p.evaluate(() => {
    const t = document.getElementById('sum-out');
    return { hidden: t.hidden, text: t.value || '' };
  });
  // у КП числа з нерозривними пробілами — порівнюємо без пробілів узагалі
  const flat = kp.text.replace(/[\s  ]/g, '');
  ok('КП зібралося', !kp.hidden && kp.text.length > 500, 'довжина ' + kp.text.length);
  ok('у КП є «не входить»', /невходить/i.test(flat));
  ok('у КП стоїть та сама сума ' + e.sum, flat.includes('€' + e.sum), 'шукали €' + e.sum);
  // Ідентифікація КП. Порожній строк дії мусить друкуватися ПРОЧЕРКОМ, а не
  // зникати: рядок «ціни фіксовані на строк дії пропозиції» інакше обіцяє строк,
  // якого в тексті немає. Сам строк — рішення власника, тому інструмент його не
  // вигадує.
  ok('у КП з порожнім строком стоїть прочерк', /Пропозиція дійсна до: _+/.test(kp.text),
     kp.text.split('\n').slice(0, 4).join(' | '));
  await p.evaluate(() => {
    const c = document.getElementById('cli');
    c.value = 'ТОВ «Перевірка»'; c.dispatchEvent(new Event('input', { bubbles: true }));
    const u = document.getElementById('until');
    u.value = '2026-09-24'; u.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await p.click('#sum-btn');
  await p.waitForTimeout(400);
  const kp2 = await p.evaluate(() => document.getElementById('sum-out').value || '');
  ok('у КП є клієнт, дата й строк дії',
     /Клієнт: ТОВ «Перевірка»/.test(kp2) && /Дата: \d\d\.\d\d\.\d{4} \d\d:\d\d/.test(kp2)
     && /Пропозиція дійсна до: 24\.09\.2026/.test(kp2),
     kp2.split('\n').slice(0, 4).join(' | '));

  // Клавіатура: роль tablist обіцяє читалці, що стрілка перемкне вкладку.
  // До 10.09 обробника не було — Tab проводив крізь чотири кнопки, стрілки
  // не робили нічого, і обіцянка ролі була порожньою.
  await p.focus('#tab-calc');
  await p.keyboard.press('ArrowRight');
  await p.waitForTimeout(300);
  const посл = await p.evaluate(() => ({
    сторінка: document.getElementById('page-spec').hidden === false,
    вибрана: document.getElementById('tab-spec').getAttribute('aria-selected'),
    tabindexАктивної: document.getElementById('tab-spec').tabIndex,
    tabindexІншої: document.getElementById('tab-calc').tabIndex,
  }));
  ok('стрілка вправо перемикає вкладку і переносить фокус',
     посл.сторінка && посл.вибрана === 'true' && посл.tabindexАктивної === 0
     && посл.tabindexІншої === -1, JSON.stringify(посл));
  await p.keyboard.press('Home');
  await p.waitForTimeout(300);
  const дім = await p.evaluate(() => document.getElementById('page-calc').hidden === false);
  ok('Home повертає на першу вкладку', дім);
  const живе = await p.evaluate(() => {
    const b = document.getElementById('o-price');
    const box = b.closest('[aria-live]');
    return box ? box.getAttribute('aria-live') : null;
  });
  ok('підсумок озвучується читалкою (aria-live)', живе === 'polite', String(живе));

  // Залік діагностики — половина (рішення 10.09.2026). Перевіряємо саме те, що
  // бачать двоє різних людей: сейл у панелі й клієнт у тексті КП. Число в коді
  // може бути правильним, а на екран потрапити не те.
  await p.evaluate(() => {
    const c = document.getElementById('c-diag');
    if(c && !c.checked) c.click();
    const l = document.getElementById('l-diag');
    if(l){ l.value = '2'; l.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  await p.waitForTimeout(400);
  const діаг = await p.evaluate(() => {
    const row = document.getElementById('o-diag');
    return { сховано: row.hidden, текст: document.getElementById('o-diag-v').textContent };
  });
  ok('панель показує суму діагностики і залік окремо',
     !діаг.сховано && /€1\s*000/.test(діаг.текст) && /залік[^\d]*€500/.test(діаг.текст),
     діаг.текст);
  await p.click('#sum-btn');
  await p.waitForTimeout(400);
  const кпд = await p.evaluate(() => document.getElementById('sum-out').value || '');
  ok('КП називає половину суми словом і числом',
     /зараховується\s+половина[^\d]*€500/.test(кпд.replace(/\s+/g, ' ')),
     (кпд.split('\n').find(l => l.indexOf('Експрес-діагностика') === 0) || '').slice(0, 150));
  // «Діагностика не входить у підсумок» тут НЕ перевіряється навмисно: це вже
  // робить перевірка «у КП стоїть та сама сума» вище, і вона рахує очікуване з
  // data/price.json без діагностики. Другий тест того самого був би заглушкою.

  // --- 5б. умови КП: оплата, два документи, гарантійне вікно ---------------
  // Найважливіше тут — НУМЕРАЦІЯ. Розділ «Оплата» збирається кодом саме тому,
  // що пункт про діагностику умовний; отже перевіряти треба обидва стани, а не
  // той, у якому діагностику обрано.
  const умови = кпд.replace(/\s+/g, ' ');
  ok('у КП є розділ «Оплата» з двома платежами проєкту',
     /ОПЛАТА/.test(кпд) && /Проєкт — 50 % після погодження пропозиції[^%]*50 % після закриття/.test(умови),
     (кпд.split('\n').find(l => /^\d\. Проєкт — 50/.test(l)) || 'рядка немає').slice(0, 120));
  ok('оплата з діагностикою: діагностика — пункт 1, проєкт — пункт 2',
     /1\. Експрес-діагностика/.test(кпд) && /2\. Проєкт — 50 %/.test(кпд),
     кпд.split('\n').filter(l => /^\d\. /.test(l)).slice(0, 4).join(' | '));
  ok('у КП названі два документи проєкту й гарантійне вікно',
     /ДВА ДОКУМЕНТИ ПРОЄКТУ/.test(кпд) && /Протокол запуску/.test(кпд)
       && /15 робочих днів від демонстрації/.test(умови),
     'документи: ' + /ДВА ДОКУМЕНТИ/.test(кпд) + ' · вікно: ' + /15 робочих днів/.test(кпд));
  // Розгортання на нашій стороні (рішення 10.09.2026). Дві протилежні обіцянки
  // жили в КП одночасно рівно до цього дня: «базу створює клієнт» в обовʼязках і
  // «ключ у нас» ніде. Перевіряємо і те, що зʼявилось, і те, що мусило зникнути.
  ok('КП каже, що базу розгортаємо ми, а платить клієнт напряму в Odoo',
     /РОЗГОРТАННЯ І ДОСТУПИ/.test(кпд) && /Базу розгортаємо ми/.test(умови)
       && /напряму в Odoo/.test(умови) && /ключ анульовуються/.test(умови),
     (кпд.split('\n').find(l => /Базу розгортаємо/.test(l)) || 'рядка немає').slice(0, 110));
  ok('клієнта більше не просять створити базу й дати доступ',
     !/Створити базу/.test(кпд) && !/надати адміністративний доступ/.test(кпд)
       && /Оплатити підписку Odoo за посиланням/.test(кпд),
     (кпд.split('\n').find(l => /Оплатити підписку/.test(l)) || 'рядка немає').slice(0, 110));
  // Слова про підписання шукаємо ТІЛЬКИ у фіксованій частині (від «Оплати» до
  // кінця): «підписання у браузері за посиланням» — це проданий пункт прайсу
  // (Odoo Sign), і на наборі з ним правило по всьому КП кричало б на правильних
  // даних. Спіймано першим же прогоном. Друга пастка тієї ж мови: «підписка» має
  // той самий корінь, що «підпис», — тому «к» і «ц» після кореня виключені
  // (підписку, підписці), інакше правило кричить на власному розділі про оплату.
  const фікс = кпд.slice(кпд.indexOf('ОПЛАТА'));
  ok('в умовах КП немає ні підписання, ні ПДВ за законодавством',
     кпд.indexOf('ОПЛАТА') > 0 && !/підпис(?![кц])/.test(фікс) && !/за законодавством/.test(фікс),
     (фікс.split('\n').filter(l => /підпис(?![кц])|законодавств/.test(l)).join(' | ') || 'таких рядків немає').slice(0, 140));

  await p.evaluate(() => {
    const c = document.getElementById('c-diag'); if(c && c.checked) c.click();
  });
  await p.waitForTimeout(300);
  await p.click('#sum-btn');
  await p.waitForTimeout(400);
  const безДіаг = await p.evaluate(() => document.getElementById('sum-out').value || '');
  const оплата = безДіаг.slice(безДіаг.indexOf('ОПЛАТА'), безДіаг.indexOf('ЩО НЕ ВХОДИТЬ'));
  ok('без діагностики розділ «Оплата» починається з проєкту й без дірки в нумерації',
     /1\. Проєкт — 50 %/.test(оплата) && !/Експрес-діагностика/.test(оплата)
       && /2\. Позиція, додана/.test(оплата) && /3\. Ціни в пропозиції/.test(оплата),
     оплата.split('\n').filter(l => /^\d\. /.test(l)).join(' | ').slice(0, 160));
  // --- 6. чек-лист кваліфікації: поріг обмежень й вердикт «стоп» -----------
  await p.getByText('ЧЕК-ЛИСТ КВАЛІФІКАЦІЇ', { exact: false }).first().click();
  await p.waitForTimeout(600);
  const q = await p.evaluate(() => {
    const c = Array.from(document.querySelectorAll('#qbar .qcheck'))
      .find(x => /скринінг/i.test(x.textContent));
    if (c) { const i = c.querySelector('input'); if (i && !i.checked) i.click(); }
    return { opened: !!c, checks: document.querySelectorAll('#qbar .qcheck').length };
  });
  await p.waitForTimeout(500);
  const warnClicks = await p.evaluate(() => {
    const w = Array.from(document.querySelectorAll('#qblocks .opt.r-warn')).slice(0, 4);
    w.forEach(x => x.click());
    return w.length;
  });
  await p.waitForTimeout(500);
  const thr = await p.evaluate(() => ({
    lim: (document.getElementById('q-lim') || {}).textContent,
    flag: (document.getElementById('q-lim-flag') || {}).textContent,
    flagHidden: (document.getElementById('q-lim-flag') || {}).hidden,
  }));
  ok('скринінг: розділ відкривається', q.opened && q.checks >= 5, 'розділів ' + q.checks);
  ok('чотири «з обмеженням» піднімають прапорець порога', warnClicks >= 4 && !thr.flagHidden,
     'натиснуто ' + warnClicks + ' · ' + thr.lim + ' · ' + String(thr.flag).slice(0, 60));

  const stopped = await p.evaluate(() => {
    const s = document.querySelector('#qblocks .opt.r-stop');
    if (s) s.click();
    return !!s;
  });
  await p.waitForTimeout(400);
  const verd = await p.evaluate(() => ({
    v: (document.getElementById('q-verdict') || {}).textContent,
    c: (document.getElementById('q-verdict') || {}).className,
  }));
  ok('відповідь «стоп» дає вердикт «не наш»', stopped && /stop/.test(verd.c), verd.v + ' | ' + verd.c);

  // --- 7. анкета клієнта ---------------------------------------------------
  // Блоки процесів сховані до галочки, тому рахуємо тільки **видимі** розділи й поля:
  // у DOM лежать усі 21 розділ, а показано має бути 6 постійних.
  await p.getByText('АНКЕТА ДЛЯ КЛІЄНТА', { exact: false }).first().click();
  await p.waitForTimeout(600);
  const VIS = () => {
    const vis = el => !!(el.offsetParent || el.getClientRects().length);
    return {
      intro: (document.getElementById('f-intro') || {}).textContent.replace(/\s+/g, ' ').trim(),
      secsAll: document.querySelectorAll('#f-body .fsec').length,
      secsVis: Array.from(document.querySelectorAll('#f-body .fsec')).filter(vis).length,
      fieldsVis: Array.from(document.querySelectorAll('#f-body .ffield')).filter(vis).length,
      procs: document.querySelectorAll('#f-body .fprocs .fopt').length,
    };
  };
  const f = await p.evaluate(VIS);
  ok('анкета: вступ називає межу про облік', /облік/i.test(f.intro), f.intro.slice(0, 120));
  ok('анкета: постійні розділи видні, блоки процесів сховані',
     f.secsVis >= 4 && f.secsVis < f.secsAll, 'видно ' + f.secsVis + ' із ' + f.secsAll);
  ok('анкета: 15 процесів на вибір', f.procs === 15, 'процесів ' + f.procs);

  await p.evaluate(() => {
    const i = document.querySelector('#f-body .fprocs .fopt input');
    if (i) i.click();
  });
  await p.waitForTimeout(500);
  const f2 = await p.evaluate(VIS);
  ok('галочка процесу відкриває блок питань', f2.fieldsVis > f.fieldsVis,
     'було видно ' + f.fieldsVis + ', стало ' + f2.fieldsVis);

  await p.evaluate(() => { const b = document.getElementById('f-btn'); if (b) b.click(); });
  await p.waitForTimeout(300);
  const fo = await p.evaluate(() => {
    const t = document.getElementById('f-out');
    return { hidden: t ? t.hidden : true, len: t ? (t.value || '').length : 0,
             head: t ? (t.value || '').slice(0, 60) : '' };
  });
  ok('анкета: «Скопіювати відповіді» дає текст', !fo.hidden && fo.len > 40,
     fo.len + ' символів: ' + fo.head);

  ok('помилок JS немає на всіх трьох сторінках', errs.length === 0, errs.slice(0, 3).join(' || '));

  await b.close();
  fs.rmSync(path.dirname(tmp), { recursive: true, force: true });

  let bad = 0;
  for (const r of out) {
    if (!r.ok) bad++;
    console.log((r.ok ? 'ok     ' : 'ПРОВАЛ ') + r.name + (r.detail ? '  [' + r.detail + ']' : ''));
  }
  console.log('\nпройшло ' + (out.length - bad) + ' із ' + out.length);
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error('тест упав: ' + (e && e.stack || e)); process.exit(1); });
