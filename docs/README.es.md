# Laboratorio de decisiones comerciales para bebidas

**¿Dónde se genera contribución, qué puntos de venta requieren revisión y cuándo un descuento produce volumen sin valor?**

[Español](README.es.md) | [English](../README.md) | [Metodología](methodology.es.md) | [Datos y supuestos](data_provenance.md)

Construí este caso independiente para analizar una decisión comercial frecuente. Un descuento puede aumentar el volumen vendido y, al mismo tiempo, reducir las ventas en dinero y la contribución del portafolio. El proyecto reúne ventas sintéticas de bebidas, evaluación de pronósticos y un simulador de precios para seis productos.

Todos los datos son sintéticos. Los resultados demuestran un método de análisis, no representan ventas, rentabilidad ni promociones de una empresa real.

## Qué encontré

El modelo simulado contiene **37,440** registros semanales por punto de venta y producto, correspondientes a **104** semanas, **60** puntos de venta y seis productos.

| Indicador del modelo sintético | Resultado |
| --- | ---: |
| Ventas simuladas al consumidor | MXN 15.38 millones |
| Contribución simulada | MXN 8.02 millones |
| Margen de contribución | 52.2 % |
| Relación de unidades entregadas sobre solicitadas | 96.3 % |
| Menor WAPE agregado en las ocho semanas de evaluación | 5.80 %, promedio móvil de ocho semanas |

En el escenario de referencia, un **descuento de 10 % en Café Clásico** cambia el portafolio de seis productos de la siguiente manera:

| Resultado del escenario | Cambio frente a precios sin descuento |
| --- | ---: |
| Unidades semanales | **+1.94 %** |
| Ventas semanales | **-0.48 %** |
| Contribución semanal | **-2.59 %** |

La conclusión comercial es que no basta con evaluar una promoción por el aumento de unidades. También debemos revisar las ventas y la contribución. Estas cifras dependen de costos y elasticidades sintéticas; no son una recomendación de descuento para un mercado real.

## Explorar el dashboard comercial

[Abrir la aplicación bilingüe en Streamlit](https://beverage-commercial-decision-lab-k9yerefuyjpyvgpjke7zny.streamlit.app/).

La aplicación incluye seis secciones para analizar decisiones comerciales:

1. **Panorama ejecutivo:** ventas, contribución, unidades, servicio ponderado, tendencias semanales y comparación con el periodo anterior de igual duración cuando hay datos.
2. **Desempeño comercial:** rankings por producto y punto de venta, comparaciones por canal y zona, y descarga de resultados.
3. **Servicio y oportunidades:** revisión del cumplimiento de entregas y revisión independiente de puntos con bajo volumen frente a pares del mismo SKU y canal.
4. **Pronósticos:** comparación histórica de modelos, WAPE y sesgo por producto, y cantidades observadas frente a los pronósticos en ocho semanas de evaluación.
5. **Simulador de precios:** descuentos simultáneos de 0 % a 20 %, sustitución opcional, impacto en el portafolio y análisis de sensibilidad.
6. **Metodología:** supuestos, definiciones y límites.

Las primeras tres secciones comparten filtros de fechas, canal, zona y producto. La vista inicial presenta las **últimas 13 semanas sintéticas**. Los indicadores generales anteriores cubren las 104 semanas. El simulador y la evaluación de pronósticos conservan sus propias bases para no alterar sus resultados al filtrar.

Las listas de revisión son señales para investigar, no pronósticos de desabasto, ventas perdidas, ingresos incrementales u oportunidades reales.

## Cómo se calcula

El motor de precios simula cambios simultáneos en los seis productos:

`volumen simulado = max(0, volumen base * (1 + suma(elasticidad * cambio proporcional de precio)))`

Las elasticidades propias se ajustaron a datos sintéticos. Las elasticidades cruzadas y relaciones de sustitución son supuestos. Las ventas y la contribución se calculan con precios y costos simulados de venta al consumidor. No se han identificado efectos causales, beneficios reales ni precios óptimos.

La comparación de pronósticos utiliza ocho semanas históricas reservadas para evaluación. El promedio móvil de ocho semanas obtuvo **5.80 % de WAPE**; Holt-Winters presentó un WAPE casi idéntico, con menor sesgo absoluto. Este resultado no demuestra que el mismo método sea siempre mejor.

## Reproducir el análisis

```bash
python -m pip install -r requirements.txt
python -m pytest -q
streamlit run app.py
```

La aplicación utiliza los datos sintéticos y parámetros de escenario existentes. Antes de ejecutar `python src/build_analysis.py` para regenerar el análisis, revisa la [metodología](methodology.es.md) y la [validación](validation.md), ya que el script histórico genera resultados analíticos y puede escribir archivos en la carpeta del notebook.

## Alcance y limitaciones

Las ventas y la contribución provienen de operaciones simuladas de **venta al consumidor** (*sell-out*). No representan facturación del distribuidor (*sell-in*), utilidad neta ni resultados de un negocio. El generador de inventarios no garantiza continuidad semanal, por lo que esta aplicación no interpreta esos saldos como evidencia para reabastecimiento.

El [archivo Power BI](../powerbi/Beverage_Commercial_Decision_Lab.pbix) se conserva como complemento histórico. Sus relaciones, medidas, filtros y totales no se han validado de manera independiente para esta versión. La aplicación Streamlit es el entregable interactivo principal. No se presentan simuladores Excel, PowerPoint o PDF como entregables públicos del repositorio.

No se ha seleccionado una licencia abierta independiente para el código. Los datos son sintéticos y se publican para explicar y reproducir el caso, no como información empresarial real.

**Carlos Segura**
