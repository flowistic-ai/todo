from typing import List, Dict

def launch_board(tasks: List[Dict]):
    """
    Launch a Dash web app with a Trello-like board showing all tasks grouped by status.
    """
    import webbrowser
    from threading import Timer
    try:
        import dash
        from dash import html
        import dash_bootstrap_components as dbc
    except ImportError:
        print("[red]Dash is not installed. Please run 'uv pip install dash dash-bootstrap-components'.[/red]")
        return

    status_columns = [
        ("Pending", "cyan"),
        ("Completed", "green"),
        ("Cancelled", "yellow"),
    ]
    def get_status(task):
        if task.get("completed"):
            return "Completed"
        elif task.get("status") == "cancelled":
            return "Cancelled"
        else:
            return "Pending"
    columns = {s: [] for s, _ in status_columns}
    for task in tasks:
        columns[get_status(task)].append(task)

    def make_card(task):
        # Color for type
        type_colors = {
            "task": "primary",
            "bug": "danger",
            "feature": "success",
            "chore": "secondary",
        }
        type_color = type_colors.get(task.get("type", "task"), "primary")
        # Priority badge
        priority_color = {
            "high": "danger",
            "medium": "warning",
            "low": "success",
        }.get(task.get("priority", "medium"), "secondary")
        # Status badge
        if task.get("completed"):
            status_label = "Completed"
            status_color = "success"
        elif task.get("status") == "cancelled":
            status_label = "Cancelled"
            status_color = "warning"
        else:
            status_label = "Pending"
            status_color = "info"
        # Tags as badges
        tags = task.get("tags", [])
        tag_badges = [dbc.Badge(tag, color="secondary", className="me-1", pill=True, style={"fontSize": "0.85rem", "background": "#e3e8f0", "color": "#4a5568"}) for tag in tags]
        return dbc.Card([
            dbc.CardHeader([
                html.Span(task["title"], style={"fontWeight": "bold", "fontSize": "1.15rem", "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif", "color": "#2d3748"}),
                dbc.Badge(status_label, color=status_color, className="ms-2", pill=True, style={"fontSize": "0.9rem"})
            ], className="d-flex justify-content-between align-items-center", style={"background": "#f1f5f9", "borderBottom": "1px solid #e2e8f0"}),
            dbc.CardBody([
                html.Div([
                    html.Span("ID: ", style={"fontWeight": "bold", "color": "#718096", "fontFamily": "monospace"}), task["task_id"]
                ], className="mb-1 text-muted", style={"fontSize": "0.95rem"}),
                html.Div([
                    dbc.Badge(task["type"], color=type_color, className="me-2", pill=True, style={"fontSize": "0.85rem"}),
                    dbc.Badge(task["priority"].capitalize(), color=priority_color, pill=True, style={"fontSize": "0.85rem"}),
                ], className="mb-2"),
                html.Div([
                    html.Span("Due: ", style={"fontWeight": "bold", "color": "#3182ce"}),
                    task["due_date"] if task.get("due_date") else "-"
                ], className="mb-2", style={"fontSize": "0.95rem"}),
                html.Div(tag_badges, className="mb-1"),
            ], style={"fontFamily": "'Segoe UI', Arial, sans-serif"})
        ], style={
            "marginBottom": "1.2rem",
            "boxShadow": "0 4px 16px rgba(56, 161, 105, 0.07)",
            "borderRadius": "0.7rem",
            "border": "1px solid #e2e8f0",
            "background": "#fff"
        })

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, "https://fonts.googleapis.com/css?family=Montserrat:600,700|Segoe+UI:400,700&display=swap"])
    app.title = "Flowistic Task Board"
    app.layout = dbc.Container([
        html.H2("Flowistic Task Board", className="my-4 text-center", style={
            "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif",
            "fontWeight": 700,
            "color": "#2b6cb0",
            "letterSpacing": "0.05em"
        }),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4(status, style={
                        "color": color,
                        "fontWeight": "bold",
                        "textAlign": "center",
                        "marginBottom": "1.2rem",
                        "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif",
                        "fontSize": "1.25rem",
                        "letterSpacing": "0.04em",
                        "textShadow": "0 2px 6px rgba(44, 62, 80, 0.05)"
                    }),
                    html.Div([
                        make_card(task) for task in columns[status]
                    ], style={
                        "maxHeight": "70vh",
                        "overflowY": "auto",
                        "padding": "0 0.5rem"
                    })
                ], style={
                    "background": "linear-gradient(135deg, #f8fafc 60%, #e3e8f0 100%)",
                    "borderRadius": "0.85rem",
                    "padding": "1.2rem 0.7rem",
                    "boxShadow": "0 4px 20px rgba(44, 62, 80, 0.07)",
                    "minHeight": "82vh",
                    "border": "1px solid #e2e8f0"
                })
            ], width=4, style={"padding": "1rem"}) for status, color in status_columns
        ], className="gy-4"),
    ], fluid=True)

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050/")

    Timer(1, open_browser).start()
    app.run(debug=False)
