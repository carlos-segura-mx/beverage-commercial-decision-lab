/*
Caso: Beverage Commercial Decision Lab
Autor: Carlos Segura
Objetivo: consultas reproducibles para desempeño comercial, servicio y forecast.

Modelo lógico esperado:
  fact_sales(date, pdv_id, sku, units_ordered, units_delivered, units_sold,
             list_price, discount_pct, net_price, unit_cost, revenue,
             cost_of_sales, contribution, opening_inventory, ending_inventory,
             promotion_flag, numeric_distribution)
  dim_product(sku, product, category, pack_ml, base_list_price, base_unit_cost)
  dim_customer(pdv_id, point_of_sale, channel, zone)
  dim_date(date, week_id, year, month_num, month, quarter, iso_week, year_week)
  forecast_holdout(date, sku, method, actual_units, forecast_units, error_units)

*/

-- 1) Tablero semanal: venta, contribución, margen y nivel de servicio.
SELECT
    d.year_week,
    c.channel,
    p.category,
    SUM(f.units_sold) AS units_sold,
    SUM(f.revenue) AS revenue,
    SUM(f.contribution) AS contribution,
    SUM(f.contribution) / NULLIF(SUM(f.revenue), 0) AS margin_pct,
    SUM(f.units_delivered) * 1.0 / NULLIF(SUM(f.units_ordered), 0) AS service_level
FROM fact_sales AS f
JOIN dim_date AS d ON d.date = f.date
JOIN dim_customer AS c ON c.pdv_id = f.pdv_id
JOIN dim_product AS p ON p.sku = f.sku
GROUP BY d.year_week, c.channel, p.category
ORDER BY d.year_week, c.channel, p.category;

-- 2) Ranking de SKU por contribución dentro de cada canal.
WITH sku_channel AS (
    SELECT
        c.channel,
        f.sku,
        p.product,
        SUM(f.units_sold) AS units_sold,
        SUM(f.revenue) AS revenue,
        SUM(f.contribution) AS contribution
    FROM fact_sales AS f
    JOIN dim_customer AS c ON c.pdv_id = f.pdv_id
    JOIN dim_product AS p ON p.sku = f.sku
    GROUP BY c.channel, f.sku, p.product
)
SELECT
    channel,
    sku,
    product,
    units_sold,
    revenue,
    contribution,
    RANK() OVER (PARTITION BY channel ORDER BY contribution DESC) AS contribution_rank
FROM sku_channel
ORDER BY channel, contribution_rank;

-- 3) Desempeño promocional observado por SKU.
SELECT
    f.sku,
    p.product,
    f.promotion_flag,
    COUNT(*) AS observations,
    AVG(f.discount_pct) AS avg_discount_pct,
    AVG(f.units_sold) AS avg_units_sold,
    AVG(f.net_price) AS avg_net_price,
    SUM(f.contribution) / NULLIF(SUM(f.revenue), 0) AS margin_pct
FROM fact_sales AS f
JOIN dim_product AS p ON p.sku = f.sku
GROUP BY f.sku, p.product, f.promotion_flag
ORDER BY f.sku, f.promotion_flag;

-- 4) Precisión del forecast por método y SKU.
SELECT
    h.sku,
    p.product,
    h.method,
    SUM(ABS(h.actual_units - h.forecast_units)) / NULLIF(SUM(h.actual_units), 0) AS wape,
    SUM(h.forecast_units - h.actual_units) / NULLIF(SUM(h.actual_units), 0) AS bias,
    AVG(ABS(h.actual_units - h.forecast_units)) AS mae
FROM forecast_holdout AS h
JOIN dim_product AS p ON p.sku = h.sku
GROUP BY h.sku, p.product, h.method
ORDER BY h.sku, wape;

-- 5) Riesgo operativo: bajo servicio y poco inventario final.
WITH operational AS (
    SELECT
        f.date,
        f.pdv_id,
        f.sku,
        f.units_ordered,
        f.units_delivered,
        f.units_sold,
        f.ending_inventory,
        f.units_delivered * 1.0 / NULLIF(f.units_ordered, 0) AS service_level
    FROM fact_sales AS f
)

-- Umbrales demostrativos:
-- servicio menor a 90% o inventario final de dos unidades o menos.
SELECT
    o.date,
    o.pdv_id,
    c.point_of_sale,
    c.channel,
    c.zone,
    o.sku,
    p.product,
    o.service_level,
    o.ending_inventory,
    o.units_sold
FROM operational AS o
JOIN dim_customer AS c ON c.pdv_id = o.pdv_id
JOIN dim_product AS p ON p.sku = o.sku
WHERE o.service_level < 0.90
   OR o.ending_inventory <= 2
ORDER BY o.date DESC, o.service_level, o.ending_inventory;

-- 6) Controles de calidad de catálogos y llaves.
SELECT 'fact_without_product' AS check_name, COUNT(*) AS issue_count
FROM fact_sales AS f
LEFT JOIN dim_product AS p ON p.sku = f.sku
WHERE p.sku IS NULL
UNION ALL
SELECT 'fact_without_customer', COUNT(*)
FROM fact_sales AS f
LEFT JOIN dim_customer AS c ON c.pdv_id = f.pdv_id
WHERE c.pdv_id IS NULL
UNION ALL
SELECT 'duplicate_product_key', COUNT(*)
FROM (
    SELECT sku FROM dim_product GROUP BY sku HAVING COUNT(*) > 1
) AS duplicated_products
UNION ALL
SELECT 'negative_commercial_value', COUNT(*)
FROM fact_sales
WHERE units_sold < 0 OR revenue < 0 OR contribution < 0;

-- 7) Oportunidad por punto de venta: distribución presente, baja venta y buen servicio.
WITH pdv_sku AS (
    SELECT
        f.pdv_id,
        f.sku,
        AVG(f.numeric_distribution) AS avg_numeric_distribution,
        SUM(f.units_sold) AS units_sold,
        SUM(f.units_delivered) * 1.0 / NULLIF(SUM(f.units_ordered), 0) AS service_level,
        SUM(f.contribution) AS contribution
    FROM fact_sales AS f
    GROUP BY f.pdv_id, f.sku
), scored AS (
    SELECT
        x.*,
        PERCENT_RANK() OVER (PARTITION BY x.sku ORDER BY x.units_sold) AS sales_percentile
    FROM pdv_sku AS x
)
SELECT
    s.pdv_id,
    c.point_of_sale,
    c.channel,
    c.zone,
    s.sku,
    p.product,
    s.avg_numeric_distribution,
    s.units_sold,
    s.service_level,
    s.contribution
FROM scored AS s
JOIN dim_customer AS c ON c.pdv_id = s.pdv_id
JOIN dim_product AS p ON p.sku = s.sku
WHERE s.avg_numeric_distribution >= 0.85
  AND s.service_level >= 0.95
  AND s.sales_percentile <= 0.25
ORDER BY s.sku, s.units_sold;
