"""Result analysis: derive chart spec, trends and quick insights from result rows.

Turns a SQL result set into a `visualization` spec (table/chart with axes) plus
lightweight statistical insights and a trend direction — so the chat UI can show
charts, tables, trends and analysis like the companion brainz app.
"""
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_NUMERIC_HINTS = ("count", "total", "sum", "amount", "qty", "quantity", "avg",
                  "average", "rate", "score", "nps", "value", "revenue", "price",
                  "number", "num", "percent", "pct")
_CATEGORY_HINTS = ("category", "type", "name", "status", "state", "branch",
                    "service_point", "product", "department", "label", "group")
_TIME_HINTS = ("date", "month", "year", "day", "week", "quarter", "created",
               "time", "period", "timestamp")


def _is_number(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, str):
        try:
            float(v.replace(",", ""))
            return True
        except ValueError:
            return False
    return False


def _to_number(v: Any) -> Optional[float]:
    try:
        if isinstance(v, str):
            return float(v.replace(",", ""))
        return float(v)
    except (TypeError, ValueError):
        return None


def _looks_temporal(name: str, values: List[Any]) -> bool:
    n = name.lower()
    if any(h in n for h in _TIME_HINTS):
        return True
    # Sniff date-like strings
    sample = [str(v) for v in values[:5] if v is not None]
    return any(re.search(r"\d{4}-\d{2}", s) for s in sample)


def _classify_columns(columns: List[str], rows: List[Dict[str, Any]]) -> Tuple[List[str], List[str], List[str]]:
    """Return (numeric_cols, category_cols, time_cols)."""
    numeric, category, time_cols = [], [], []
    for c in columns:
        values = [r.get(c) for r in rows]
        non_null = [v for v in values if v is not None]
        numeric_ratio = (sum(1 for v in non_null if _is_number(v)) / len(non_null)) if non_null else 0
        if _looks_temporal(c, values):
            time_cols.append(c)
        elif numeric_ratio >= 0.8:
            numeric.append(c)
        else:
            category.append(c)
    return numeric, category, time_cols


def build_visualization(columns: List[str], rows: List[Dict[str, Any]],
                        user_query: str = "") -> Dict[str, Any]:
    """Return a visualization spec: {type, chart_type?, xAxis?, yAxis?, ...}."""
    if not rows:
        return {"type": "empty"}

    if not columns:
        columns = list(rows[0].keys())

    # Single value (1 row, 1 numeric col) -> metric card.
    if len(rows) == 1 and len(columns) == 1 and _is_number(rows[0].get(columns[0])):
        return {"type": "metric", "label": columns[0], "value": rows[0].get(columns[0])}

    numeric, category, time_cols = _classify_columns(columns, rows)
    q = (user_query or "").lower()

    # Honor an explicit chart request in the question.
    requested = None
    for kind in ("pie", "line", "area", "scatter", "bar", "column"):
        if kind in q:
            requested = "bar" if kind == "column" else kind
            break

    chartable = len(rows) <= 50 and numeric and (category or time_cols)
    if not chartable:
        return {"type": "table", "columns": columns}

    y = numeric[0]
    if time_cols:
        x = time_cols[0]
        chart_type = requested or "line"   # time series -> line
    else:
        x = category[0]
        chart_type = requested or ("pie" if len(rows) <= 8 else "bar")

    return {
        "type": "chart",
        "chart_type": chart_type,
        "xAxis": x,
        "yAxis": y,
        "series": numeric[:3],
        "columns": columns,
    }


def compute_trend(columns: List[str], rows: List[Dict[str, Any]],
                  viz: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """For time-series-ish data, compute direction and percent change."""
    if viz.get("type") != "chart" or not rows or len(rows) < 2:
        return None
    y = viz.get("yAxis")
    if not y:
        return None
    series = [_to_number(r.get(y)) for r in rows]
    series = [v for v in series if v is not None]
    if len(series) < 2:
        return None
    first, last = series[0], series[-1]
    direction = "flat"
    pct = 0.0
    if first != 0:
        pct = round((last - first) / abs(first) * 100, 1)
    if last > first:
        direction = "up"
    elif last < first:
        direction = "down"
    return {
        "direction": direction,
        "percent_change": pct,
        "start": first,
        "end": last,
        "min": min(series),
        "max": max(series),
    }


def compute_insights(columns: List[str], rows: List[Dict[str, Any]],
                     viz: Dict[str, Any], trend: Optional[Dict[str, Any]]) -> List[str]:
    """Generate short, data-grounded insight bullets."""
    insights: List[str] = []
    if not rows:
        return ["No matching records were found."]

    insights.append(f"{len(rows)} row(s) returned.")

    if viz.get("type") == "chart":
        x, y = viz.get("xAxis"), viz.get("yAxis")
        pairs = []
        for r in rows:
            val = _to_number(r.get(y))
            if val is not None:
                pairs.append((r.get(x), val))
        if pairs:
            top = max(pairs, key=lambda p: p[1])
            low = min(pairs, key=lambda p: p[1])
            total = sum(v for _, v in pairs)
            insights.append(f"Highest {y}: {top[0]} ({top[1]:g}).")
            insights.append(f"Lowest {y}: {low[0]} ({low[1]:g}).")
            if total:
                insights.append(f"Total {y} across results: {total:g}.")

    if trend:
        arrow = {"up": "increased", "down": "decreased", "flat": "stayed flat"}[trend["direction"]]
        insights.append(
            f"Trend: {viz.get('yAxis')} {arrow}"
            + (f" by {abs(trend['percent_change'])}% from {trend['start']:g} to {trend['end']:g}."
               if trend["direction"] != "flat" else ".")
        )
    return insights


def analyze(columns: List[str], rows: List[Dict[str, Any]],
            user_query: str = "") -> Dict[str, Any]:
    """One-shot: returns {visualization, trend, insights}."""
    viz = build_visualization(columns, rows, user_query)
    trend = compute_trend(columns, rows, viz)
    insights = compute_insights(columns, rows, viz, trend)
    return {"visualization": viz, "trend": trend, "insights": insights}
