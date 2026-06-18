import plotly.graph_objects as go
from utils.style import COLORS


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


def build_gantt(processes, timeline, metrics, frame_duration=700):
    """
    Build an animated Plotly Gantt chart that advances time unit by time unit.
    The speed of the animation can be adjusted via 'frame_duration' (in milliseconds).

    Color rules:
        green  — process is running (within deadline)
        yellow — process is waiting (ready but not on CPU)
        red    — context-switch overhead
        gray   — process running after its deadline has passed
    """
    fig = go.Figure()
    pid_list = [p["id"] for p in processes]
    deadline_map = {p["id"]: p.get("deadline") for p in processes}
    bars = []
    # Transition duration is set to 80% of frame_duration to allow a brief pause at each new time unit
    transition_duration = int(frame_duration * 0.8)

    ## Waiting bars (yellow)
    # A process is "waiting" whenever it has arrived but is not running and not
    # in an overhead slot attributed to itself
    for m in metrics:
        pid = m["id"]
        arrival = m["arrival"]
        slices = sorted(
            [s for s in timeline if s["pid"] == pid and s["type"] == "running"],
            key=lambda s: s["start"]
        )
        # Collect time ranges that belong to this pid's overhead (the save phase)
        own_overhead = [
            (s["start"], s["end"]) for s in timeline
            if s["pid"] == pid and s["type"] == "overhead"
        ]

        def subtract_overhead(gap_start, gap_end):
            """
            Split a waiting gap by removing any overhead intervals that fall
            within it, so waiting bars are never drawn on top of overhead bars.
            Returns a list of (start, end) sub-gaps.
            """
            intervals = [(gap_start, gap_end)]
            for overhead_start, overhead_end in own_overhead:
                new = []
                for (s, e) in intervals:
                    if overhead_end <= s or overhead_start >= e:
                        new.append((s, e))  # no overlap
                    else:
                        if s < overhead_start:
                            new.append((s, overhead_start))
                        if overhead_end < e:
                            new.append((overhead_end, e))
                intervals = new
            return intervals
        
        def add_waiting(gap_start, gap_end, pid=pid):
            for waiting_start, waiting_end in subtract_overhead(gap_start, gap_end):
                if waiting_end > waiting_start:
                    bars.append({
                        "pid": pid, "start": waiting_start, "end": waiting_end,
                        "color": COLORS["waiting"],
                        "hover": f"<b>{pid}</b> waiting<br>{waiting_start:.3g} → {waiting_end:.3g}<extra></extra>"
                    })

        if slices and arrival < slices[0]["start"]:
            add_waiting(arrival, slices[0]["start"])
        for i in range(len(slices) - 1):
            add_waiting(slices[i]["end"], slices[i + 1]["start"])

    ## Running bars (green)
    for seg in timeline:
        if seg["type"] != "running":
            continue
        pid = seg["pid"]
        dl = deadline_map.get(pid)
        color = COLORS["deadline"] if (dl is not None and seg["start"] >= dl) else COLORS["running"]
        bars.append({
            "pid": pid, "start": seg["start"], "end": seg["end"],
            "color": color,
            "hover": f"<b>{pid}</b> running<br>{seg['start']:.3g} → {seg['end']:.3g}<extra></extra>"
        })

    ## Overhead bars (red): only on the row of the process being saved
    # Each overhead segment already carries the correct pid (set in algorithms.py)
    # We draw it at full opacity AFTER the waiting bars so it is never covered
    for seg in timeline:
        if seg["type"] != "overhead":
            continue
        bars.append({
            "pid": seg["pid"], "start": seg["start"], "end": seg["end"],
            "color": COLORS["overhead"],
            "hover": f"<b>{seg['pid']}</b> context switch<br>{seg['start']:.3g} → {seg['end']:.3g}<extra></extra>"
        })

    total_time = int(max((s["end"] for s in timeline), default=1))

    # Starts all bars with width 0 (state at t=0)
    for b in bars:
        fig.add_trace(go.Bar(
            x=[0], base=[b["start"]], y=[b["pid"]], orientation="h",
            marker_color=b["color"], marker_line_width=0,
            showlegend=False, hovertemplate=b["hover"]
        ))

    # Legend dummy traces
    anchor = pid_list[0] if pid_list else ""
    for name, color in [
        ("Running",                COLORS["running"]),
        ("Waiting",                COLORS["waiting"]),
        ("Overhead",               COLORS["overhead"]),
        ("Running after deadline", COLORS["deadline"]),
    ]:
        fig.add_trace(go.Bar(
            x=[0], y=[anchor], orientation="h", marker_color=color,
            name=name, showlegend=True, hoverinfo="skip"
        ))

    # Animation (frames t=0, t=1, t=2 ...)
    frames = []
    for t in range(total_time + 1):
        frame_data = []
        for b in bars:
            # width of the bar at time 't' cannot exceed its maximum size
            current_width = max(0, min(b["end"], t) - b["start"])
            frame_data.append(go.Bar(x=[current_width]))
        frames.append(go.Frame(data=frame_data, traces=list(range(len(bars))), name=str(t)))
    fig.frames = frames

    fig.update_layout(
        barmode="overlay",
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["card"],
        font=dict(color=COLORS["text"], family="monospace"),
        xaxis=dict(
            title="Time", showgrid=True, gridcolor=COLORS["border"],
            tickmode="linear", dtick=1, range=[0, total_time + 0.5],
        ),
        yaxis=dict(
            title="Process", categoryorder="array", categoryarray=list(reversed(pid_list)),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=60, r=20, t=40, b=95),
        height=max(320, 140 + 60 * len(pid_list)),

        # Play/Pause buttons
        updatemenus=[dict(
            type="buttons", direction="left", pad={"r": 10, "t": 10},
            showactive=False, x=0.0, xanchor="left", y=-0.22, yanchor="top",
            bgcolor=COLORS["card"], bordercolor=COLORS["border"], font=dict(color=COLORS["text"], size=12),
            buttons=[
                dict(
                    label="▶ Play", method="animate",
                    args=[None, {
                        "frame": {"duration": frame_duration, "redraw": False},
                        "fromcurrent": True, 
                        "transition": {"duration": transition_duration, "easing": "linear"},
                    }],
                ),
                dict(
                    label="⏸ Pause", method="animate",
                    args=[[None], {
                        "frame": {"duration": 0, "redraw": False},
                        "mode": "immediate",
                        "transition": {"duration": 0},
                    }],
                ),
            ]
        )],
        # Scrubber slider
        sliders=[dict(
            active=0, 
            pad={"b": 10, "t": 50}, x=0.0, xanchor="left", len=1.0, y=-0.13, yanchor="top",
            currentvalue=dict(
                font=dict(size=10, color=COLORS["muted"]),
                prefix="Time: ", visible=True, xanchor="center",
            ),
            tickcolor=COLORS["border"], font=dict(color=COLORS["muted"], size=7),
            bgcolor=COLORS["card"], bordercolor=COLORS["border"],
            transition=dict(duration=transition_duration),
            steps=[
                dict(
                    method="animate", label=str(t),
                    args=[[str(t)], {
                        "frame": {"duration": frame_duration, "redraw": False},
                        "mode": "immediate",
                        "transition": {"duration": transition_duration, "easing": "linear"},
                    }],
                )
                for t in range(total_time + 1)
            ],
        )],
    )
    return fig
