from __future__ import annotations

import base64
import io
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
IMG_DIR = ROOT / "images"
NOTEBOOK_DIR = ROOT / "notebook"
for directory in (DATA_DIR, IMG_DIR, NOTEBOOK_DIR):
    directory.mkdir(parents=True, exist_ok=True)

SEED = 20260831
rng = np.random.default_rng(SEED)

COLORS = {
    "navy": "#0F172A",
    "blue": "#2563EB",
    "sky": "#7DD3FC",
    "orange": "#F97316",
    "green": "#16A34A",
    "red": "#DC2626",
    "gray": "#64748B",
    "light": "#E2E8F0",
}


def make_dimensions() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    products = pd.DataFrame(
        [
            ["CFCL-355", "Cafe Clasico", "Cafe listo para tomar", 355, 35.0, 16.5, -1.75, 13.0],
            ["CFVN-355", "Cafe Vainilla", "Cafe listo para tomar", 355, 38.0, 18.2, -1.95, 10.0],
            ["CFMO-355", "Cafe Moka", "Cafe listo para tomar", 355, 40.0, 19.5, -2.10, 8.0],
            ["TELM-500", "Te Limon", "Te listo para tomar", 500, 28.0, 12.5, -1.40, 12.0],
            ["FRTR-500", "Bebida Frutal", "Bebida saborizada", 500, 30.0, 13.8, -1.60, 11.0],
            ["ENRG-473", "Energetica", "Bebida energetica", 473, 45.0, 23.0, -1.20, 7.0],
        ],
        columns=[
            "sku", "product", "category", "pack_ml", "base_list_price",
            "base_unit_cost", "true_own_elasticity", "base_weekly_units",
        ],
    )

    channels = (
        ["Supermercados"] * 15
        + ["Tiendas de abarrotes"] * 35
        + ["Food service"] * 10
    )
    zones = ["Merida Norte", "Merida Sur", "Yucatan Costa", "Yucatan Interior"]
    customers = []
    for idx, channel in enumerate(channels, start=1):
        zone = zones[(idx - 1) % len(zones)]
        potential = float(rng.lognormal(mean=0.0, sigma=0.22))
        customers.append(
            [f"PDV-{idx:03d}", f"Punto de venta {idx:03d}", channel, zone, potential]
        )
    customers = pd.DataFrame(
        customers,
        columns=["pdv_id", "point_of_sale", "channel", "zone", "customer_potential"],
    )

    dates = pd.date_range("2024-09-02", periods=104, freq="W-MON")
    calendar = pd.DataFrame({"date": dates})
    iso = calendar["date"].dt.isocalendar()
    calendar["week_id"] = np.arange(1, len(calendar) + 1)
    calendar["year"] = calendar["date"].dt.year
    calendar["month_num"] = calendar["date"].dt.month
    calendar["month"] = calendar["date"].dt.strftime("%b")
    calendar["quarter"] = "Q" + calendar["date"].dt.quarter.astype(str)
    calendar["iso_week"] = iso.week.astype(int)
    calendar["year_week"] = calendar["year"].astype(str) + "-W" + calendar["iso_week"].astype(str).str.zfill(2)
    calendar["is_year_end"] = calendar["iso_week"].between(47, 52).astype(int)
    return products, customers, calendar


def simulate_sales(
    products: pd.DataFrame, customers: pd.DataFrame, calendar: pd.DataFrame
) -> pd.DataFrame:
    channel_factor = {
        "Supermercados": 1.45,
        "Tiendas de abarrotes": 0.85,
        "Food service": 1.10,
    }
    zone_factor = {
        "Merida Norte": 1.12,
        "Merida Sur": 0.95,
        "Yucatan Costa": 1.02,
        "Yucatan Interior": 0.88,
    }
    rows: list[list[object]] = []

    for week_idx, date_row in calendar.iterrows():
        iso_week = int(date_row["iso_week"])
        inflation = 1.0 + 0.00082 * week_idx
        reference_inflation = 1.0 + 0.00045 * week_idx
        category_trend = 1.0 + 0.0016 * week_idx
        annual_wave = 1.0 + 0.045 * math.sin(2 * math.pi * iso_week / 52.0)
        summer = 1.07 if 19 <= iso_week <= 31 else 1.0
        year_end = 1.13 if 47 <= iso_week <= 52 else 1.0

        for product in products.itertuples(index=False):
            product_season = annual_wave
            if product.sku.startswith("CF"):
                product_season *= 1.08 if 35 <= iso_week <= 52 else 1.0
            if product.sku == "ENRG-473":
                product_season *= summer
            if product.sku in ("TELM-500", "FRTR-500"):
                product_season *= 1.04 if 12 <= iso_week <= 30 else 1.0

            for customer in customers.itertuples(index=False):
                promo_probability = {
                    "Supermercados": 0.24,
                    "Tiendas de abarrotes": 0.12,
                    "Food service": 0.08,
                }[customer.channel]
                is_promo = rng.random() < promo_probability
                if is_promo:
                    discount = float(rng.choice([0.05, 0.10, 0.15], p=[0.45, 0.40, 0.15]))
                else:
                    discount = 0.0

                list_price = product.base_list_price * inflation
                net_price = list_price * (1.0 - discount)
                reference_price = product.base_list_price * reference_inflation
                price_effect = (net_price / reference_price) ** product.true_own_elasticity
                distribution = float(np.clip(rng.normal(0.945, 0.035), 0.78, 1.0))
                display_effect = 1.035 if is_promo and customer.channel == "Supermercados" else 1.0
                expected = (
                    product.base_weekly_units
                    * customer.customer_potential
                    * channel_factor[customer.channel]
                    * zone_factor[customer.zone]
                    * category_trend
                    * product_season
                    * year_end
                    * distribution
                    * price_effect
                    * display_effect
                )
                latent_demand = int(rng.poisson(max(expected, 0.2)))
                units_ordered = max(1, int(math.ceil(expected * rng.uniform(1.08, 1.22))))
                service_noise = rng.normal(0.965 - 0.025 * is_promo, 0.025)
                fill_rate = float(np.clip(service_noise, 0.82, 1.0))
                units_delivered = max(0, int(round(units_ordered * fill_rate)))
                opening_inventory = max(0, int(round(expected * rng.uniform(0.25, 0.55))))
                available = opening_inventory + units_delivered
                units_sold = min(latent_demand, available)
                ending_inventory = max(0, available - units_sold)
                unit_cost = product.base_unit_cost * (1.0 + 0.00062 * week_idx)
                revenue = units_sold * net_price
                cost_of_sales = units_sold * unit_cost
                contribution = revenue - cost_of_sales

                rows.append(
                    [
                        date_row["date"].date().isoformat(),
                        int(date_row["week_id"]),
                        date_row["year_week"],
                        customer.pdv_id,
                        product.sku,
                        units_ordered,
                        units_delivered,
                        units_sold,
                        round(list_price, 2),
                        discount,
                        round(net_price, 2),
                        round(unit_cost, 2),
                        round(revenue, 2),
                        round(cost_of_sales, 2),
                        round(contribution, 2),
                        opening_inventory,
                        ending_inventory,
                        int(is_promo),
                        round(distribution, 4),
                    ]
                )

    columns = [
        "date", "week_id", "year_week", "pdv_id", "sku", "units_ordered",
        "units_delivered", "units_sold", "list_price", "discount_pct",
        "net_price", "unit_cost", "revenue", "cost_of_sales", "contribution",
        "opening_inventory", "ending_inventory", "promotion_flag", "numeric_distribution",
    ]
    return pd.DataFrame(rows, columns=columns)


def wape(actual: np.ndarray, forecast: np.ndarray) -> float:
    return float(np.abs(actual - forecast).sum() / max(np.abs(actual).sum(), 1e-9))


def metrics(actual: np.ndarray, forecast: np.ndarray) -> dict[str, float]:
    error = forecast - actual
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "wape": wape(actual, forecast),
        "bias": float(error.sum() / max(actual.sum(), 1e-9)),
    }


def moving_average_forecast(train: np.ndarray, horizon: int, window: int = 8) -> np.ndarray:
    history = list(map(float, train))
    forecasts = []
    for _ in range(horizon):
        value = float(np.mean(history[-window:]))
        forecasts.append(value)
        history.append(value)
    return np.array(forecasts)


def seasonal_naive_forecast(train: np.ndarray, horizon: int, season: int = 52) -> np.ndarray:
    values = []
    for step in range(horizon):
        idx = len(train) - season + (step % season)
        values.append(float(train[idx]))
    return np.array(values)


def holt_winters_additive(
    train: np.ndarray,
    horizon: int,
    season: int = 52,
    alpha: float = 0.35,
    beta: float = 0.05,
    gamma: float = 0.25,
) -> np.ndarray:
    y = np.asarray(train, dtype=float)
    if len(y) < season + 4:
        return moving_average_forecast(y, horizon)
    first_season = y[:season]
    level = float(np.mean(first_season))
    slope = float(np.polyfit(np.arange(len(y)), y, 1)[0])
    seasonal = first_season - (level + slope * np.arange(season))
    for t, value in enumerate(y):
        s_idx = t % season
        prior_level = level
        level = alpha * (value - seasonal[s_idx]) + (1 - alpha) * (level + slope)
        slope = beta * (level - prior_level) + (1 - beta) * slope
        seasonal[s_idx] = gamma * (value - level) + (1 - gamma) * seasonal[s_idx]
    return np.array(
        [level + (step + 1) * slope + seasonal[(len(y) + step) % season] for step in range(horizon)]
    )


def fit_elasticity(
    fact: pd.DataFrame, products: pd.DataFrame, customers: pd.DataFrame, calendar: pd.DataFrame
) -> pd.DataFrame:
    enriched = (
        fact.merge(customers[["pdv_id", "channel", "zone"]], on="pdv_id", how="left")
        .merge(calendar[["week_id", "month_num"]], on="week_id", how="left")
    )
    output = []
    for product in products.itertuples(index=False):
        frame = enriched.loc[enriched["sku"] == product.sku].copy()
        frame["log_units"] = np.log(frame["units_sold"].clip(lower=0) + 0.5)
        frame["log_price"] = np.log(frame["net_price"].clip(lower=0.01))
        dummies = pd.get_dummies(
            frame[["month_num", "channel", "zone", "pdv_id"]].astype(str),
            drop_first=True,
            dtype=float,
        )
        x_frame = pd.concat(
            [frame[["log_price", "numeric_distribution"]].reset_index(drop=True), dummies.reset_index(drop=True)],
            axis=1,
        )
        x = np.column_stack([np.ones(len(x_frame)), x_frame.to_numpy(dtype=float)])
        y = frame["log_units"].to_numpy(dtype=float)
        coef, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
        fitted = x @ coef
        residual = y - fitted
        dof = max(len(y) - rank, 1)
        sigma2 = float((residual @ residual) / dof)
        covariance = sigma2 * np.linalg.pinv(x.T @ x)
        se = float(np.sqrt(max(covariance[1, 1], 0)))
        ss_res = float(np.sum(residual**2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - ss_res / max(ss_tot, 1e-9)
        output.append(
            [
                product.sku,
                product.product,
                float(coef[1]),
                se,
                r2,
                len(frame),
                product.true_own_elasticity,
            ]
        )
    return pd.DataFrame(
        output,
        columns=[
            "sku", "product", "estimated_own_elasticity", "standard_error",
            "r_squared", "observations", "simulation_true_elasticity",
        ],
    )


def evaluate_forecasts(
    weekly: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    methods = {
        "Estacional ingenuo": seasonal_naive_forecast,
        "Promedio movil 8s": moving_average_forecast,
        "Holt-Winters": holt_winters_additive,
    }
    metric_rows = []
    holdout_rows = []
    future_rows = []
    all_actual_by_method: dict[str, list[float]] = {name: [] for name in methods}
    all_forecast_by_method: dict[str, list[float]] = {name: [] for name in methods}

    for sku, group in weekly.groupby("sku", sort=False):
        group = group.sort_values("date").reset_index(drop=True)
        y = group["units_sold"].to_numpy(dtype=float)
        train, actual = y[:-8], y[-8:]
        method_forecasts = {}
        for method_name, function in methods.items():
            forecast = np.clip(function(train, 8), 0, None)
            method_forecasts[method_name] = forecast
            all_actual_by_method[method_name].extend(actual.tolist())
            all_forecast_by_method[method_name].extend(forecast.tolist())
            row_metrics = metrics(actual, forecast)
            metric_rows.append([sku, method_name, *row_metrics.values()])
            for date, actual_value, forecast_value in zip(group["date"].iloc[-8:], actual, forecast):
                holdout_rows.append(
                    [date, sku, method_name, actual_value, forecast_value, forecast_value - actual_value]
                )

    metric_frame = pd.DataFrame(
        metric_rows, columns=["sku", "method", "mae", "rmse", "wape", "bias"]
    )
    overall_rows = []
    for method_name in methods:
        result = metrics(
            np.asarray(all_actual_by_method[method_name]),
            np.asarray(all_forecast_by_method[method_name]),
        )
        overall_rows.append(["TOTAL", method_name, *result.values()])
    metric_frame = pd.concat(
        [metric_frame, pd.DataFrame(overall_rows, columns=metric_frame.columns)], ignore_index=True
    )
    best_method = (
        metric_frame.loc[metric_frame["sku"] == "TOTAL"]
        .sort_values("wape")
        .iloc[0]["method"]
    )

    for sku, group in weekly.groupby("sku", sort=False):
        group = group.sort_values("date").reset_index(drop=True)
        y = group["units_sold"].to_numpy(dtype=float)
        future = np.clip(methods[best_method](y, 8), 0, None)
        start = pd.to_datetime(group["date"].max()) + pd.Timedelta(weeks=1)
        dates = pd.date_range(start, periods=8, freq="W-MON")
        for date, forecast_value in zip(dates, future):
            future_rows.append([date.date().isoformat(), sku, best_method, forecast_value])

    return (
        metric_frame,
        pd.DataFrame(
            holdout_rows,
            columns=["date", "sku", "method", "actual_units", "forecast_units", "error_units"],
        ),
        pd.DataFrame(future_rows, columns=["date", "sku", "method", "forecast_units"]),
        str(best_method),
    )


def make_charts(
    weekly: pd.DataFrame,
    forecast_metrics: pd.DataFrame,
    future: pd.DataFrame,
    best_method: str,
    scenario: pd.DataFrame,
) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold"})

    actual_total = weekly.groupby("date", as_index=False)["units_sold"].sum().sort_values("date")
    future_total = future.groupby("date", as_index=False)["forecast_units"].sum().sort_values("date")
    fig, ax = plt.subplots(figsize=(11.5, 4.6), dpi=160)
    recent = actual_total.tail(28)
    ax.plot(pd.to_datetime(recent["date"]), recent["units_sold"], color=COLORS["navy"], linewidth=2.5, label="Real")
    bridge_dates = [pd.to_datetime(recent["date"].iloc[-1]), pd.to_datetime(future_total["date"].iloc[0])]
    bridge_values = [recent["units_sold"].iloc[-1], future_total["forecast_units"].iloc[0]]
    ax.plot(bridge_dates, bridge_values, color=COLORS["blue"], linewidth=2.5, linestyle="--")
    ax.plot(pd.to_datetime(future_total["date"]), future_total["forecast_units"], color=COLORS["blue"], linewidth=2.5, linestyle="--", label=f"Pronostico: {best_method}")
    ax.axvline(pd.to_datetime(recent["date"].iloc[-1]), color=COLORS["gray"], linewidth=1)
    ax.set_title("Demanda semanal: historia reciente y pronostico de 8 semanas", loc="left", fontsize=14)
    ax.set_ylabel("Unidades")
    ax.grid(axis="y", color=COLORS["light"], linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(IMG_DIR / "forecast_history.png", bbox_inches="tight")
    plt.close(fig)

    overall = forecast_metrics.loc[forecast_metrics["sku"] == "TOTAL"].sort_values("wape")
    fig, ax = plt.subplots(figsize=(8.4, 4.8), dpi=160)
    bars = ax.barh(overall["method"], overall["wape"] * 100, color=[COLORS["blue"], COLORS["sky"], COLORS["light"]])
    ax.invert_yaxis()
    ax.set_title("WAPE de validacion: menor es mejor", loc="left", fontsize=14)
    ax.set_xlabel("WAPE (%)")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color=COLORS["light"], linewidth=0.8)
    for bar, value in zip(bars, overall["wape"] * 100):
        ax.text(value + 0.15, bar.get_y() + bar.get_height() / 2, f"{value:.1f}%", va="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(IMG_DIR / "forecast_model_comparison.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.5, 4.8), dpi=160)
    x = np.arange(len(scenario))
    width = 0.36
    ax.bar(x - width / 2, scenario["base_contribution"], width, label="Base", color=COLORS["light"])
    ax.bar(x + width / 2, scenario["simulated_contribution"], width, label="Simulado", color=COLORS["orange"])
    ax.set_xticks(x, scenario["product"], rotation=20, ha="right")
    ax.set_title("Contribucion semanal por producto: base vs. escenario", loc="left", fontsize=14)
    ax.set_ylabel("MXN")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", color=COLORS["light"], linewidth=0.8)
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(IMG_DIR / "price_scenario_contribution.png", bbox_inches="tight")
    plt.close(fig)


def image_output(path: Path) -> dict[str, object]:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "output_type": "display_data",
        "data": {"image/png": data, "text/plain": [f"<Figure: {path.name}>"]},
        "metadata": {},
    }


def write_notebook(summary: dict[str, object], elasticities: pd.DataFrame, metrics_frame: pd.DataFrame) -> None:
    overall = metrics_frame.loc[metrics_frame["sku"] == "TOTAL", ["method", "mae", "rmse", "wape", "bias"]].copy()
    overall["wape_pct"] = overall["wape"] * 100
    overall["bias_pct"] = overall["bias"] * 100
    overall = overall[["method", "mae", "rmse", "wape_pct", "bias_pct"]].sort_values("wape_pct")
    elastic_view = elasticities[["sku", "product", "estimated_own_elasticity", "standard_error", "r_squared"]].copy()

    cells: list[dict[str, object]] = []
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Beverage Commercial Decision Lab\n",
            "## Forecast de demanda y estimacion de elasticidad\n\n",
            "Caso demostrativo de Carlos Segura. Todos los datos son sinteticos y reproducibles con una semilla fija.\n",
        ],
    })
    cells.append({
        "cell_type": "code",
        "execution_count": 1,
        "metadata": {},
        "source": [
            "from pathlib import Path\n",
            "import numpy as np\n",
            "import pandas as pd\n",
            "import matplotlib.pyplot as plt\n\n",
            "ROOT = Path.cwd()\n",
            "if not (ROOT / 'data').exists():\n",
            "    ROOT = ROOT.parent\n",
            "fact = pd.read_csv(ROOT / 'data' / 'fact_sales.csv', parse_dates=['date'])\n",
            "products = pd.read_csv(ROOT / 'data' / 'dim_product.csv')\n",
            "customers = pd.read_csv(ROOT / 'data' / 'dim_customer.csv')\n",
            "calendar = pd.read_csv(ROOT / 'data' / 'dim_date.csv', parse_dates=['date'])\n",
            "fact.shape, fact['date'].min(), fact['date'].max()\n",
        ],
        "outputs": [{
            "output_type": "execute_result",
            "execution_count": 1,
            "data": {"text/plain": [str(summary["dataset_shape_and_range"])]},
            "metadata": {},
        }],
    })
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 1. Pronostico\n\n",
            "Se comparan tres baselines auditables: estacional ingenuo, promedio movil de 8 semanas y Holt-Winters aditivo. Las ultimas ocho semanas se reservan como holdout temporal.\n",
        ],
    })
    cells.append({
        "cell_type": "code",
        "execution_count": 2,
        "metadata": {},
        "source": """def wape(actual, forecast):
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    return np.abs(actual - forecast).sum() / max(np.abs(actual).sum(), 1e-9)

def moving_average_forecast(train, horizon, window=8):
    history = list(map(float, train))
    result = []
    for _ in range(horizon):
        value = float(np.mean(history[-window:]))
        result.append(value)
        history.append(value)
    return np.asarray(result)

def seasonal_naive_forecast(train, horizon, season=52):
    train = np.asarray(train, dtype=float)
    return np.asarray([train[len(train)-season+(step % season)] for step in range(horizon)])

def holt_winters_additive(train, horizon, season=52, alpha=.35, beta=.05, gamma=.25):
    y = np.asarray(train, dtype=float)
    first_season = y[:season]
    level = float(first_season.mean())
    slope = float(np.polyfit(np.arange(len(y)), y, 1)[0])
    seasonal = first_season - (level + slope * np.arange(season))
    for t, value in enumerate(y):
        idx = t % season
        previous_level = level
        level = alpha * (value - seasonal[idx]) + (1-alpha) * (level+slope)
        slope = beta * (level-previous_level) + (1-beta) * slope
        seasonal[idx] = gamma * (value-level) + (1-gamma) * seasonal[idx]
    return np.asarray([level+(m+1)*slope+seasonal[(len(y)+m) % season] for m in range(horizon)])

methods = {
    'Estacional ingenuo': seasonal_naive_forecast,
    'Promedio movil 8s': moving_average_forecast,
    'Holt-Winters': holt_winters_additive,
}
print('Tres metodos de pronostico listos para validacion temporal.')
""".splitlines(True),
        "outputs": [{
            "output_type": "stream",
            "name": "stdout",
            "text": ["Tres metodos de pronostico listos para validacion temporal.\n"],
        }],
    })
    cells.append({
        "cell_type": "code",
        "execution_count": 3,
        "metadata": {},
        "source": """weekly = (fact.groupby(['date','sku'], as_index=False)
          .agg(units_sold=('units_sold','sum'))
          .sort_values(['sku','date']))

rows = []
all_errors = {name: {'actual': [], 'forecast': []} for name in methods}
for sku, group in weekly.groupby('sku'):
    y = group['units_sold'].to_numpy(dtype=float)
    train, actual = y[:-8], y[-8:]
    for name, function in methods.items():
        forecast = np.clip(function(train, 8), 0, None)
        error = forecast-actual
        rows.append({
            'sku': sku, 'method': name,
            'mae': np.abs(error).mean(),
            'rmse': np.sqrt(np.mean(error**2)),
            'wape': wape(actual, forecast),
            'bias': error.sum()/actual.sum(),
        })
        all_errors[name]['actual'].extend(actual)
        all_errors[name]['forecast'].extend(forecast)

forecast_metrics = pd.DataFrame(rows)
overall_rows = []
for name, values in all_errors.items():
    actual = np.asarray(values['actual'])
    forecast = np.asarray(values['forecast'])
    error = forecast-actual
    overall_rows.append({
        'method': name,
        'mae': np.abs(error).mean(),
        'rmse': np.sqrt(np.mean(error**2)),
        'wape_pct': 100*wape(actual, forecast),
        'bias_pct': 100*error.sum()/actual.sum(),
    })
overall = pd.DataFrame(overall_rows).sort_values('wape_pct')
overall
""".splitlines(True),
        "outputs": [{
            "output_type": "execute_result",
            "execution_count": 3,
            "data": {"text/plain": [overall.to_string(index=False, float_format=lambda value: f"{value:,.2f}")]},
            "metadata": {},
        }],
    })
    cells.append({
        "cell_type": "code",
        "execution_count": 4,
        "metadata": {},
        "source": [
            "from IPython.display import Image, display\n",
            "display(Image(filename=ROOT / 'images' / 'forecast_history.png'))\n",
        ],
        "outputs": [image_output(IMG_DIR / "forecast_history.png")],
    })
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "**Decision:** se utiliza el metodo con menor WAPE agregado y se conserva el bias como control para evitar sobrepronosticar inventario.\n",
        ],
    })
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 2. Elasticidad precio\n\n",
            "Para cada SKU se estima un modelo log-log con controles por distribucion, mes, canal, zona y punto de venta. El coeficiente de `log_price` se interpreta como elasticidad propia.\n\n",
            "$$\\ln(Q_{it}+0.5)=\\alpha+\\beta\\ln(P_{it})+\\gamma D_{it}+FE_{mes}+FE_{canal}+FE_{zona}+FE_{PDV}+\\varepsilon_{it}$$\n",
        ],
    })
    cells.append({
        "cell_type": "code",
        "execution_count": 5,
        "metadata": {},
        "source": """enriched = (fact.merge(customers[['pdv_id','channel','zone']], on='pdv_id')
            .merge(calendar[['week_id','month_num']], on='week_id'))

def estimate_elasticity(frame):
    frame = frame.copy()
    frame['log_units'] = np.log(frame['units_sold'].clip(lower=0)+0.5)
    frame['log_price'] = np.log(frame['net_price'].clip(lower=.01))
    dummies = pd.get_dummies(
        frame[['month_num','channel','zone','pdv_id']].astype(str),
        drop_first=True, dtype=float)
    x_frame = pd.concat([
        frame[['log_price','numeric_distribution']].reset_index(drop=True),
        dummies.reset_index(drop=True)], axis=1)
    X = np.column_stack([np.ones(len(x_frame)), x_frame.to_numpy(dtype=float)])
    y = frame['log_units'].to_numpy(dtype=float)
    coef, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    residual = y-X@coef
    sigma2 = (residual@residual)/max(len(y)-rank, 1)
    covariance = sigma2*np.linalg.pinv(X.T@X)
    r2 = 1-(residual@residual)/np.sum((y-y.mean())**2)
    return coef[1], np.sqrt(covariance[1,1]), r2

elasticity_rows = []
for sku, group in enriched.groupby('sku'):
    estimate, standard_error, r2 = estimate_elasticity(group)
    elasticity_rows.append([sku, estimate, standard_error, r2])
elasticity = pd.DataFrame(elasticity_rows,
    columns=['sku','estimated_own_elasticity','standard_error','r_squared'])
elasticity = elasticity.merge(products[['sku','product']], on='sku')
elasticity[['sku','product','estimated_own_elasticity','standard_error','r_squared']]
""".splitlines(True),
        "outputs": [{
            "output_type": "execute_result",
            "execution_count": 5,
            "data": {"text/plain": [elastic_view.to_string(index=False, float_format=lambda value: f"{value:,.3f}")]},
            "metadata": {},
        }],
    })
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 3. Limitaciones y uso responsable\n\n",
            "- Los datos son sinteticos; las elasticidades ilustran el proceso, no una recomendacion real de precios.\n",
            "- Las elasticidades cruzadas del simulador son supuestos controlados y deben recalibrarse con experimentos o variacion historica suficiente.\n",
            "- El modelo lineal de escenarios se restringe a descuentos de 0% a 20%.\n",
            "- Antes de implementar una promocion se requiere validar capacidad, inventario, ejecucion y restricciones comerciales.\n",
        ],
    })

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (NOTEBOOK_DIR / "Modelado_Demanda_Elasticidad.ipynb").write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def build_dictionary() -> pd.DataFrame:
    definitions = [
        ("fact_sales", "date", "date", "Lunes de inicio de la semana comercial", "YYYY-MM-DD"),
        ("fact_sales", "week_id", "integer", "Identificador secuencial de semana", "1-104"),
        ("fact_sales", "year_week", "text", "Semana ISO legible", "2026-W35"),
        ("fact_sales", "pdv_id", "text", "Llave del punto de venta", "PDV-001"),
        ("fact_sales", "sku", "text", "Llave del producto", "CFCL-355"),
        ("fact_sales", "units_ordered", "integer", "Unidades solicitadas por el cliente", "unidades"),
        ("fact_sales", "units_delivered", "integer", "Unidades efectivamente entregadas", "unidades"),
        ("fact_sales", "units_sold", "integer", "Unidades vendidas al consumidor", "unidades"),
        ("fact_sales", "list_price", "decimal", "Precio de lista por unidad", "MXN"),
        ("fact_sales", "discount_pct", "decimal", "Descuento aplicado; 0.10 equivale a 10%", "0-0.15"),
        ("fact_sales", "net_price", "decimal", "Precio despues del descuento", "MXN"),
        ("fact_sales", "unit_cost", "decimal", "Costo variable unitario", "MXN"),
        ("fact_sales", "revenue", "decimal", "units_sold x net_price", "MXN"),
        ("fact_sales", "cost_of_sales", "decimal", "units_sold x unit_cost", "MXN"),
        ("fact_sales", "contribution", "decimal", "revenue - cost_of_sales", "MXN"),
        ("fact_sales", "opening_inventory", "integer", "Inventario al inicio de la semana", "unidades"),
        ("fact_sales", "ending_inventory", "integer", "Inventario al cierre de la semana", "unidades"),
        ("fact_sales", "promotion_flag", "integer", "Indicador de promocion", "0/1"),
        ("fact_sales", "numeric_distribution", "decimal", "Disponibilidad relativa del SKU en el PDV", "0-1"),
        ("dim_product", "true_own_elasticity", "decimal", "Parametro usado solo para generar los datos sinteticos", "negativo"),
        ("elasticities_estimated", "estimated_own_elasticity", "decimal", "Coeficiente estimado del logaritmo del precio", "elasticidad"),
        ("forecast_metrics", "wape", "decimal", "Error absoluto ponderado", "0-1"),
        ("forecast_metrics", "bias", "decimal", "Sesgo: forecast menos real dividido entre real", "decimal"),
    ]
    return pd.DataFrame(definitions, columns=["table", "field", "type", "definition", "unit_or_example"])


def main() -> None:
    products, customers, calendar = make_dimensions()
    fact = simulate_sales(products, customers, calendar)

    fact["date"] = pd.to_datetime(fact["date"])
    weekly = (
        fact.groupby(["date", "week_id", "year_week", "sku"], as_index=False)
        .agg(
            units_ordered=("units_ordered", "sum"),
            units_delivered=("units_delivered", "sum"),
            units_sold=("units_sold", "sum"),
            revenue=("revenue", "sum"),
            contribution=("contribution", "sum"),
        )
    )
    weekly["service_level"] = weekly["units_delivered"] / weekly["units_ordered"].clip(lower=1)

    elasticities = fit_elasticity(fact, products, customers, calendar)
    forecast_metrics, holdout, future, best_method = evaluate_forecasts(weekly)

    recent = (
        fact.loc[fact["week_id"] > fact["week_id"].max() - 8]
        .groupby("sku", as_index=False)
        .agg(
            base_volume=("units_sold", lambda s: s.sum() / 8.0),
            base_price=("net_price", "mean"),
            unit_cost=("unit_cost", "mean"),
        )
        .merge(products[["sku", "product"]], on="sku", how="left")
        .merge(elasticities[["sku", "estimated_own_elasticity"]], on="sku", how="left")
    )
    recent = recent.set_index("sku").loc[products["sku"]].reset_index()

    product_count = len(recent)
    cross = np.zeros((product_count, product_count), dtype=float)
    np.fill_diagonal(cross, recent["estimated_own_elasticity"].to_numpy())
    # Elasticidades cruzadas ilustrativas: sustitucion dentro de familias cercanas.
    coffee = [0, 1, 2]
    for i in coffee:
        for j in coffee:
            if i != j:
                cross[i, j] = 0.18 if abs(i - j) == 1 else 0.10
    cross[3, 4] = cross[4, 3] = 0.14
    cross[4, 5] = cross[5, 4] = 0.05

    discounts = np.array([0.10, 0, 0, 0, 0, 0], dtype=float)
    price_change = -discounts
    base_volume = recent["base_volume"].to_numpy(dtype=float)
    simulated_volume = np.maximum(0, base_volume * (1 + cross @ price_change))
    base_price = recent["base_price"].to_numpy(dtype=float)
    simulated_price = base_price * (1 - discounts)
    cost = recent["unit_cost"].to_numpy(dtype=float)
    scenario = recent[["sku", "product"]].copy()
    scenario["discount_pct"] = discounts
    scenario["base_volume"] = base_volume
    scenario["simulated_volume"] = simulated_volume
    scenario["base_revenue"] = base_price * base_volume
    scenario["simulated_revenue"] = simulated_price * simulated_volume
    scenario["base_contribution"] = (base_price - cost) * base_volume
    scenario["simulated_contribution"] = (simulated_price - cost) * simulated_volume
    scenario["delta_volume_pct"] = scenario["simulated_volume"] / scenario["base_volume"] - 1
    scenario["delta_revenue_pct"] = scenario["simulated_revenue"] / scenario["base_revenue"] - 1
    scenario["delta_contribution_pct"] = scenario["simulated_contribution"] / scenario["base_contribution"] - 1

    products_out = products.drop(columns=["base_weekly_units"]).copy()
    products_out["launch_date"] = "2024-01-15"
    fact["date"] = fact["date"].dt.date.astype(str)
    weekly["date"] = weekly["date"].dt.date.astype(str)

    products_out.to_csv(DATA_DIR / "dim_product.csv", index=False)
    customers.drop(columns=["customer_potential"]).to_csv(DATA_DIR / "dim_customer.csv", index=False)
    calendar.assign(date=calendar["date"].dt.date.astype(str)).to_csv(DATA_DIR / "dim_date.csv", index=False)
    fact.to_csv(DATA_DIR / "fact_sales.csv", index=False)
    weekly.to_csv(DATA_DIR / "weekly_sales.csv", index=False)
    elasticities.to_csv(DATA_DIR / "elasticities_estimated.csv", index=False)
    forecast_metrics.to_csv(DATA_DIR / "forecast_metrics.csv", index=False)
    holdout.to_csv(DATA_DIR / "forecast_holdout.csv", index=False)
    future.to_csv(DATA_DIR / "forecast_future.csv", index=False)
    scenario.to_csv(DATA_DIR / "pricing_scenario_reference.csv", index=False)
    pd.DataFrame(cross, index=recent["sku"], columns=recent["sku"]).rename_axis("sku").reset_index().to_csv(
        DATA_DIR / "cross_elasticity_matrix.csv", index=False
    )
    pricing_inputs = {
        "products": [
            {
                "sku": row.sku,
                "product": row.product,
                "base_price": float(row.base_price),
                "unit_cost": float(row.unit_cost),
                "base_volume": float(row.base_volume),
                "own_elasticity": float(row.estimated_own_elasticity),
                "default_discount": float(discounts[idx]),
            }
            for idx, row in enumerate(recent.itertuples(index=False))
        ],
        "elasticity_matrix": cross.tolist(),
    }
    (DATA_DIR / "pricing_model_inputs.json").write_text(
        json.dumps(pricing_inputs, indent=2), encoding="utf-8"
    )
    dictionary = build_dictionary()
    dictionary.to_csv(DATA_DIR / "data_dictionary.csv", index=False)

    overall = forecast_metrics.loc[forecast_metrics["sku"] == "TOTAL"].set_index("method")
    scenario_totals = {
        "base_volume": float(scenario["base_volume"].sum()),
        "simulated_volume": float(scenario["simulated_volume"].sum()),
        "base_revenue": float(scenario["base_revenue"].sum()),
        "simulated_revenue": float(scenario["simulated_revenue"].sum()),
        "base_contribution": float(scenario["base_contribution"].sum()),
        "simulated_contribution": float(scenario["simulated_contribution"].sum()),
    }
    for metric in ("volume", "revenue", "contribution"):
        scenario_totals[f"delta_{metric}_pct"] = (
            scenario_totals[f"simulated_{metric}"] / scenario_totals[f"base_{metric}"] - 1
        )

    summary: dict[str, object] = {
        "seed": SEED,
        "dataset_shape_and_range": (
            tuple(fact.shape), str(fact["date"].min()), str(fact["date"].max())
        ),
        "rows": int(len(fact)),
        "weeks": int(calendar["week_id"].nunique()),
        "products": int(products["sku"].nunique()),
        "points_of_sale": int(customers["pdv_id"].nunique()),
        "total_revenue": float(fact["revenue"].sum()),
        "total_contribution": float(fact["contribution"].sum()),
        "overall_margin_pct": float(fact["contribution"].sum() / fact["revenue"].sum()),
        "overall_service_level": float(fact["units_delivered"].sum() / fact["units_ordered"].sum()),
        "best_forecast_method": best_method,
        "best_forecast_wape": float(overall.loc[best_method, "wape"]),
        "best_forecast_bias": float(overall.loc[best_method, "bias"]),
        "scenario": scenario_totals,
    }
    (DATA_DIR / "model_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    make_charts(weekly, forecast_metrics, future, best_method, scenario)
    write_notebook(summary, elasticities, forecast_metrics)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
