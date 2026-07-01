import dash
from dash import dcc, html, Input, Output, State, ALL, ctx
import dash_bootstrap_components as dbc
from utils.style import COLORS, CARD_STYLE, LABEL_STYLE, HEADER_STYLE
from utils.metrics_and_gantt import compute_metrics, build_gantt
from utils.algorithms import (run_fifo, run_sjf, run_round_robin, run_priority, 
                              run_edf, run_cfs, run_dwarr)


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "CPU Scheduling Simulator"


def make_process_row(i):
    """Return a single row of process input fields."""
    return dbc.Row([
        dbc.Col(dbc.Input(id={"type": "pid",      "index": i}, placeholder=f"P{i+1}", size="sm"), width=1),
        dbc.Col(dbc.Input(id={"type": "arrival",  "index": i}, placeholder="0",      size="sm", type="number", min=0), width=2),
        dbc.Col(dbc.Input(id={"type": "burst",    "index": i}, placeholder="reqd",   size="sm", type="number", min=1), width=2),
        dbc.Col(dbc.Input(id={"type": "priority", "index": i}, placeholder="opt",    size="sm", type="number", min=1), width=2),
        dbc.Col(dbc.Input(id={"type": "deadline", "index": i}, placeholder="opt",    size="sm", type="number", min=1), width=2),
    ], className="mb-1 g-2", id=f"proc-row-{i}")


app.layout = html.Div(style={"background": COLORS["bg"], "minHeight": "100vh", "padding": "24px", "fontFamily": "monospace"}, children=[
    # Title
    html.Div([
        html.H2("⚙ Single-core CPU Scheduling Simulator ⚙", style={**HEADER_STYLE, "fontSize": "22px"}),
        html.P("First-In First-Out · Shortest Job First · Round-Robin · Priority · Earliest Deadline First · Completely Fair Scheduler · Deadline-Weighted Adaptive Round-Robin",
               style={"color": COLORS["muted"], "fontSize": "12px", "marginBottom": "0"}),
    ], style={"marginBottom": "20px"}),

    dbc.Row([
        # Left panels: inputs 
        dbc.Col(width=5, children=[
            html.Div(style=CARD_STYLE, children=[
                html.P("Number of processes", style=LABEL_STYLE),
                dbc.Input(id="num-procs", type="number", value=4, min=1, max=10, size="sm",
                          style={"width": "80px", "marginBottom": "12px"}),
                # Column headers
                dbc.Row([
                    dbc.Col(html.Small("ID",       style={"color": COLORS["muted"]}), width=1),
                    dbc.Col(html.Small("Arrival",  style={"color": COLORS["muted"]}), width=2),
                    dbc.Col(html.Small("Burst",    style={"color": COLORS["muted"]}), width=2),
                    dbc.Col(html.Small("Priority", style={"color": COLORS["muted"]}), width=2),
                    dbc.Col(html.Small("Deadline", style={"color": COLORS["muted"]}), width=2),
                ], className="mb-1 g-2"),

                html.Div(id="proc-inputs"),
            ]),

            html.Div(style=CARD_STYLE, children=[
                html.P("Preemptive parameters", style=LABEL_STYLE),
                dbc.Row([
                    dbc.Col([
                        html.Small("Quantum", style={"color": COLORS["muted"]}),
                        dbc.Input(id="quantum", type="number", value=2, min=1, size="sm"),
                    ], width=6),
                    dbc.Col([
                        html.Small("Overhead", style={"color": COLORS["muted"]}),
                        dbc.Input(id="overhead", type="number", value=1, min=0, size="sm"),
                    ], width=6),
                ], className="g-2"),
            ]),

            # Algorithm buttons
            html.Div(style=CARD_STYLE, children=[
                html.P("Select Algorithm", style=LABEL_STYLE),
                dbc.ButtonGroup([
                    dbc.Button("FIFO",     id="btn-fifo",     n_clicks=0, size="sm", outline=True, color="info"),
                    dbc.Button("SJF",      id="btn-sjf",      n_clicks=0, size="sm", outline=True, color="info"),
                    dbc.Button("RR",       id="btn-rr",       n_clicks=0, size="sm", outline=True, color="info"),
                    dbc.Button("Priority", id="btn-priority", n_clicks=0, size="sm", outline=True, color="info"),
                    dbc.Button("EDF",      id="btn-edf",      n_clicks=0, size="sm", outline=True, color="info"),
                    dbc.Button("CFS",      id="btn-cfs",      n_clicks=0, size="sm", outline=True, color="info"),
                    dbc.Button("DWARR",    id="btn-dwarr",    n_clicks=0, size="sm", outline=True, color="info")
                ], className="d-flex flex-wrap gap-1"),
                html.Div(id="btn-warning", style={"color": "#f87171", "fontSize": "11px", "marginTop": "6px"}),
            ])
        ]),

        # Right panel: results
        dbc.Col(width=7, children=[
            html.Div(id="results-area", style={"color": COLORS["text"]}),
        ])
    ]),

    # Hidden store for processes data
    dcc.Store(id="store-processes")
])


@app.callback(
    Output("proc-inputs", "children"),
    Input("num-procs", "value")
)
def render_proc_rows(n):
    if not n:
        return []
    return [make_process_row(i) for i in range(int(n))]


@app.callback(
    Output("store-processes", "data"),
    Input({"type": "pid",      "index": ALL}, "value"),
    Input({"type": "arrival",  "index": ALL}, "value"),
    Input({"type": "burst",    "index": ALL}, "value"),
    Input({"type": "priority", "index": ALL}, "value"),
    Input({"type": "deadline", "index": ALL}, "value")
)
def store_processes(pids, arrivals, bursts, priorities, deadlines):
    procs = []
    for i, burst in enumerate(bursts):
        if burst is None:
            continue
        procs.append({
            "id":       (pids[i] or f"P{i+1}").strip(),
            "arrival":  int(arrivals[i]) if arrivals[i] is not None else 0,
            "burst":    int(burst),
            "priority": int(priorities[i]) if priorities[i] is not None else None,
            "deadline": int(deadlines[i]) if deadlines[i] is not None else None,
        })
    return procs


@app.callback(
    Output("results-area", "children"),
    Output("btn-warning", "children"),
    Input("btn-fifo",     "n_clicks"),
    Input("btn-sjf",      "n_clicks"),
    Input("btn-rr",       "n_clicks"),
    Input("btn-priority", "n_clicks"),
    Input("btn-edf",      "n_clicks"),
    Input("btn-cfs",      "n_clicks"),
    Input("btn-dwarr",    "n_clicks"),
    State("store-processes", "data"),
    State("quantum",  "value"),
    State("overhead", "value"),
    prevent_initial_call=True,
)
def run_algorithm(n_fifo, n_sjf, n_rr, n_pri, n_edf, n_cfs, n_dwarr, processes, quantum, overhead):
    triggered = ctx.triggered_id
    if not processes:
        return html.P("Fill in at least the burst time for each process.", style={"color": COLORS["muted"]}), ""

    quantum  = int(quantum)  if quantum  is not None else 2
    overhead = int(overhead) if overhead is not None else 0

    # Validation
    warning = ""
    if triggered == "btn-priority":
        if any(p["priority"] is None for p in processes):
            return dash.no_update, "All processes need a priority value to use Priority Scheduling."
    if triggered == "btn-edf":
        if any(p["deadline"] is None for p in processes):
            return dash.no_update, "All processes need a deadline to use EDF."
    if triggered == "btn-cfs":
        if any(p["priority"] is None for p in processes):
            return dash.no_update, "All processes need a priority value to use CFS."
    if triggered == "btn-dwarr":
        if any(p["deadline"] is None for p in processes):
            return dash.no_update, "All processes need a deadline to use DWARR."

    # Run selected algorithm
    algorithm_label = {
        "btn-fifo":     "FIFO (Non-preemptive)",
        "btn-sjf":      "SJF (Non-preemptive)",
        "btn-rr":       "Round-Robin (Preemptive)",
        "btn-priority": "Priority (Preemptive)",
        "btn-edf":      "EDF (Preemptive)",
        "btn-cfs":      "CFS (Preemptive)",
        "btn-dwarr":    "DWARR (Preemptive)"
    }[triggered]

    if triggered == "btn-fifo":
        timeline = run_fifo(processes)
    elif triggered == "btn-sjf":
        timeline = run_sjf(processes)
    elif triggered == "btn-rr":
        timeline = run_round_robin(processes, quantum, overhead)
    elif triggered == "btn-priority":
        timeline = run_priority(processes, quantum, overhead)
    elif triggered == "btn-edf":
        timeline = run_edf(processes, quantum, overhead)
    elif triggered == "btn-cfs":
        timeline = run_cfs(processes, overhead)
    elif triggered == "btn-dwarr":
        timeline = run_dwarr(processes, overhead)
    else:
        return dash.no_update, ""

    metrics = compute_metrics(processes, timeline)
    gantt   = build_gantt(processes, timeline, metrics)
    avg_tat = sum(m["turnaround"] for m in metrics) / len(metrics) if metrics else 0

    # Metrics table
    col_style  = {"padding": "6px 10px", "borderBottom": f"1px solid {COLORS['border']}"}
    head_style = {**col_style, "color": COLORS["accent"], "fontSize": "11px", "textTransform": "uppercase"}

    header = html.Tr(
        [html.Th(c, style=head_style)
        for c in ["ID","Arrival","Burst","Deadline","Priority","Start","Finish","Waiting","Turnaround","Deadline OK?"]]
    )

    rows = []
    for m in metrics:
        dl_color = ("#4ade80" if m["deadline_ok"] == "✓"
                    else "#f87171" if m["deadline_ok"] == "✗"
                    else COLORS["text"])
        rows.append(html.Tr([
            html.Td(m["id"],          style=col_style),
            html.Td(m["arrival"],     style=col_style),
            html.Td(m["burst"],       style=col_style),
            html.Td(m["deadline"],    style=col_style),
            html.Td(m["priority"],    style=col_style),
            html.Td(m["start"],       style=col_style),
            html.Td(m["finish"],      style=col_style),
            html.Td(m["waiting"],     style=col_style),
            html.Td(m["turnaround"],  style=col_style),
            html.Td(m["deadline_ok"], style={**col_style, "color": dl_color, "fontWeight": "700"}),
        ]))

    table = html.Table(
        [html.Thead(header), html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse", "fontSize": "12px"},
    )

    content = html.Div([
        html.P(algorithm_label, style={**HEADER_STYLE, "marginBottom": "8px", "fontSize": "14px"}),

        # Gantt
        html.Div(style=CARD_STYLE, children=[
            html.P("Gantt Chart", style=LABEL_STYLE),
            dcc.Graph(figure=gantt, config={"displayModeBar": False}),
        ]),

        # Table
        html.Div(style=CARD_STYLE, children=[
            html.P("Results Table", style=LABEL_STYLE),
            html.Div(table, style={"overflowX": "auto"}),
        ]),

        # Average turnaround
        html.Div(style={**CARD_STYLE, "textAlign": "center"}, children=[
            html.Span("Average Turnaround: ", style={"color": COLORS["muted"]}),
            html.Span(f"{avg_tat:.2f}", style={"color": COLORS["accent"], "fontSize": "22px", "fontWeight": "700"}),
        ]),
    ])

    return content, warning


if __name__ == "__main__":
    app.run(debug=True)
