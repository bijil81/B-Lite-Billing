"""Context-aware help content for main application menus."""

from __future__ import annotations


def _topic(title: str, summary: str, sections: list[tuple[str, list[str]]]) -> dict:
    return {
        "title": title,
        "summary": summary,
        "sections": [
            {"heading": heading, "items": items}
            for heading, items in sections
        ],
    }


HELP_TOPICS = {
    "admin_panel": _topic(
        "Admin Panel Help",
        "Use Admin Panel to maintain master data such as services, products, variants, and user accounts.",
        [
            ("What this page does", [
                "Admin Panel is the control room for business master data. Changes here affect Billing, Inventory, and user access.",
                "Use Services for service names and prices. Use Products for physical items, pack sizes, and stock-related setup.",
                "User Management should be handled only by the owner because wrong changes can block staff login.",
            ]),
            ("Step by step", [
                "Open the correct tab first: Services, Products, or Users.",
                "For a new product, choose category, brand, base product, pack size, unit, price, and stock.",
                "Save the entry, then refresh the list and verify that the item appears correctly.",
                "For user accounts, create the username, display name, password, and role, then test login once before handing over the account.",
            ]),
            ("Import guide", [
                "Use Import JSON when you already have exported product data in JSON format.",
                "Use Import Excel when the sheet contains Item Name, Brand, Category, Pack Size, Unit, Price, and Stock columns.",
                "After import, always scan the product list for duplicates or wrong categories before using the items in Billing.",
            ]),
            ("Common mistakes", [
                "Do not delete active master records without checking whether Billing or Inventory is still using them.",
                "Avoid mixing service names and product names in the same tab.",
            ]),
        ],
    ),
    "dashboard": _topic(
        "Dashboard Help",
        "Use Dashboard for the daily business snapshot before you move into detailed modules.",
        [
            ("What this page does", [
                "Dashboard gives a quick overview of sales, reminders, and current activity.",
                "It is best used at the start of the day and before closing to check whether anything needs attention.",
            ]),
            ("Step by step", [
                "Review total sales, pending reminders, and appointment summary cards.",
                "If a number looks wrong, open the related module such as Reports, Billing, or Appointments and verify the source data.",
                "Treat Dashboard as a summary page, not the final source of truth for detailed corrections.",
            ]),
            ("Tips", [
                "Keep Dashboard as the first screen for reception users so they can notice pending work quickly.",
                "After fixing data in another module, reopen Dashboard to confirm that the summary is updated.",
            ]),
        ],
    ),
    "billing": _topic(
        "Billing Help",
        "Use Billing to create customer bills, apply offers, and save the final transaction safely.",
        [
            ("What this page does", [
                "Billing supports both Services and Products. Services are service work items, while Products are sellable inventory items.",
                "Customer details, loyalty, offers, wallet usage, print, PDF, and WhatsApp all start from this screen.",
            ]),
            ("Step by step", [
                "Load an existing customer by typing name or phone, or continue as walk-in if needed.",
                "Choose Services or Products mode before searching items.",
                "Search and add each line item, then review GST, discount, coupon, redeem code, and payment mode.",
                "Press Save first. After save succeeds, use Print, PDF, or WhatsApp as required.",
            ]),
            ("Variant products", [
                "In Products mode, the search list can show both old items and new variant items such as Parachute Hair Oil 100ml.",
                "Quantity means the number of pieces sold. The pack size in the name is only the product variant label.",
            ]),
            ("Common mistakes", [
                "Do not print before saving if you want the bill to appear in reports and history.",
                "Double-check coupon and redeem values before final save because those affect the net bill amount.",
            ]),
        ],
    ),
    "customers": _topic(
        "Customers Help",
        "Use Customers to register, search, edit, and review customer history.",
        [
            ("What this page does", [
                "This page stores customer name, phone, birthday, points, visits, and related history.",
                "Billing and Appointments use the same customer master, so clean data here improves the whole app.",
            ]),
            ("Step by step", [
                "Search by name or phone before adding a new customer to avoid duplicates.",
                "Open the customer record and update name, birthday, and contact details carefully.",
                "Review visit count and points only after confirming the saved bill history is correct.",
            ]),
            ("Tips", [
                "Capture birthdays correctly because offers, reminders, and birthday campaigns depend on them.",
                "If v5 customer database is enabled, this page is reading the relational SQLite layer.",
            ]),
        ],
    ),
    "appointments": _topic(
        "Appointments Help",
        "Use Appointments to book, reschedule, and complete upcoming visits.",
        [
            ("What this page does", [
                "Appointments helps the reception desk schedule customers with service, date, time, and staff.",
                "It also tracks appointment status such as Scheduled, Complete, Cancelled, and No Show.",
            ]),
            ("Step by step", [
                "Click Book Appointment and type customer name or phone to load existing customer suggestions.",
                "Choose service, date, time, and staff, then save the booking.",
                "Select a row later to mark it Complete, Cancel, No Show, or send WhatsApp reminder.",
            ]),
            ("Tips", [
                "Use existing customer suggestions whenever possible so billing and history stay linked.",
                "If the book window feels small on a system, resize once and confirm all fields are visible before saving.",
            ]),
        ],
    ),
    "membership": _topic(
        "Memberships Help",
        "Use Memberships to manage prepaid plans, discounts, and customer benefit balances.",
        [
            ("What this page does", [
                "Memberships lets you define plans and assign them to customers with wallet or discount benefits.",
                "These benefits are later used in Billing when the customer is recognized.",
            ]),
            ("Step by step", [
                "Create or review the membership plan first.",
                "Assign the plan to the customer and confirm validity dates, wallet value, and discount rules.",
                "During billing, verify that the recognized customer receives the correct membership benefit.",
            ]),
            ("Common mistakes", [
                "Do not manually reduce wallet values outside the billing flow unless you are making a deliberate correction.",
                "Avoid overlapping plans on the same customer unless you have a clear business rule for it.",
            ]),
        ],
    ),
    "offers": _topic(
        "Offers Help",
        "Use Offers to configure promotions that can be applied during billing.",
        [
            ("What this page does", [
                "Offers store reusable discount rules such as flat discount, percentage discount, or campaign-based pricing.",
                "Only active offers should remain enabled for daily use.",
            ]),
            ("Step by step", [
                "Create an offer with a clear name and correct discount type.",
                "Set validity and active status carefully.",
                "Open Billing and test the offer once before staff starts using it on live bills.",
            ]),
            ("Tips", [
                "Use simple names that reception staff can recognize quickly.",
                "Disable expired or seasonal offers instead of keeping the list cluttered.",
            ]),
        ],
    ),
    "redeem_codes": _topic(
        "Redeem Help",
        "Use Redeem to create and track coupon or redemption codes.",
        [
            ("What this page does", [
                "Redeem codes are customer-facing codes that can apply a discount or wallet-like benefit at billing time.",
                "Tracking code usage prevents duplicate redemptions.",
            ]),
            ("Step by step", [
                "Create the code with value, validity, and usage rule.",
                "Share the code only after testing it in Billing.",
                "When a customer uses it, save the bill and then confirm that the code shows as used.",
            ]),
            ("Common mistakes", [
                "Do not reuse the same public code without tracking how often it should be valid.",
                "Always verify expiry date before activating a campaign.",
            ]),
        ],
    ),
    "cloud_sync": _topic(
        "Cloud Sync Help",
        "Use Cloud Sync for backup or remote synchronization after local data is stable.",
        [
            ("What this page does", [
                "Cloud Sync is for backup and remote movement of business data, not for daily billing operations.",
                "Local save should succeed first before depending on cloud sync.",
            ]),
            ("Step by step", [
                "Confirm internet, credentials, and destination settings.",
                "Run sync once and wait for completion instead of repeatedly pressing the same action.",
                "Keep local backup files even if cloud sync succeeds.",
            ]),
            ("Tips", [
                "Use sync at quieter times of the day when billing pressure is low.",
                "If sync fails, fix credentials first instead of forcing repeated retries.",
            ]),
        ],
    ),
    "staff": _topic(
        "Staff Help",
        "Use Staff to maintain employee details, attendance, and role-related information.",
        [
            ("What this page does", [
                "Staff records support attendance, reporting, and operational visibility.",
                "Wrong staff names or duplicates can affect appointments, attendance, and reporting accuracy.",
            ]),
            ("Step by step", [
                "Create the staff profile with correct name, contact details, and role.",
                "Check attendance entries carefully, especially if auto attendance is enabled through login/logout.",
                "Before deactivating a staff record, verify whether appointments or reports still rely on it.",
            ]),
            ("Tips", [
                "Keep naming consistent so the same staff member is not entered twice with small spelling differences.",
                "Use attendance corrections sparingly and only after verifying the date.",
            ]),
        ],
    ),
    "inventory": _topic(
        "Inventory Help",
        "Use Inventory to manage stock items, pack-size products, and quick quantity updates.",
        [
            ("What this page does", [
                "Inventory keeps stock quantity, category, cost, and pack details for physical products.",
                "This screen now supports variant-style fields such as brand, base product, pack size, and measurement unit.",
            ]),
            ("Step by step", [
                "Use Search and Category filter to locate an item before editing.",
                "For a new item, first choose Category, Brand, Base Product, and Unit from the dropdowns.",
                "Then type Item Name, Pack Size, Quantity, Min Stock Alert, and Cost, and save the item.",
                "Use Quick Stock Update for routine stock quantity changes on existing items.",
            ]),
            ("How to read the fields", [
                "Quantity means the number of pieces, bottles, or boxes physically in stock.",
                "Unit means the product measurement such as ml, g, kg, L, or pcs.",
                "Pack Size Value is the measurement amount, for example 100 with unit ml becomes 100ml.",
            ]),
            ("Tips", [
                "Select dropdown fields first because they help standardize names and reduce typing mistakes.",
                "Use the same base product and brand format for repeat items so Billing search stays clean.",
            ]),
        ],
    ),
    "expenses": _topic(
        "Expenses Help",
        "Use Expenses to record operating costs such as rent, salary, supplies, and utilities.",
        [
            ("What this page does", [
                "Expenses become part of closing and reporting, so accuracy here affects profit visibility.",
                "This screen is for non-sale outgoing amounts, not for product stock sales.",
            ]),
            ("Step by step", [
                "Choose or type the correct expense category.",
                "Enter amount, date, and description clearly.",
                "Save and then check Reports or Closing Report if you need to confirm the total impact.",
            ]),
            ("Tips", [
                "Short but clear descriptions make later audit much easier.",
                "Do not combine multiple unrelated expenses in one entry if separate tracking matters.",
            ]),
        ],
    ),
    "whatsapp_bulk": _topic(
        "Bulk WhatsApp Help",
        "Use Bulk WhatsApp to send messages to many customers in a controlled way.",
        [
            ("What this page does", [
                "This screen helps run promotions, reminders, or campaign messages to multiple contacts.",
                "It should be used carefully because wrong filters or repeated sends can annoy customers.",
            ]),
            ("Step by step", [
                "Prepare or review the recipient list first.",
                "Draft a clear message template.",
                "Test the message on a small set before sending to the full list.",
            ]),
            ("Tips", [
                "Avoid sending too frequently.",
                "Keep campaign messages short and relevant to the selected audience.",
            ]),
        ],
    ),
    "reports": _topic(
        "Reports Help",
        "Use Reports to review sales, saved bills, exports, and service performance.",
        [
            ("What this page does", [
                "Reports summarizes business performance from saved billing data.",
                "It includes date filtering, exports, bill preview, charts, and service-related analysis.",
            ]),
            ("Step by step", [
                "Pick the date range first or use quick filters such as Today or This Month.",
                "Review the totals at the top before exporting.",
                "Select a bill row if you want preview, print, or load the bill back into Billing.",
                "Use CSV or Excel export only after confirming the filtered result is correct.",
            ]),
            ("Tips", [
                "If totals look wrong, compare with Billing and Closing Report for the same date range.",
                "Use Saved Bills preview to inspect item-level details before making corrections.",
            ]),
        ],
    ),
    "closing_report": _topic(
        "Closing Report Help",
        "Use Closing Report for end-of-day reconciliation and settlement checking.",
        [
            ("What this page does", [
                "Closing Report helps confirm the day's final business numbers before day-end closing.",
                "It is useful for checking payment split, expenses, and daily net position.",
            ]),
            ("Step by step", [
                "Use this page after all bills and expenses for the day are already saved.",
                "Review total sales, payment mode split, and expense deductions.",
                "If numbers do not match expectations, verify Billing and Reports first before adjusting anything.",
            ]),
            ("Tips", [
                "Run it once before staff leaves for the day so missing bills can still be corrected.",
                "Do not use closing figures as final until you confirm that late bills were also saved.",
            ]),
        ],
    ),
    "ai_assistant": _topic(
        "AI Assistant Help",
        "Use AI Assistant for guided help, workflow explanations, and operational suggestions.",
        [
            ("What this page does", [
                "AI Assistant can explain features, help troubleshoot, and suggest safer workflows inside the app.",
                "It is a support tool, not the final authority for destructive data actions.",
            ]),
            ("Step by step", [
                "Ask one clear question at a time for best results.",
                "Use it for process guidance such as billing flow, reports, customer handling, or feature understanding.",
                "Review any suggestion before applying it in a live workflow.",
            ]),
            ("Tips", [
                "Questions with exact screen names usually get better answers.",
                "Use AI for guidance, but verify business-critical changes manually.",
            ]),
        ],
    ),
    "settings": _topic(
        "Settings Help",
        "Use Settings to configure business identity, printing, security, preferences, and advanced rollout options.",
        [
            ("What this page does", [
                "Settings controls shop identity, theme, billing defaults, notifications, and internal rollout flags.",
                "Some sections are normal business settings, while others are advanced owner-only controls.",
            ]),
            ("Step by step", [
                "Open the correct tab first such as Shop Info, Theme, Security, or Preferences.",
                "Change only one group of settings at a time and save before moving on.",
                "For important changes like print setup or database rollout flags, restart the app after saving.",
            ]),
            ("Advanced rollout note", [
                "The database rollout flags are for staged migration, testing, and rollback.",
                "Normal daily users usually do not need to change them.",
            ]),
            ("Tips", [
                "Use Security tab to change the current password safely.",
                "Verify print and notification settings after any environment change such as new PC or new printer.",
            ]),
        ],
    ),
}


def get_help_topic(key: str) -> dict:
    key = str(key or "").strip()
    return HELP_TOPICS.get(key, {
        "title": "Help",
        "summary": "Use this screen to manage the selected module carefully.",
        "sections": [
            {
                "heading": "How to use",
                "items": [
                    "Review the visible controls and fields on the current screen first.",
                    "Save only after checking your entries carefully.",
                    "If something looks wrong, return to the previous screen and verify the source data.",
                ],
            },
        ],
    })
