"""Interactive, bilingual commercial decisions case with a price what-if simulator."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.scenario_engine import discount_curve, load_model, simulate

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
st.set_page_config(page_title="Beverage Commercial Decision Lab", page_icon="🥤", layout="wide")
lang = st.sidebar.radio("Idioma / Language", ["Español", "English"], horizontal=True)


def T(es: str, en: str) -> str:
    return es if lang == "Español" else en


PRODUCT_NAMES = {
    "CFCL-355": ("Café Clásico", "Classic Coffee"),
    "CFVN-355": ("Café Vainilla", "Vanilla Coffee"),
    "CFMO-355": ("Café Moka", "Mocha Coffee"),
    "TELM-500": ("Té Limón", "Lemon Tea"),
    "FRTR-500": ("Bebida Frutal", "Fruit Drink"),
    "ENRG-473": ("Energética", "Energy Drink"),
}
MODEL_LABELS = {
    "Estacional ingenuo": T("Base estacional", "Seasonal baseline"),
    "Promedio movil 8s": T("Promedio móvil (8 sem.)", "Moving average (8 weeks)"),
    "Holt-Winters": "Holt-Winters",
}


def name_of(sku: str) -> str:
    return PRODUCT_NAMES.get(sku, (sku, sku))[0 if lang == "Español" else 1]


@st.cache_data(show_spinner=False)
def load_csv(filename: str, parse_dates: tuple[str, ...] = ()) -> pd.DataFrame:
    return pd.read_csv(DATA / filename, parse_dates=list(parse_dates))


@st.cache_data(show_spinner=False)
def get_model() -> dict:
    return load_model(DATA / "pricing_model_inputs.json")


try:
    model = get_model()
except (FileNotFoundError, ValueError, KeyError) as exc:
    st.error(T("Falta un insumo del simulador o su estructura no es válida.",
               "A simulator input is missing or invalid."))
    st.code(str(exc))
    st.stop()

st.title("Beverage Commercial Decision Lab")
st.caption(T(
    "CS Intelligence | Caso comercial con datos sintéticos | Precio, demanda y contribución",
    "CS Intelligence | Synthetic commercial case | Pricing, demand and contribution"
))
st.write(T(
    "¿Cuándo un cambio de precio mejora el volumen, pero perjudica la contribución?",
    "When does a price change increase volume but reduce contribution?"
))

tabs = st.tabs([
    T("Simulador de precios", "Price Simulator"),
    T("Panorama ejecutivo", "Executive Overview"),
    T("Cartera y canales", "Portfolio & Channels"),
    T("Pronósticos", "Forecasting"),
    T("Metodología", "Methodology"),
])


def change_presets(preset: str) -> None:
    for p in model["products"]:
        st.session_state[f"discount_{p['sku']}"] = (
            10.0 if preset == "reference" and p["sku"] == "CFCL-355" else 0.0
        )


with tabs[0]:
    st.subheader(T("Simulador de descuentos y elasticidades", "Discount and elasticity simulator"))
    st.write(T(
        "Modifica los descuentos de varios productos y compara el resultado con el escenario sin cambios. "
        "El cálculo considera la respuesta propia al precio y, opcionalmente, la sustitución entre productos.",
        "Change discounts for several products and compare the result with unchanged prices. "
        "The calculation includes own-price response and optional substitution between products."
    ))
    b1, b2 = st.columns([1,1])
    with b1:
        st.button(T("Sin descuentos", "Reset discounts"),
                  on_click=change_presets, args=("zero",), use_container_width=True)
    with b2:
        st.button(T("Ejemplo: Café Clásico -10 %", "Example: Classic Coffee -10%"),
                  on_click=change_presets, args=("reference",), use_container_width=True)
    st.markdown(f"**{T('Descuento por producto (%)', 'Discount by product (%)')}**")
    discounts = {}
    input_cols = st.columns(3)
    for i, p in enumerate(model["products"]):
        with input_cols[i % 3]:
            default = 100 * float(p.get("default_discount", 0.0))
            value = st.number_input(
                name_of(p["sku"]), min_value=0.0, max_value=20.0,
                value=default, step=0.5, format="%.1f",
                key=f"discount_{p['sku']}"
            )
            discounts[p["sku"]] = value / 100
    use_cross = st.checkbox(
        T("Incluir sustitución entre productos", "Include cross-product substitution"),
        value=True,key="cross_effects"
    )
    st.caption(T(
        "Los descuentos se limitan a 0-20 %. Las elasticidades propias proceden de ajustes sobre datos sintéticos; "
        "las elasticidades cruzadas son supuestos de escenario.",
        "Discounts are limited to 0-20%. Own-price elasticities are fitted to synthetic data; "
        "cross-price elasticities are scenario assumptions."
    ))
    details, result = simulate(model, discounts, use_cross=use_cross)
    display = details.copy()
    display["product"] = display["sku"].map(name_of)

    cols = st.columns(4)
    cols[0].metric(T("Volumen semanal", "Weekly volume"),
                   f"{result['scenario_volume']:,.1f}",f"{result['delta_volume_pct']:+.2%}")
    cols[1].metric(T("Ventas semanales (MXN)", "Weekly revenue (MXN)"),
                   f"${result['scenario_revenue']:,.0f}",f"{result['delta_revenue_pct']:+.2%}")
    cols[2].metric(T("Contribución (MXN)", "Contribution (MXN)"),
                   f"${result['scenario_contribution']:,.0f}",f"{result['delta_contribution_pct']:+.2%}")
    cols[3].metric(T("Margen de contribución", "Contribution margin"),
                   f"{result['scenario_margin_pct']:.1f}%",
                   f"{result['scenario_margin_pct']-result['base_margin_pct']:+.1f} pp")
    if result["delta_volume"] > 0.001 and result["delta_contribution"] < -0.001:
        st.warning(T(
            "El escenario eleva las unidades, pero reduce la contribución. "
            "Más volumen no implica necesariamente un mejor resultado comercial.",
            "This scenario increases units while reducing contribution. "
            "Higher volume does not necessarily mean a better commercial outcome."
        ))
    elif result["delta_contribution"] > 0.001:
        st.success(T(
            "La contribución simulada aumenta. Verifica la sensibilidad a los supuestos antes de considerarlo una decisión comercial.",
            "Simulated contribution increases. Check sensitivity to assumptions before treating this as a commercial decision."
        ))
    else:
        st.info(T(
            "La contribución simulada no aumenta. Revisa los cambios de precio y los efectos entre productos.",
            "Simulated contribution does not increase. Review price changes and cross-product effects."
        ))

    subtabs = st.tabs([
        T("Comparación", "Comparison"),
        T("Efectos cruzados", "Cross effects"),
        T("Sensibilidad", "Sensitivity"),
    ])
    with subtabs[0]:
        table_cols = ["product","base_price","discount_pct","scenario_price",
                      "base_volume","scenario_volume","volume_change",
                      "base_volume_share_pct","scenario_volume_share_pct",
                      "base_revenue","scenario_revenue","revenue_change",
                      "base_contribution","scenario_contribution","contribution_change"]
        table = display[table_cols].copy().round(2)
        table = table.rename(columns={
            "product":T("Producto","Product"),
            "base_price":T("Precio base","Base price"),
            "discount_pct":T("Descuento (%)","Discount (%)"),
            "scenario_price":T("Precio sim.","Scenario price"),
            "base_volume":T("Vol. base","Base volume"),
            "scenario_volume":T("Vol. sim.","Scenario volume"),
            "volume_change":T("Cambio vol.","Volume change"),
            "base_volume_share_pct":T("Participación base (%)","Base share (%)"),
            "scenario_volume_share_pct":T("Participación sim. (%)","Scenario share (%)"),
            "base_revenue":T("Venta base","Base revenue"),
            "scenario_revenue":T("Venta sim.","Scenario revenue"),
            "revenue_change":T("Cambio venta","Revenue change"),
            "base_contribution":T("Contribución base","Base contribution"),
            "scenario_contribution":T("Contribución sim.","Scenario contribution"),
            "contribution_change":T("Cambio contrib.","Contribution change"),
        })
        st.dataframe(table, hide_index=True,use_container_width=True)
        st.caption(T(
            "Comparación semanal ilustrativa. La tabla resume el escenario como en una hoja de simulación; "
            "puedes desplazarte horizontalmente.",
            "Illustrative weekly comparison. The table presents a spreadsheet-style scenario; "
            "scroll horizontally for additional columns."
        ))
        st.download_button(
            T("Descargar escenario (CSV)", "Download scenario (CSV)"),
            data=details.to_csv(index=False).encode("utf-8-sig"),
            file_name="beverage_pricing_scenario.csv",mime="text/csv"
        )
        plot = display.sort_values("contribution_change")
        fig = px.bar(plot,x="contribution_change",y="product",orientation="h",
                     color="contribution_change",color_continuous_scale="RdBu",
                     color_continuous_midpoint=0,
                     labels={"contribution_change":T("Cambio de contribución (MXN/sem.)","Contribution change (MXN/week)"),
                             "product":T("Producto","Product")},
                     title=T("¿Qué productos explican el cambio de contribución?",
                             "Which products drive the contribution change?"))
        fig.update_layout(coloraxis_showscale=False,margin=dict(l=5,r=5,t=55,b=30))
        st.plotly_chart(fig,use_container_width=True)
        with st.expander(T("Participación de volumen y valor","Volume and revenue shares")):
            shares=display[["product","base_volume_share_pct","scenario_volume_share_pct",
                            "base_revenue_share_pct","scenario_revenue_share_pct"]].round(2)
            st.dataframe(shares.rename(columns={
                "product":T("Producto","Product"),
                "base_volume_share_pct":T("Volumen base (%)","Base volume (%)"),
                "scenario_volume_share_pct":T("Volumen sim. (%)","Scenario volume (%)"),
                "base_revenue_share_pct":T("Venta base (%)","Base revenue (%)"),
                "scenario_revenue_share_pct":T("Venta sim. (%)","Scenario revenue (%)"),
            }),hide_index=True,use_container_width=True)

    with subtabs[1]:
        st.write(T(
            "Descomposición aproximada del cambio de unidades: efecto del propio precio y efecto de descuentos en otros productos.",
            "Approximate change in units decomposed into own-price response and response to other products' discounts."
        ))
        effects=display[["product","own_effect_units","cross_effect_units"]].melt(
            id_vars="product",var_name="effect",value_name="units"
        )
        effect_labels={
            "own_effect_units":T("Efecto propio","Own-price effect"),
            "cross_effect_units":T("Efecto cruzado","Cross-price effect")
        }
        effects["effect"]=effects.effect.map(effect_labels)
        effect_chart=px.bar(effects,x="units",y="product",color="effect",barmode="relative",
                            orientation="h",labels={
                                "units":T("Cambio de unidades por semana","Weekly unit change"),
                                "product":T("Producto","Product"),
                                "effect":T("Componente","Component")},
                            title=T("Efectos propios y sustitución entre productos",
                                    "Own-price response and product substitution"))
        st.plotly_chart(effect_chart,use_container_width=True)
        m=np.asarray(model["elasticity_matrix"])
        short=[name_of(p["sku"]) for p in model["products"]]
        heat=go.Figure(go.Heatmap(
            z=m,x=short,y=short,colorscale="RdBu",zmid=0,
            text=np.round(m,2),texttemplate="%{text:.2f}",
            hovertemplate=T("Afectado: %{y}<br>Precio modificado: %{x}<br>Elasticidad: %{z:.2f}<extra></extra>",
                            "Affected: %{y}<br>Changed price: %{x}<br>Elasticity: %{z:.2f}<extra></extra>"),
            colorbar=dict(title=T("Elasticidad","Elasticity"))
        ))
        heat.update_layout(title=T("Matriz de elasticidades del escenario","Scenario elasticity matrix"),
                           height=450,margin=dict(l=20,r=20,t=60,b=25))
        st.plotly_chart(heat,use_container_width=True)
        st.caption(T(
            "Filas: volumen del producto afectado. Columnas: precio que cambia. La diagonal procede de elasticidades estimadas sobre datos sintéticos; "
            "los cruces son supuestos de sustitución. No son efectos causales identificados.",
            "Rows: affected product volume. Columns: changed price. Diagonal values come from synthetic-data estimates; "
            "off-diagonal values are substitution assumptions, not identified causal effects."
        ))

    with subtabs[2]:
        st.write(T(
            "Evalúa descuentos de 0 a 20 % en un producto, manteniendo constantes los demás descuentos actuales.",
            "Evaluate 0-20% discounts on one product, holding other current discounts fixed."
        ))
        sku=st.selectbox(T("Producto para sensibilidad","Product for sensitivity"),
                         [p["sku"] for p in model["products"]],format_func=name_of)
        curve=discount_curve(model,sku,discounts,use_cross)
        curve["volume_pct"] = 100*curve["delta_volume_pct"]
        curve["revenue_pct"] = 100*curve["delta_revenue_pct"]
        curve["contribution_pct"] = 100*curve["delta_contribution_pct"]
        tidy=curve[["discount_pct","volume_pct","revenue_pct","contribution_pct"]].melt(
            id_vars="discount_pct",var_name="metric",value_name="change_pct")
        metric_labels={
            "volume_pct":T("Volumen","Volume"),
            "revenue_pct":T("Ventas","Revenue"),
            "contribution_pct":T("Contribución","Contribution")
        }
        tidy["metric"]=tidy.metric.map(metric_labels)
        f=px.line(tidy,x="discount_pct",y="change_pct",color="metric",markers=False,
                  labels={"discount_pct":T("Descuento (%)","Discount (%)"),
                          "change_pct":T("Cambio frente al escenario sin descuentos (%)",
                                         "Change versus no-discount baseline (%)"),
                          "metric":T("Indicador","Metric")},
                  title=T("Sensibilidad del portafolio a un descuento","Portfolio discount sensitivity"))
        f.add_vline(x=100*discounts[sku],line_dash="dot")
        f.add_hline(y=0,line_dash="dash")
        st.plotly_chart(f,use_container_width=True)
        st.caption(T(
            "El eje de referencia mantiene los precios originales. Las curvas son escenarios condicionados a elasticidades y costos sintéticos; "
            "no constituyen un descuento óptimo estimado experimentalmente.",
            "The reference is the original prices. Curves are conditional on synthetic elasticities and costs; "
            "they are not experimentally identified optimal discounts."
        ))


try:
    fact=load_csv("fact_sales.csv",("date",))
    customers=load_csv("dim_customer.csv")
    products=load_csv("dim_product.csv")
    weekly=load_csv("weekly_sales.csv",("date",))
    metrics=load_csv("forecast_metrics.csv")
    future=load_csv("forecast_future.csv",("date",))
except (FileNotFoundError, ValueError) as exc:
    with tabs[1]:
        st.error(T("No se encontraron todos los datos para los módulos históricos.",
                   "Some data needed for historical modules are missing."))
        st.code(str(exc))
    st.stop()

fact=fact.merge(customers[["pdv_id","channel","zone"]],on="pdv_id",how="left",validate="many_to_one")
labels=products.set_index("sku")["product"].to_dict()

with tabs[1]:
    st.subheader(T("¿Dónde se genera contribución?", "Where does contribution come from?"))
    st.caption(T(
        "Las cifras son ventas simuladas al consumidor (sell-out), no ingresos verificados de un distribuidor.",
        "Numbers represent synthetic consumer sell-out, not verified distributor revenue."
    ))
    ca,zb=st.columns(2)
    with ca:
        channel=st.selectbox(T("Canal","Channel"),
                             ["all"]+sorted(fact.channel.dropna().unique().tolist()),
                             format_func=lambda x:T("Todos","All") if x=="all" else x,
                             key="overview_channel")
    with zb:
        zone=st.selectbox(T("Zona","Zone"),
                          ["all"]+sorted(fact.zone.dropna().unique().tolist()),
                          format_func=lambda x:T("Todas","All") if x=="all" else x,
                          key="overview_zone")
    slice_df=fact.copy()
    if channel!="all":slice_df=slice_df.loc[slice_df.channel.eq(channel)]
    if zone!="all":slice_df=slice_df.loc[slice_df.zone.eq(zone)]
    revenue=float(slice_df.revenue.sum()); contrib=float(slice_df.contribution.sum())
    units=float(slice_df.units_sold.sum())
    service=float(slice_df.units_delivered.sum()/slice_df.units_ordered.sum()) if slice_df.units_ordered.sum() else 0.0
    ca,cb,cc,cd=st.columns(4)
    ca.metric(T("Ventas (MXN)","Revenue (MXN)"),f"${revenue/1e6:,.2f} M")
    cb.metric(T("Contribución (MXN)","Contribution (MXN)"),f"${contrib/1e6:,.2f} M")
    cc.metric(T("Margen","Margin"),f"{contrib/revenue:.1%}" if revenue else "N/A")
    cd.metric(T("Servicio","Service level"),f"{service:.1%}")
    tr=slice_df.groupby("date",as_index=False)[["revenue","contribution"]].sum()
    plot=tr.melt(id_vars="date",value_vars=["revenue","contribution"],
                 var_name="measure",value_name="mxn")
    plot["measure"]=plot["measure"].map({
        "revenue":T("Ventas","Revenue"),
        "contribution":T("Contribución","Contribution")})
    st.plotly_chart(px.line(plot,x="date",y="mxn",color="measure",
        labels={"date":T("Semana","Week"),"mxn":"MXN","measure":T("Indicador","Measure")},
        title=T("Evolución semanal sintética","Synthetic weekly performance")),
        use_container_width=True)
    st.caption(T(
        "El nivel de servicio se calcula como unidades entregadas / unidades solicitadas. No demuestra continuidad de inventario.",
        "Service level is delivered units / ordered units. It does not demonstrate inventory continuity."
    ))

with tabs[2]:
    st.subheader(T("Productos, canales y zonas", "Products, channels and regions"))
    by_product=fact.groupby("sku",as_index=False).agg(
        revenue=("revenue","sum"),contribution=("contribution","sum"),
        units=("units_sold","sum"))
    by_product["product"]=by_product.sku.map(name_of)
    by_product["margin_pct"]=(100*by_product.contribution/by_product.revenue).round(2)
    ranking=by_product.sort_values("contribution",ascending=False)
    st.plotly_chart(px.bar(ranking,x="product",y="contribution",
        labels={"product":T("Producto","Product"),"contribution":T("Contribución (MXN)","Contribution (MXN)")},
        title=T("Contribución por producto","Contribution by product")),
        use_container_width=True)
    st.dataframe(ranking[["product","units","revenue","contribution","margin_pct"]]
        .rename(columns={"product":T("Producto","Product"),"units":T("Unidades","Units"),
                         "revenue":T("Ventas (MXN)","Revenue (MXN)"),
                         "contribution":T("Contribución (MXN)","Contribution (MXN)"),
                         "margin_pct":T("Margen (%)","Margin (%)")}).round(2),
        use_container_width=True,hide_index=True)
    channel_df=fact.groupby(["channel","zone"],as_index=False)[["revenue","contribution"]].sum()
    st.plotly_chart(px.bar(channel_df,x="channel",y="contribution",color="zone",barmode="group",
        labels={"channel":T("Canal","Channel"),"contribution":T("Contribución (MXN)","Contribution (MXN)"),
                "zone":T("Zona","Region")},
        title=T("Contribución por canal y zona","Contribution by channel and region")),
        use_container_width=True)
    st.caption(T(
        "La contribución utiliza costos y precios sintéticos de sell-out. No equivale a utilidad neta ni a margen de un mayorista.",
        "Contribution uses synthetic sell-out prices and costs. It is neither net profit nor distributor margin."
    ))

with tabs[3]:
    st.subheader(T("¿Qué método pronostica mejor?", "Which forecast works best?"))
    total=metrics.loc[metrics.sku.eq("TOTAL")].copy()
    total["label"]=total.method.map(MODEL_LABELS)
    total["wape_pct"]=100*total.wape
    total["bias_pct"]=100*total.bias
    order=[MODEL_LABELS[x] for x in ["Estacional ingenuo","Promedio movil 8s","Holt-Winters"]]
    total["label"]=pd.Categorical(total.label,categories=order,ordered=True)
    total=total.sort_values("label")
    st.plotly_chart(px.bar(total,x="label",y="wape_pct",text=total.wape_pct.map(lambda v:f"{v:.2f}%"),
        labels={"label":T("Método","Method"),"wape_pct":"WAPE (%)"},
        title=T("Error en las últimas ocho semanas sintéticas","Error in the last eight synthetic weeks")),
        use_container_width=True)
    st.dataframe(total[["label","wape_pct","bias_pct","mae"]].rename(columns={
        "label":T("Método","Method"),"wape_pct":"WAPE (%)",
        "bias_pct":T("Sesgo (%)","Bias (%)"),"mae":"MAE"}).round(2),
        hide_index=True,use_container_width=True)
    st.caption(T(
        "El promedio móvil de ocho semanas registra WAPE de 5.80 %. Holt-Winters es casi idéntico en WAPE, pero muestra menor sesgo absoluto en esta evaluación. No hay revalidación continua.",
        "The eight-week moving average achieves 5.80% WAPE. Holt-Winters has nearly identical WAPE but lower absolute bias in this evaluation. Rolling validation is not included."
    ))
    prod=st.selectbox(T("Producto para pronóstico","Forecast product"),
                      sorted(future.sku.unique().tolist()),format_func=name_of)
    historic=weekly.loc[weekly.sku.eq(prod),["date","units_sold"]].tail(30).copy()
    historic["serie"]=T("Observado","Observed")
    historic=historic.rename(columns={"units_sold":"units"})
    projected=future.loc[future.sku.eq(prod),["date","forecast_units"]].copy()
    projected["serie"]=T("Pronóstico de referencia","Reference forecast")
    projected=projected.rename(columns={"forecast_units":"units"})
    historic_plot=pd.concat([historic,projected],ignore_index=True)
    st.plotly_chart(px.line(historic_plot,x="date",y="units",color="serie",markers=True,
         labels={"date":T("Semana","Week"),"units":T("Unidades","Units"),"serie":T("Serie","Series")},
         title=T("Serie histórica y proyección de ocho semanas","Historical series and eight-week projection")),
         use_container_width=True)
    st.caption(T(
        "Proyección generada desde el último periodo sintético de agosto de 2026. No es una predicción vigente ni incorpora ventas actuales.",
        "Projection generated from the last synthetic period in August 2026. It is not a current forecast and includes no live sales."
    ))

with tabs[4]:
    st.subheader(T("Cómo interpretar el caso", "How to interpret this case"))
    st.write(T(
        "El conjunto contiene 104 semanas, 60 puntos de venta y seis productos simulados. "
        "Las métricas financieras se derivan de unidades supuestamente vendidas al consumidor, no de facturación observada de un distribuidor.",
        "The dataset covers 104 weeks, 60 simulated points of sale and six products. "
        "Financial metrics use assumed consumer sell-out quantities, not observed distributor invoicing."
    ))
    st.write(T(
        "El simulador calcula el cambio proporcional en volumen a partir de una aproximación lineal de elasticidades "
        "propias estimadas sobre los datos sintéticos y elasticidades cruzadas fijadas como supuestos. "
        "Recalcula precio, unidades, participación, ventas y contribución para todos los SKU de manera simultánea.",
        "The simulator calculates proportional volume changes from a linear approximation of own-price elasticities "
        "fitted to synthetic data and cross-price elasticities fixed as assumptions. It recalculates price, units, "
        "shares, revenue and contribution for all SKUs simultaneously."
    ))
    st.write(T(
        "Los saldos de inventario del generador histórico no garantizan continuidad entre semanas. "
        "Por eso la aplicación no utiliza esos saldos para recomendar reposición ni cuantificar desabastos.",
        "Inventory balances in the historical generator do not guarantee continuity across weeks. "
        "Therefore the app does not use those balances for replenishment decisions or stockout estimates."
    ))
    st.write(T(
        "Las elasticidades propias no están causalmente identificadas; los efectos cruzados tampoco fueron estimados. "
        "Un escenario no sustituye pruebas comerciales controladas, datos de competencia o información de costos reales.",
        "Own-price elasticities are not causally identified, and cross effects were not fitted. "
        "Scenarios cannot replace controlled commercial tests, competitor data or real costs."
    ))
    st.markdown(T(
        "Consulta el [repositorio y las notas de método](https://github.com/carlos-segura-mx/beverage-commercial-decision-lab) para reproducir el caso.",
        "See the [repository and methodology](https://github.com/carlos-segura-mx/beverage-commercial-decision-lab) to reproduce the case."
    ))

st.divider()
st.caption(T(
    "Caso independiente con datos sintéticos. No implica trabajo para una empresa real ni resultados comerciales observados.",
    "Independent synthetic-data case. It does not imply client work or observed commercial outcomes."
))
