# Laboratorio de decisiones comerciales para bebidas

**Cuando una promoción incrementa las unidades, pero reduce la contribución, ¿cómo conviene evaluar la decisión?**

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

## Explorar la aplicación Streamlit

La aplicación bilingüe abre con el **Simulador de precios**. Permite configurar descuentos de 0 % a 20 % por producto, activar o desactivar los efectos cruzados y comparar el portafolio antes y después del cambio. Incluye:

- Precios, volúmenes, participaciones, ventas y contribución base y simulados por producto.
- Totales del portafolio, diferencias y descarga CSV.
- Separación de efectos propios del precio y efectos entre productos.
- Matriz de elasticidades y curvas de sensibilidad de descuentos.
- Vistas complementarias de desempeño comercial y evaluación histórica de pronósticos.

**Publicación:** en Streamlit Community Cloud se selecciona este repositorio, rama `main` y archivo principal `app.py`. La URL se incorporará cuando esté desplegada y comprobada.

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

**Carlos Segura | CS Intelligence**
