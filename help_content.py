"""Context-aware user guide content for B-Lite Management v6.1.0.

The in-app Help popup and the PDF user manual both read this file, so the
customer sees the same workflow instructions in both places.
"""

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
    "dashboard": _topic(
        "Dashboard Help",
        "Use Dashboard to see the daily business position before opening detailed modules.",
        [
            ("When to use this page", [
                "Open Dashboard at the start of the day to check today revenue, appointments, reminders, and quick activity.",
                "Open it again before closing to confirm that billing, appointments, and warnings look normal.",
                "Dashboard is a summary page. If a number looks wrong, verify the detailed page such as Reports, Billing, or Appointments.",
            ]),
            ("Step by step", [
                "Check the top summary cards first. They show the current business snapshot.",
                "Review the 7-day revenue trend to see whether recent saved invoice revenue is increasing or decreasing.",
                "Check pending appointments, reminders, and alerts before starting live billing.",
                "After correcting data in another page, return to Dashboard or reopen it to confirm the summary refreshed.",
            ]),
            ("Common checks", [
                "Today revenue comes from saved bills, not from unsaved billing drafts.",
                "A zero day in the trend can mean no saved sales for that date.",
                "If Dashboard and Reports differ, filter Reports for the same date and use Reports as the detailed reference.",
            ]),
        ],
    ),
    "billing": _topic(
        "Billing Help",
        "Use Billing to create service bills, product bills, discounts, wallet payments, printouts, PDFs, and WhatsApp sharing.",
        [
            ("Recommended billing flow", [
                "First search or enter the customer name and phone. Use the same phone number every time so history, due, membership, and wallet can match.",
                "Choose Services when adding salon work such as facial, haircut, or waxing.",
                "Choose Products when selling stock items such as shampoo, oil, cream, or grocery-style products.",
                "Select the item category if needed, search the item name or item code, enter quantity, confirm price, then press Add Item.",
                "Review every line in the live bill preview before saving. Correct quantity or price before final save.",
                "Select payment mode, enter paid amount if needed, and confirm due status before pressing Save.",
                "After Save succeeds, use Print, PDF, or WhatsApp. Saved bills appear in Reports.",
            ]),
            ("Customer fields", [
                "Name is used for bill display and customer search.",
                "Phone is the strongest matching field for customers, due, membership, wallet, and WhatsApp.",
                "Birthday should be entered as DD-MM-YYYY when available so birthday offers and reminders can work.",
                "If the customer is new, save the bill once with name and phone so the customer master can be created or updated.",
                "If outstanding due is shown, collect it only when the customer is actually paying old balance.",
            ]),
            ("Services and Products buttons", [
                "Services switches the item picker to service catalog and service pricing.",
                "Products switches the item picker to product catalog and stock-aware product selection.",
                "Use the barcode scan box only for products that have barcode values saved.",
                "In product mode, quantity means how many units or packs are sold. Pack size is part of the product variant label.",
            ]),
            ("Add Item and Undo Last", [
                "Add Item adds the currently selected service or product into the draft bill.",
                "Undo Last removes the most recently added line from the current unsaved bill.",
                "Use Undo Last for quick correction before save. For older saved bills, use Reports or a correction workflow instead.",
            ]),
            ("Discount Apply", [
                "Tick Discount only when a manual discount is allowed for this bill.",
                "Enter Disc Rs and press Apply. Typed discount is not active until Apply is pressed.",
                "Check the total after applying discount. Manual discount reduces the current sale amount.",
                "Do not use manual discount to clear old due. Use Add Due for old balance collection.",
            ]),
            ("Loyalty points and membership", [
                "Use Loyalty Points only when the customer has points and the business allows points redemption.",
                "Membership discount applies only for a recognized active member and is shown separately.",
                "Membership discount is a discount. Wallet is prepaid payment, not discount.",
                "If membership does not appear, confirm the customer phone number matches the membership record.",
            ]),
            ("Use Wallet", [
                "Tick Use Wallet only when the customer wants to spend available wallet credit.",
                "Leave Wallet Rs blank to use the maximum possible wallet amount.",
                "Enter a smaller Wallet Rs and press Apply to use only part of the wallet.",
                "Wallet is deducted only after Save succeeds. Preview and draft changes do not reduce wallet balance.",
                "The printout shows wallet used and remaining wallet balance when wallet payment is applied.",
            ]),
            ("Payment and due", [
                "Choose Cash, Card, UPI, or Credit based on the actual payment received.",
                "Paid amount should match the amount received. If paid amount is less than payable, the balance becomes due.",
                "Use Credit only when the business allows the customer to keep due.",
                "If customer is blacklisted, avoid credit billing and collect Cash, Card, or UPI.",
                "Add Due is for collecting previous outstanding balance inside the current billing session.",
            ]),
            ("Offer, Coupon, and Redeem", [
                "Offer dropdown applies predefined active offers from the Offers page.",
                "Coupon applies campaign codes or coupon-style discounts when configured.",
                "Redeem applies generated redeem codes from the Redeem page.",
                "Use Clear near the offer or redeem section to remove a wrongly applied benefit before saving.",
                "Always recheck the final payable amount after applying offer, coupon, or redeem.",
            ]),
            ("Finish and share buttons", [
                "Save finalizes the invoice and writes the bill to reports and history.",
                "Print prints the saved or current bill through the configured print path.",
                "PDF creates or opens a PDF copy based on the print fallback path.",
                "WhatsApp sends the bill message or image through the configured WhatsApp helper.",
                "Clear removes the current draft. Use it only after confirming the bill is saved or no longer needed.",
            ]),
            ("Keyboard shortcuts", [
                "F2 saves the bill.",
                "F4 creates PDF.",
                "F5 prints.",
                "F6 sends WhatsApp.",
                "F8 clears the draft.",
            ]),
            ("Important safety notes", [
                "Do not print a customer bill as final before saving if the sale must appear in reports.",
                "Do not close the app during Save, Print, or WhatsApp send.",
                "If printer is virtual PDF, XPS, or OneNote, the app routes to PDF fallback instead of direct thermal print.",
            ]),
        ],
    ),
    "customers": _topic(
        "Customers Help",
        "Use Customers to add, edit, search, settle due, blacklist, restore, and review customer records.",
        [
            ("Main workflow", [
                "Search by phone before adding a customer. This avoids duplicate customer records.",
                "Click Add Customer to create a new profile with name, phone, birthday, and other details.",
                "Select a customer row to enable actions such as Edit, History, Settle Due, or Delete.",
                "Double click a row to open customer history when available.",
            ]),
            ("Search and Clear", [
                "Type customer name or phone in Search to filter the directory.",
                "Use Clear to remove the search filter and show the full list again.",
                "If a customer is not visible, clear filters and check deleted customers before adding a duplicate.",
            ]),
            ("Actions", [
                "Edit opens the customer form for updating name, phone, birthday, due, or blacklist status.",
                "History shows previous visits, bills, points, and customer activity where available.",
                "Settle Due records money paid against outstanding customer balance.",
                "Delete moves the customer to deleted history when supported. Restore is available from View Deleted.",
                "Permanent Delete should be used only by an authorized owner or manager after backup.",
            ]),
            ("Settle Due", [
                "Open Settle Due only after selecting the correct customer.",
                "Enter the amount actually paid and select the payment mode.",
                "Confirm payment only after checking current due and entered amount.",
                "After settlement, verify the due value in Customers or Billing.",
            ]),
            ("Data quality rules", [
                "Phone number should be unique whenever possible.",
                "Use the same spelling for repeat customers to keep reports clean.",
                "Do not blacklist customers by mistake because it affects credit billing behavior.",
            ]),
        ],
    ),
    "appointments": _topic(
        "Appointments Help",
        "Use Appointments to book visits, manage the day calendar, send reminders, and convert bookings to bills.",
        [
            ("Calendar workflow", [
                "Use Prev, Today, Next, or Pick to choose the working date.",
                "Use Staff filter to focus the calendar on one staff member when the shop is busy.",
                "Use Search to find bookings by customer, phone, service, or staff.",
                "Click a booking to view details. Double click a booking to edit it.",
                "Click an empty slot or Quick Booking to create a new appointment.",
            ]),
            ("Book or edit appointment", [
                "Enter customer name and phone. Use existing customer suggestions when available.",
                "Choose service, staff, date, start time, and end time.",
                "Add notes for special requests, advance payment notes, or customer preference.",
                "Press Save Booking to store the appointment.",
                "Use Delete only when the booking is cancelled or created by mistake.",
            ]),
            ("Buttons", [
                "Save Booking saves a new or edited appointment.",
                "Convert to Bill sends the appointment context to Billing when the customer arrives.",
                "Reminder sends a WhatsApp reminder when WhatsApp is configured.",
                "Edit opens the selected booking for changes.",
                "Delete removes the selected booking after confirmation.",
            ]),
            ("Good operating practice", [
                "Confirm date and time before saving because wrong booking time affects staff planning.",
                "Keep staff names consistent so the calendar columns stay clean.",
                "Use notes for customer-specific instructions instead of putting those instructions in the service name.",
            ]),
        ],
    ),
    "membership": _topic(
        "Memberships Help",
        "Use Memberships to assign packages, manage wallet credit, and maintain benefit templates.",
        [
            ("Active Members tab", [
                "Use New Membership to assign a package to a customer.",
                "Select the customer, choose package, confirm payment method, and press Assign Package.",
                "Check validity dates, discount, wallet value, and status before using the membership in Billing.",
                "Active members are recognized in Billing mainly through the customer phone number.",
            ]),
            ("Package Templates tab", [
                "Use Add Template to create a reusable package with name, price, benefits, discount, and validity.",
                "Use Delete Template only when the package should no longer be offered.",
                "Keep template names simple so staff can choose the correct plan quickly.",
            ]),
            ("Wallet Top-up tab", [
                "Search or choose the member customer first.",
                "Check current wallet balance before adding money.",
                "Enter top-up amount only after receiving payment from the customer.",
                "Press Top-up Wallet and verify the updated wallet balance.",
            ]),
            ("Wallet rules", [
                "Wallet is prepaid customer credit and is spent from Billing using Use Wallet.",
                "Do not manually reduce wallet except for a deliberate correction.",
                "Every wallet spend through Billing should link to an invoice to prevent double deduction.",
                "Expired or inactive memberships should not be used for wallet spending unless the business has a specific rule.",
            ]),
        ],
    ),
    "offers": _topic(
        "Offers Help",
        "Use Offers to create billing offers, control active campaigns, and remove expired discounts.",
        [
            ("Offer list", [
                "Use filters to view Active, Expired, Inactive, or All offers.",
                "Select a row to use Edit, Deactivate, or Delete.",
                "Double click an offer to edit details quickly.",
            ]),
            ("Create or edit offer", [
                "Click Create Offer or Edit.",
                "Enter offer name, discount type, value, optional matching text, valid from, valid to, and description.",
                "Keep Active enabled only when the offer should appear in Billing.",
                "Press Save Offer and test once in Billing before staff uses it live.",
            ]),
            ("Buttons", [
                "Load Templates imports starter offer templates.",
                "Create Offer opens a blank offer form.",
                "Edit changes the selected offer.",
                "Deactivate hides the offer from active use without deleting history.",
                "Delete removes the selected offer after confirmation.",
            ]),
            ("Safety rules", [
                "Avoid overlapping offers with similar names because staff may choose the wrong one.",
                "Deactivate seasonal offers after campaign end.",
                "Use clear descriptions for audit and later review.",
            ]),
        ],
    ),
    "redeem_codes": _topic(
        "Redeem Help",
        "Use Redeem to generate one-time or campaign discount codes and send them to customers.",
        [
            ("Generate and Send tab", [
                "Choose discount type: amount or percentage.",
                "Enter discount value, expiry date, note or occasion, and number of codes.",
                "Click Generate Code(s) to create one or more codes.",
                "Click Generate for All Customers only when the campaign is ready for all saved customers.",
                "After generating, open All Codes to send, copy, or review usage.",
            ]),
            ("All Codes tab", [
                "Use filters to view unused, used, expired, or all codes.",
                "Use Refresh after generating or using codes.",
                "Select a code row before using Send WhatsApp, Copy Code, Delete, or other actions.",
            ]),
            ("Usage in Billing", [
                "Customer gives the code at billing time.",
                "Enter the code in the Redeem field on Billing and press Apply.",
                "Save the bill to mark the code as used when the redemption succeeds.",
                "Do not share the same one-time code with multiple customers.",
            ]),
        ],
    ),
    "cloud_sync": _topic(
        "Cloud Sync Help",
        "Use Cloud Sync for folder sync, offline backup and restore, and mobile web viewer access.",
        [
            ("Folder sync", [
                "Choose a sync folder using Quick Select or Browse.",
                "Use Auto sync after every bill save only when the folder is reliable and always available.",
                "Press Sync Now to manually copy current backup files and recent bill data to the sync folder.",
                "Read the Sync Log for success or failure details.",
            ]),
            ("Offline backup and restore", [
                "Choose an offline backup folder on another drive, USB disk, or external location.",
                "Use Backup Now before major changes, imports, restores, or build testing.",
                "Use Restore From Backup only when you are sure the selected backup is the correct older state.",
                "After restore, reopen important pages and verify customers, bills, inventory, and settings.",
            ]),
            ("Mobile viewer", [
                "Set port and viewer PIN.",
                "Press Start Mobile Viewer to start local browser access from the same WiFi network.",
                "Open the shown URL on mobile and enter the PIN.",
                "Use Run Connection Check if mobile cannot open the page.",
                "Stop or close the viewer when mobile access is no longer needed.",
            ]),
            ("Safety rules", [
                "Cloud sync is not a replacement for local backup.",
                "Do not restore backup during live billing.",
                "Keep the viewer PIN private because it protects mobile access.",
            ]),
        ],
    ),
    "staff": _topic(
        "Staff Help",
        "Use Staff to manage employee profiles, attendance, commissions, and user access handoff.",
        [
            ("Staff List tab", [
                "Use Add Staff to create staff profile with name, role, phone, salary or commission settings.",
                "Use Search to filter staff by name, role, or phone.",
                "Select a staff row to Edit, Toggle Active, Delete, or open User Management.",
                "Use Photo only when you want staff profile photo support.",
            ]),
            ("Attendance tab", [
                "Review check-in and check-out records for each staff member.",
                "If auto attendance is enabled, login and logout can affect attendance.",
                "Correct attendance only after confirming the date and staff member.",
            ]),
            ("Commission tab", [
                "Review commission by staff and period when service or billing data supports it.",
                "Keep staff assignment consistent in appointments and billing to make commission reports useful.",
            ]),
            ("User Management", [
                "User Mgmt opens login account controls.",
                "Create user accounts only for real staff who need app access.",
                "Assign the minimum role needed for the job: receptionist, staff, manager, or owner.",
                "Test login after creating or resetting a user account.",
            ]),
        ],
    ),
    "inventory": _topic(
        "Inventory Help",
        "Use Inventory to manage stock, product details, import, purchase bills, quick updates, and low-stock monitoring.",
        [
            ("Stock grid", [
                "Use Search to find items by name, brand, category, or other visible fields.",
                "Use Category filter to narrow the list.",
                "Use Low Stock to show items at or below minimum stock.",
                "Use All Items to return to the normal full stock view.",
                "Double click an item to open the item editor.",
            ]),
            ("Top buttons", [
                "Add Item opens the stock item editor.",
                "Import opens the import workflow for product data.",
                "Purchase Bill records supplier purchase and increases stock with movement history.",
                "Add Product opens Admin Panel Products tab for product master setup.",
                "Add Services opens Admin Panel Services tab for service master setup.",
            ]),
            ("Quick Stock Update", [
                "Select or type the item name.",
                "Enter the new quantity or adjustment quantity based on the selected Type.",
                "Press Update to apply the stock change.",
                "Use this only for routine stock correction. Use Purchase Bill when stock increased because of supplier purchase.",
            ]),
            ("Item editor", [
                "Enter item name, category, brand, unit, current quantity, minimum stock alert, cost price, sale price, and barcode when available.",
                "For variants, keep base product, pack size, and unit consistent. Example: Shampoo 100 ml and Shampoo 200 ml should share the same base product.",
                "Use Generate for barcode only when the product does not already have a supplier barcode.",
                "Save Item writes the change. Cancel closes without saving.",
            ]),
            ("Import", [
                "Use import for prepared Excel, JSON, or CSV product lists.",
                "For old services_db.json files, Products tab import reads Products section and Services tab import reads Services section.",
                "Review import preview or summary. Check skipped rows and warnings.",
                "After import, search the stock grid and Billing product search to confirm the items appear correctly.",
            ]),
            ("Stock safety", [
                "Quantity should represent physical stock count.",
                "Do not edit stock blindly after sales. Billing can reduce stock automatically for product sales.",
                "Use Reduce Stock or adjustment reason for damage, expiry, wastage, theft, or correction when available.",
                "Keep cost price updated for profit warning and margin checks.",
            ]),
        ],
    ),
    "expenses": _topic(
        "Expenses Help",
        "Use Expenses to record non-sale outgoing amounts such as rent, salary, supplies, and utilities.",
        [
            ("Main workflow", [
                "Choose or type the correct expense category.",
                "Enter amount, date, and clear description.",
                "Press Save to store the expense.",
                "Use Search or date filters to review saved expenses.",
                "Edit or delete only after selecting the correct expense row.",
            ]),
            ("Good practice", [
                "Record expenses on the actual date they occurred or were paid.",
                "Do not combine unrelated expenses in one entry if later reporting matters.",
                "Use clear descriptions such as Electricity bill May 2026 or Shampoo supplier transport.",
            ]),
            ("Reporting impact", [
                "Expenses affect daily closing and profit review.",
                "If closing report looks wrong, verify same-day expenses first.",
            ]),
        ],
    ),
    "whatsapp_bulk": _topic(
        "Bulk WhatsApp Help",
        "Use Bulk WhatsApp to send controlled customer campaigns, reminders, or announcements.",
        [
            ("Before sending", [
                "Prepare the recipient list and message first.",
                "Filter customers carefully so the campaign reaches only the intended group.",
                "Keep the message short, clear, and relevant.",
                "Send a test message to one number before sending to many customers.",
            ]),
            ("Sending workflow", [
                "Confirm WhatsApp Web session is logged in and ready.",
                "Review the message template and any customer placeholders.",
                "Start bulk send and wait. Do not repeatedly press send.",
                "Check success and failure results after the run.",
            ]),
            ("Safety rules", [
                "Avoid frequent promotional messages to the same customer.",
                "Do not send sensitive billing details in a bulk campaign.",
                "Respect customer opt-out requests and local messaging rules.",
            ]),
        ],
    ),
    "reports": _topic(
        "Reports Help",
        "Use Reports to filter sales, review saved invoices, export data, inspect charts, and restore deleted bills.",
        [
            ("Sales List tab", [
                "Set From and To dates or use Today, This Month, or All.",
                "Use Search to filter by customer, phone, invoice, or other visible data.",
                "Select a bill row to show preview and quick actions.",
                "Use Load to Bill only when you need to inspect or reuse bill data in Billing.",
                "Use Print to print the selected saved bill.",
                "Use Delete Bill only when a bill is wrong and should move to deleted history.",
            ]),
            ("Export buttons", [
                "Export Excel creates spreadsheet output for the current filtered result.",
                "Export CSV creates a simple table file for accounting or data transfer.",
                "Export PDF creates a PDF report for the current filter.",
                "GST Export creates tax-focused export where GST data is available.",
                "More Exports opens advanced export center for customer ledger, supplier ledger, and similar outputs.",
                "Always set date filters before exporting.",
            ]),
            ("Charts tab", [
                "Choose the chart type from the Chart control.",
                "Use charts to understand trends, not to correct data.",
                "If charts are unavailable in a source run, rebuild with chart dependencies or use Sales List and exports.",
            ]),
            ("Saved Bills tab", [
                "Use Search to find saved PDF bills.",
                "Use Refresh to reload the saved bill list.",
                "Use Open Folder to open the saved bill directory.",
                "Select a saved bill to preview, open, print, or share depending on available actions.",
            ]),
            ("Service Report tab", [
                "Set From and To dates.",
                "Press Generate Report.",
                "Review Service-wise Revenue and Product-wise Sales tables.",
                "Use pagination buttons when the result has many rows.",
            ]),
            ("Grocery Reports tab", [
                "Use product-wise and grocery-style report views for stock-sale analysis where product data supports it.",
                "Compare product sales with inventory movement when investigating stock mismatch.",
            ]),
            ("Deleted bills", [
                "Open View Deleted to see deleted bill history.",
                "Restore Selected returns a deleted bill to active history.",
                "Permanent Delete is destructive and should be used only after backup and owner approval.",
            ]),
        ],
    ),
    "closing_report": _topic(
        "Closing Report Help",
        "Use Closing Report to verify day-end sales, payments, expenses, and final cash position.",
        [
            ("When to use", [
                "Use this page after all daily bills, due settlements, and expenses are saved.",
                "Run it before staff leaves so missing bills or cash differences can be corrected immediately.",
            ]),
            ("Step by step", [
                "Choose the closing date or period.",
                "Generate or refresh the report.",
                "Review sales total, payment mode split, due, expenses, and net position.",
                "Compare cash/card/UPI totals with real counter collection.",
                "If numbers do not match, check Reports and Expenses for the same date.",
            ]),
            ("Common mistakes", [
                "Do not finalize closing before late bills are saved.",
                "Do not treat draft bills as sales.",
                "Do not ignore expenses because they affect final day-end view.",
            ]),
        ],
    ),
    "ai_assistant": _topic(
        "AI Assistant Help",
        "Use AI Assistant for guided explanations, troubleshooting, and workflow suggestions.",
        [
            ("How to ask", [
                "Ask one clear question at a time.",
                "Mention the exact page name such as Billing, Reports, Inventory, or Settings.",
                "Include the error message or invoice number when asking about a specific issue.",
            ]),
            ("Good use cases", [
                "Ask how to create a bill, apply wallet, export reports, or check stock.",
                "Ask for help understanding an error or workflow.",
                "Ask for a checklist before performing backup, restore, import, or closing.",
            ]),
            ("Limits", [
                "AI guidance should be verified for money, tax, delete, restore, and security decisions.",
                "Do not paste private passwords, license keys, or sensitive customer data unless the feature explicitly requires it.",
            ]),
        ],
    ),
    "settings": _topic(
        "Settings Help",
        "Use Settings to configure shop identity, theme, billing, GST, print, security, backups, licensing, updates, and advanced options.",
        [
            ("General rule", [
                "Change one settings group at a time and press Save before moving to another group.",
                "Most normal preferences apply immediately or after reopening the related page.",
                "Restart is needed only for startup-level changes, advanced rollout switches, and some build/runtime integrations.",
            ]),
            ("Shop Info and Theme", [
                "Shop Info controls business name, address, phone, and details used on bills and reports.",
                "Theme controls visual style and should be checked on the main app after saving.",
                "After changing shop identity, create one test PDF or print preview to verify bill header.",
            ]),
            ("Print / Bill", [
                "Select paper size such as Thermal 58 mm, Thermal 80 mm, A5, or A4 based on the real printer or PDF format.",
                "Choose font size and characters per line so invoice number, title, customer, and totals do not cut off.",
                "Use the preview to confirm alignment before live printing.",
                "Save print settings. Billing preview should refresh without full app restart where runtime refresh is supported.",
                "If the selected printer is PDF, XPS, OneNote, or another virtual printer, use PDF fallback instead of direct print.",
            ]),
            ("Billing and GST", [
                "Default Payment sets the normal payment mode shown in Billing.",
                "GST Type controls inclusive or exclusive tax behavior.",
                "GST Rate is the default rate when product-wise rules do not override it.",
                "Product-wise GST can use global, item, or hybrid source depending on business mode.",
                "Missing Item GST controls what happens when a product has no GST rule.",
            ]),
            ("GST master and classification", [
                "Category-wise GST sets defaults such as Grocery, Fruits, or Body Care.",
                "Add / Update saves a category tax rule.",
                "Remove deletes the selected rule.",
                "Reset Defaults restores starter GST rules.",
                "Classification rules can match product name, keyword, HSN/SAC, SKU, or barcode before category fallback.",
            ]),
            ("Security and notifications", [
                "Use Security to change password and security preferences.",
                "Notification timeout controls how long popup notifications stay visible.",
                "Reset All Dismissed brings back dismissed notifications.",
            ]),
            ("Backup and activity", [
                "Enable scheduled backup only after choosing a reliable backup folder.",
                "Frequency, time, retain count, and day control automatic backup timing.",
                "Save Backup Schedule stores the backup plan.",
                "View Activity Log shows audit and operational events.",
            ]),
            ("License and About", [
                "Refresh Status checks current license status.",
                "Activation actions should be used only with valid license information.",
                "Re-check VC Runtime verifies Windows runtime dependency availability.",
                "Save URL stores update manifest URL. Check Now checks for available updates.",
            ]),
            ("Advanced rollout", [
                "Advanced migration and feature switches are owner-only controls.",
                "Use them only after backup and validation.",
                "Changing database rollout flags can require app restart because modules initialize data paths at startup.",
            ]),
        ],
    ),
    "admin_panel": _topic(
        "Admin Panel Help",
        "Use Admin Panel to maintain Services, Products, Users, and Backup/Activity controls.",
        [
            ("Services tab", [
                "Choose Category or select All to view service items.",
                "Use New Category and Add to create a service category.",
                "Select a service row to load Name and Price fields.",
                "Edit Name or Price and press Save / Update.",
                "Use Delete Item only after confirming the service is no longer needed.",
                "Import JSON or Import Excel can import service lists. Old services_db.json uses the Services section on this tab.",
            ]),
            ("Products tab", [
                "Choose Category or All to view product rows.",
                "Products show Product Name, Brand, Category, Variant, Price, and Stock.",
                "Enter Name, Brand, Pack Size, Unit, Stock Qty, and Price for product setup.",
                "Press Save / Update to save the product and sync catalog/inventory.",
                "Use Refresh to reload after import or external changes.",
                "Import JSON or Import Excel can import product lists. Old services_db.json uses the Products section on this tab.",
            ]),
            ("Users tab", [
                "Open User Management to add, edit, reset passwords, and manage login roles.",
                "Create separate users for staff instead of sharing owner login.",
                "Give each user the minimum role needed for their job.",
                "Test login after creating or changing a user account.",
            ]),
            ("Backup and Logs tab", [
                "Run Backup Now before imports, restores, build tests, or risky changes.",
                "Open Activity Log to review app actions and troubleshooting history.",
                "If an error happens in installed app, check app_debug.log and Activity Log before guessing.",
            ]),
            ("Import safety", [
                "Keep service files and product files separate when possible.",
                "For old combined services_db.json, import from the correct tab so the app selects the correct section.",
                "After import, verify a few rows in Admin Panel, Inventory, Billing search, and Reports if relevant.",
            ]),
        ],
    ),
}


def get_help_topic(key: str) -> dict:
    key = str(key or "").strip()
    return HELP_TOPICS.get(key, {
        "title": "Help",
        "summary": "Use this screen carefully and save only after checking your entries.",
        "sections": [
            {
                "heading": "How to use",
                "items": [
                    "Review the visible fields and buttons on the current screen.",
                    "Search before adding new records to avoid duplicates.",
                    "Save only after checking amount, date, customer, item, and payment details.",
                    "If something looks wrong, cancel or close and verify the source data before continuing.",
                ],
            },
        ],
    })
