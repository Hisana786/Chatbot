import json
import os
import urllib.error
import urllib.request

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


def _get_supabase_client():
    try:
        from supabase import create_client
    except ImportError:
        return None

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url or not supabase_key:
        return None

    return create_client(supabase_url, supabase_key)


def _count_rows(client, table_name):
    if client is None:
        return 0

    try:
        response = client.table(table_name).select("*", count="exact").execute()
        data = getattr(response, "data", None) or []
        count = getattr(response, "count", None)
        if count is not None:
            return int(count)
        return len(data)
    except Exception:
        return 0


def _recent_orders(client):
    if client is None:
        return []

    try:
        response = (
            client.table("orders")
            .select("order_id, customer_id, order_status, total_amount, created_at")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [
            {
                "id": row.get("order_id"),
                "customer": row.get("customer_id") or "N/A",
                "status": row.get("order_status") or "pending",
                "total": row.get("total_amount") or 0,
            }
            for row in rows
        ]
    except Exception:
        return []


def _recent_ai_logs(client):
    if client is None:
        return []

    try:
        response = (
            client.table("ai_agent_logs")
            .select("log_id, agent_name, action, created_at")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [
            {
                "title": row.get("action") or row.get("agent_name") or "AI event",
                "time": row.get("created_at") or "recently",
            }
            for row in rows
        ]
    except Exception:
        return []


def index(request):
    client = _get_supabase_client()

    context = {
        "total_customers": _count_rows(client, "customers"),
        "total_products": _count_rows(client, "products"),
        "total_orders": _count_rows(client, "orders"),
        "total_ai_logs": _count_rows(client, "ai_agent_logs"),
        "recent_orders": _recent_orders(client),
        "recent_ai_logs": _recent_ai_logs(client),
        "project_summary": [
            {
                "title": "Laptop stock health",
                "text": "AI compares current unit counts against demand spikes so the team can act before ASP or sales revenue drops.",
                "value": "92.8%",
            },
            {
                "title": "Restock forecast",
                "text": "The workflow evaluates low-stock models and highlights the next laptop SKUs to reorder based on sales velocity.",
                "value": "7 SKUs",
            },
            {
                "title": "Supplier action queue",
                "text": "Pending vendor follow-ups and reorder triggers keep procurement aligned with live stock and order volume.",
                "value": "12 open",
            },
        ],
        "pipeline_items": [
            {"name": "Laptop stock monitor", "status": "Healthy", "detail": "Average stock validation under 2s"},
            {"name": "AI restock recommendations", "status": "Live", "detail": "Triggered for low-stock SKU events"},
            {"name": "Order and supplier sync", "status": "Synced", "detail": "Connected to recent transactions and logs"},
        ],
    }
    return render(request, "dashboard/dashboard.html", context)


def _fallback_chatbot_reply(message):
    lower = message.lower()
    if "stock" in lower or "inventory" in lower:
        return "I can help with inventory checks. If you want live stock data, connect your Supabase project and add an OpenAI API key to enable the full AI assistant."
    if "order" in lower:
        return "I can help review recent orders, confirm status, and flag urgent stock shortages."
    if "supplier" in lower:
        return "For supplier questions, I recommend checking the latest purchase agreements and preferred vendor list before placing a reorder."
    if not message.strip():
        return "Please type a message so I can help."
    return "I’m the LaptopCare assistant. Ask me about stock, orders, suppliers, or product availability."


def _openai_reply(message):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        payload = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": "You are a friendly LaptopCare inventory assistant."},
                {"role": "user", "content": message},
            ],
            "temperature": 0.4,
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip() if content.strip() else None
    except (urllib.error.URLError, ValueError, KeyError, IndexError):
        return None


def generate_chatbot_reply(message):
    message = (message or "").strip()
    if not message:
        return "Please type a message so I can help."

    reply = _openai_reply(message)
    if reply:
        return reply
    return _fallback_chatbot_reply(message)


def chat_page(request):
    return render(request, "dashboard/chat.html")


def reports_page(request):
    context = {
        "sales_total": "$248,400",
        "inventory_value": "$96,250",
        "low_stock_count": 12,
        "order_completion": "94.2%",
        "top_products": [
            {"name": "Dell XPS 13", "sales": 142, "revenue": "$48,400"},
            {"name": "Lenovo ThinkPad T14", "sales": 98, "revenue": "$33,060"},
            {"name": "MacBook Pro 14", "sales": 64, "revenue": "$29,120"},
        ],
        "status_breakdown": [
            {"label": "Delivered", "value": 68, "color": "#a78bfa"},
            {"label": "Processing", "value": 21, "color": "#c084fc"},
            {"label": "Pending", "value": 11, "color": "#e9d5ff"},
        ],
    }
    return render(request, "dashboard/reports.html", context)


@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    message = (data.get("message") or request.POST.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Message is required."}, status=400)

    return JsonResponse({"reply": generate_chatbot_reply(message)})
