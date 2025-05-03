from typing import List, Dict
import webbrowser
from threading import Timer
import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from datetime import datetime

def launch_board(tasks: List[Dict]):
    """
    Launch a Dash web app with a Trello-like board showing all tasks grouped by status.
    """
    try:
        # Only catch ImportError for CLI fallback, not for main board rendering
        pass
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
        # Repeat info
        repeat = task.get("repeat")
        repeat_badge = None
        if repeat:
            repeat_badge = dbc.Badge(f"Repeats: {repeat}", color="info", pill=True, style={"fontSize": "0.85rem", "marginLeft": "0.5rem", "background": "#e6fffa", "color": "#234e52", "border": "1px solid #38b2ac"})
        # Next scheduled date (for repeatable tasks)
        next_due = None
        if repeat and task.get("due_date"):
            next_due = task["due_date"]
        # Repeat info row
        repeat_info_row = None
        if repeat:
            repeat_info_row = html.Div([
                html.Span("Next: ", style={"fontWeight": "bold", "color": "#319795"}),
                html.Span(next_due, style={"color": "#234e52", "fontWeight": 500})
            ], className="mb-1", style={"fontSize": "0.92rem"})
        # Tags as badges
        tags = task.get("tags", [])
        tag_badges = [dbc.Badge(tag, color="secondary", className="me-1", pill=True, style={"fontSize": "0.85rem", "background": "#e3e8f0", "color": "#4a5568"}) for tag in tags]
        # --- View Details Link ---
        details_link = dcc.Link(
            'View Details', 
            href=f"/task/{task['task_id']}", 
            style={"fontSize": "0.92rem", "fontWeight": 500, "color": "#3182ce", "textDecoration": "underline", "marginTop": "0.5rem", "display": "inline-block"}
        )
        return dbc.Card([
            dbc.CardHeader([
                html.Span(task["title"], style={"fontWeight": "bold", "fontSize": "1.15rem", "fontFamily": "'Montserrat', 'Segoe UI', Arial, sans-serif", "color": "#2d3748"}),
                dbc.Badge(status_label, color=status_color, className="ms-2", pill=True, style={"fontSize": "0.9rem"}),
                repeat_badge if repeat_badge else None
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
                repeat_info_row if repeat_info_row else None,
                html.Div(tag_badges, className="mb-1"),
                details_link
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
    def layout_board(filtered_tasks=None):
        # Use filtered_tasks if provided, else use all tasks
        current_tasks = filtered_tasks if filtered_tasks is not None else tasks
        columns = {s: [] for s, _ in status_columns}
        for task in current_tasks:
            columns[get_status(task)].append(task)
        # Filter toggle for repeatable tasks
        filter_repeat = dcc.Checklist(
            options=[{"label": "Show only repeatable tasks", "value": "repeatable"}],
            value=[],
            id="repeat-filter",
            style={"marginBottom": "1.2rem", "fontWeight": 500, "fontSize": "1.05rem"}
        )
        # Board columns
        board_columns = []
        for status, color in status_columns:
            filtered = columns[status]
            board_columns.append(
                dbc.Col([
                    html.H4(status, style={"color": color, "fontWeight": 700, "marginBottom": "1rem"}),
                    *[make_card(task) for task in filtered]
                ], width=3, style={"minWidth": "320px"})
            )
        # Dashboard summary for repeatable tasks
        repeatable_count = sum(1 for t in current_tasks if t.get("repeat"))
        overdue_repeat_count = sum(1 for t in current_tasks if t.get("repeat") and t.get("due_date") and t["due_date"] < datetime.now().isoformat())
        dashboard = dbc.Card([
            dbc.CardBody([
                html.H5("Repeatable Tasks", className="card-title mb-1", style={"fontWeight": 700}),
                html.Div([
                    dbc.Badge(f"Total: {repeatable_count}", color="info", className="me-2", style={"fontSize": "1rem", "padding": "0.7em 1.2em"}),
                    dbc.Badge(f"Overdue: {overdue_repeat_count}", color="danger" if overdue_repeat_count else "secondary", className="me-2", style={"fontSize": "1rem", "padding": "0.7em 1.2em"})
                ])
            ])
        ], style={"boxShadow": "0 2px 8px rgba(44,62,80,0.08)", "borderRadius": "0.7rem", "marginBottom": "1.2rem"})
        return dbc.Container([
            dashboard,
            filter_repeat,
            dbc.Row(board_columns, className="g-4 flex-nowrap", style={"overflowX": "auto"})
        ], fluid=True)

    def layout_task_details(task_id):
        # Find the task by id
        task = next((t for t in tasks if str(t['task_id']) == str(task_id)), None)
        if not task:
            return dbc.Container([
                html.Div([
                    html.H3("Task not found", style={"color": "#e53e3e", "fontWeight": 700, "marginBottom": "1.5rem"}),
                    dcc.Link("← Back to Board", href="/", style={"color": "#3182ce", "fontWeight": 500, "marginTop": "1.5rem", "display": "inline-block"})
                ], style={"textAlign": "center", "padding": "3rem 0"})
            ], style={"maxWidth": "600px", "margin": "0 auto"})

        from datetime import datetime
        import dateutil.parser
        def format_duration(minutes):
            if not minutes:
                return "0m"
            hours, mins = divmod(minutes, 60)
            return f"{hours}h {mins}m" if hours else f"{mins}m"
        sessions = task.get('work_sessions', [])
        total_time = sum(s.get('duration', 0) for s in sessions)
        completed_sessions = sum(1 for s in sessions if not s.get('interrupted'))
        interrupted_sessions = sum(1 for s in sessions if s.get('interrupted'))
        created_at = task.get('created_at')
        if created_at:
            created_at = dateutil.parser.parse(created_at)
            created_str = created_at.strftime('%Y-%m-%d %H:%M')
        else:
            created_str = "-"
        notes = task.get('notes', [])
        # Badge styles
        type_colors = {
            "task": "primary",
            "bug": "danger",
            "feature": "success",
            "chore": "secondary",
        }
        type_color = type_colors.get(task.get("type", "task"), "primary")
        priority_color = {
            "high": "danger",
            "medium": "warning",
            "low": "success",
        }.get(task.get("priority", "medium"), "secondary")
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
        tag_badges = [dbc.Badge(tag, color="secondary", className="me-1", pill=True, style={"fontSize": "0.85rem", "background": "#e3e8f0", "color": "#4a5568"}) for tag in task.get('tags', [])]
        # Main Card
        rows = [
            html.Tr([html.Th("Task ID"), html.Td(task["task_id"])]),
            html.Tr([html.Th("Title"), html.Td(task["title"])]),
            html.Tr([html.Th("Type"), html.Td(task["type"])]),
            html.Tr([html.Th("Priority"), html.Td(task["priority"])]),
            html.Tr([html.Th("Status"), html.Td(task["status"])]),
            html.Tr([html.Th("Due Date"), html.Td(task["due_date"] if task.get("due_date") else "-")]),
        ]
        # Add repeat row if present
        if task.get("repeat"):
            rows.append(html.Tr([html.Th("Repeat"), html.Td(task["repeat"])]))
            # Show next scheduled date
            if task.get("due_date"):
                rows.append(html.Tr([html.Th("Next Due"), html.Td(task["due_date"])]))
        return dbc.Container([
            dcc.Link("← Back to Board", href="/", style={"color": "#3182ce", "fontWeight": 500, "marginBottom": "1.5rem", "display": "inline-block"}),
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        html.Span(f"Task {task['task_id']}: ", style={"fontWeight": 700, "fontSize": "1.2rem", "color": "#2d3748"}),
                        html.Span(task['title'], style={"fontWeight": 600, "fontSize": "1.1rem", "color": "#2d3748"}),
                        dbc.Badge(status_label, color=status_color, className="ms-2", pill=True, style={"fontSize": "0.9rem"})
                    ], className="d-flex align-items-center justify-content-between"),
                ], style={"background": "#f7fafc", "borderBottom": "1px solid #e2e8f0", "padding": "1rem 1.5rem"}),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H5("Details", style={"fontWeight": 600, "marginBottom": "1rem", "color": "#2b6cb0"}),
                            html.Table([
                                html.Thead([html.Tr([html.Th(col) for col in ["Attribute", "Value"]])]),
                                html.Tbody(rows)
                            ], style={"fontSize": "1rem", "borderCollapse": "collapse", "width": "100%"}),
                        ], width=6),
                        dbc.Col([
                            html.H5("Work Sessions", style={"fontWeight": 600, "marginBottom": "1rem", "color": "#38a169"}),
                            html.Ul([
                                html.Li([html.Span("Total Time Worked: ", style={"fontWeight": 500}), html.Span(format_duration(total_time), style={"color": "#555"})]),
                                html.Li([html.Span("Completed Sessions: ", style={"fontWeight": 500}), html.Span(str(completed_sessions), style={"color": "#555"})]),
                                html.Li([html.Span("Interrupted Sessions: ", style={"fontWeight": 500}), html.Span(str(interrupted_sessions), style={"color": "#555"})]),
                            ], style={"fontSize": "1rem", "listStyle": "none", "paddingLeft": 0}),
                        ], width=6)
                    ], className="mb-4"),
                    html.Hr(),
                    html.H5("Notes", style={"fontWeight": 600, "color": "#805ad5", "marginBottom": "1rem"}),
                    dbc.Alert("No notes yet.", color="secondary", className="mb-3", style={"fontSize": "1rem", "background": "#f7fafc", "color": "#555"}) if not notes else html.Ul([
                        html.Li(note, style={"fontSize": "1rem", "marginBottom": "0.7rem", "color": "#333"}) for note in notes
                    ], style={"paddingLeft": "1.2rem"}),
                ], style={"padding": "2rem 2rem 1.5rem 2rem"})
            ], style={
                "maxWidth": "700px",
                "margin": "0 auto 2.5rem auto",
                "boxShadow": "0 6px 24px rgba(44,62,80,0.13)",
                "borderRadius": "1.1rem",
                "border": "1px solid #e2e8f0",
                "background": "#fff"
            }),
            dcc.Link("← Back to Board", href="/", style={"color": "#3182ce", "fontWeight": 500, "marginTop": "1.5rem", "display": "inline-block"})
        ], style={"padding": "2.5rem 0"})

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

    app = dash.Dash(
        __name__, 
        external_stylesheets=[
            dbc.themes.BOOTSTRAP, 
            "https://fonts.googleapis.com/css?family=Montserrat:600,700|Segoe+UI:400,700&display=swap"
            ],
        suppress_callback_exceptions=True
        )
    app.title = "Flowistic Task Board"
    app.layout = html.Div([
        dcc.Location(id="url"),
        sidebar,
        # Hidden checklist to satisfy Dash callback system
        dcc.Checklist(
            options=[{"label": "Show only repeatable tasks", "value": "repeatable"}],
            value=[],
            id="repeat-filter",
            style={"display": "none"}
        ),
        html.Div(id="page-content", style={"marginLeft": "240px", "padding": "2rem 2rem 2rem 2rem"})
    ])

    # Add callback for filtering
    @app.callback(
        Output("page-content", "children"),
        [Input("url", "pathname")],
        [State("repeat-filter", "value")]
    )
    def display_page(pathname, repeat_filter):
        import re
        match = re.match(r"/task/(.+)", pathname or "")
        if match:
            task_id = match.group(1)
            return layout_task_details(task_id)
        if pathname == "/statistics":
            return layout_statistics()
        # Filter tasks if checklist is checked
        filtered_tasks = tasks
        if repeat_filter and "repeatable" in repeat_filter:
            filtered_tasks = [t for t in tasks if t.get("repeat")]
        return layout_board(filtered_tasks=filtered_tasks)

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050/")

    Timer(1, open_browser).start()
    app.run(debug=False)
