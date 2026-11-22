"""Commercial BI views for synthetic beverage sell-out data.

The module deliberately excludes the historical synthetic inventory balances:
they were generated independently by row and do not reconcile over weeks.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


def ratio(a,b):
    return float(a/b) if b else float("nan")


def metrics(df):
    values={k:float(df[k].sum()) for k in
            ("revenue","contribution","units_sold","units_ordered","units_delivered")}
    values["margin"]=ratio(values["contribution"],values["revenue"])
    values["service"]=ratio(values["units_delivered"],values["units_ordered"])
    values["unfilled"]=values["units_ordered"]-values["units_delivered"]
    return values


def grouped(df,keys):
    result=df.groupby(keys,as_index=False,dropna=False)[
        ["revenue","contribution","units_sold","units_ordered","units_delivered"]].sum()
    result["margin"]=np.where(result.revenue.ne(0),result.contribution/result.revenue,np.nan)
    result["service"]=np.where(result.units_ordered.ne(0),
                               result.units_delivered/result.units_ordered,np.nan)
    result["unfilled"]=result.units_ordered-result.units_delivered
    return result


def filtered_sales(df,T,name_of):
    first,last=df.date.min(),df.date.max()
    st.sidebar.divider()
    st.sidebar.subheader(T("Filtros comerciales","Commercial filters"))
    choice=st.sidebar.date_input(T("Periodo","Date range"),
        value=((last-pd.Timedelta(weeks=12)).date(),last.date()),
        min_value=first.date(),max_value=last.date(),key="bi_dates")
    if not isinstance(choice,tuple) or len(choice)!=2:
        start,end=last-pd.Timedelta(weeks=12),last
    else:
        start,end=pd.Timestamp(choice[0]),pd.Timestamp(choice[1])
    options={
        "channel":sorted(df.channel.dropna().unique().tolist()),
        "zone":sorted(df.zone.dropna().unique().tolist()),
        "sku":sorted(df.sku.dropna().unique().tolist()),
    }
    channels=st.sidebar.multiselect(T("Canales","Channels"),options["channel"],
                                    default=options["channel"],key="bi_channels") or options["channel"]
    zones=st.sidebar.multiselect(T("Zonas","Regions"),options["zone"],
                                 default=options["zone"],key="bi_zones") or options["zone"]
    products=st.sidebar.multiselect(T("Productos","Products"),options["sku"],
                   default=options["sku"],format_func=name_of,key="bi_products") or options["sku"]
    mask=(df.date.between(start,end)&df.channel.isin(channels)&
          df.zone.isin(zones)&df.sku.isin(products))
    current=df.loc[mask].copy()
    span=end-start+pd.Timedelta(days=7)
    prev_start,prev_end=start-span,start-pd.Timedelta(days=7)
    previous=df.loc[(df.date.between(prev_start,prev_end)&
        df.channel.isin(channels)&df.zone.isin(zones)&df.sku.isin(products))].copy()
    expected=(end-start).days//7+1
    if previous.date.nunique()!=expected:
        previous=previous.iloc[:0]
    st.sidebar.caption(T(
        "Los filtros afectan los tres tableros comerciales. Pronósticos y simulador usan su propia base histórica.",
        "Filters apply to three commercial views. Forecasting and pricing use their own historical data."
    ))
    return current,previous,start,end


def render_executive(df,previous,start,end,T,name_of):
    st.subheader(T("¿Cómo evoluciona el negocio?","How is the business performing?"))
    st.caption(T("Ventas sintéticas al consumidor, no ingresos reales de un distribuidor.",
                 "Synthetic consumer sell-out, not real distributor revenue."))
    if df.empty:
        st.warning(T("Sin datos para los filtros elegidos.","No observations match these filters."))
        return
    now=metrics(df)
    before=metrics(previous) if not previous.empty else None
    st.caption(T(
        f"Periodo: {start:%d/%m/%Y} a {end:%d/%m/%Y}. Las variaciones comparan periodos iguales cuando existe información.",
        f"Period: {start:%Y-%m-%d} to {end:%Y-%m-%d}. Deltas compare equal-length periods when data are available."
    ))
    def delta(key):
        if before is None or before[key]==0:return None
        return f"{now[key]/before[key]-1:+.1%}"
    a,b,c,d,e=st.columns(5)
    a.metric(T("Ventas","Revenue"),f"${now['revenue']/1e6:,.2f} M",delta("revenue"))
    b.metric(T("Contribución","Contribution"),f"${now['contribution']/1e6:,.2f} M",delta("contribution"))
    c.metric(T("Unidades","Units"),f"{now['units_sold']:,.0f}",delta("units_sold"))
    d.metric(T("Margen","Margin"),f"{now['margin']:.1%}")
    e.metric(T("Servicio","Delivery service"),f"{now['service']:.1%}")
    st.caption(T("Margen: contribución / ventas. Servicio: unidades entregadas / solicitadas.",
                 "Margin: contribution / revenue. Service: delivered / ordered units."))
    option=st.selectbox(T("Indicador en el tiempo","Time-series measure"),
        ["revenue","contribution","units_sold","service"],
        format_func=lambda x:{"revenue":T("Ventas","Revenue"),
            "contribution":T("Contribución","Contribution"),
            "units_sold":T("Unidades","Units"),
            "service":T("Servicio","Service")}[x],key="bi_time_metric")
    weekly=grouped(df,["date"])
    fig=px.line(weekly,x="date",y=option,markers=True,
        labels={"date":T("Semana","Week"),option:T("Valor","Value")},
        title=T("Evolución semanal","Weekly trend"))
    if option=="service":fig.update_yaxes(tickformat=".0%",range=[0,1.05])
    st.plotly_chart(fig,use_container_width=True)
    a,b=st.columns(2)
    with a:
        channel=grouped(df,["channel"])
        st.plotly_chart(px.bar(channel,x="channel",y="contribution",
            title=T("Contribución por canal","Contribution by channel"),
            labels={"channel":T("Canal","Channel"),"contribution":"MXN"}),
            use_container_width=True)
    with b:
        zone=grouped(df,["zone"])
        st.plotly_chart(px.bar(zone,x="zone",y="contribution",
            title=T("Contribución por zona","Contribution by region"),
            labels={"zone":T("Zona","Region"),"contribution":"MXN"}),
            use_container_width=True)
    products=grouped(df,["sku"]).sort_values("contribution",ascending=False)
    top3=products.head(3).contribution.sum()/products.contribution.sum()
    st.info(T(
        f"Los tres productos principales reúnen {top3:.1%} de la contribución del periodo filtrado. El resultado es descriptivo.",
        f"The top three products account for {top3:.1%} of filtered contribution. This is descriptive."
    ))


def render_commercial(df,T,name_of):
    st.subheader(T("¿Qué productos y puntos de venta aportan más?",
                   "Which products and outlets contribute most?"))
    if df.empty:
        st.warning(T("Sin datos para los filtros elegidos.","No observations match these filters."))
        return
    measure=st.selectbox(T("Indicador para comparar","Comparison metric"),
        ["contribution","revenue","units_sold"],key="bi_rank_measure",
        format_func=lambda x:{"contribution":T("Contribución","Contribution"),
            "revenue":T("Ventas","Revenue"),
            "units_sold":T("Unidades","Units")}[x])
    products=grouped(df,["sku"]).sort_values(measure,ascending=False)
    products["product"]=products.sku.map(name_of)
    st.plotly_chart(px.bar(products,x="product",y=measure,
        labels={"product":T("Producto","Product"),measure:T("Indicador","Measure")},
        title=T("Ranking por producto","Product ranking")),use_container_width=True)
    product_table=products[["product","units_sold","revenue","contribution","margin","service"]].copy()
    product_table[["margin","service"]]=(100*product_table[["margin","service"]]).round(2)
    st.dataframe(product_table.rename(columns={"product":T("Producto","Product"),
        "units_sold":T("Unidades","Units"),"revenue":T("Ventas (MXN)","Revenue (MXN)"),
        "contribution":T("Contribución (MXN)","Contribution (MXN)"),
        "margin":T("Margen (%)","Margin (%)"),"service":T("Servicio (%)","Service (%)")}).round(2),
        hide_index=True,use_container_width=True)
    region=grouped(df,["channel","zone"])
    st.plotly_chart(px.bar(region,x="channel",y=measure,color="zone",barmode="group",
        title=T("Desempeño por canal y zona","Performance by channel and region"),
        labels={"channel":T("Canal","Channel"),"zone":T("Zona","Region"),
                measure:T("Indicador","Measure")}),use_container_width=True)
    outlets=grouped(df,["pdv_id","channel","zone"]).sort_values(measure,ascending=False)
    outlets["service_pct"]=(100*outlets.service).round(2)
    n=st.selectbox(T("Puntos de venta para mostrar","Outlets to show"),[10,20,60],
                    key="bi_top_outlets")
    st.dataframe(outlets[["pdv_id","channel","zone","units_sold","revenue","contribution","service_pct"]]
        .head(n).rename(columns={"pdv_id":T("PDV","Outlet"),
            "channel":T("Canal","Channel"),"zone":T("Zona","Region"),
            "units_sold":T("Unidades","Units"),"revenue":T("Ventas (MXN)","Revenue (MXN)"),
            "contribution":T("Contribución (MXN)","Contribution (MXN)"),
            "service_pct":T("Servicio (%)","Service (%)")}).round(2),
        hide_index=True,use_container_width=True)
    st.download_button(T("Descargar desglose por PDV","Download outlet breakdown"),
        data=outlets.to_csv(index=False).encode("utf-8-sig"),
        file_name="beverage_outlet_breakdown.csv",mime="text/csv")
    st.caption(T("Comparaciones descriptivas, sin ajuste por tamaño del local o demanda no observada.",
                 "Descriptive comparisons without adjustment for outlet size or unobserved demand."))


def service_review(df,threshold=.95,min_orders=50):
    site=grouped(df,["pdv_id","sku","channel","zone"])
    site=site.loc[site.units_ordered>=min_orders].copy()
    if site.empty:return site.copy(),site.copy()
    low=site.loc[site.service<threshold].sort_values(["service","unfilled"])
    peers=site.groupby(["channel","sku"])["units_sold"]
    site["peers"]=peers.transform("size")
    site["lower_quartile"]=peers.transform(lambda x:x.quantile(.25))
    candidates=site.loc[(site.peers>=4)&(site.service>=.95)&
                        (site.units_sold<=site.lower_quartile)].sort_values("units_sold")
    return low,candidates


def render_service(df,T,name_of):
    st.subheader(T("¿Dónde revisar servicio y cobertura?","Where should delivery and coverage be reviewed?"))
    st.caption(T(
        "El nivel de servicio compara unidades entregadas contra solicitadas. El faltante no es una estimación de ventas perdidas; no se usan saldos de inventario.",
        "Service compares delivered with ordered units. Undelivered units are not lost-sales estimates; inventory balances are excluded."
    ))
    if df.empty:
        st.warning(T("Sin datos para los filtros elegidos.","No observations match these filters."))
        return
    total=metrics(df)
    a,b,c=st.columns(3)
    a.metric(T("Servicio","Service"),f"{total['service']:.1%}")
    b.metric(T("Unidades solicitadas","Ordered units"),f"{total['units_ordered']:,.0f}")
    c.metric(T("Unidades sin entregar","Undelivered units"),f"{total['unfilled']:,.0f}")
    a,b=st.columns(2)
    with a:threshold=st.slider(T("Umbral de servicio (%)","Service threshold (%)"),
                               80,100,95,key="bi_service_threshold")
    with b:min_orders=st.number_input(
        T("Mínimo de unidades solicitadas","Minimum ordered units"),
        min_value=0,max_value=50000,value=50,step=25,key="bi_service_min")
    regional=grouped(df,["channel","zone"])
    regional["pct"]=100*regional.service
    matrix=regional.pivot(index="channel",columns="zone",values="pct")
    if not matrix.empty:
        st.plotly_chart(px.imshow(matrix,text_auto=".1f",aspect="auto",
            labels={"x":T("Zona","Region"),"y":T("Canal","Channel"),
                    "color":T("Servicio (%)","Service (%)")},
            title=T("Servicio por canal y zona (%)","Service by channel and region (%)")),
            use_container_width=True)
    low,candidates=service_review(df,threshold/100,min_orders)
    st.subheader(T("Revisión de entregas","Delivery review"))
    st.caption(T("PDV y producto bajo el umbral seleccionado; no son desabastos confirmados.",
                 "Outlet and product below the chosen threshold; these are not confirmed stockouts."))
    if low.empty:
        st.info(T("No hay registros bajo el umbral.","No records are below the threshold."))
    else:
        low=low.copy()
        low["product"]=low.sku.map(name_of)
        low["service_pct"]=(100*low.service).round(2)
        st.dataframe(low[["pdv_id","product","channel","units_ordered","unfilled","service_pct"]]
            .head(30).rename(columns={"pdv_id":T("PDV","Outlet"),
                "product":T("Producto","Product"),"channel":T("Canal","Channel"),
                "units_ordered":T("Unidades solicitadas","Ordered units"),
                "unfilled":T("Sin entregar","Undelivered"),
                "service_pct":T("Servicio (%)","Service (%)")}),
            hide_index=True,use_container_width=True)
        st.download_button(T("Descargar revisión de entregas","Download delivery review"),
            data=low.to_csv(index=False).encode("utf-8-sig"),
            file_name="beverage_delivery_review.csv",mime="text/csv")
    st.subheader(T("Revisión comercial","Commercial review"))
    st.caption(T(
        "PDV con servicio de al menos 95 % y volumen en el cuartil inferior frente al mismo producto y canal, con cuatro o más puntos comparables. Es una señal para investigar, no una oportunidad de venta demostrada.",
        "Outlets with at least 95% service and bottom-quartile volume among same-product, same-channel peers (at least four). This prompts investigation, not a confirmed sales opportunity."
    ))
    if candidates.empty:
        st.info(T("No hay candidatos bajo estos criterios.","No candidates meet these criteria."))
    else:
        candidates=candidates.copy()
        candidates["product"]=candidates.sku.map(name_of)
        candidates["service_pct"]=(100*candidates.service).round(2)
        st.dataframe(candidates[["pdv_id","product","channel","units_sold","lower_quartile","service_pct"]]
            .head(30).rename(columns={"pdv_id":T("PDV","Outlet"),
                "product":T("Producto","Product"),"channel":T("Canal","Channel"),
                "units_sold":T("Unidades","Units"),
                "lower_quartile":T("Cuartil inferior","Lower quartile"),
                "service_pct":T("Servicio (%)","Service (%)")}).round(2),
            hide_index=True,use_container_width=True)
        st.download_button(T("Descargar revisión comercial","Download commercial review"),
            data=candidates.to_csv(index=False).encode("utf-8-sig"),
            file_name="beverage_commercial_review.csv",mime="text/csv")
    st.caption(T("Son reglas descriptivas para priorizar revisiones, no modelos de riesgo ni resultados económicos.",
                 "These are descriptive review rules, not risk models or financial outcomes."))
