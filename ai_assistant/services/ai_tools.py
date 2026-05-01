"""
ai_tools.py — BOBY'S Salon AI Assistant Tools
===============================================
All functions the AI can call to read data or trigger actions.
Each function returns structured JSON.
Safe READ operations run directly.
WRITE/ACTION operations require confirmation via controller.
"""
import os, csv, json
from datetime import datetime, date
from collections import defaultdict
from branding import get_appdata_dir_name


def _tool_log(message: str):
    try:
        from utils import app_log
        app_log(message)
    except Exception:
        pass


# ── Data paths (same as existing app) ────────────────────
try:
    from utils import (DATA_DIR, F_CUSTOMERS, F_APPOINTMENTS,
                       F_INVENTORY, F_STAFF, F_EXPENSES,
                       F_REPORT, load_json, today_str, month_str,
                       safe_float, fmt_currency)
except ImportError:
    # Fallback for standalone testing
    import sys
    DATA_DIR = os.path.join(os.environ.get("APPDATA",""), get_appdata_dir_name())
    F_CUSTOMERS    = os.path.join(DATA_DIR, "customers.json")
    F_APPOINTMENTS = os.path.join(DATA_DIR, "appointments.json")
    F_INVENTORY    = os.path.join(DATA_DIR, "inventory.json")
    F_STAFF        = os.path.join(DATA_DIR, "staff.json")
    F_EXPENSES     = os.path.join(DATA_DIR, "expenses.json")
    F_REPORT       = os.path.join(DATA_DIR, "bills_report.csv")

    def load_json(path, default=None):
        try:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            _tool_log(f"[ai_tools load_json] {e}")
        return default if default is not None else {}

    def today_str():  return date.today().strftime("%Y-%m-%d")
    def month_str():  return date.today().strftime("%Y-%m")
    def safe_float(v):
        try:
            return float(v)
        except Exception as e:
            _tool_log(f"[ai_tools safe_float] {e}")
            return 0.0
    def fmt_currency(v): return f"₹{v:,.2f}"


# ─────────────────────────────────────────────────────────
# TOOL REGISTRY — all available tools for the AI agent
# ─────────────────────────────────────────────────────────
TOOL_DEFINITIONS = [
    {
        "name": "get_today_sales",
        "description": "Get today's sales summary: total revenue, number of bills, payment breakdown, and top services sold today.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_monthly_summary",
        "description": "Get monthly revenue summary. Pass month as YYYY-MM format. Defaults to current month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month in YYYY-MM format, e.g. 2026-03"}
            },
            "required": []
        }
    },
    {
        "name": "get_top_services",
        "description": "Get the most popular/top-selling services by count and revenue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "description": "Number of top services to return (default 5)"},
                "period": {"type": "string", "description": "today | this_month | all (default: this_month)"}
            },
            "required": []
        }
    },
    {
        "name": "get_customer_details",
        "description": "Get details of a specific customer: visits, loyalty points, last visit, birthday, membership.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer name or phone number"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "check_low_stock",
        "description": "Check inventory items that are low or out of stock. Returns items below minimum stock level.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_appointments_today",
        "description": "Get all appointments scheduled for today with customer name, time, service, and status.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_staff_summary",
        "description": "Get staff attendance and commission summary for the current month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month YYYY-MM (default: current month)"}
            },
            "required": []
        }
    },
    {
        "name": "get_birthday_customers",
        "description": "Get customers whose birthday is today or this month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "today | this_month (default: today)"}
            },
            "required": []
        }
    },
    {
        "name": "get_expenses_summary",
        "description": "Get expense summary for current or specified month by category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month YYYY-MM (default: current)"}
            },
            "required": []
        }
    },
    {
        "name": "suggest_offers",
        "description": "Analyze customer data and suggest promotional offers or actions to boost business.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "search_customers",
        "description": "Search customers by name, phone, or visit history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term (name or phone)"},
                "sort_by": {"type": "string", "description": "visits | points | last_visit (default: visits)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "create_invoice",
        "description": "⚠️ ACTION: Pre-fill and open the billing screen with specified items. Requires user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "customer_phone": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":  {"type": "string"},
                            "price": {"type": "number"},
                            "qty":   {"type": "integer"}
                        }
                    }
                },
                "payment_mode": {"type": "string", "description": "Cash | Card | UPI"}
            },
            "required": ["items"]
        }
    },
    {
        "name": "send_whatsapp_message",
        "description": "⚠️ ACTION: Send a WhatsApp message to a customer. Requires user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone":   {"type": "string", "description": "Customer phone number"},
                "message": {"type": "string", "description": "Message to send"}
            },
            "required": ["phone", "message"]
        }
    },
]

# Tools that require user confirmation before execution
ACTION_TOOLS = {"create_invoice", "send_whatsapp_message"}


# ─────────────────────────────────────────────────────────
# READ TOOLS
# ─────────────────────────────────────────────────────────

def get_today_sales() -> dict:
    """Today's complete sales summary."""
    try:
        today = today_str()
        total = bills = 0.0
        payment_modes = defaultdict(float)
        services_count = defaultdict(int)
        recent_bills = []

        if os.path.exists(F_REPORT):
            with open(F_REPORT, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                hdr = next(reader, None)
                for row in reader:
                    if not row or not row[0].startswith(today):
                        continue
                    bills += 1
                    amt = safe_float(row[5] if len(row) > 5 else 0)
                    total += amt
                    pay = row[6] if len(row) > 6 else "Cash"
                    payment_modes[pay] += amt
                    svcs = row[4] if len(row) > 4 else ""
                    for s in svcs.split(","):
                        s = s.strip().split("x")[0].strip()
                        if s:
                            services_count[s] += 1
                    if len(recent_bills) < 5:
                        recent_bills.append({
                            "customer": row[2] if len(row) > 2 else "",
                            "amount":   fmt_currency(amt),
                            "payment":  pay,
                            "time":     row[0][11:16] if len(row[0]) > 11 else ""
                        })

        top_svcs = sorted(services_count.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "status":        "success",
            "date":          today,
            "total_revenue": fmt_currency(total),
            "total_raw":     total,
            "total_bills":   int(bills),
            "avg_bill":      fmt_currency(total / bills) if bills else "₹0.00",
            "payment_breakdown": {k: fmt_currency(v) for k, v in payment_modes.items()},
            "top_services":  [{"service": s, "count": c} for s, c in top_svcs],
            "recent_bills":  recent_bills,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_monthly_summary(month: str = "") -> dict:
    """Monthly revenue summary."""
    try:
        mo = month or month_str()
        total = bills = expenses_total = 0.0
        daily = defaultdict(float)

        if os.path.exists(F_REPORT):
            with open(F_REPORT, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if not row or not row[0].startswith(mo):
                        continue
                    bills += 1
                    amt = safe_float(row[5] if len(row) > 5 else 0)
                    total += amt
                    day = row[0][:10]
                    daily[day] += amt

        expenses = load_json(F_EXPENSES, [])
        for e in expenses:
            if e.get("date", "").startswith(mo):
                expenses_total += safe_float(e.get("amount", 0))

        profit = total - expenses_total
        peak_day = max(daily.items(), key=lambda x: x[1]) if daily else ("—", 0)

        return {
            "status":          "success",
            "month":           mo,
            "total_revenue":   fmt_currency(total),
            "total_bills":     int(bills),
            "avg_daily":       fmt_currency(total / len(daily)) if daily else "₹0.00",
            "total_expenses":  fmt_currency(expenses_total),
            "net_profit":      fmt_currency(profit),
            "peak_day":        peak_day[0],
            "peak_revenue":    fmt_currency(peak_day[1]),
            "days_active":     len(daily),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_top_services(n: int = 5, period: str = "this_month") -> dict:
    """Top services by popularity and revenue."""
    try:
        if period == "today":
            prefix = today_str()
        elif period == "this_month":
            prefix = month_str()
        else:
            prefix = ""

        svc_count   = defaultdict(int)
        svc_revenue = defaultdict(float)

        if os.path.exists(F_REPORT):
            with open(F_REPORT, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if not row: continue
                    if prefix and not row[0].startswith(prefix): continue
                    svcs = row[4] if len(row) > 4 else ""
                    amt  = safe_float(row[5] if len(row) > 5 else 0)
                    for s in svcs.split(","):
                        s = s.strip()
                        if s:
                            name = s.split("x")[0].strip()
                            svc_count[name] += 1
                            svc_revenue[name] += amt / max(1, len(svcs.split(",")))

        top = sorted(svc_count.items(), key=lambda x: x[1], reverse=True)[:n]
        return {
            "status":  "success",
            "period":  period,
            "top_services": [
                {
                    "rank":    i + 1,
                    "service": s,
                    "count":   c,
                    "revenue": fmt_currency(svc_revenue[s])
                }
                for i, (s, c) in enumerate(top)
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_customer_details(name: str) -> dict:
    """Get a specific customer's details."""
    try:
        customers = load_json(F_CUSTOMERS, {})
        name_lower = name.lower().strip()
        match = None
        for phone, c in customers.items():
            if (name_lower in c.get("name", "").lower() or
                    name_lower in phone):
                match = (phone, c)
                break

        if not match:
            return {"status": "not_found",
                    "message": f"Customer '{name}' not found"}

        phone, c = match
        visits  = c.get("visits", [])
        total_spent = sum(safe_float(v.get("total", 0)) for v in visits)

        return {
            "status":       "success",
            "name":         c.get("name", ""),
            "phone":        phone,
            "birthday":     c.get("birthday", "—"),
            "points":       c.get("points", 0),
            "vip":          c.get("vip", False),
            "total_visits": len(visits),
            "total_spent":  fmt_currency(total_spent),
            "last_visit":   visits[-1].get("date", "—") if visits else "—",
            "last_service": visits[-1].get("services", "—") if visits else "—",
            "last_3_visits": [
                {"date": v.get("date",""), "services": v.get("services",""),
                 "total": fmt_currency(safe_float(v.get("total",0)))}
                for v in reversed(visits[-3:])
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_low_stock() -> dict:
    """Inventory items below minimum stock."""
    try:
        inv = load_json(F_INVENTORY, {})
        low = []
        out = []
        for item_id, item in inv.items():
            qty  = safe_float(item.get("qty", 0))
            mins = safe_float(item.get("min_stock", 5))
            name = item.get("name", item_id)
            unit = item.get("unit", "pcs")
            if qty == 0:
                out.append({"name": name, "qty": 0, "unit": unit,
                             "min": mins, "status": "OUT OF STOCK"})
            elif qty <= mins:
                low.append({"name": name, "qty": qty, "unit": unit,
                             "min": mins, "status": "LOW STOCK"})

        return {
            "status":       "success",
            "out_of_stock": out,
            "low_stock":    low,
            "total_alerts": len(out) + len(low),
            "summary":      f"{len(out)} out of stock, {len(low)} low stock"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_appointments_today() -> dict:
    """Today's appointments."""
    try:
        appts = load_json(F_APPOINTMENTS, [])
        today = today_str()
        today_list = [
            {
                "time":     a.get("time", ""),
                "customer": a.get("customer", ""),
                "phone":    a.get("phone", ""),
                "service":  a.get("service", ""),
                "staff":    a.get("staff", ""),
                "status":   a.get("status", "Scheduled"),
            }
            for a in appts
            if a.get("date", "") == today
        ]
        today_list.sort(key=lambda x: x["time"])

        scheduled = sum(1 for a in today_list if a["status"] == "Scheduled")
        completed = sum(1 for a in today_list if a["status"] == "Completed")

        return {
            "status":      "success",
            "date":        today,
            "total":       len(today_list),
            "scheduled":   scheduled,
            "completed":   completed,
            "appointments": today_list
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_staff_summary(month: str = "") -> dict:
    """Staff attendance and commission summary."""
    try:
        mo    = month or month_str()
        staff = load_json(F_STAFF, {})
        summary = []

        for name, s in staff.items():
            if not s.get("active", True):
                continue
            att_list = s.get("attendance", [])
            mo_att   = [a for a in att_list if a.get("date","")[:7] == mo]
            present  = sum(1 for a in mo_att if a.get("status") == "Present")
            absent   = sum(1 for a in mo_att if a.get("status") == "Absent")
            leave    = sum(1 for a in mo_att if a.get("status") == "Leave")
            pct      = round(present / len(mo_att) * 100) if mo_att else 0

            comm_pct  = safe_float(s.get("commission_pct", 0))
            mo_sales  = sum(
                safe_float(sale.get("amount", 0))
                for sale in s.get("sales", [])
                if sale.get("month", "") == mo
            )
            comm_earn = mo_sales * comm_pct / 100

            summary.append({
                "name":       name,
                "role":       s.get("role", ""),
                "present":    present,
                "absent":     absent,
                "leave":      leave,
                "att_pct":    f"{pct}%",
                "sales":      fmt_currency(mo_sales),
                "commission": fmt_currency(comm_earn),
            })

        return {
            "status":  "success",
            "month":   mo,
            "staff":   summary,
            "total_staff": len(summary)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_birthday_customers(period: str = "today") -> dict:
    """Customers with birthday today or this month."""
    try:
        customers = load_json(F_CUSTOMERS, {})
        today_md  = date.today().strftime("-%m-%d")
        this_mo   = f"-{date.today().strftime('%m')}-"
        result    = []

        for phone, c in customers.items():
            bd = c.get("birthday", "")
            if not bd:
                continue
            if period == "today" and bd.endswith(today_md):
                result.append({
                    "name":    c.get("name", ""),
                    "phone":   phone,
                    "birthday": bd,
                    "points":  c.get("points", 0)
                })
            elif period == "this_month" and this_mo in bd:
                result.append({
                    "name":    c.get("name", ""),
                    "phone":   phone,
                    "birthday": bd,
                    "points":  c.get("points", 0)
                })

        return {
            "status":    "success",
            "period":    period,
            "count":     len(result),
            "customers": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_expenses_summary(month: str = "") -> dict:
    """Monthly expense breakdown by category."""
    try:
        mo       = month or month_str()
        expenses = load_json(F_EXPENSES, [])
        by_cat   = defaultdict(float)
        total    = 0.0

        for e in expenses:
            if not e.get("date", "").startswith(mo):
                continue
            cat = e.get("category", "Other")
            amt = safe_float(e.get("amount", 0))
            by_cat[cat] += amt
            total += amt

        cats_sorted = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
        return {
            "status":     "success",
            "month":      mo,
            "total":      fmt_currency(total),
            "total_raw":  total,
            "by_category": [
                {"category": c, "amount": fmt_currency(a),
                 "pct": f"{a/total*100:.0f}%" if total else "0%"}
                for c, a in cats_sorted
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def suggest_offers() -> dict:
    """AI-ready data for offer suggestions."""
    try:
        customers = load_json(F_CUSTOMERS, {})
        total_customers = len(customers)
        inactive = []
        high_value = []
        today_md = date.today().strftime("-%m-%d")
        birthdays_today = []

        for phone, c in customers.items():
            visits = c.get("visits", [])
            pts    = c.get("points", 0)
            name   = c.get("name", phone)
            bd     = c.get("birthday", "")

            if bd and bd.endswith(today_md):
                birthdays_today.append(name)

            if not visits:
                continue
            last_visit = visits[-1].get("date","")
            try:
                days_ago = (date.today() -
                            date.fromisoformat(last_visit)).days
                if days_ago > 45:
                    inactive.append({"name": name, "phone": phone,
                                     "days_ago": days_ago})
                if pts > 500:
                    high_value.append({"name": name, "phone": phone,
                                       "points": pts})
            except Exception:
                pass

        top_svc = get_top_services(3)

        return {
            "status":            "success",
            "total_customers":   total_customers,
            "inactive_30plus":   sorted(inactive, key=lambda x: x["days_ago"], reverse=True)[:10],
            "high_value_members": sorted(high_value, key=lambda x: x["points"], reverse=True)[:5],
            "birthdays_today":   birthdays_today,
            "top_services":      top_svc.get("top_services", []),
            "suggestions_ready": True
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def search_customers(query: str, sort_by: str = "visits") -> dict:
    """Search customers by name or phone."""
    try:
        customers = load_json(F_CUSTOMERS, {})
        q = query.lower().strip()
        results = []

        for phone, c in customers.items():
            if q in c.get("name","").lower() or q in phone:
                visits = c.get("visits", [])
                results.append({
                    "name":    c.get("name", ""),
                    "phone":   phone,
                    "visits":  len(visits),
                    "points":  c.get("points", 0),
                    "last_visit": visits[-1].get("date","—") if visits else "—"
                })

        sort_keys = {"visits": "visits", "points": "points",
                     "last_visit": "last_visit"}
        key = sort_keys.get(sort_by, "visits")
        results.sort(key=lambda x: x[key], reverse=True)

        return {
            "status":  "success",
            "query":   query,
            "count":   len(results),
            "results": results[:10]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────────────────────
# ACTION TOOLS (require confirmation — handled by controller)
# ─────────────────────────────────────────────────────────

def create_invoice(customer_name: str = "", customer_phone: str = "",
                   items: list = None, payment_mode: str = "Cash") -> dict:
    """Prepare invoice data — actual creation done by controller."""
    items = items or []
    subtotal = sum(i.get("price", 0) * i.get("qty", 1) for i in items)
    return {
        "status":         "ready_for_action",
        "action":         "create_invoice",
        "requires_confirmation": True,
        "data": {
            "customer_name":  customer_name,
            "customer_phone": customer_phone,
            "items":          items,
            "payment_mode":   payment_mode,
            "subtotal":       fmt_currency(subtotal),
        },
        "summary": f"Create bill for {customer_name or 'Walk-in'}: {len(items)} item(s), Total {fmt_currency(subtotal)}"
    }


def send_whatsapp_message(phone: str, message: str) -> dict:
    """Prepare WhatsApp data — actual send done by controller."""
    return {
        "status":         "ready_for_action",
        "action":         "send_whatsapp",
        "requires_confirmation": True,
        "data": {
            "phone":   phone,
            "message": message,
        },
        "summary": f"Send WhatsApp to {phone}: '{message[:50]}...'"
    }


# ─────────────────────────────────────────────────────────
# TOOL DISPATCHER
# ─────────────────────────────────────────────────────────
TOOL_MAP = {
    "get_today_sales":        get_today_sales,
    "get_monthly_summary":    get_monthly_summary,
    "get_top_services":       get_top_services,
    "get_customer_details":   get_customer_details,
    "check_low_stock":        check_low_stock,
    "get_appointments_today": get_appointments_today,
    "get_staff_summary":      get_staff_summary,
    "get_birthday_customers": get_birthday_customers,
    "get_expenses_summary":   get_expenses_summary,
    "suggest_offers":         suggest_offers,
    "search_customers":       search_customers,
    "create_invoice":         create_invoice,
    "send_whatsapp_message":  send_whatsapp_message,
}


def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    """Call a tool by name with given input."""
    fn = TOOL_MAP.get(tool_name)
    if not fn:
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}
    try:
        return fn(**tool_input)
    except Exception as e:
        return {"status": "error", "message": str(e), "tool": tool_name}
