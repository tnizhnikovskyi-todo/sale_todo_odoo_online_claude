# Процедура збірки бази клієнта

**Згенеровано** `tools/build_runbook.py` з `data/price.json` і `data/config-map.json`.
Руками не правити — правити джерела й перезібрати.

Цей документ відповідає на два питання, на які прайс не відповідає: **у якому порядку**
налаштовувати куплені позиції і **за якою адресою в Odoo** лежить кожен пункт складу
робіт. Що саме куплено — видно в калькуляторі; персональний чек-лист по пунктах —
на четвертій сторінці калькулятора.

## Перед початком

1. **План підписки — Custom.** Не тому, що ми користуємось Studio (не користуємось), а
   тому, що налаштування виконується через зовнішнє API, а воно є **тільки на Custom**.
   Мультикомпанійність — теж лише там. Підписку оформлює клієнт сам.
2. **Ключ API** просимо зі строком дії на час робіт. У репозиторії ключ не зберігається.
3. **Українська локалізація стане сама** разом із застосунком рахунків: план `ua_psbo`,
   близько 700 рахунків і ставки ПДВ. Ми їх **не налаштовуємо й не супроводжуємо** —
   сказати клієнтові вголос до того, як він це побачить.
4. **Обліку, податків і зарплати в базі не робимо.** Це межа контуру, не обмеження Odoo.

## Порядок позицій

Порядок порахований із жорстких залежностей прайсу: позиція не може йти раніше за ту,
без якої вона технічно неможлива. Позиції, яких клієнт не купив, просто пропускаються —
порядок решти від цього не змінюється.

| № | Позиція | Група | Іде після |
|---:|---|---|---|
| 1 | **Експрес-діагностика** | Вхід у роботу | — |
| 2 | **База** | Основа | — |
| 3 | **Рахунки та оплати** | Основа | — |
| 4 | **Склад** | Закупівлі, склад, виробництво | — |
| 5 | **Міграція довідників** | Основа | Склад |
| 6 | **Мультикомпанійність** | Основа | Рахунки та оплати |
| 7 | **Навчання команди** | Основа | — |
| 8 | **CRM** | Продажі й клієнти | — |
| 9 | **Продажі** | Продажі й клієнти | Рахунки та оплати |
| 10 | **Сайт і каталог** | Продажі й клієнти | — |
| 11 | **Інтернет-магазин** | Продажі й клієнти | Продажі; Склад; Рахунки та оплати |
| 12 | **Точка продажу** | Продажі й клієнти | Склад; Рахунки та оплати |
| 13 | **Закупівлі** | Закупівлі, склад, виробництво | Рахунки та оплати |
| 14 | **Виробництво** | Закупівлі, склад, виробництво | Склад |
| 15 | **Проєкти й таймшити** | Проєкти й сервіс | Продажі; Рахунки та оплати |
| 16 | **Виїзні роботи** | Проєкти й сервіс | Продажі; Склад; Рахунки та оплати |
| 17 | **Планування** | Проєкти й сервіс | одна з: Проєкти й таймшити, Виїзні роботи |
| 18 | **Сервісні заявки** | Проєкти й сервіс | — |
| 19 | **Підписки** | Проєкти й сервіс | Продажі; Рахунки та оплати |
| 20 | **Оренда** | Проєкти й сервіс | Продажі; Склад; Рахунки та оплати |
| 21 | **Обслуговування обладнання** | Проєкти й сервіс | — |
| 22 | **Управлінський облік** | Фінанси й адміністрування | Рахунки та оплати |
| 23 | **Витрати співробітників** | Фінанси й адміністрування | Рахунки та оплати |
| 24 | **Персонал і відпустки** | Фінанси й адміністрування | — |
| 25 | **Документи й підписи** | Фінанси й адміністрування | — |
| 26 | **Дашборди й звіти** | Аналітика й документи | — |
| 27 | **Друковані форми** | Аналітика й документи | — |

## Що робити в кожній позиції

### Експрес-діагностика


#### Рівень 1

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| розмова про поточний процес | — |  |
| перелік систем, що вже є | — |  |
| перевірка меж нашого контуру | — |  |
| орієнтовний набір позицій | — | калькулятор: вибір відповіді → позиція + рівень |
| усна відповідь про строк і діапазон ціни; ціна фіксується письмово | — |  |
| перелік того, чого не буде | — |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| розбір двох-трьох процесів | — |  |
| письмова пропозиція з набором | — |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| зустріч на місці | — |  |
| опитування кількох підрозділів | — |  |
| коротка карта процесів | — |  |

### База

**Застосунки (усі рівні):** `base`, `contacts`, `mail`, `board`

#### Рівень 1

Доставити застосунки: `base`, `contacts`, `mail`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| компанія з реквізитами | `res.company` | Налаштування → Користувачі та компанії → Компанії |
| українська мова інтерфейсу, часовий пояс і валюта UAH | `res.lang`, `res.users`, `res.company`<br>поля: `res.users.tz`, `res.company.currency_id` |  |
| користувачі та групи доступу | `res.users`, `res.groups.privilege`<br>поля: `res.users.group_ids` |  |
| довідник контрагентів | `res.partner` |  |
| налаштування пошти й повідомлень | `mail.alias.domain`, `res.users`<br>поля: `res.users.notification_type` |  |
| нумерація документів: префікс, рік, лічильник | `ir.sequence` | Налаштування → Технічні → Послідовності |
| двофакторна автентифікація для всіх працівників | `ir.config_parameter` | Налаштування → Права доступу |
| оглядова сесія 1 година із записом | — |  |

#### Рівень 2

Доставити застосунки: `board`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| права роздільні за ролями | `res.users`<br>поля: `res.users.group_ids` |  |
| шаблони листів і підписи | `mail.template`, `res.partner`, `res.users`<br>поля: `res.users.signature` |  |
| дашборд під роль | `spreadsheet.dashboard`, `spreadsheet.dashboard.group`<br>поля: `spreadsheet.dashboard.group_ids` |  |
| власні поля в картці контрагента (штатно) | `properties.base.definition`, `ir.model.fields` |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| права за ролями і командами; видимість за підрозділом — правилами записів (там, де в моделі є поле підрозділу або власне поле) | `ir.rule`, `ir.model.fields`<br>поля: `ir.model.fields.groups` |  |
| кілька офісів або підрозділів у структурі компанії (склади — у позиції «Склад») | `res.company`<br>поля: `res.company.parent_id` |  |
| правила видимості записів (правила записів доменом, без коду) | `ir.rule`<br>поля: `ir.rule.domain_force` | Налаштування → Технічні → Правила записів |
| обов’язковість і значення за замовчуванням | `ir.model.fields`, `ir.default`, `stock.putaway.rule`<br>поля: `ir.model.fields.required` |  |

### Рахунки та оплати

**Застосунки (усі рівні):** `account`, `product`, `uom`

#### Рівень 1

Доставити застосунки: `account`, `product`, `uom`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| журнали продажів, купівель, банку й каси | `account.journal` |  |
| умови оплати й банківські реквізити в документах | `account.payment.term`, `res.partner.bank`, `account.journal`<br>поля: `account.journal.bank_account_id` |  |
| довідник номенклатури: категорії, одиниці виміру, внутрішні коди | `product.template`, `product.category`, `uom.uom` |  |
| перевірка стандартного бланка рахунку | `ir.actions.report` |  |
| нумерація рахунків і платежів | `account.journal`<br>поля: `account.journal.code` |  |
| реєстрація оплат і зіставлення з рахунками | `account.payment.register`, `account.payment`<br>поля: `account.payment.state` | account.payment.register → action_create_payments |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька банківських рахунків і кас | `account.journal` |  |
| імпорт банківської виписки CAMT.053 / CSV / OFX із мапінгом колонок | — |  |
| поля реквізитів у документі | `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| журнали, нумерація й реквізити для кожної юрособи | `account.journal`<br>поля: `account.journal.company_id` |  |
| валютні рахунки; курс вводиться вручну або імпортом | `account.journal`, `res.currency.rate`<br>поля: `account.journal.currency_id` |  |
| звірка виписки з документами й контроль незакритих | `account.bank.statement.line` |  |

### Склад

**Застосунки (усі рівні):** `stock`, `product`, `uom`, `product_expiry`, `stock_account`, `account`
**Попередити:** без «Продажі» — відгрузки народжуються із замовлень клієнта; без Продажів — ручні переміщення
**Попередити:** без «Закупівлі» — приходи народжуються із замовлень постачальнику; без Закупівель — ручні
**Попередити:** без «Управлінський облік» — інвентаризація з відхиленнями в грошах — оцінка запасів у позиції «Управлінський облік»
**Попередити:** без «Рахунки та оплати» — грошові відхилення інвентаризації проводяться в журнал — потрібні налаштовані рахунки

#### Рівень 1

Доставити застосунки: `stock`, `product`, `uom`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| складський бік номенклатури: одиниці виміру, штрихкоди, ознака складського обліку | `product.template`, `uom.uom`<br>поля: `product.template.is_storable` |  |
| один склад і локації зберігання | `stock.warehouse`, `stock.location` |  |
| прихід від постачальника | `stock.picking` | stock.picking типу «Надходження» → button_validate |
| відгрузка клієнту | `stock.picking`, `confirm.stock.sms` |  |
| звіт про поточні залишки | `stock.quant` |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька локацій і переміщення між ними | `stock.picking`, `stock.move` |  |
| облік партій або серійних номерів | `product.template`, `stock.lot`<br>поля: `product.template.tracking` |  |
| резервування під замовлення | `stock.picking`, `stock.move`<br>поля: `stock.picking.state`, `stock.move.availability` |  |
| власні поля в товарі й переміщенні (штатно) | `stock.picking.type`, `stock.picking`, `product.category`<br>поля: `stock.picking.type.picking_properties_definition`, `stock.picking.picking_properties`, `product.category.product_properties_definition` | stock.picking.type.picking_properties_definition → stock.picking.picking_properties |

#### Рівень 3

Доставити застосунки: `product_expiry`, `stock_account`, `account`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| інвентаризації з відхиленнями (факт / облік / різниця) | `stock.quant`, `stock.inventory.conflict` |  |
| кілька складів; розмежування доступу — через окремі юрособи (потребує позиції «Мультикомпанійність») | `stock.warehouse` |  |
| окреме робоче місце комірника: свій пункт меню, своє подання операцій і свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |
| терміни придатності партій — штатний модуль Expiration Dates | `product.template`, `stock.lot` |  |

### Міграція довідників

**Застосунки (усі рівні):** `base_import`, `product`, `stock`, `sale`, `purchase`, `account`
**Спершу має бути:** Склад
**Попередити:** без «Продажі» — «перенесення цін і умов» — це прайси й умови оплати Продажів
**Попередити:** без «Продажі» — відкриті замовлення клієнтів — документи Продажів
**Попередити:** без «Закупівлі» — відкриті замовлення постачальникам — документи Закупівель
**Попередити:** без «Рахунки та оплати» — початкові сальдо контрагентів заносяться в журнали обліку

#### Рівень 1

Доставити застосунки: `base_import`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| шаблон файлу під імпорт | — |  |
| перенесення контрагентів | `res.partner` |  |
| перенесення номенклатури | `product.template` |  |
| перевірка обов'язкових полів | — |  |
| звіт про завантажені записи | — |  |

#### Рівень 2

Доставити застосунки: `product`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| чищення дублів і нормалізація назв | `data_merge.model`, `data_merge.rule`, `data_merge.group` | Чищення даних → Дублі |
| зіставлення категорій і одиниць виміру | `product.category`, `uom.uom` |  |
| перенесення цін і умов | `product.pricelist` |  |
| службові поля для звірки з джерелом | `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

Доставити застосунки: `stock`, `sale`, `purchase`, `account`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| зведення кількох джерел в одну структуру | — |  |
| перенесення складських залишків | `stock.quant`, `stock.inventory.conflict` |  |
| перенесення відкритих замовлень і боргів | `sale.order`, `account.move`, `sale.advance.payment.inv`<br>поля: `sale.order.load`, `account.move.load` |  |
| подання для контролю перенесених даних | `ir.ui.view` |  |

### Мультикомпанійність

**Застосунки (усі рівні):** `base`, `product`, `account_inter_company_rules`, `sale_purchase_inter_company_rules`
**Спершу має бути:** Рахунки та оплати
**Попередити:** без «Продажі» — міжкомпанійні продажі потребують налаштованих Продажів в обох компаніях
**Попередити:** без «Закупівлі» — дзеркальне замовлення постачальнику — Закупівлі в компанії-покупці

#### Рівень 1

Доставити застосунки: `base`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| друга юрособа з реквізитами | `res.company` |  |
| спільні довідники | `res.partner`<br>поля: `res.partner.company_id` |  |
| вибір компанії в документах | `res.users`<br>поля: `res.users.company_ids` |  |
| окремі нумерації документів | `account.journal`<br>поля: `account.journal.code` |  |
| звіти в розрізі компанії | `account.report`<br>поля: `account.report.filter_multi_company` |  |

#### Рівень 2

Доставити застосунки: `product`, `account_inter_company_rules`, `sale_purchase_inter_company_rules`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| роздільні права за компаніями | `res.users`<br>поля: `res.users.company_ids` |  |
| окремі прайси й умови | `product.pricelist`<br>поля: `product.pricelist.company_id` |  |
| міжкомпанійні продажі — після підключення стандартних модулів Inter-Company | `res.company` |  |
| поле компанії у власних довідниках (штатно) | `properties.base.definition`, `res.company` |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| готові зведення по групі: продажі, закупівлі й рахунки колонками за компаніями — збережені як спільні звіти | `ir.filters`, `sale.report`, `purchase.report`, `account.invoice.report` |  |
| правила видимості за компаніями | `ir.rule` |  |

### Навчання команди


#### Рівень 1

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| сесія для ключових користувачів | — |  |
| демонстрація наскрізного процесу | `sale.order`, `stock.picking`, `account.move`, `account.payment` | sale.order → stock.picking → account.move → account.payment |
| відповіді на запитання | — |  |
| пам'ятка на одну сторінку | — |  |
| запис сесії | — |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| окремі сесії за ролями | `res.users`, `res.groups`<br>поля: `res.users.group_ids`, `res.groups.privilege_id` |  |
| письмові інструкції за ролями | — |  |
| тренувальні завдання на тестових даних | — |  |
| наповнена база знань за налаштованими блоками: де в базі що налаштовано і що робить роль | — |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| сесії для кількох груп | — |  |
| повторна сесія через два тижні | `mail.activity` |  |
| інструкція адміністратора системи | — |  |

### CRM

**Застосунки (усі рівні):** `crm`, `calendar`, `contacts`, `sales_team`, `utm`, `phone_validation`, `base_automation`

#### Рівень 1

Доставити застосунки: `crm`, `calendar`, `contacts`, `sales_team`, `utm`, `phone_validation`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| одна воронка зі стадіями | `crm.stage` |  |
| картка клієнта з контактами | `crm.lead`, `res.partner`<br>поля: `crm.lead.partner_id` | crm.lead.partner_id → res.partner |
| ведення угод і активностей | `crm.lead`, `mail.activity`, `mail.activity.type` |  |
| календар зустрічей і дзвінків | `calendar.event` |  |
| звіт за воронкою | `crm.lead` |  |

#### Рівень 2

Доставити застосунки: `base_automation`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька воронок під напрями | `crm.stage`<br>поля: `crm.stage.team_ids` |  |
| джерела лідів і мітки кампаній | `utm.source`, `utm.campaign`, `crm.tag` |  |
| автоматичні активності за стадіями | `base.automation`, `mail.activity.type`, `mail.activity` | Налаштування → Технічні → Правила автоматизації |
| власні поля в угоді та картці клієнта (штатно) | `crm.team`, `properties.base.definition`<br>поля: `crm.team.lead_properties_definition` |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| команди продажів і території | `crm.team`, `crm.team.member` |  |
| ціль команди на місяць (штатно); особисті плани — у дашборді Spreadsheet | `crm.team`, `crm.team.member`, `spreadsheet.dashboard`<br>поля: `crm.team.invoiced_target`, `crm.team.invoiced` |  |
| пріоритезація та скоринг лідів | `crm.lead`<br>поля: `crm.lead.automated_probability` |  |
| окреме робоче місце під роль: свій пункт меню, своє подання воронки й свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |
| кнопки-дії в картці угоди | `ir.actions.server` |  |

### Продажі

**Застосунки (усі рівні):** `sale_management`, `sale`, `sales_team`, `account`, `payment`, `utm`, `mrp`
**Спершу має бути:** Рахунки та оплати
**Попередити:** без «Склад» — для товарного бізнесу відгрузка й резерв — Склад; без нього товари продаються без залишків
**Попередити:** без «Виробництво» — «комплекти» як набори (kit) — специфікація в застосунку Виробництво; тип Combo перевірено на стенді: складові не списуються, заміною не є

#### Рівень 1

Доставити застосунки: `sale_management`, `sale`, `sales_team`, `account`, `payment`, `utm`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| шаблон комерційної пропозиції | `sale.order.template` |  |
| один прайс-лист | `product.pricelist`, `sale.order`<br>поля: `sale.order.pricelist_id` | product.pricelist → sale.order.pricelist_id → price_unit рядка |
| замовлення клієнта | `sale.order` |  |
| рахунок (стандартний бланк Odoo); акт виконаних робіт — власним бланком у позиції «Друковані форми» | `sale.advance.payment.inv`, `account.move` | sale.advance.payment.inv → account.move → action_post → PDF |
| звіт за продажами | `sale.report` |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька прайсів і сегментів | `product.pricelist` |  |
| правила знижок | `product.pricelist.item` |  |
| погодження КП у браузері за посиланням: клієнт приймає й підписує без реєстрації (штатний підпис у замовленні) | `sale.order`<br>поля: `sale.order.require_signature` | портальна форма підпису → /my/orders/<id>/accept |
| додаткові поля в замовленні та КП | `ir.model.fields`, `sale.order`, `ir.ui.view` |  |

#### Рівень 3

Доставити застосунки: `mrp`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| узгодження знижок за рівнями | `ir.model.fields`, `base.automation`, `ir.actions.server` |  |
| опційні позиції в пропозиції; набори з кількох товарів — потребують застосунку «Виробництво» | `sale.order.line`, `sale.order.template.line`<br>поля: `sale.order.line.is_optional`, `sale.order.template.line.is_optional` |  |
| автоматичні правила ціноутворення | `product.pricelist.item` |  |
| окреме робоче місце під сегмент: свій пункт меню, своє подання замовлень і свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |
| кнопки узгодження в замовленні | `ir.actions.server` |  |

### Сайт і каталог

**Застосунки (усі рівні):** `website`, `website_crm`, `crm`, `website_sale`, `sale`, `website_blog`
**Попередити:** без «CRM» — «форма звернення в CRM» створює ліди лише з позицією CRM; без неї форма надсилає лист на пошту
**Попередити:** без «Інтернет-магазин» — каталог товарів на сайті — це eCommerce: разом із ним з'являється кошик; його або ховаємо, або продаємо позицію «Інтернет-магазин»
**Попередити:** без «Продажі» — товари каталогу — довідник і ціни Продажів

#### Рівень 1

Доставити застосунки: `website`, `website_crm`, `crm`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| головна сторінка | `ir.ui.view`, `website.page`<br>поля: `ir.ui.view.arch` | ir.ui.view.arch сторінки (website.page → view_id): розмітка штатних блоків s_banner, s_three_columns |
| сторінка про компанію та контакти | `ir.ui.view`, `website.page`<br>поля: `ir.ui.view.copy` |  |
| форма звернення в CRM | `ir.ui.view`, `crm.lead`, `website.page`<br>поля: `ir.ui.view.arch` |  |
| базове SEO і метадані | `website.page`, `website`<br>поля: `website.robots_txt` |  |
| адаптація під мобільні | — |  |

#### Рівень 2

Доставити застосунки: `website_sale`, `sale`, `website_blog`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| каталог товарів з категоріями | `product.public.category`, `product.template` |  |
| блог або новини | `blog.blog`, `blog.post` |  |
| кілька форм під різні звернення | `ir.ui.view`, `website.page`<br>поля: `ir.ui.view.arch` | Сайт → Сторінки |
| атрибути товару для каталогу й фільтрів (штатно) | `product.attribute`, `product.attribute.value`, `product.template.attribute.line` |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| друга мова сайту | `res.lang`, `website`<br>поля: `website.language_ids` |  |
| складна структура меню | `website.menu`<br>поля: `website.menu.parent_id` |  |
| брендування: логотип і favicon сайту, кольори, шрифти й зображення в самих блоках, тема з переліку штатних | `website`<br>поля: `website.logo`, `website.favicon` |  |
| фільтри каталогу за атрибутами, тегами і ціною (штатно) | `product.attribute`, `product.tag`<br>поля: `product.tag.visible_to_customers` |  |

### Інтернет-магазин

**Застосунки (усі рівні):** `website_sale`, `website`, `sale`, `payment`, `delivery`, `account`, `portal`, `product`, `website_sale_stock`, `stock`, `website_sale_collect`, `loyalty`, `sale_loyalty`, `website_sale_loyalty`
**Спершу має бути:** Продажі; Склад; Рахунки та оплати
**Попередити:** без «Сайт і каталог» — магазин живе на сайті: головна, меню, тема — без позиції «Сайт» він висить на порожньому шаблоні
**Попередити:** без «Склад» — для фізичних товарів доставка — це відгрузка зі складу (документація 19.0: для обробки доставок потрібен застосунок Склад)

#### Рівень 1

Доставити застосунки: `website_sale`, `website`, `sale`, `payment`, `delivery`, `account`, `portal`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| товари з фото й описом | `product.template` |  |
| кошик і оформлення замовлення | — |  |
| оплата переказом на рахунок або при отриманні (онлайн-еквайринг — лише провайдером зі стандартного переліку Odoo; LiqPay, monobank, WayForPay, Fondy — немає) | `payment.provider` |  |
| один спосіб доставки з фіксованим тарифом (Нова Пошта, Укрпошта — без інтеграції, ТТН вручну) | `delivery.carrier` |  |
| лист-підтвердження замовлення | `mail.template`, `sale.order` |  |

#### Рівень 2

Доставити застосунки: `product`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| варіанти товарів і атрибути | `product.attribute`, `product.template.attribute.line` |  |
| кілька способів оплати зі стандартного переліку Odoo (українські еквайринги — немає) | `payment.provider` |  |
| кілька способів доставки з тарифами за правилами (вага / сума / зона); автотарифи й ТТН перевізників — немає | `delivery.carrier`, `delivery.price.rule`<br>поля: `delivery.carrier.delivery_type` | Магазин → Конфігурація → Способи доставки |
| атрибути й варіанти товару (штатно) | `product.attribute`, `product.product` |  |

#### Рівень 3

Доставити застосунки: `website_sale_stock`, `stock`, `website_sale_collect`, `loyalty`, `sale_loyalty`, `website_sale_loyalty`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| наявність зі складів у реальному часі | `product.template` |  |
| акції та промокоди | `loyalty.program`, `loyalty.rule`, `loyalty.reward`<br>поля: `loyalty.program.program_type` | Магазин → Знижки й лояльність |
| самовивіз з кількох точок | `delivery.carrier` |  |
| окреме робоче місце під замовлення магазину: свій пункт меню, своє подання й свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |
| поля логістики в замовленні | `ir.model.fields`, `ir.ui.view` |  |

### Точка продажу

**Застосунки (усі рівні):** `point_of_sale`, `stock`, `stock_account`, `account`, `barcodes`, `pos_hr`, `hr`, `loyalty`, `pos_loyalty`
**Спершу має бути:** Склад; Рахунки та оплати
**Попередити:** без «Склад» — Склад встановлюється разом із касою автоматично (документація 19.0); на базовому рівні товари можна вести без залишків
**Попередити:** без «Персонал і відпустки» — касири входять за PIN як співробітники (pos_hr) — потрібні картки

#### Рівень 1

Доставити застосунки: `point_of_sale`, `stock`, `stock_account`, `account`, `barcodes`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| одна каса з товарами | `pos.config`, `product.template`<br>поля: `product.template.available_in_pos` |  |
| продаж за готівку й карту | `pos.payment.method` |  |
| чек продажу й повернення | `pos.order` |  |
| відкриття й закриття зміни | `pos.session` | pos.session: opening_control → opened → closed |
| звіт за зміну | `ir.actions.report` |  |

#### Рівень 2

Доставити застосунки: `pos_hr`, `hr`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька кас і касирів | `pos.config`, `hr.employee`<br>поля: `hr.employee.pin` | pos_hr → hr.employee.pin |
| списання зі складу за продажем | `pos.config` |  |
| знижки на касі | `pos.config`<br>поля: `pos.config.manual_discount` |  |
| власний текст шапки й підвалу чека (штатно); власні поля замовлення POS для бекофісу | `pos.config`, `ir.model.fields`, `ir.ui.view`<br>поля: `pos.config.receipt_header` |  |

#### Рівень 3

Доставити застосунки: `loyalty`, `pos_loyalty`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька точок продажу | `pos.config` |  |
| програма лояльності | `loyalty.program` |  |
| роздільні склади за точками | `stock.warehouse`, `pos.config`<br>поля: `pos.config.warehouse_id` |  |
| окреме робоче місце для звірки змін: свій пункт меню, своє подання й свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |

### Закупівлі

**Застосунки (усі рівні):** `purchase`, `account`, `purchase_stock`, `stock`, `approvals`, `purchase_requisition`
**Спершу має бути:** Рахунки та оплати
**Попередити:** без «Склад» — «приймання товару» існує лише зі Складом (purchase_stock); без позиції — одно-кроковий прихід на склад за замовчуванням, залишки без контролю

#### Рівень 1

Доставити застосунки: `purchase`, `account`, `purchase_stock`, `stock`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| відбір і мітки постачальників | `res.partner` |  |
| замовлення постачальнику | `purchase.order`, `stock.picking` | purchase.order → button_confirm → stock.picking типу «прихід» |
| приймання товару | `stock.picking`<br>поля: `stock.picking.button_validate` |  |
| ціни постачальників | `product.supplierinfo` |  |
| звіт за закупівлями | `purchase.report` |  |

#### Рівень 2

Доставити застосунки: `approvals`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| заявки від підрозділів — у застосунку «Погодження» | `approval.category`, `approval.request`, `approval.product.line` |  |
| узгодження за сумою — штатний поріг, один рівень | `res.company` |  |
| контроль строків постачання | `product.supplierinfo`, `res.company`, `purchase.order.line`<br>поля: `product.supplierinfo.delay`, `res.company.days_to_purchase`, `purchase.order.line.date_planned` |  |
| поля умов постачання в замовленні | `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

Доставити застосунки: `purchase_requisition`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| порівняння пропозицій постачальників | `purchase.order`<br>поля: `purchase.order.alternative_po_ids` |  |
| багатокрокове узгодження закупки за сумою: ознака кроку й віза ролі | `purchase.order`, `base.automation` |  |
| рамкові договори; графік — датами приходу в замовленнях за договором | `purchase.requisition`, `purchase.requisition.line`, `purchase.order`<br>поля: `purchase.order.requisition_id` | Закупівлі → Угоди про закупівлю |
| подання для контролю цін | `ir.ui.view` |  |
| кнопки узгодження заявки | `ir.actions.server` |  |

### Виробництво

**Застосунки (усі рівні):** `mrp`, `stock`, `mrp_account`, `account`, `mrp_workorder`, `hr`
**Спершу має бути:** Склад
**Попередити:** без «Управлінський облік» — собівартість випуску проводиться через оцінку запасів (mrp_account)
**Попередити:** без «Персонал і відпустки» — облік часу операцій у цеховому інтерфейсі ведеться за співробітниками (перевірено на стенді)
**Попередити:** без «Рахунки та оплати» — собівартість випуску проводиться в журнал запасів

#### Рівень 1

Доставити застосунки: `mrp`, `stock`, `mrp_account`, `account`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| специфікація виробу (BoM) | `mrp.bom`, `mrp.bom.line` | Виробництво → Специфікації |
| набори (kit): специфікація типу «набір», списання складових без виробничого замовлення | `mrp.bom`<br>поля: `mrp.bom.type` |  |
| замовлення на виробництво | `mrp.production` |  |
| списання матеріалів | `stock.move.line`, `mrp.production`<br>поля: `stock.move.line.lot_id`, `mrp.production.button_mark_done` |  |
| випуск готової продукції | `stock.quant` |  |
| звіт про виконані замовлення | `mrp.report` |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька рівнів специфікацій | `mrp.bom` |  |
| напівфабрикати | `mrp.bom` |  |
| планування замовлень за строками | `mrp.production`<br>поля: `mrp.production.date_start` |  |
| поля специфікації під технологію | `ir.model.fields`, `mrp.bom`, `ir.ui.view` |  |

#### Рівень 3

Доставити застосунки: `mrp_workorder`, `hr`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| робочі центри й операції | `mrp.workcenter`, `mrp.routing.workcenter` |  |
| облік часу операцій у цеховому інтерфейсі — потребує «Співробітників» | `mrp.workorder`, `mrp.workcenter.productivity`, `hr.employee` |  |
| списання відходів на локацію втрат; оприбуткування зворотних — через побічні продукти | `stock.scrap`, `mrp.bom.byproduct` |  |
| подання нарядів і замовлень у бекофісі; цеховий інтерфейс — штатний | `ir.ui.view` |  |

### Проєкти й таймшити

**Застосунки (усі рівні):** `project`, `hr_timesheet`, `timesheet_grid`, `hr`, `hr_hourly_cost`, `analytic`, `sale_timesheet`, `sale_project`, `sale`, `account`, `project_account`, `account_budget`
**Спершу має бути:** Продажі; Рахунки та оплати
**Попередити:** без «Персонал і відпустки» — списання годин потребує картки співробітника на кожного виконавця (hr_timesheet залежить від hr); у Базі карток немає
**Попередити:** без «Управлінський облік» — «бюджети й контроль перевищень» — бюджети аналітики, рівень 3 позиції «Управлінський облік»

#### Рівень 1

Доставити застосунки: `project`, `hr_timesheet`, `timesheet_grid`, `hr`, `hr_hourly_cost`, `analytic`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| проєкти й задачі зі стадіями | `project.project`, `project.task.type` |  |
| виконавці та строки | `project.task` |  |
| списання годин на задачі | `account.analytic.line` |  |
| звіт за витраченим часом | `account.analytic.line` |  |
| статус проєктів на дашборді | `project.project` |  |
| картки виконавців-співробітників (без кадрового обліку) | `hr.employee` |  |

#### Рівень 2

Доставити застосунки: `sale_timesheet`, `sale_project`, `sale`, `account`, `project_account`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| ставки й рентабельність проєкту | `hr.employee`, `project.project`<br>поля: `hr.employee.hourly_cost` |  |
| рахунки за витраченим часом | `account.analytic.line`, `sale.advance.payment.inv` |  |
| шаблони проєктів під типові роботи | `project.project`<br>поля: `project.project.is_template` |  |
| власні поля в проєкті й задачі | `project.task`, `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

Доставити застосунки: `account_budget`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька типів проєктів з різними процесами | `project.task.type`<br>поля: `project.task.type.project_ids` |  |
| бюджети й контроль перевищень | `budget.analytic`, `budget.line` |  |
| наскрізна аналітика за клієнтами | `account.analytic.account` |  |
| окреме робоче місце під тип проєктів: свій пункт меню, своє подання й свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |
| кнопки переходу між стадіями | `ir.actions.server` |  |

### Виїзні роботи

**Застосунки (усі рівні):** `industry_fsm`, `project`, `project_enterprise`, `timesheet_grid`, `hr_timesheet`, `hr`, `industry_fsm_report`, `worksheet`, `industry_fsm_sale`, `industry_fsm_stock`, `sale`, `sale_stock`, `stock`, `account`
**Спершу має бути:** Продажі; Склад; Рахунки та оплати
**Попередити:** без «Проєкти й таймшити» — наряди — це задачі Проєктів; FSM створює власний проєкт, але стадії, таймшити й довідники спільні з позицією Проєкти, якщо вона є
**Попередити:** без «Персонал і відпустки» — час виконавця в наряді — таймшит співробітника; карток виконавців у Базі немає

#### Рівень 1

Доставити застосунки: `industry_fsm`, `project`, `project_enterprise`, `timesheet_grid`, `hr_timesheet`, `hr`, `industry_fsm_report`, `worksheet`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| наряди на виконавців | `project.project`, `project.task`<br>поля: `project.project.is_fsm` |  |
| графік виїздів | `project.task` |  |
| відмітка виконання | `project.task`<br>поля: `project.task.fsm_done` |  |
| звіт виконавця | `worksheet.template`, `project.task`<br>поля: `project.task.worksheet_template_id` |  |
| звіт за виїздами | `project.task` |  |
| картки виконавців-співробітників (без кадрового обліку) | `hr.employee` |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| карта виїздів за день у порядку планового часу (лінія маршруту — за наявності токена MapBox у клієнта) | `ir.ui.view`, `ir.actions.act_window`, `ir.actions.act_window.view`, `ir.ui.menu` |  |
| мобільний доступ виконавця | — |  |
| фото й підпис клієнта на місці | — |  |
| поля наряду під тип роботи | `project.project`, `ir.model.fields`, `ir.ui.view`<br>поля: `project.project.task_properties_definition` |  |

#### Рівень 3

Доставити застосунки: `industry_fsm_sale`, `industry_fsm_stock`, `sale`, `sale_stock`, `stock`, `account`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| планування виїздів по карті з урахуванням адрес (вручну) | `project.task`<br>поля: `project.task.sequence` | allow_resequence="true" у поданні карти → project.task.sequence |
| облік запчастин у наряді | — |  |
| підрядники — як користувачі з ліцензією Odoo (оплачує клієнт) або доступ до задач через Project Sharing без призначення виконавцем | `project.project`, `project.task`<br>поля: `project.project.privacy_visibility`, `project.task.user_ids` |  |
| мобільне подання виконавця | `ir.ui.view` |  |

### Планування

**Застосунки (усі рівні):** `planning`, `hr`, `resource`, `project_forecast`, `project`, `hr_skills`, `planning_hr_skills`
**Спершу має бути:** одна з: Проєкти й таймшити, Виїзні роботи
**Попередити:** без «Персонал і відпустки» — зміни призначаються співробітникам-ресурсам; ролі й доступність — у картці співробітника

#### Рівень 1

Доставити застосунки: `planning`, `hr`, `resource`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| календар завантаження команди | `planning.slot` |  |
| призначення виконавців на періоди | `planning.slot` |  |
| облік доступності | `resource.calendar`, `planning.slot`<br>поля: `planning.slot.allocated_hours` |  |
| перегляд конфліктів | `planning.slot`<br>поля: `planning.slot.overlap_slot_count` |  |
| звіт за завантаженням | `planning.slot` |  |
| картки виконавців-співробітників (без кадрового обліку) | `hr.employee` |  |

#### Рівень 2

Доставити застосунки: `project_forecast`, `project`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька команд і ролей | `planning.role`, `hr.employee`<br>поля: `hr.employee.planning_role_ids` |  |
| зміни й графіки роботи | `resource.calendar`, `resource.calendar.attendance` | Налаштування → Технічні → Робочі графіки |
| планування за ролями, проєктами й замовленнями | `planning.slot` |  |
| поля навичок і ролей виконавців (штатно) | `planning.role`, `planning.slot`<br>поля: `planning.role.slot_properties_definition`, `planning.slot.slot_properties` | planning.role.slot_properties_definition → planning.slot.slot_properties |

#### Рівень 3

Доставити застосунки: `hr_skills`, `planning_hr_skills`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| автопідбір за ролями і доступністю (Auto Plan); навички — довідково в картці співробітника | `planning.slot`<br>поля: `planning.slot.action_self_assign` |  |
| автопризначення відкритих змін; контроль перевантаження за індикатором годин | `planning.slot` |  |
| звіт планових годин проти доступних по періодах (pivot / Spreadsheet) | `planning.slot`, `resource.calendar`<br>поля: `planning.slot.allocated_hours` |  |
| окреме робоче місце керівника: свій пункт меню, своє подання завантаження й свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |

### Сервісні заявки

**Застосунки (усі рівні):** `helpdesk`, `portal`, `mail`, `website_helpdesk`, `website`, `knowledge`, `website_helpdesk_knowledge`
**Попередити:** без «Сайт і каталог» — веб-форма звернень — сторінка на сайті (website_helpdesk); портал заявок працює й без сайту, форма — ні

#### Рівень 1

Доставити застосунки: `helpdesk`, `portal`, `mail`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| одна черга заявок | `helpdesk.team`, `helpdesk.stage` |  |
| категорії та пріоритети | `helpdesk.tag`, `helpdesk.ticket`<br>поля: `helpdesk.ticket.priority` |  |
| призначення виконавця | `helpdesk.team` |  |
| листування в заявці | `helpdesk.ticket` |  |
| звіт за заявками | `helpdesk.ticket`<br>поля: `helpdesk.ticket.report.analysis` |  |

#### Рівень 2

Доставити застосунки: `website_helpdesk`, `website`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька черг за напрямами | `helpdesk.team`, `helpdesk.stage`<br>поля: `helpdesk.stage.team_ids` |  |
| SLA і контроль строків (штатні політики) | `helpdesk.sla`, `helpdesk.sla.status` |  |
| портал клієнта для звернень | `helpdesk.team`<br>поля: `helpdesk.team.use_website_helpdesk_form` |  |
| власні поля заявки під категорії (штатно) | `helpdesk.team`, `helpdesk.ticket`<br>поля: `helpdesk.team.ticket_properties`, `helpdesk.ticket.properties` | helpdesk.team.ticket_properties → helpdesk.ticket.properties |

#### Рівень 3

Доставити застосунки: `knowledge`, `website_helpdesk_knowledge`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| автоматична маршрутизація | `helpdesk.tag`, `helpdesk.team`<br>поля: `helpdesk.tag.assignment`, `helpdesk.team.assign_method` | helpdesk.tag.assignment (мітка → виконавці) |
| база знань (застосунок Knowledge) і типові відповіді; структура — ми, контент — клієнт | `knowledge.article` |  |
| звітність за виконанням SLA | `helpdesk.sla`, `helpdesk.sla.status`<br>поля: `helpdesk.sla.report.analysis` |  |
| окреме робоче місце команди: свій пункт меню, своє подання черги й свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |
| кнопки типових дій у заявці | `ir.actions.server` |  |

### Підписки

**Застосунки (усі рівні):** `sale_subscription`, `sale_management`, `sale`, `account`, `payment`
**Спершу має бути:** Продажі; Рахунки та оплати

#### Рівень 1

Доставити застосунки: `sale_subscription`, `sale_management`, `sale`, `account`, `payment`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| один тариф | `sale.subscription.plan` |  |
| договір з клієнтом | `sale.order`, `product.template`<br>поля: `product.template.recurring_invoice` |  |
| регулярний рахунок | `sale.order`, `account.move` | sale.order підписки → account.move за next_invoice_date |
| облік оплат | `account.payment.register` |  |
| звіт за активними підписками | `sale.order` |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька тарифів | `sale.subscription.plan` |  |
| автоматичне продовження з виставленням рахунку (автосписання з картки для UA недоступне) | `ir.cron`, `sale.order`<br>поля: `sale.order.next_invoice_date` |  |
| нагадування про оплату | `mail.template`, `base.automation` | Налаштування → Технічні → Шаблони листів і Правила автоматизації |
| поля тарифу в договорі | `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| розширення (upsell) з пропорційним донарахуванням; зменшення — без повернення коштів | `sale.order`<br>поля: `sale.order.prepare_upsell_order` |  |
| пропорційні нарахування — для послуг; для товарів не рахуються | `sale.order.line`<br>поля: `sale.order.line.recurring_invoice` |  |
| аналітика Retention і MRR; churn у відсотках — окремий дашборд | `sale.order`<br>поля: `sale.order.recurring_monthly` |  |
| подання для контролю продовжень | `ir.ui.view` |  |

### Оренда

**Застосунки (усі рівні):** `sale_renting`, `sale_management`, `sale`, `account`, `sale_stock_renting`, `stock`
**Спершу має бути:** Продажі; Склад; Рахунки та оплати

#### Рівень 1

Доставити застосунки: `sale_renting`, `sale_management`, `sale`, `account`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| об'єкти оренди | `product.template`<br>поля: `product.template.rent_ok` |  |
| видача й повернення | `sale.order` |  |
| тариф за період | `product.pricing`, `sale.temporal.recurrence` |  |
| договір і рахунок | `sale.order` | sale.order оренди → рахунок штатним майстром |
| звіт за орендою | `sale.rental.report` |  |

#### Рівень 2

Доставити застосунки: `sale_stock_renting`, `stock`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| графік оренд по товарах і серійниках (Gantt) | `product.template`<br>поля: `product.template.tracking` | Оренда → Графік |
| тарифи за різними періодами | `product.pricing` |  |
| бронювання наперед | `sale.order`, `res.company` |  |
| поля стану й комплектації об’єкта | `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| застава окремою позицією; оцінка пошкоджень — вручну | `product.template`, `sale.order.line` |  |
| технологічна пауза між орендами (штатно); ТО об’єктів — заявками в застосунку «Обслуговування», без автоматичного зв’язку з орендою | `product.template`, `maintenance.request`<br>поля: `product.template.preparation_time` |  |
| комплектація позиціями з серійниками; типові комплекти — шаблонами пропозицій | `sale.order.line`, `sale.order.template` |  |
| подання графіка під адміністратора | `ir.ui.view` |  |

### Обслуговування обладнання

**Застосунки (усі рівні):** `maintenance`, `stock`
**Попередити:** без «Персонал і відпустки» — обладнання закріплюється за співробітником (hr_maintenance ставиться автоматично, якщо є Співробітники); без них — лише за користувачем
**Попередити:** без «Склад» — «облік запчастин» — власного механізму в Обслуговуванні немає; лише списання чи переміщення на Складі

#### Рівень 1

Доставити застосунки: `maintenance`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| реєстр обладнання | `maintenance.equipment` |  |
| аварійні заявки | `maintenance.request` |  |
| призначення виконавця | `maintenance.request`, `maintenance.equipment`<br>поля: `maintenance.request.user_id`, `maintenance.equipment.maintenance_team_id` |  |
| історія робіт | `maintenance.request` |  |
| звіт за заявками | `maintenance.request` |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| планові роботи за графіком | `maintenance.request` |  |
| нагадування про регламент | `maintenance.request`<br>поля: `maintenance.request.schedule_date` |  |
| тривалість ремонтів і MTTR (штатно) | `maintenance.equipment` |  |
| поля обладнання під тип | `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

Доставити застосунки: `stock`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| MTBF, MTTR і прогноз наступної відмови (штатно); лічильник наробки — власним полем, вручну | `maintenance.equipment` |  |
| запчастини — списанням зі складу окремим переміщенням (потребує позиції «Склад») | `maintenance.request`, `stock.picking` |  |
| кілька майданчиків обслуговування | `maintenance.team`, `maintenance.equipment`, `stock.location`<br>поля: `maintenance.equipment.location_id` | maintenance.equipment.location_id → stock.location (НЕ текст: посилання на складську локацію) |
| подання регламентів і кнопки закриття | `ir.ui.view`, `ir.actions.server` |  |

### Управлінський облік

**Застосунки (усі рівні):** `account`, `account_accountant`, `account_reports`, `analytic`, `account_budget`
**Спершу має бути:** Рахунки та оплати

#### Рівень 1

Доставити застосунки: `account`, `account_accountant`, `account_reports`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| рахунки й каси | `account.journal` |  |
| облік надходжень і виплат | `account.payment`, `account.bank.statement.line` |  |
| звіт про рух коштів (стандартний Cash Flow) | `account.report` |  |
| заборгованість контрагентів | `account.report` |  |
| дашборд грошей | `account.journal` |  |

#### Рівень 2

Доставити застосунки: `analytic`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| напрями й аналітика витрат | `account.analytic.plan`, `account.analytic.account` |  |
| P&L за напрямами | `account.report`<br>поля: `account.report.filter_analytic_groupby` |  |
| взаєморозрахунки з деталізацією | `account.report` |  |
| аналітичні поля в документах | `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

Доставити застосунки: `account_budget`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| план-факт до P&L штатно; бюджети за напрямами — модуль Budget Management | `budget.analytic`, `budget.line` |  |
| кілька валют у документах і звітах; курс — вручну або імпортом: автозавантаження в Odoo є, але офіційного курсу НБУ серед джерел немає | `res.currency.rate`, `res.company`<br>поля: `res.company.currency_provider` |  |
| багатовимірна аналітика | `account.analytic.plan` |  |
| власні списки для звірки | `ir.ui.view` |  |
| поля бюджетних статей | `ir.model.fields`, `ir.ui.view` |  |

### Витрати співробітників

**Застосунки (усі рівні):** `hr_expense`, `hr`, `account`, `account_accountant`
**Спершу має бути:** Рахунки та оплати
**Попередити:** без «Персонал і відпустки» — витрати подає співробітник, узгоджує керівник з його картки — потрібні картки й ієрархія (hr_expense залежить від hr)
**Попередити:** без «Управлінський облік» — «звірка з корпоративними картками» — банківська виписка й звірка в позиції «Управлінський облік»

#### Рівень 1

Доставити застосунки: `hr_expense`, `hr`, `account`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| подання витрат співробітником | `hr.expense` |  |
| категорії витрат | `product.template`<br>поля: `product.template.can_be_expensed` |  |
| прикріплення чеків | `hr.expense` |  |
| компенсація | `account.payment.register` |  |
| звіт за витратами | `hr.expense` |  |
| картки виконавців-співробітників (без кадрового обліку) | `hr.employee` |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| узгодження керівником | `hr.expense`<br>поля: `hr.expense.state` |  |
| додатковий крок узгодження, якщо сума перевищує ліміт категорії (правилом); жорстка блокада — поза периметром | `hr.expense`, `base.automation` |  |
| звіти за підрозділами | `hr.department`, `hr.expense`, `hr.employee`<br>поля: `hr.employee.department_id` |  |
| поля категорій і лімітів | `product.category`, `ir.model.fields`, `ir.ui.view`<br>поля: `product.category.product_properties_definition` |  |

#### Рівень 3

Доставити застосунки: `account_accountant`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька рівнів узгодження | `approval.category`, `approval.category.approver`<br>поля: `approval.category.approver_ids` | approval.category.approver_ids → окремі записи approval.category.approver (user_id, sequence, required) |
| аванс співробітнику — платежем із зіставленням у позиції «Рахунки та оплати» | `account.payment.register`, `account.bank.statement.line` |  |
| зіставлення витрат «оплачено компанією» з імпортованою банківською випискою; автосинхронізація з банком UA — не гарантується | `account.bank.statement.line`, `hr.expense`<br>поля: `hr.expense.payment_mode` |  |
| кнопки узгодження у витраті | `ir.actions.server` |  |

### Персонал і відпустки

**Застосунки (усі рівні):** `hr`, `hr_holidays`, `calendar`, `resource`, `documents_hr`, `documents`
**Попередити:** без «Документи й підписи» — «кадрові документи» — застосунок Документи (documents_hr) або вкладення в картці без сховища

#### Рівень 1

Доставити застосунки: `hr`, `hr_holidays`, `calendar`, `resource`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| картки співробітників | `hr.employee` |  |
| структура підрозділів | `hr.department`<br>поля: `hr.department.parent_id` |  |
| заявки на відпустку | `hr.leave` | hr.leave: request_date_from/to → number_of_days |
| облік залишку днів | `hr.leave.allocation`, `hr.leave` |  |
| календар відсутностей | `hr.leave` |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| типи відсутностей | `hr.leave.type` |  |
| узгодження керівником | `hr.leave.type`<br>поля: `hr.leave.type.leave_validation_type` |  |
| звіти за відсутностями | `hr.leave` |  |
| власні поля в картці співробітника (штатно) | `res.company`, `hr.employee`<br>поля: `res.company.employee_properties_definition`, `hr.employee.employee_properties` | res.company.employee_properties_definition → hr.employee.employee_properties |

#### Рівень 3

Доставити застосунки: `documents_hr`, `documents`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| графіки роботи й змінність | `resource.calendar`, `hr.employee`<br>поля: `hr.employee.resource_calendar_id` |  |
| кілька підрозділів з різними правилами | `hr.leave.type`, `hr.department`<br>поля: `hr.leave.type.company_id` |  |
| файли співробітника в Документах, версії умов найму | `documents.document` |  |
| окреме робоче місце кадровика: свій пункт меню, своє подання й свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |

### Документи й підписи

**Застосунки (усі рівні):** `documents`, `sign`

#### Рівень 1

Доставити застосунки: `documents`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| сховище документів | `documents.document` |  |
| структура папок і теги | `documents.document`, `documents.tag`<br>поля: `documents.document.folder_id` |  |
| права доступу до папок | `documents.document`, `documents.access`, `documents.sharing`<br>поля: `documents.document.access_internal` |  |
| пошук за документами | `documents.document` |  |
| прикріплення до записів | `documents.document` |  |

#### Рівень 2

Доставити застосунки: `sign`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| узгодження документів через застосунок «Погодження» (запит із вкладенням і погоджувачами) | `approval.category`, `approval.request` |  |
| електронний підпис Odoo Sign — підписання у браузері за посиланням | `sign.template` |  |
| нагадування про підписання | `sign.request` |  |
| поля типу документа | `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кроки погодження з порядком і обовʼязковістю кожного погоджувача; умова «залежно від суми» — правилом; маршрутів із розгалуженнями й ескалаціями немає | `approval.approver`, `approval.request`, `base.automation` |  |
| шаблони для підпису (Sign); документ із реквізитами запису — друкованим бланком (позиція «Друковані форми») | `ir.attachment`, `sign.template`, `sign.document`, `sign.item`<br>поля: `sign.template.document_ids` | ir.attachment → sign.template.document_ids → sign.document → sign.item (type_id, page, posX, posY) |
| контроль версій та історія змін | `documents.access`<br>поля: `documents.access.tracking` |  |
| подання маршрутів і кнопки етапів | `ir.ui.view`, `ir.actions.server` |  |

### Дашборди й звіти

**Застосунки (усі рівні):** `spreadsheet_dashboard`, `spreadsheet_dashboard_edition`, `account_reports`, `digest`
**Попередити:** без «одна з: CRM, Продажі, Закупівлі, Склад, Виробництво, Проєкти й таймшити, Сервісні заявки, Виїзні роботи, Підписки, Оренда, Обслуговування обладнання, Управлінський облік, Витрати співробітників, Персонал і відпустки, Точка продажу, Інтернет-магазин» — дашборд без джерела даних порожній — потрібна хоча б одна позиція з операціями
**Попередити:** без «Управлінський облік» — «порівняння періодів у фінансових звітах» — звіти позиції «Управлінський облік»

#### Рівень 1

Доставити застосунки: `spreadsheet_dashboard`, `spreadsheet_dashboard_edition`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| два-три стандартні звіти | `sale.report`, `purchase.report`, `helpdesk.ticket`, `account.report`<br>поля: `helpdesk.ticket.report.analysis` |  |
| фільтри й групування | — |  |
| вивантаження в Excel | — |  |
| доступ за ролями | `res.groups`, `spreadsheet.dashboard`<br>поля: `spreadsheet.dashboard.group_ids` |  |
| збережені подання | `ir.filters` |  |

#### Рівень 2

Доставити застосунки: `account_reports`, `digest`

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| дашборд керівника | `spreadsheet.dashboard`, `spreadsheet.dashboard.group` |  |
| зведення за напрямами | `account.analytic.account`, `account.report` |  |
| порівняння періодів у звітах pivot та фінансових | `account.report`<br>поля: `account.report.filter_period_comparison` |  |
| розрахункові показники формулами в дашборді | `spreadsheet.dashboard` | Панелі приладів → Дашборди Spreadsheet |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| кілька дашбордів за ролями | `spreadsheet.dashboard`<br>поля: `spreadsheet.dashboard.group_ids` |  |
| зведений дашборд власника з показниками кількох застосунків (Spreadsheet) | — |  |
| періодичні листи з KPI (Digest) і надсилання документа за подією | `digest.digest` |  |
| окремі робочі місця під ролі: свій пункт меню, своє подання й свій фільтр | `ir.ui.view`, `ir.actions.act_window`, `ir.ui.menu`<br>поля: `ir.actions.act_window.view_id`, `ir.ui.menu.group_ids`, `ir.ui.view.group_ids` |  |

### Друковані форми

**Попередити:** без «одна з: Продажі, Закупівлі, Склад, Управлінський облік, Точка продажу, Підписки, Оренда, Виїзні роботи, Виробництво, Сервісні заявки, Обслуговування обладнання» — бланк друкується для документа якогось застосунку — без позицій із документами нема що оформлювати

#### Рівень 1

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| логотип і реквізити у стандартних формах | `res.company`, `ir.ui.view`, `report.layout`<br>поля: `res.company.external_report_layout_id` | res.company.external_report_layout_id → ir.ui.view (НЕ report.layout) |
| шрифт із вбудованих; колонтитули єдині на всі документи | `res.company`<br>поля: `res.company.font` |  |
| друк у мові контрагента для стандартних форм | `res.partner`<br>поля: `res.partner.lang` | res.partner.lang → мова рендеру звіту |
| перевірка друку | — |  |
| перевірка нумерації у надрукованих документах | `ir.sequence`, `account.journal`<br>поля: `account.journal.code` |  |

#### Рівень 2

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| два-три власні бланки | `ir.actions.report`, `ir.ui.view`<br>поля: `ir.actions.report.copy` |  |
| факсиміле як зображення і поле для підпису | `ir.ui.view` |  |
| окремі бланки під тип документа з розмежуванням доступу | `ir.actions.report`<br>поля: `ir.actions.report.group_ids` |  |
| поля для бланка в документі | `ir.model.fields`, `ir.ui.view` |  |

#### Рівень 3

| Пункт | Де в Odoo | Шлях у меню |
|---|---|---|
| верстка статичними й динамічними таблицями | `ir.ui.view` |  |
| двомовні статичні підписи; повний переклад — окремий бланк | — |  |
| специфічні бланки під галузь | `ir.ui.view`, `ir.actions.report` |  |
| поля бланка — власним полем і правкою бланка; замість умовних блоків — окремі бланки під варіанти документа | `ir.model.fields`, `ir.ui.view`, `ir.actions.report`<br>поля: `ir.actions.report.copy` |  |

## Пункти без машинної адреси — 36

Тут карта нічим не допоможе: це або послуга (сесія, виїзд, показ), або дія в
інтерфейсі, яка не лишає окремого запису. Робота по них береться з журналу
`docs/журнал-налаштування-edu-online-todo.md`.

- diag р.1 · розмова про поточний процес
- diag р.1 · перелік систем, що вже є
- diag р.1 · перевірка меж нашого контуру
- diag р.1 · орієнтовний набір позицій
- diag р.1 · усна відповідь про строк і діапазон ціни; ціна фіксується письмово
- diag р.1 · перелік того, чого не буде
- diag р.2 · розбір двох-трьох процесів
- diag р.2 · письмова пропозиція з набором
- diag р.3 · зустріч на місці
- diag р.3 · опитування кількох підрозділів
- diag р.3 · коротка карта процесів
- base р.1 · оглядова сесія 1 година із записом
- inv р.2 · імпорт банківської виписки CAMT.053 / CSV / OFX із мапінгом колонок
- mig р.1 · шаблон файлу під імпорт
- mig р.1 · перевірка обов'язкових полів
- mig р.1 · звіт про завантажені записи
- mig р.3 · зведення кількох джерел в одну структуру
- trn р.1 · сесія для ключових користувачів
- trn р.1 · відповіді на запитання
- trn р.1 · пам'ятка на одну сторінку
- trn р.1 · запис сесії
- trn р.2 · письмові інструкції за ролями
- trn р.2 · тренувальні завдання на тестових даних
- trn р.2 · наповнена база знань за налаштованими блоками: де в базі що налаштовано і що робить роль
- trn р.3 · сесії для кількох груп
- trn р.3 · інструкція адміністратора системи
- web р.1 · адаптація під мобільні
- shop р.1 · кошик і оформлення замовлення
- fsm р.2 · мобільний доступ виконавця
- fsm р.2 · фото й підпис клієнта на місці
- fsm р.3 · облік запчастин у наряді
- dsh р.1 · фільтри й групування
- dsh р.1 · вивантаження в Excel
- dsh р.3 · зведений дашборд власника з показниками кількох застосунків (Spreadsheet)
- prt р.1 · перевірка друку
- prt р.3 · двомовні статичні підписи; повний переклад — окремий бланк

## Чого бракує для `apply-config`

Карта дає **адресу** пункту (324 із 360 пунктів мають модель), але не дає **рецепта**:
яких значень набути полям і в якому порядку викликати створення всередині пункту.
Поки рецепта немає, автоматична збірка неможлива, і це чесна межа інструмента.

Щоб рецепт зʼявився, у `data/verify.json` кожному пункту потрібне окреме поле
`рецепт` — перелік кроків виду:

```json
"рецепт": [
 {"дія": "create", "модель": "ir.filters",
  "значення": {"name": "…", "model_id": "sale.order", "domain": "…", "sort": "[]"},
  "назвати": "фільтр_сегмента"},
 {"дія": "create", "модель": "ir.ui.menu",
  "значення": {"name": "…", "parent_id": 336, "action": "act_window,$дія_сегмента"}}
]
```

Три речі, які рецепт мусить уміти, інакше він не працюватиме на живій базі:

1. **Посилання на щойно створений запис** (`$назва`) — інакше подання, дію й меню
   не звʼязати.
2. **Пошук замість жорсткого id** — `parent_id` кореневого меню або id ролі на кожній
   базі свій, тому в рецепті має стояти пошук за ознакою, а не число.
3. **Перевірку після кроку** — конектор повідомляє помилку й тоді, коли дія відбулася
   (перевірено дорого, див. базу знань), тому кожен крок закінчується перечитуванням.

Оцінка обсягу: рецепти потрібні для 324 пунктів із моделями. Писати їх варто не всі відразу, а по позиціях — починаючи з «Бази» і «Проєктів», бо саме на них міряється окупність інструментарію у фазі 0.

