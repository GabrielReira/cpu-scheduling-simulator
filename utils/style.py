COLORS = {
    "running":   "#4ade80",
    "overhead":  "#ff5555",
    "deadline":  "#6b7280",
    "waiting":   "#feec23",
    "bg":        "#0f172a",
    "card":      "#1e293b",
    "border":    "#334155",
    "text":      "#f1f5f9",
    "muted":     "#94a3b8",
    "accent":    "#38bdf8",
}

PROCESS_COLORS = [
    "#38bdf8", "#818cf8", "#fb923c", "#a78bfa",
    "#34d399", "#f472b6", "#facc15", "#60a5fa",
]

CARD_STYLE = {
    "background": COLORS["card"],
    "border": f"1px solid {COLORS['border']}",
    "borderRadius": "8px",
    "padding": "16px",
    "marginBottom": "16px",
}

LABEL_STYLE = {"color": COLORS["muted"], "fontSize": "11px", "marginBottom": "4px", "textTransform": "uppercase", "letterSpacing": "0.05em"}
HEADER_STYLE = {"color": COLORS["accent"], "fontFamily": "monospace", "fontWeight": "700"}
