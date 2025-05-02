from typing import List, Dict
import webbrowser
from threading import Timer
import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

def launch_board(tasks: List[Dict]):
    """
    Launch a Dash web app with a Trello-like board showing all tasks grouped by status.
    """
    try:
        import dash
        from dash import html
        import dash_bootstrap_components as dbc
    except ImportError:
        print("[red]Dash is not installed. Please run 'uv pip install dash dash-bootstrap-components'.[/red]")
        return

    status_columns = [
        ("Pending", "cyan"),
        ("Doing", "orange"),
        ("Completed", "green"),
        ("Cancelled", "yellow"),
    ]
    def get_status(task):
        if task.get("completed"):
            return "Completed"
        elif task.get("status") == "cancelled":
            return "Cancelled"
        elif task.get("status") == "doing":
            return "Doing"
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
        elif task.get("status") == "doing":
            status_label = "Doing"
            status_color = "info"
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

    # --- Side Navigation ---
    SIDEBAR_STYLE = {
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "220px",
        "padding": "2rem 1rem 1rem 1rem",
        "background": "#2b6cb0",
        "color": "#fff",
        "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif",
        "boxShadow": "2px 0 8px rgba(44,62,80,0.07)",
        "zIndex": 1000
    }
    sidebar = html.Div([
        html.H3("Project", className="mb-4", style={"fontWeight": 700, "fontSize": "1.3rem", "color": "#fff"}),
        dbc.Nav([
            dbc.NavLink("Board", href="/", active="exact", style={"color": "#fff", "fontWeight": 500, "fontSize": "1.1rem"}),
            dbc.NavLink("Statistics", href="/statistics", active="exact", style={"color": "#fff", "fontWeight": 500, "fontSize": "1.1rem"}),
        ], vertical=True, pills=True),
    ], style=SIDEBAR_STYLE)

    # --- Main Content Layouts ---
    def layout_board():
        header_styles = {
            "Pending": {
                "background": "linear-gradient(90deg, #6dd5ed 0%, #2193b0 100%)",
                "color": "#fff",
                "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif",
                "fontWeight": 800,
                "fontSize": "1.35rem",
                "letterSpacing": "0.04em",
                "borderRadius": "0.7rem 0.7rem 0 0",
                "boxShadow": "0 2px 12px rgba(33,147,176,0.07)",
                "padding": "0.85rem 0.5rem",
                "textAlign": "center",
                "marginBottom": "1.2rem",
                "textShadow": "0 1px 4px rgba(33,147,176,0.10)"
            },
            "Doing": {
                "background": "linear-gradient(90deg, #ffb347 0%, #ffcc33 100%)",
                "color": "#fff",
                "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif",
                "fontWeight": 800,
                "fontSize": "1.35rem",
                "letterSpacing": "0.04em",
                "borderRadius": "0.7rem 0.7rem 0 0",
                "boxShadow": "0 2px 12px rgba(255,204,51,0.07)",
                "padding": "0.85rem 0.5rem",
                "textAlign": "center",
                "marginBottom": "1.2rem",
                "textShadow": "0 1px 4px rgba(255,204,51,0.10)"
            },
            "Completed": {
                "background": "linear-gradient(90deg, #43e97b 0%, #38f9d7 100%)",
                "color": "#fff",
                "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif",
                "fontWeight": 800,
                "fontSize": "1.35rem",
                "letterSpacing": "0.04em",
                "borderRadius": "0.7rem 0.7rem 0 0",
                "boxShadow": "0 2px 12px rgba(56,249,215,0.07)",
                "padding": "0.85rem 0.5rem",
                "textAlign": "center",
                "marginBottom": "1.2rem",
                "textShadow": "0 1px 4px rgba(56,249,215,0.10)"
            },
            "Cancelled": {
                "background": "linear-gradient(90deg, #f7971e 0%, #ffd200 100%)",
                "color": "#fff",
                "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif",
                "fontWeight": 800,
                "fontSize": "1.35rem",
                "letterSpacing": "0.04em",
                "borderRadius": "0.7rem 0.7rem 0 0",
                "boxShadow": "0 2px 12px rgba(255,210,0,0.07)",
                "padding": "0.85rem 0.5rem",
                "textAlign": "center",
                "marginBottom": "1.2rem",
                "textShadow": "0 1px 4px rgba(255,210,0,0.10)"
            },
        }
        columns = {
            "Pending": [],
            "Doing": [],
            "Completed": [],
            "Cancelled": []
        }
        for task in tasks:
            status = task.get("status", "Pending").capitalize()
            if status not in columns:
                status = "Pending"
            columns[status].append(task)
        status_columns = [
            ("Pending", "#2193b0"),
            ("Doing", "#ffb347"),
            ("Completed", "#38f9d7"),
            ("Cancelled", "#ffd200")
        ]
        # Always show all four columns in one row, each with equal width
        return dbc.Container([
            html.H2("Flowistic Task Board", className="my-4 text-center", style={
                "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif",
                "fontWeight": 700,
                "color": "#2b6cb0",
                "letterSpacing": "0.05em"
            }),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div(status, style=header_styles[status]),
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
                ], width=3, style={"padding": "1rem"}) for status, color in status_columns
            ], className="gy-4"),
        ], fluid=True)

    def layout_statistics():
        # Compute statistics
        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t.get("completed"))
        pending = sum(1 for t in tasks if not t.get("completed") and t.get("status") != "cancelled")
        cancelled = sum(1 for t in tasks if t.get("status") == "cancelled")
        priorities = [t.get("priority", "medium") for t in tasks]
        types = [t.get("type", "task") for t in tasks]
        tags = [tag for t in tasks for tag in t.get("tags", [])]
        overdue = sum(1 for t in tasks if t.get("due_date") and not t.get("completed") and t.get("status") != "cancelled")
        # Timeline chart (creation and completion)
        df = pd.DataFrame(tasks)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["completed_at"] = pd.to_datetime(df.get("completed_at", None), errors="coerce") if "completed_at" in df.columns else pd.NaT
        # Creation timeline
        creation_timeline = df.groupby(df["created_at"].dt.date).size().reset_index(name="Created")
        # Completion timeline
        if "completed_at" in df.columns:
            completion_timeline = df.dropna(subset=["completed_at"]).groupby(df["completed_at"].dt.date).size().reset_index(name="Completed")
        else:
            completion_timeline = pd.DataFrame({"created_at": [], "Completed": []})
        # Merge for timeline chart
        timeline = pd.merge(creation_timeline, completion_timeline, left_on="created_at", right_on="completed_at", how="outer").fillna(0)
        timeline = timeline.rename(columns={"created_at": "Date"})
        # Timeline chart
        timeline_fig = px.line(timeline, x="Date", y=["Created", "Completed"], markers=True, title="Task Creation & Completion Timeline")
        # Status stats
        status_counts = {"Pending": pending, "Doing": sum(1 for t in tasks if t.get("status") == "doing"), "Completed": completed, "Cancelled": cancelled}
        # Priority chart
        priority_counts = {p: priorities.count(p) for p in set(priorities)}
        priority_fig = px.pie(
            names=list(priority_counts.keys()),
            values=list(priority_counts.values()),
            title="Tasks by Priority",
            color_discrete_sequence=px.colors.sequential.Blues
        )
        # Type chart
        type_counts = {tp: types.count(tp) for tp in set(types)}
        type_fig = px.pie(
            names=list(type_counts.keys()),
            values=list(type_counts.values()),
            title="Tasks by Type",
            color_discrete_sequence=px.colors.sequential.Teal
        )
        # Status bar chart
        status_fig = px.bar(
            x=list(status_counts.keys()),
            y=list(status_counts.values()),
            labels={"x": "Status", "y": "Count"},
            title="Task Status Overview",
            color=list(status_counts.keys()),
            color_discrete_map={"Pending": "#3182ce", "Doing": "#ffb347", "Completed": "#38a169", "Cancelled": "#ed8936"}
        )
        # Cards for quick stats
        stat_cards = dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Total Tasks", className="card-title mb-1", style={"fontWeight": 700}),
                    html.H2(total_tasks, className="card-text", style={"color": "#2b6cb0", "fontWeight": 700}),
                ])
            ], style={"boxShadow": "0 2px 8px rgba(44,62,80,0.08)", "borderRadius": "0.7rem"}), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Completed", className="card-title mb-1", style={"fontWeight": 700}),
                    html.H2(completed, className="card-text", style={"color": "#38a169", "fontWeight": 700}),
                ])
            ], style={"boxShadow": "0 2px 8px rgba(44,62,80,0.08)", "borderRadius": "0.7rem"}), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Pending", className="card-title mb-1", style={"fontWeight": 700}),
                    html.H2(pending, className="card-text", style={"color": "#3182ce", "fontWeight": 700}),
                ])
            ], style={"boxShadow": "0 2px 8px rgba(44,62,80,0.08)", "borderRadius": "0.7rem"}), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Doing", className="card-title mb-1", style={"fontWeight": 700}),
                    html.H2(sum(1 for t in tasks if t.get("status") == "doing"), className="card-text", style={"color": "#ffb347", "fontWeight": 700}),
                ])
            ], style={"boxShadow": "0 2px 8px rgba(44,62,80,0.08)", "borderRadius": "0.7rem"}), width=3),
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Cancelled", className="card-title mb-1", style={"fontWeight": 700}),
                    html.H2(cancelled, className="card-text", style={"color": "#ed8936", "fontWeight": 700}),
                ])
            ], style={"boxShadow": "0 2px 8px rgba(44,62,80,0.08)", "borderRadius": "0.7rem"}), width=3),
        ], className="mb-4")
        # Badges for extra stats
        extra_stats = html.Div([
            dbc.Badge(f"Overdue: {overdue}", color="danger", className="me-2", style={"fontSize": "1rem", "padding": "0.7em 1.2em"}),
            dbc.Badge(f"Tags: {len(set(tags))}", color="info", className="me-2", style={"fontSize": "1rem", "padding": "0.7em 1.2em"}),
        ], className="mb-4")
        # Layout
        return dbc.Container([
            html.H2("Project Statistics", className="my-4 text-center", style={
                "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif",
                "fontWeight": 700,
                "color": "#2b6cb0",
                "letterSpacing": "0.05em"
            }),
            stat_cards,
            extra_stats,
            dbc.Row([
                dbc.Col(dcc.Graph(figure=status_fig), width=6),
                dbc.Col(dcc.Graph(figure=priority_fig), width=3),
                dbc.Col(dcc.Graph(figure=type_fig), width=3),
            ], className="mb-4"),
            dbc.Row([
                dbc.Col(dcc.Graph(figure=timeline_fig), width=12)
            ]),
        ], fluid=True)

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, "https://fonts.googleapis.com/css?family=Montserrat:600,700|Segoe+UI:400,700&display=swap"])
    app.title = "Flowistic Task Board"
    app.layout = html.Div([
        dcc.Location(id="url"),
        sidebar,
        html.Div(id="page-content", style={"marginLeft": "240px", "padding": "2rem 2rem 2rem 2rem"})
    ])

    @app.callback(Output("page-content", "children"), [Input("url", "pathname")])
    def display_page(pathname):
        if pathname == "/statistics":
            return layout_statistics()
        return layout_board()

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050/")

    Timer(1, open_browser).start()
    app.run(debug=False)
