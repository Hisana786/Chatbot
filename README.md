# Chatbot

This project combines an AI-assisted inventory dashboard with an n8n-powered stock-analysis workflow for smarter purchasing decisions.

## Overview
To reduce manual inventory work, identify stock shortages quickly, and help businesses make better purchasing decisions.

## Included files
- `ai_inventory_management_workflow.json` — importable n8n workflow.
- `supabase_setup.sql` — creates the table used to save analysis results.
- `manage.py` and the Django app files — run the dashboard, chatbot, and reports UI.

## Workflow steps
1. Webhook receives a POST request.
2. Code node validates `product_id` and `requested_quantity`.
3. HTTP Request retrieves product stock from Supabase `products`.
4. Code node compares requested quantity with current stock and calculates any shortage.
5. IF node checks whether the product exists.
6. If found, the result is inserted into `ai_inventory_analysis_results`.
7. Respond to Webhook returns the analysis as JSON.
8. If the product is not found, the workflow returns HTTP 404.

## Supabase preparation
1. Ensure your existing `public.products` table has:
   - `product_id` (UUID primary key)
   - `product_name`
   - `brand`
   - `model`
   - `stock_quantity` (integer)
   - `price`
   - `primary_supplier_id` (optional)
2. Run `supabase_setup.sql` in Supabase SQL Editor.
3. In your n8n host, set environment variables:
   - `SUPABASE_URL` = `https://YOUR_PROJECT_REF.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` = your Supabase service-role key
4. Import the JSON in n8n: **Workflows → Import from File**.
5. Confirm the expressions in the two HTTP Request nodes can access those environment variables. Some hosted n8n plans restrict `$env`; if so, replace the header values with an n8n Header Auth credential or another secure credential method.
6. Save and activate the workflow after testing.

Never put the Supabase service-role key in browser code or send it to customers. Keep it only in n8n's secure server-side environment/credentials.

## Test request

POST to the n8n webhook test URL with JSON:

```json
{
  "product_id": "YOUR_EXISTING_PRODUCT_UUID",
  "requested_quantity": 12,
  "reorder_buffer": 5,
  "request_id": "REQ-1001"
}
```

Use the **Test URL** while the workflow is in test mode. Activate the workflow and use the **Production URL** for live calls.

## Example response when stock is short

```json
{
  "found": true,
  "product_name": "Dell Inspiron 15",
  "current_stock": 5,
  "requested_quantity": 12,
  "shortage_quantity": 7,
  "stock_sufficient": false,
  "status": "stock_shortage",
  "reorder_recommendation": {
    "recommended_quantity": 12,
    "reason": "Requested 12, but only 5 are in stock. Shortage: 7.",
    "supplier_id": "..."
  }
}
```

## Notes / production hardening
- This workflow recommends reorder quantity; it does not automatically create a supplier purchase order or change product stock.
- To avoid overselling under concurrent orders, perform stock reservation/decrement inside a PostgreSQL transaction or Supabase RPC function, not only in this workflow.
- Add authentication to the webhook (for example, an n8n Header Auth credential), request rate limiting, and input validation before production.
- Configure an Error Trigger workflow for API failures and alerting.
- Confirm the exact `products` column names match your Supabase schema before activation.
