"""Reusable Plotly chart builders — theme-aware (light/dark)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.theme import is_light


def _c() -> dict:
    """Theme-dependent chart colors."""
    if is_light():
        return {"up": "#16A34A", "down": "#E11D48", "line": "#2F6BFF", "glow": "#0891B2",
                "grid": "rgba(15,23,42,0.08)", "text": "#0F172A", "muted": "#5B6472",
                "template": "plotly_white"}
    return {"up": "#1DD75B", "down": "#FF5C73", "line": "#4F8CFF", "glow": "#00E5FF",
            "grid": "rgba(152,162,179,0.10)", "text": "#FFFFFF", "muted": "#98A2B3",
            "template": "plotly_dark"}


def _layout(c: dict, with_axes: bool = True) -> dict:
    lay = dict(
        template=c["template"],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=70, b=10),
        hovermode="x unified",
        # title sits top-left; legend top-right on the same row to avoid overlap
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right",
                    font=dict(color=c["muted"], size=11)),
        font=dict(color=c["muted"]),
        title_font=dict(color=c["text"], size=16),
    )
    if with_axes:
        lay["xaxis"] = dict(gridcolor=c["grid"], rangeslider=dict(visible=False))
        lay["yaxis"] = dict(gridcolor=c["grid"])
    return lay


def _title(text: str) -> dict:
    """Top-left anchored title that never collides with the legend."""
    return dict(text=text, x=0, xanchor="left", y=0.98, yanchor="top")


def sparkline(series: pd.Series) -> go.Figure:
    """Tiny axis-less trend line for index cards."""
    c = _c()
    color = c["up"] if len(series) > 1 and series.iloc[-1] >= series.iloc[0] else c["down"]
    fig = go.Figure(go.Scatter(
        x=list(range(len(series))), y=series.values, mode="lines",
        line=dict(color=color, width=1.8), hoverinfo="skip",
    ))
    fig.update_layout(
        template=c["template"], paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=56, margin=dict(l=0, r=0, t=2, b=2), showlegend=False,
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
    )
    return fig


def line_chart(df: pd.DataFrame, title: str = "") -> go.Figure:
    c = _c()
    color = c["up"] if len(df) > 1 and df["Close"].iloc[-1] >= df["Close"].iloc[0] else c["down"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Close",
                             line=dict(color=color, width=2)))
    fig.update_layout(title=_title(title), height=380, **_layout(c))
    return fig


def mood_gauge(score: int) -> go.Figure:
    c = _c()
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"color": c["text"], "size": 40}},
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=c["muted"],
                      tickfont=dict(color=c["muted"], size=10)),
            bar=dict(color=c["glow"], thickness=0.28),
            bgcolor="rgba(127,127,127,0.06)",
            borderwidth=0,
            steps=[
                dict(range=[0, 40], color="rgba(225,29,72,0.12)"),
                dict(range=[40, 60], color="rgba(217,119,6,0.10)"),
                dict(range=[60, 100], color="rgba(22,163,74,0.12)"),
            ],
        ),
    ))
    fig.update_layout(template=c["template"], paper_bgcolor="rgba(0,0,0,0)",
                      height=210, margin=dict(l=25, r=25, t=20, b=5))
    return fig


def allocation_donut(labels: list[str], values: list[float]) -> go.Figure:
    c = _c()
    palette = ["#4F8CFF", "#7C5CFF", "#0891B2", "#16A34A", "#D97706",
               "#E11D48", "#38bdf8", "#a78bfa", "#f472b6", "#34d399"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.62,
        marker=dict(colors=palette[:len(labels)],
                    line=dict(color="rgba(127,127,127,0.25)", width=1)),
        textinfo="label+percent", textfont=dict(color=c["text"], size=12),
    ))
    fig.update_layout(template=c["template"], paper_bgcolor="rgba(0,0,0,0)",
                      height=340, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    return fig


def technical_chart(df: pd.DataFrame, title: str = "", show_bb: bool = True, show_ma: bool = True) -> go.Figure:
    c = _c()
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        row_heights=[0.5, 0.14, 0.18, 0.18], vertical_spacing=0.03,
        subplot_titles=("", "Volume", "RSI (14)", "MACD (12,26,9)"),
    )
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="OHLC", increasing_line_color=c["up"], decreasing_line_color=c["down"],
    ), row=1, col=1)
    if show_bb and "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], name="BB upper",
                                 line=dict(color="rgba(127,140,160,0.6)", width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], name="BB lower",
                                 line=dict(color="rgba(127,140,160,0.6)", width=1),
                                 fill="tonexty", fillcolor="rgba(127,140,160,0.07)"), row=1, col=1)
    if show_ma:
        for col_name, color in (("SMA50", "#D97706"), ("SMA200", "#7C5CFF")):
            if col_name in df.columns and df[col_name].notna().any():
                fig.add_trace(go.Scatter(x=df.index, y=df[col_name], name=col_name,
                                         line=dict(color=color, width=1.2)), row=1, col=1)
    if "Volume" in df.columns:
        vcolors = [c["up"] if cl >= o else c["down"] for cl, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                             marker_color=vcolors, opacity=0.5, showlegend=False), row=2, col=1)
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                                 line=dict(color=c["line"], width=1.4), showlegend=False), row=3, col=1)
        fig.add_hline(y=70, line=dict(color=c["down"], width=1, dash="dot"), row=3, col=1)
        fig.add_hline(y=30, line=dict(color=c["up"], width=1, dash="dot"), row=3, col=1)
    if "macd" in df.columns:
        hcolors = [c["up"] if v >= 0 else c["down"] for v in df["hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df["hist"], name="Hist",
                             marker_color=hcolors, opacity=0.5, showlegend=False), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["macd"], name="MACD",
                                 line=dict(color=c["line"], width=1.3), showlegend=False), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["signal"], name="Signal",
                                 line=dict(color="#D97706", width=1.3), showlegend=False), row=4, col=1)
    fig.update_layout(title=_title(title), height=820, xaxis_rangeslider_visible=False,
                      **_layout(c, with_axes=False))
    fig.update_xaxes(gridcolor=c["grid"])
    fig.update_yaxes(gridcolor=c["grid"])
    for ann in fig.layout.annotations:
        ann.font.color = c["muted"]
    return fig


def candlestick_chart(df: pd.DataFrame, title: str = "", mas: tuple[int, ...] = (20, 50)) -> go.Figure:
    c = _c()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.75, 0.25], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="OHLC", increasing_line_color=c["up"], decreasing_line_color=c["down"],
    ), row=1, col=1)
    for window in mas:
        if len(df) > window:
            fig.add_trace(go.Scatter(x=df.index, y=df["Close"].rolling(window).mean(),
                                     mode="lines", name=f"MA{window}",
                                     line=dict(width=1.2)), row=1, col=1)
    if "Volume" in df.columns:
        colors = [c["up"] if cl >= o else c["down"] for cl, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                             marker_color=colors, opacity=0.5), row=2, col=1)
    fig.update_layout(title=_title(title), height=560, xaxis_rangeslider_visible=False,
                      **_layout(c, with_axes=False))
    fig.update_xaxes(gridcolor=c["grid"])
    fig.update_yaxes(gridcolor=c["grid"])
    return fig
