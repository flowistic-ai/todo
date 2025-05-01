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
        tag_badges = [dbc.Badge(tag, color="secondary", className="me-1", pill=True) for tag in tags]
        return dbc.Card([
            dbc.CardHeader([
                html.Span(task["title"], style={"fontWeight": "bold", "fontSize": "1.1rem"}),
                dbc.Badge(status_label, color=status_color, className="ms-2", pill=True)
            ], className="d-flex justify-content-between align-items-center"),
            dbc.CardBody([
                html.Div([
                    html.Span("ID: ", style={"fontWeight": "bold"}), task["task_id"]
                ], className="mb-1 text-muted"),
                html.Div([
                    dbc.Badge(task["type"], color=type_color, className="me-2", pill=True),
                    dbc.Badge(task["priority"].capitalize(), color=priority_color, pill=True),
                ], className="mb-2"),
                html.Div([
                    html.Span("Due: ", style={"fontWeight": "bold"}),
                    task["due_date"] if task.get("due_date") else "-"
                ], className="mb-2"),
                html.Div(tag_badges, className="mb-1"),
            ])
        ], style={"marginBottom": "1rem", "boxShadow": "0 2px 8px rgba(0,0,0,0.08)", "borderRadius": "0.5rem"})

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = "Flowistic Task Board"
    app.layout = dbc.Container([
        html.H2("Flowistic Task Board"),
        dbc.Row([
            dbc.Col([
                html.H4(status, style={"color": color}),
                *[make_card(task) for task in columns[status]]
            ], width=4) for status, color in status_columns
        ])
    ], fluid=True)

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050/")

    Timer(1, open_browser).start()
    app.run(debug=False)
