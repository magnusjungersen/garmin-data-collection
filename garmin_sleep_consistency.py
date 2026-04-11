"""
Generates an interactive sleep window timeline and saves it to docs/sleep_consistency.html.
Reads from Google Sheets via garmin_data.py — no direct Garmin API calls.
"""

import os
from datetime import timedelta
import plotly.graph_objects as go
from garmin_data import fetch_sleep_data

OUTPUT = "docs/sleep_consistency.html"
DAYS = 30
WINDOWS = [7, 14, 30]


def to_shifted_hours(dt) -> float:
    """
    Express a time as hours since the previous noon (12:00).
    Maps the sleep-relevant window to a positive linear scale:
        noon     →  0.0
        8 PM     →  8.0
        midnight → 12.0
        6 AM     → 18.0
    Sleep bars always have bedtime < wake time as positive numbers.
    """
    h = dt.hour + dt.minute / 60 + dt.second / 3600
    if h < 12:
        h += 24
    return h - 12


def shifted_to_label(h: float) -> str:
    total = (h + 12) % 24
    hours = int(total)
    minutes = int(round((total - hours) * 60))
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours:02d}:{minutes:02d}"


def compute_window_averages(rows: list[dict], days: int) -> dict:
    subset = rows[-days:]
    bed_hours = [to_shifted_hours(r["sleep_start"]) for r in subset]
    wake_hours = [to_shifted_hours(r["sleep_end"]) for r in subset]
    durations = [w - b for b, w in zip(bed_hours, wake_hours)]
    avg_bed = sum(bed_hours) / len(bed_hours)
    avg_wake = sum(wake_hours) / len(wake_hours)
    avg_dur_min = round(sum(durations) / len(durations) * 60)
    return {
        "avg_bed": avg_bed,
        "avg_wake": avg_wake,
        "avg_dur_min": avg_dur_min,
        "start_date": (subset[0]["date"] - timedelta(days=1)).isoformat(),
    }


def main():
    os.makedirs("docs", exist_ok=True)

    print(f"Reading {DAYS} days of sleep data from Sheets...")
    rows = fetch_sleep_data(days=DAYS)

    if not rows:
        print("No data available.")
        return

    dates = [r["date"].isoformat() for r in rows]
    line_x_start = (rows[0]["date"] - timedelta(days=1)).isoformat()
    line_x_end = (rows[-1]["date"] + timedelta(days=1)).isoformat()
    bedtime_h = [to_shifted_hours(r["sleep_start"]) for r in rows]
    wake_h = [to_shifted_hours(r["sleep_end"]) for r in rows]
    durations = [w - b for b, w in zip(bedtime_h, wake_h)]
    scores = [r["sleep_score"] or 0 for r in rows]

    duration_labels = [
        f"{r['total_sleep_seconds'] // 3600}h {(r['total_sleep_seconds'] % 3600) // 60:02d}m"
        for r in rows
    ]

    hover_texts = [
        (
            f"<b>{r['date'].strftime('%A, %b %d')}</b><br>"
            f"Bedtime: {r['sleep_start'].strftime('%H:%M')}<br>"
            f"Wake: {r['sleep_end'].strftime('%H:%M')}<br>"
            f"Duration: {r['total_sleep_seconds'] // 3600}h "
            f"{(r['total_sleep_seconds'] % 3600) // 60}m<br>"
            f"Sleep score: {r['sleep_score']}"
        )
        for r in rows
    ]

    # Precompute averages for each window
    avgs = {w: compute_window_averages(rows, min(w, len(rows))) for w in WINDOWS}

    fig = go.Figure()

    # Trace 0: sleep window bars (always visible)
    fig.add_trace(go.Bar(
        x=dates,
        y=durations,
        base=bedtime_h,
        text=duration_labels,
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="white", size=10, family="monospace"),
        marker=dict(
            color=scores,
            colorscale="Viridis",
            cmin=50,
            cmax=90,
            colorbar=dict(
                title=dict(text="Sleep score", side="right", font=dict(color="#e0e0e0")),
                tickvals=[50, 60, 70, 80, 90],
                tickfont=dict(color="#e0e0e0"),
            ),
        ),
        hovertext=hover_texts,
        hoverinfo="text",
        name="Sleep window",
    ))

    # Traces 1-2 per window: avg bedtime + avg wake lines
    # Layout: [bars, bed_7d, wake_7d, bed_14d, wake_14d, bed_30d, wake_30d]
    for i, w in enumerate(WINDOWS):
        a = avgs[w]
        dur_label = f"{a['avg_dur_min'] // 60}h {a['avg_dur_min'] % 60:02d}m"
        visible = i == 0  # only 7d visible by default

        fig.add_trace(go.Scatter(
            x=[line_x_start, line_x_end],
            y=[a["avg_bed"], a["avg_bed"]],
            mode="lines",
            line=dict(color="#7EB8F7", width=2, dash="solid"),
            name=f"Avg bedtime: {shifted_to_label(a['avg_bed'])}",
            hoverinfo="skip",
            visible=visible,
        ))

        fig.add_trace(go.Scatter(
            x=[line_x_start, line_x_end],
            y=[a["avg_wake"], a["avg_wake"]],
            mode="lines",
            line=dict(color="#56D9B1", width=2, dash="dot"),
            name=f"Avg wake: {shifted_to_label(a['avg_wake'])} · Avg duration: {dur_label}",
            hoverinfo="skip",
            visible=visible,
        ))

    # Buttons: update x-axis range + toggle which average traces are visible
    def make_visibility(active_idx: int) -> list[bool]:
        # Trace 0 (bars) always visible, then pairs per window
        vis = [True]
        for i in range(len(WINDOWS)):
            vis += [i == active_idx, i == active_idx]
        return vis

    def make_annotation(a: dict) -> dict:
        dur = f"{a['avg_dur_min'] // 60}h {a['avg_dur_min'] % 60:02d}m"
        return dict(
            text=(
                f"<b>Avg</b>  "
                f"sleep {shifted_to_label(a['avg_bed'])} "
                f"· wake {shifted_to_label(a['avg_wake'])} "
                f"· {dur}"
            ),
            x=1.0, y=1.065,
            xref="paper", yref="paper",
            xanchor="right", yanchor="middle",
            showarrow=False,
            font=dict(color="#a0a0c0", size=12),
        )

    buttons = []
    for i, w in enumerate(WINDOWS):
        a = avgs[w]
        buttons.append(dict(
            label=f"{w} days",
            method="update",
            args=[
                {"visible": make_visibility(i)},
                {
                    "xaxis.range": [a["start_date"], line_x_end],
                    "annotations": [make_annotation(a)],
                },
            ],
        ))

    # Y-axis ticks: every 2 hours from 20:00 to 11:00 next day
    # In shifted hours: 20:00=8, 22:00=10, 00:00=12, ..., 10:00=22, 11:00=23
    y_ticks = list(range(10, 23, 2)) + [23]
    y_labels = [shifted_to_label(h) for h in y_ticks]

    dark_bg = "#1e1e2e"
    dark_grid = "rgba(255,255,255,0.08)"
    font_color = "#e0e0e0"

    fig.update_layout(
        title=dict(
            text="Sleep Consistency",
            font=dict(size=20, color=font_color),
            x=0.5,
            xanchor="center",
            y=0.97,
        ),
        font=dict(color=font_color),
        annotations=[make_annotation(avgs[7])],
        updatemenus=[dict(
            type="buttons",
            direction="right",
            x=0.0,
            xanchor="left",
            y=1.12,
            showactive=True,
            active=0,
            buttons=buttons,
            bgcolor="#c0c0d8",
            bordercolor="#888899",
            font=dict(color="#1e1e2e"),
        )],
        xaxis=dict(
            title="Date",
            type="date",
            range=[avgs[7]["start_date"], line_x_end],
            rangeslider=dict(visible=True, thickness=0.08, bgcolor="#2a2a3e"),
            gridcolor=dark_grid,
            linecolor="#444466",
            tickcolor="#444466",
        ),
        yaxis=dict(
            title="Time of day",
            tickvals=y_ticks,
            ticktext=y_labels,
            range=[9.5, 23.5],
            fixedrange=True,
            gridcolor=dark_grid,
            linecolor="#444466",
            tickcolor="#444466",
        ),
        showlegend=False,
        plot_bgcolor=dark_bg,
        paper_bgcolor=dark_bg,
        height=560,
        bargap=0.25,
        margin=dict(t=80, b=100),
    )

    fig.write_html(
        OUTPUT,
        include_plotlyjs="cdn",
        full_html=True,
        config={"displayModeBar": False},
        div_id="sleep-chart",
    )
    # Inject dark background on the page itself so there's no white flash
    with open(OUTPUT, "r") as f:
        html = f.read()
    html = html.replace(
        "<head>",
        '<head><style>body{background:#1e1e2e;margin:0;padding:0;}</style>',
    )
    with open(OUTPUT, "w") as f:
        f.write(html)
    print(f"Chart saved to {OUTPUT}")


if __name__ == "__main__":
    main()
