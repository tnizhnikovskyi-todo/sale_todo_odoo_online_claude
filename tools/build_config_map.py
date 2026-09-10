# -*- coding: utf-8 -*-
"""Збирає data/config-map.json — карту налаштування контуру.

Що це таке. У journalі перевірки (data/verify.json) у кожного пункту складу робіт є
поле «де»: прозою написано, у якій моделі Odoo і яким шляхом у меню це налаштовується.
Проза добра для людини й погана для інструмента. Цей скрипт витягає з неї структуру:
для кожного пункту — перелік моделей, перелік полів і шлях у меню.

Навіщо. Карта — вхід для двох речей: процедури збірки (tools/build_runbook.py) і
майбутнього apply-config. Вона ж показує покриття: скільки пунктів мають машинно
читану адресу, а скільки лишаються прозою.

Чого карта НЕ робить. Вона не рецепт: у ній немає значень полів і порядку викликів
усередині пункту. Щоб зʼявився apply-config, у verify.json потрібне окреме поле
«рецепт» — про це сказано в docs/setup-runbook.md.

Перелік моделей звірений із живою базою edu-online-todo 09.09.2026: кандидати з «де»
перевірені запитом до ir.model, і в MODELS лишилися тільки ті, що справді існують.
Щоб перезвірити на іншій базі: зібрати кандидатів регуляркою TOKEN, спитати
ir.model.search_read([('model','in',кандидати)]) і порівняти з MODELS.
"""

import collections
import io
import json
import re
import sys

VERIFY = 'data/verify.json'
PRICE = 'data/price.json'
OUT = 'data/config-map.json'

TOKEN = re.compile(r'\b[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\b')
NOT_MODEL_SUFFIX = ('.py', '.md', '.json', '.html', '.csv', '.odoo', '.com')

# Звірено з ir.model на живій базі 09.09.2026 — див. docstring.
# Три моделі data_merge.* додано 10.09.2026 тим самим запитом: застосунок
# «Чищення даних» ставиться окремо, у стандартній базі його немає.
MODELS = set("""
account.analytic.account account.analytic.line account.analytic.plan
account.bank.statement account.bank.statement.line account.invoice.report
account.journal account.move account.payment account.payment.register
account.payment.term account.report
approval.approver approval.category approval.category.approver
approval.product.line approval.request purchase.requisition purchase.requisition.line
base.automation blog.blog blog.post budget.analytic budget.line calendar.event
crm.lead crm.stage crm.tag crm.team crm.team.member data_merge.group
data_merge.model data_merge.rule delivery.carrier
digest.digest documents.access documents.document documents.sharing documents.tag
helpdesk.sla helpdesk.sla.status helpdesk.stage helpdesk.tag helpdesk.team
helpdesk.ticket hr.department hr.employee hr.expense hr.leave
hr.leave.allocation hr.leave.type
ir.actions.act_window ir.actions.act_window.view ir.actions.report
ir.actions.server ir.attachment ir.config_parameter ir.cron ir.default
ir.filters ir.model ir.model.fields ir.rule ir.sequence ir.ui.menu ir.ui.view
knowledge.article loyalty.program loyalty.reward loyalty.rule delivery.price.rule
mail.activity mail.activity.type mail.alias
mail.alias.domain mail.template maintenance.equipment maintenance.request
maintenance.team mrp.bom mrp.production mrp.report mrp.workcenter
mrp.workcenter.productivity mrp.workorder payment.provider planning.role
planning.slot pos.config pos.order pos.payment pos.payment.method pos.session
product.attribute product.attribute.value product.category product.pricelist
product.pricelist.item product.pricing product.product product.public.category
product.supplierinfo product.tag product.template
product.template.attribute.line project.project project.task project.task.type
properties.base.definition purchase.order purchase.order.line purchase.report
purchase.requisition report.layout res.company res.currency res.currency.rate
res.groups res.groups.privilege res.lang res.partner res.partner.bank res.users
resource.calendar sale.advance.payment.inv sale.order sale.order.line
sale.order.template sale.order.template.line sale.rental.report sale.report
sale.subscription.plan sale.temporal.recurrence sign.document sign.item
sign.request sign.template spreadsheet.dashboard spreadsheet.dashboard.group
stock.inventory.conflict stock.location stock.lot stock.move stock.move.line
stock.picking stock.picking.type stock.putaway.rule stock.quant stock.scrap
stock.warehouse uom.uom utm.campaign utm.source website website.menu
website.page worksheet.template confirm.stock.sms
""".split())

# Токени, які виглядають як модель, але нею не є — перевірено тим самим запитом.
# Тримаємо явно, щоб карта не «знаходила» їх знову після правки нот.
NOT_MODELS = set("""
account.analytic account.bank account.invoice approval.product auth_totp.policy
confirm.stock ir.actions ir.ui o.company_id order_line.discount
point_of_sale.report_saledetails product.public project_enterprise.project_task_map_view
properties.base sale.advance sale.rental sale.subscription sale.temporal
stock.inventory stock.putaway website.favicon website.logo website.robots_txt
account.report_invoice_with_payments o.company_id.logo o.invoice_line_ids
product.produce_delay
""".split())


# ── Модулі Odoo, згадані в нотатках ──────────────────────────────────────────
# У полі «де» трапляються не тільки моделі, а й **модулі**: «worksheet +
# industry_fsm_report», «застосунок data_cleaning», «spreadsheet_dashboard_edition —
# установлений». Раніше такі пункти виглядали як «без адреси в карті», хоча адреса в
# них найконкретніша з можливих: щоб пункт працював, модуль має бути в базі.
#
# Перелік звірений із `ir.module.module` живої бази (372 встановлені модулі), бо
# відрізнити модуль від назви поля за виглядом неможливо: `partner_id`, `date_start`,
# `allocated_hours` — теж snake_case. Тому тут лише ті, що справді згадані в журналі.
#
# AUTO — модулі з `auto_install = true`: вони приходять самі разом із залежностями й
# у `apps` позиції їх не має бути. Це не дрібниця: без цього поділу перевірка
# «модуль згаданий, а в apps його немає» дала б шість хибних тривог із шести.
MODULES = set("""
account_bank_statement_import account_budget auth_totp base_import data_cleaning
documents_hr hr_skills industry_fsm_report industry_fsm_stock mail_mobile mrp_workorder
point_of_sale pos_hr pos_loyalty product_expiry project_enterprise
sale_purchase_inter_company_rules spreadsheet_dashboard_edition timesheet_grid web_map
web_mobile website_helpdesk website_sale_collect website_sale_stock worksheet
""".split())
AUTO = set("""
account_bank_statement_import auth_totp data_cleaning mail_mobile web_map web_mobile
""".split())


def split_de(de):
    """Розкладає поле «де» на моделі, поля й шлях у меню."""
    models, fields, unknown = [], [], []
    for m in TOKEN.finditer(de):
        tok = m.group(0)
        if tok.endswith(NOT_MODEL_SUFFIX):
            continue
        if tok in MODELS:
            if tok not in models:
                models.append(tok)
            continue
        # найдовший префікс, який є моделлю → решта це поле або метод
        parts = tok.split('.')
        hit = None
        for k in range(len(parts) - 1, 0, -1):
            pref = '.'.join(parts[:k])
            if pref in MODELS:
                hit = pref
                break
        if hit:
            if hit not in models:
                models.append(hit)
            if tok not in fields:
                fields.append(tok)
        elif tok not in NOT_MODELS and tok not in unknown:
            unknown.append(tok)
    # шлях у меню: усе, що після «·» і містить стрілку
    path = ''
    for chunk in de.split('·'):
        if '→' in chunk:
            path = chunk.strip()
            break
    return models, fields, path, unknown


def main():
    verify = json.load(io.open(VERIFY, encoding='utf-8'))
    price = json.load(io.open(PRICE, encoding='utf-8'))
    names = {}
    apps = {}
    for g in price['групи']:
        for it in g['items']:
            names[it['id']] = it['n']
            apps[it['id']] = it.get('apps', [])

    out = collections.OrderedDict()
    out['_схема'] = collections.OrderedDict([
        ('що це', 'карта налаштування: пункт складу робіт → моделі Odoo, поля й шлях у меню'),
        ('джерело', 'поле «де» з data/verify.json; перелік моделей звірений із ir.model'),
        ('чого немає', 'значень полів і порядку викликів усередині пункту — це не рецепт'),
        ('генерується', 'python3 tools/build_config_map.py'),
    ])
    out['база звірки'] = verify.get('база', '')
    out['позиції'] = collections.OrderedDict()

    stat = collections.Counter()
    model_use = collections.Counter()
    unknown_all = collections.Counter()
    no_addr = []
    module_use = collections.Counter()
    app_gaps = []
    own_apps = {}
    for g in price['групи']:
        for it in g['items']:
            own_apps[it['id']] = set(
                m for mm in (it.get('apps') or {}).values() for m in mm)

    for g in price['групи']:
        for it in g['items']:
            pid = it['id']
            block = collections.OrderedDict([('n', names[pid]),
                                             ('застосунки', apps[pid]),
                                             ('рівні', collections.OrderedDict())])
            for lk in ('1', '2', '3'):
                items = verify['позиції'].get(pid, {}).get(lk, {}).get('пункти', {})
                rows = []
                for txt, st in items.items():
                    stat['пунктів'] += 1
                    de = st.get('де', '') or ''
                    models, fields, path, unknown = split_de(de)
                    mods = sorted(set(re.findall(
                        r'\b([a-z][a-z0-9]+(?:_[a-z0-9]+)+)\b', de)) & MODULES)
                    for mo in mods:
                        module_use[mo] += 1
                        # Модуль, який не ставиться сам, мусить бути в apps позиції —
                        # інакше пункт продано, а застосунку в базі клієнта не буде.
                        if mo not in AUTO and mo not in own_apps.get(pid, set()):
                            app_gaps.append('%s р.%s «%s»: модуль %s згаданий у нотатці, '
                                            'але його немає в apps позиції' % (pid, lk, txt, mo))
                    for mm in models:
                        model_use[mm] += 1
                    for uu in unknown:
                        unknown_all[uu] += 1
                    if models:
                        stat['з моделями'] += 1
                    else:
                        no_addr.append('%s р.%s · %s' % (pid, lk, txt))
                    if path:
                        stat['зі шляхом у меню'] += 1
                    rows.append(collections.OrderedDict([
                        ('пункт', txt),
                        ('моделі', models),
                        ('модулі', mods),
                        ('поля', fields),
                        ('шлях', path),
                    ]))
                if rows:
                    block['рівні'][lk] = rows
            out['позиції'][pid] = block

    out['зведення'] = collections.OrderedDict([
        ('пунктів', stat['пунктів']),
        ('з моделями', stat['з моделями']),
        ('без машинної адреси', stat['пунктів'] - stat['з моделями']),
        ('зі шляхом у меню', stat['зі шляхом у меню']),
        ('різних моделей', len(model_use)),
        ('пунктів із модулями', sum(1 for pid in out['позиції']
                                    for lk in out['позиції'][pid]['рівні']
                                    for r in out['позиції'][pid]['рівні'][lk]
                                    if r['модулі'])),
        ('різних модулів', len(module_use)),
        ('топ моделей', collections.OrderedDict(model_use.most_common(15))),
    ])
    out['без машинної адреси'] = no_addr
    out['модулі в нотатках'] = collections.OrderedDict(
        sorted(module_use.items(), key=lambda x: (-x[1], x[0])))

    io.open(OUT, 'w', encoding='utf-8').write(
        json.dumps(out, ensure_ascii=False, indent=1) + '\n')

    print('OK: %s — %d пунктів, %d з моделями, %d без адреси, %d різних моделей'
          % (OUT, stat['пунктів'], stat['з моделями'],
             stat['пунктів'] - stat['з моделями'], len(model_use)))
    print('    шлях у меню вказаний у %d пунктах' % stat['зі шляхом у меню'])
    if unknown_all:
        print('    УВАГА: токени, схожі на модель, але невідомі — перевірити на базі '
              'і додати в MODELS або NOT_MODELS:')
        for tok, n in unknown_all.most_common(12):
            print('      %-44s ×%d' % (tok, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
    if app_gaps:
        print('  ⚠ модуль згаданий у нотатці, але його немає в apps позиції:')
        for g_ in app_gaps:
            print('     %s' % g_)
        print('     (модулі з auto_install у цю перевірку не входять — вони ставляться самі)')
