import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import os

# --- Load Data ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "naijastock.db")
conn = sqlite3.connect(DB_PATH)

try:
    stock_df = pd.read_sql("SELECT * FROM stock_data", conn)
    signal_df = pd.read_sql("SELECT * FROM weekly_signals", conn)
except Exception:
    stock_df = pd.DataFrame()
    signal_df = pd.DataFrame()

conn.close()

stock_df['date'] = pd.to_datetime(stock_df['date'], errors='coerce')
signal_df['date'] = pd.to_datetime(signal_df['date'], errors='coerce')
if 'company_name' not in stock_df.columns:
    stock_df['company_name'] = stock_df['ticker']

# --- App Init ---
app = dash.Dash(__name__)
app.title = "NaijaStock Insight"

companies = sorted(stock_df['company_name'].dropna().unique())

# --- App Layout ---
app.layout = html.Div([
    html.H1("📊 NaijaStock Insight Dashboard"),
    
    html.Label("Select Companies:"),
    dcc.Dropdown(companies, companies[:5], multi=True, id='company-dropdown'),
    
    html.Label("Chart Type:"),
    dcc.RadioItems(['Line Chart', 'Candlestick'], 'Line Chart', id='chart-type'),

    html.Br(),
    dcc.Graph(id='price-chart'),

    html.H3("🚦 BUY Signals Table"),
    dcc.Checklist(['Show Only BUY Signals'], ['Show Only BUY Signals'], id='buy-filter'),
    html.Div(id='signal-table')
])

# --- Callbacks ---
@app.callback(
    Output('price-chart', 'figure'),
    Input('company-dropdown', 'value'),
    Input('chart-type', 'value')
)
def update_chart(companies_selected, chart_type):
    filtered = stock_df[stock_df['company_name'].isin(companies_selected)]
    if chart_type == 'Line Chart':
        fig = px.line(filtered, x='date', y='close', color='company_name', title="Price Trend")
    else:
        fig = go.Figure()
        for company in companies_selected:
            sub = filtered[filtered['company_name'] == company]
            fig.add_trace(go.Candlestick(
                x=sub['date'], open=sub['open'], high=sub['high'],
                low=sub['low'], close=sub['close'], name=company
            ))
        fig.update_layout(title="Candlestick Chart")
    return fig

@app.callback(
    Output('signal-table', 'children'),
    Input('company-dropdown', 'value'),
    Input('buy-filter', 'value')
)
def update_signal_table(companies_selected, filter_buy):
    latest = signal_df['date'].max()
    filtered = signal_df[signal_df['date'] == latest]
    if 'Show Only BUY Signals' in filter_buy:
        filtered = filtered[filtered['signal_score'] == 1]
    filtered = filtered[filtered['company_name'].isin(companies_selected)]
    return html.Table([
        html.Tr([html.Th(col) for col in ['Company', 'RSI', 'MACD', '5-Day Return', 'Signal']])
    ] + [
        html.Tr([
            html.Td(row['company_name']),
            html.Td(f"{row['rsi']:.2f}"),
            html.Td(f"{row['macd']:.2f}"),
            html.Td(f"{row['five_day_return']:.2f}%"),
            html.Td(int(row['signal_score']))
        ]) for _, row in filtered.iterrows()
    ])

# --- Run Server ---
if __name__ == "__main__":
    app.run(debug=True)
