# Medidas DAX — Beverage Commercial Decision Lab

Modelo recomendado: `DimDate[date]` → `FactSales[date]`, `DimProduct[sku]` → `FactSales[sku]`, `DimCustomer[pdv_id]` → `FactSales[pdv_id]`. Marcar `DimDate` como tabla de fechas. Relacionar `ForecastHoldout` y `ForecastFuture` con `DimDate` y `DimProduct` por sus dimensiones, evitando relaciones directas entre hechos.

```DAX
Unidades Vendidas = SUM ( FactSales[units_sold] )

Unidades Pedidas = SUM ( FactSales[units_ordered] )

Unidades Entregadas = SUM ( FactSales[units_delivered] )

Venta Neta = SUM ( FactSales[revenue] )

Costo de Venta = SUM ( FactSales[cost_of_sales] )

Contribución = SUM ( FactSales[contribution] )

Margen % = DIVIDE ( [Contribución], [Venta Neta] )

Precio Neto Promedio =
DIVIDE ( [Venta Neta], [Unidades Vendidas] )

Descuento Promedio Ponderado =
DIVIDE (
    SUMX ( FactSales, FactSales[discount_pct] * FactSales[units_sold] ),
    [Unidades Vendidas]
)

Nivel de Servicio =
DIVIDE ( [Unidades Entregadas], [Unidades Pedidas] )

Inventario Final = SUM ( FactSales[ending_inventory] )

Distribución Numérica = AVERAGE ( FactSales[numeric_distribution] )

Venta AA =
CALCULATE ( [Venta Neta], DATEADD ( DimDate[date], -1, YEAR ) )

Crecimiento Venta % =
DIVIDE ( [Venta Neta] - [Venta AA], [Venta AA] )

Unidades 4S =
CALCULATE (
    [Unidades Vendidas],
    DATESINPERIOD ( DimDate[date], MAX ( DimDate[date] ), -28, DAY )
)

Unidades 4S Anteriores =
CALCULATE (
    [Unidades Vendidas],
    DATESINPERIOD ( DimDate[date], MAX ( DimDate[date] ) - 28, -28, DAY )
)

Tendencia Unidades 4S % =
DIVIDE ( [Unidades 4S] - [Unidades 4S Anteriores], [Unidades 4S Anteriores] )

Forecast Unidades = SUM ( ForecastFuture[forecast_units] )

Actual Holdout = SUM ( ForecastHoldout[actual_units] )

Forecast Holdout = SUM ( ForecastHoldout[forecast_units] )

Error Absoluto =
SUMX (
    ForecastHoldout,
    ABS ( ForecastHoldout[actual_units] - ForecastHoldout[forecast_units] )
)

WAPE = DIVIDE ( [Error Absoluto], [Actual Holdout] )

Bias =
DIVIDE ( [Forecast Holdout] - [Actual Holdout], [Actual Holdout] )

Semáforo WAPE =
SWITCH (
    TRUE (),
    [WAPE] <= 0.06, "Verde",
    [WAPE] <= 0.10, "Ámbar",
    "Rojo"
)

PDV con Riesgo =
COUNTROWS (
    FILTER (
        SUMMARIZE (
            FactSales,
            DimCustomer[pdv_id],
            DimProduct[sku],
            "Servicio", [Nivel de Servicio],
            "Stock", [Inventario Final]
        ),
        [Servicio] < 0.90 || [Stock] <= 2
    )
)

Participación Contribución % =
DIVIDE (
    [Contribución],
    CALCULATE ( [Contribución], ALLSELECTED ( DimProduct[product] ) )
)

Título Periodo =
"Resultados al " & FORMAT ( MAX ( DimDate[date] ), "dd mmm yyyy" )
```

Formato sugerido: moneda en MXN sin decimales; porcentajes con un decimal; WAPE y Bias con un decimal; unidades con separador de miles. Aplicar formato condicional a `Margen %`, `Nivel de Servicio`, `WAPE` y `Bias`.
