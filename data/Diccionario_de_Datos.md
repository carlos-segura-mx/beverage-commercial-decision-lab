# Diccionario de datos

Todos los datos son sintéticos y se generaron con semilla fija `20260831`. El caso contiene 37,440 observaciones semanales: 104 semanas × 60 puntos de venta × 6 SKU.

## `fact_sales.csv`

| Campo | Tipo | Descripción |
|---|---|---|
| `date` | fecha | Inicio de la semana comercial |
| `week_id` | entero | Consecutivo de semana |
| `year_week` | texto | Semana ISO, formato AAAA-Www |
| `pdv_id` | texto | Llave del punto de venta |
| `sku` | texto | Llave del producto |
| `units_ordered` | entero | Unidades solicitadas por el PDV |
| `units_delivered` | entero | Unidades entregadas |
| `units_sold` | entero | Unidades vendidas al consumidor |
| `list_price` | decimal | Precio de lista unitario, MXN |
| `discount_pct` | decimal | Descuento observado, 0–1 |
| `net_price` | decimal | Precio neto unitario, MXN |
| `unit_cost` | decimal | Costo unitario, MXN |
| `revenue` | decimal | Venta neta = unidades × precio neto |
| `cost_of_sales` | decimal | Costo de venta = unidades × costo unitario |
| `contribution` | decimal | Venta neta − costo de venta |
| `opening_inventory` | entero | Inventario inicial semanal |
| `ending_inventory` | entero | Inventario final semanal |
| `promotion_flag` | entero | 1 si hubo promoción; 0 en otro caso |
| `numeric_distribution` | decimal | Fracción de cobertura numérica, 0–1 |

## Dimensiones

| Archivo | Llave | Contenido |
|---|---|---|
| `dim_product.csv` | `sku` | Producto, categoría, empaque, precio, costo y elasticidad de simulación |
| `dim_customer.csv` | `pdv_id` | Punto de venta, canal y zona |
| `dim_date.csv` | `date` | Año, mes, trimestre y semana ISO |

## Resultados analíticos

| Archivo | Grano | Uso |
|---|---|---|
| `weekly_sales.csv` | semana × SKU | Serie agregada de demanda, venta, contribución y servicio |
| `elasticities_estimated.csv` | SKU | Elasticidad precio propia estimada, error estándar y R² |
| `forecast_metrics.csv` | SKU × método | MAE, RMSE, WAPE y Bias en holdout |
| `forecast_holdout.csv` | semana × SKU × método | Actual y predicción para comparación fuera de muestra |
| `forecast_future.csv` | semana futura × SKU | Forecast de producción a 8 semanas |
| `cross_elasticity_matrix.csv` | SKU origen × SKU afectado | Supuestos de canibalización y sustitución |
| `pricing_scenario_reference.csv` | SKU | Escenario de descuento, volumen, venta y contribución |

## Reglas de calidad

- `sku`, `pdv_id` y `date` no deben ser nulos en la tabla de hechos.
- `units_delivered ≤ units_ordered` y las variables comerciales no deben ser negativas.
- `net_price = list_price × (1 − discount_pct)` dentro de tolerancia de redondeo.
- `revenue = units_sold × net_price`; `contribution = revenue − cost_of_sales`.
- Toda llave de hechos debe existir en su dimensión correspondiente.
