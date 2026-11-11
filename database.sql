-- LaptopCare Enterprise Automation Database
-- PostgreSQL / Supabase SQL
-- Run in Supabase SQL Editor.
-- NOTE: Review RLS policies and connect Supabase Auth before production use.

create extension if not exists pgcrypto;

-- 1. Suppliers
create table if not exists public.suppliers (
    supplier_id uuid primary key default gen_random_uuid(),
    supplier_name varchar(150) not null,
    email varchar(150) unique,
    phone varchar(30),
    company_name varchar(150),
    address text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 2. Products
create table if not exists public.products (
    product_id uuid primary key default gen_random_uuid(),
    product_name varchar(150) not null,
    brand varchar(100),
    model varchar(100),
    description text,
    price numeric(12,2) not null check (price >= 0),
    stock_quantity integer not null default 0 check (stock_quantity >= 0),
    warranty_months integer not null default 0 check (warranty_months >= 0),
    primary_supplier_id uuid references public.suppliers(supplier_id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 3. Customers
create table if not exists public.customers (
    customer_id uuid primary key default gen_random_uuid(),
    full_name varchar(150) not null,
    email varchar(150) unique not null,
    phone varchar(30),
    address text,
    city varchar(100),
    state varchar(100),
    postal_code varchar(20),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 4. Orders
create table if not exists public.orders (
    order_id uuid primary key default gen_random_uuid(),
    customer_id uuid not null references public.customers(customer_id) on delete restrict,
    order_date timestamptz not null default now(),
    total_amount numeric(12,2) not null default 0 check (total_amount >= 0),
    order_status varchar(30) not null default 'pending'
        check (order_status in ('pending','confirmed','processing','shipped','delivered','cancelled')),
    payment_status varchar(30) not null default 'unpaid'
        check (payment_status in ('unpaid','paid','refunded','failed')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 5. Order items: resolves the many-to-many relationship between orders and products
create table if not exists public.order_items (
    order_item_id uuid primary key default gen_random_uuid(),
    order_id uuid not null references public.orders(order_id) on delete cascade,
    product_id uuid not null references public.products(product_id) on delete restrict,
    quantity integer not null check (quantity > 0),
    unit_price numeric(12,2) not null check (unit_price >= 0),
    subtotal numeric(14,2) generated always as (quantity * unit_price) stored,
    created_at timestamptz not null default now()
);

-- 6. Supplier products: resolves the many-to-many relationship between suppliers and products
create table if not exists public.supplier_products (
    supplier_product_id uuid primary key default gen_random_uuid(),
    supplier_id uuid not null references public.suppliers(supplier_id) on delete cascade,
    product_id uuid not null references public.products(product_id) on delete cascade,
    supply_price numeric(12,2) check (supply_price is null or supply_price >= 0),
    created_at timestamptz not null default now(),
    unique (supplier_id, product_id)
);

-- 7. Shipments
create table if not exists public.shipments (
    shipment_id uuid primary key default gen_random_uuid(),
    order_id uuid not null references public.orders(order_id) on delete cascade,
    tracking_number varchar(100) unique,
    courier_name varchar(100),
    shipment_status varchar(30) not null default 'preparing'
        check (shipment_status in ('preparing','dispatched','in_transit','out_for_delivery','delivered','returned')),
    shipping_address text,
    shipped_at timestamptz,
    estimated_delivery timestamptz,
    delivered_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 8. AI agent activity logs
create table if not exists public.ai_agent_logs (
    log_id uuid primary key default gen_random_uuid(),
    customer_id uuid references public.customers(customer_id) on delete set null,
    order_id uuid references public.orders(order_id) on delete set null,
    product_id uuid references public.products(product_id) on delete set null,
    agent_name varchar(100) not null,
    action varchar(150) not null,
    input_data jsonb not null default '{}'::jsonb,
    output_data jsonb not null default '{}'::jsonb,
    execution_status varchar(30) not null default 'success'
        check (execution_status in ('success','failed','pending','escalated')),
    error_message text,
    response_time_ms integer check (response_time_ms is null or response_time_ms >= 0),
    created_at timestamptz not null default now()
);

-- Reusable updated_at trigger
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_suppliers_updated_at on public.suppliers;
create trigger trg_suppliers_updated_at before update on public.suppliers
for each row execute function public.set_updated_at();

drop trigger if exists trg_products_updated_at on public.products;
create trigger trg_products_updated_at before update on public.products
for each row execute function public.set_updated_at();

drop trigger if exists trg_customers_updated_at on public.customers;
create trigger trg_customers_updated_at before update on public.customers
for each row execute function public.set_updated_at();

drop trigger if exists trg_orders_updated_at on public.orders;
create trigger trg_orders_updated_at before update on public.orders
for each row execute function public.set_updated_at();

drop trigger if exists trg_shipments_updated_at on public.shipments;
create trigger trg_shipments_updated_at before update on public.shipments
for each row execute function public.set_updated_at();

-- Indexes for common lookups and joins
create index if not exists idx_products_brand on public.products(brand);
create index if not exists idx_products_stock on public.products(stock_quantity);
create index if not exists idx_orders_customer on public.orders(customer_id);
create index if not exists idx_orders_status on public.orders(order_status);
create index if not exists idx_orders_date on public.orders(order_date desc);
create index if not exists idx_order_items_order on public.order_items(order_id);
create index if not exists idx_order_items_product on public.order_items(product_id);
create index if not exists idx_supplier_products_supplier on public.supplier_products(supplier_id);
create index if not exists idx_supplier_products_product on public.supplier_products(product_id);
create index if not exists idx_shipments_order on public.shipments(order_id);
create index if not exists idx_shipments_status on public.shipments(shipment_status);
create index if not exists idx_ai_logs_customer on public.ai_agent_logs(customer_id);
create index if not exists idx_ai_logs_created on public.ai_agent_logs(created_at desc);
create index if not exists idx_ai_logs_status on public.ai_agent_logs(execution_status);

-- Security starter:
-- RLS is intentionally not enabled here because a correct policy depends on
-- your auth.users/profile mapping and staff roles. Do not expose tables with
-- unrestricted anon access. Enable RLS and add role-based policies before launch.
