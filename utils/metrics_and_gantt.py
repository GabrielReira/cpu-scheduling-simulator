import plotly.graph_objects as go
from utils.style import COLORS, PROCESS_COLORS


def compute_metrics(processes, timeline):
    """
    Compute per-process: start, finish, waiting, turnaround, deadline_ok.
      start      = first moment the process actually runs.
      finish     = last moment the process finishes running.
      waiting    = turnaround - burst  (time spent NOT on CPU, excluding overhead).
      turnaround = finish - arrival.
    """
    results = []
    for p in processes:
        pid = p["id"]
        slices = [s for s in timeline if s["pid"] == pid and s["type"] == "running"]
        if not slices:
            continue
        start      = min(s["start"] for s in slices)
        finish     = max(s["end"]   for s in slices)
        turnaround = finish - p["arrival"]
        waiting    = turnaround - p["burst"]
        deadline_ok = "—"
        if p.get("deadline") is not None:
            deadline_ok = "✓" if finish <= p["deadline"] else "✗"
        results.append({
            "id":          pid,
            "arrival":     p["arrival"],
            "burst":       p["burst"],
            "deadline":    p.get("deadline", "—"),
            "priority":    p.get("priority", "—"),
            "start":       start,
            "finish":      finish,
            "waiting":     waiting,
            "turnaround":  turnaround,
            "deadline_ok": deadline_ok,
        })
    return results


def build_gantt(processes, timeline, metrics):
    """
    Build a Plotly Gantt chart.

    Color rules:
      green  — process is running (within deadline)
      yellow — process is waiting (ready but not on CPU)
      red    — context-switch overhead (shown only on the row of the saved process)
      gray   — process running after its deadline has passed

    Overhead segments in the timeline carry the pid of the process being saved,
    so they are drawn exclusively on that process's row (no cross-row overlay).
    Overhead bars are drawn AFTER waiting bars and set to full opacity so they
    are never hidden behind yellow segments.
    """
    pid_list = [p["id"] for p in processes]
    fig = go.Figure()

    ## Waiting bars (yellow)
    # A process is "waiting" whenever it has arrived but is not running and not
    # in an overhead slot attributed to itself.
    for m in metrics:
        pid     = m["id"]
        arrival = m["arrival"]
        slices  = sorted(
            [s for s in timeline if s["pid"] == pid and s["type"] == "running"],
            key=lambda s: s["start"],
        )
        # Collect time ranges that belong to this pid's overhead (the save phase)
        own_overhead = [
            (s["start"], s["end"])
            for s in timeline
            if s["pid"] == pid and s["type"] == "overhead"
        ]

        def _subtract_overhead(gap_start, gap_end):
            """
            Split a waiting gap by removing any overhead intervals that fall
            within it, so waiting bars are never drawn on top of overhead bars.
            Returns a list of (start, end) sub-gaps.
            """
            intervals = [(gap_start, gap_end)]
            for oh_start, oh_end in own_overhead:
                new_intervals = []
                for (s, e) in intervals:
                    if oh_end <= s or oh_start >= e:
                        new_intervals.append((s, e))  # no overlap
                    else:
                        if s < oh_start:
                            new_intervals.append((s, oh_start))
                        if oh_end < e:
                            new_intervals.append((oh_end, e))
                intervals = new_intervals
            return intervals

        def _add_waiting(gap_start, gap_end):
            for ws, we in _subtract_overhead(gap_start, gap_end):
                if we > ws:
                    fig.add_trace(go.Bar(
                        x=[we - ws], base=[ws],
                        y=[pid], orientation="h",
                        marker_color=COLORS["waiting"], marker_line_width=0,
                        name="Waiting", showlegend=False,
                        hovertemplate=f"<b>{pid}</b> waiting<br>{ws} → {we}<extra></extra>",
                    ))

        # gap from arrival to first execution
        if slices and arrival < slices[0]["start"]:
            _add_waiting(arrival, slices[0]["start"])

        # gaps between consecutive execution slices
        for i in range(len(slices) - 1):
            _add_waiting(slices[i]["end"], slices[i + 1]["start"])

    ## Running bars (green or gray if past deadline)
    deadline_map = {p["id"]: p.get("deadline") for p in processes}

    for seg in timeline:
        if seg["type"] != "running":
            continue
        pid   = seg["pid"]
        dl    = deadline_map.get(pid)
        color = COLORS["running"]
        if dl is not None and seg["start"] >= dl:
            color = COLORS["deadline"]
        fig.add_trace(go.Bar(
            x=[seg["end"] - seg["start"]], base=[seg["start"]],
            y=[pid], orientation="h",
            marker_color=color, marker_line_width=0,
            name="Running", showlegend=False,
            hovertemplate=f"<b>{pid}</b> running<br>{seg['start']} → {seg['end']}<extra></extra>",
        ))

    ## Overhead bars (red): only on the row of the process being saved
    # Each overhead segment already carries the correct pid (set in algorithms.py).
    # We draw it at full opacity AFTER the waiting bars so it is never covered.
    for seg in timeline:
        if seg["type"] != "overhead":
            continue
        pid = seg["pid"]   # the process whose state is being saved
        fig.add_trace(go.Bar(
            x=[seg["end"] - seg["start"]], base=[seg["start"]],
            y=[pid], orientation="h",
            marker_color=COLORS["overhead"], marker_line_width=0,
            opacity=1.0,
            name="Overhead", showlegend=False,
            hovertemplate=f"<b>{pid}</b> context switch<br>{seg['start']} → {seg['end']}<extra></extra>",
        ))

    # Legend dummy traces
    anchor = pid_list[0] if pid_list else ""
    for name, color in [
        ("Running",              COLORS["running"]),
        ("Waiting",              COLORS["waiting"]),
        ("Overhead (save)",      COLORS["overhead"]),
        ("Running after DL",     COLORS["deadline"]),
    ]:
        fig.add_trace(go.Bar(
            x=[0], y=[anchor], orientation="h",
            marker_color=color, name=name, showlegend=True,
            hoverinfo="skip",
        ))

    total_time = max((s["end"] for s in timeline), default=1)

    fig.update_layout(
        barmode="overlay",
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["card"],
        font=dict(color=COLORS["text"], family="monospace"),
        xaxis=dict(
            title="Time",
            showgrid=True, gridcolor=COLORS["border"],
            tickmode="linear", dtick=1,
            range=[0, total_time + 0.5],
        ),
        yaxis=dict(
            title="Process",
            categoryorder="array",
            categoryarray=list(reversed(pid_list)),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=60, r=20, t=40, b=40),
        height=max(250, 80 + 60 * len(pid_list)),
    )

    return fig
