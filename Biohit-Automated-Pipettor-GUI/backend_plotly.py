import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

def generate_interactive_html(time_arr, values_arr, filepath, title="Full Plate Ca2+ Traces"):
    """
    values_arr shape is (n_samples, 48).
    Creates an interactive Plotly HTML file.
    """
    rows = 8
    cols = 6
    
    fig = make_subplots(
        rows=rows, cols=cols,
        shared_xaxes=True,
        shared_yaxes=True,
        subplot_titles=[f"{chr(65+r)}{c+1}" for r in range(rows) for c in range(cols)],
        vertical_spacing=0.03,
        horizontal_spacing=0.01
    )
    
    for row in range(rows):
        for col in range(cols):
            idx = row * cols + col
            fig.add_trace(
                go.Scatter(
                    x=time_arr,
                    y=values_arr[:, idx],
                    mode='lines',
                    name=f"{chr(65+row)}{col+1}",
                    line=dict(width=1),
                    hoverinfo="x+y+name"
                ),
                row=row+1, col=col+1
            )
            
    fig.update_layout(
        title=title,
        height=1200,
        showlegend=False,
        plot_bgcolor="white",
        hovermode="x unified"
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    
    fig.write_html(filepath)
