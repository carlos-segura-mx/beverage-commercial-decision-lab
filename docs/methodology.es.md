# Metodología e interpretación

[Español](methodology.es.md) | [English](methodology.md)

## Decisión comercial

La pregunta central es si una promoción de precios mejora la contribución del portafolio al considerar al mismo tiempo los cambios de volumen, la sustitución entre productos y la variación de precios. El dashboard también ofrece información descriptiva de ventas al consumidor y comparación histórica de pronósticos.

## Entorno sintético

El caso reúne 104 semanas indexadas (con fechas simuladas), 60 puntos de venta, seis productos y 37,440 registros por punto de venta, SKU y semana. Las ventas sintéticas son unidades vendidas al consumidor multiplicadas por el precio neto supuesto. La contribución resta el costo de venta sintético. No equivale a utilidad operativa ni al margen del distribuidor.

## Metodología del dashboard comercial

Las secciones comerciales comparten filtros de fechas, canal, zona y SKU. La vista inicial abarca las últimas 13 semanas sintéticas. Ventas, contribución y unidades se agregan por suma. El margen divide la contribución total entre las ventas simuladas al consumidor. El nivel de servicio divide las unidades entregadas totales entre las solicitadas, sin promediar porcentajes por punto de venta.

Cuando existe un periodo anterior de igual duración bajo los mismos filtros, el panorama ejecutivo calcula las variaciones de ventas, contribución y unidades. En caso contrario, no se presenta comparación. Las unidades sin entregar no se convierten en supuestas ventas perdidas.

La lista de entregas identifica pares PDV/SKU bajo un umbral ajustable de servicio, sujetos a una cantidad mínima solicitada. La revisión comercial identifica pares con servicio de al menos 95 % y volumen situado en el cuartil inferior de sus pares del mismo producto y canal, con un mínimo de cuatro puntos comparables. Son reglas descriptivas, no pronósticos de demanda ni efectos causales. No se usan inventarios sin continuidad.

## Simulador de precios

Para un producto i con precio P_i, volumen Q_i y costo unitario C_i, se elige descuento d_i entre 0 y 0.20. El cambio proporcional del precio es -d_i. Se aplica una respuesta lineal:

`Q_i_nuevo = max(0, Q_i * (1 + suma_j(E_ij * (-d_j))))`

`P_i_nuevo = P_i * (1 - d_i)`

`Ventas_i_nuevas = Q_i_nuevo * P_i_nuevo`

`Contribución_i_nueva = Q_i_nuevo * (P_i_nuevo - C_i)`

La diagonal de E contiene elasticidades propias ajustadas sobre datos sintéticos. Los valores fuera de la diagonal son supuestos de sustitución. Al desactivar los efectos cruzados, esos valores se convierten en cero para el escenario. Un descuento positivo significa una disminución del precio, no un aumento.

El punto de partida utiliza los promedios semanales de volumen vendido, precio neto y costo unitario de las últimas ocho semanas sintéticas. En el escenario de referencia, solo Café Clásico recibe un descuento del 10 %. El resultado es volumen +1.94 %, ventas -0.48 % y contribución -2.59 % frente a precios sin cambios. El análisis de sensibilidad recorre descuentos de 0 a 20 % para el producto seleccionado, manteniendo constantes los demás descuentos elegidos.

Son aproximaciones para escenarios moderados, no elasticidades causales comprobadas ni precios óptimos. No incorporan respuesta de competidores, restricciones de inventario, respuestas no lineales, acuerdos comerciales ni cambios en costos.

## Evaluación de pronósticos

Se reservan ocho semanas para comparar un modelo base estacional, el promedio móvil de ocho semanas y Holt-Winters aditivo sobre seis series de productos. WAPE es la suma de errores absolutos dividida entre las unidades observadas. El sesgo es la suma con signo del pronóstico menos lo observado, dividida entre unidades observadas. El promedio móvil obtuvo 5.80 % de WAPE agregado; Holt-Winters tuvo una diferencia aproximada de 0.001 puntos porcentuales, con menor sesgo absoluto en esta prueba. Una sola evaluación no equivale a validación móvil continua.

## Inventarios y entregas

El nivel de servicio sintético corresponde a unidades entregadas entre unidades solicitadas. El generador actual asigna inventarios iniciales de manera independiente por observación y no garantiza continuidad entre semanas. Por ello no deben utilizarse inventarios finales para recomendar reposición o estimar exposición financiera. Las medidas DAX y relaciones del archivo Power BI requieren validación independiente en Power BI Desktop.

## Reproducibilidad

La aplicación Streamlit lee los CSV sintéticos publicados y `data/pricing_model_inputs.json`. Las fórmulas están en `src/scenario_engine.py` y sus pruebas reconcilian el escenario de referencia de `data/model_results.json`. El script histórico `src/build_analysis.py` regenera los datos y resultados, pero también puede escribir en la carpeta del notebook; conviene revisar los cambios antes de publicarlos.

Consulta [procedencia de datos](data_provenance.md) y [validación](validation.md).
