from datetime import datetime
import plotly.graph_objects as go
from .utils import calculate_climbing_conditions_score, get_weather_icon

def color_range_for_temp(y):
    if y < 25: return "rgba(255, 0, 0, 0.3)"
    if y <= 35: return "rgba(255, 255, 0, 0.3)"
    if y <= 65: return "rgba(0, 255, 0, 0.3)"
    if y <= 80: return "rgba(255, 255, 0, 0.3)"
    return "rgba(255, 0, 0, 0.3)"

def color_range_for_humidity(y):
    if y < 35: return "rgba(0, 255, 0, 0.3)"
    if y <= 45: return "rgba(255, 255, 0, 0.3)"
    return "rgba(255, 0, 0, 0.3)"

def color_range_for_ccs(y):
    if y < 4: return "rgba(255, 0, 0, 0.3)"
    if y <= 6: return "rgba(255, 255, 0, 0.3)"
    return "rgba(0, 255, 0, 0.3)"

def process_hourly_data(adapted, model, value_type):
    values, colors, x_labels, hover_text = [], [], [], []

    for entry in adapted:
        dt = datetime.utcfromtimestamp(entry['dt'])
        temp = entry['main']['temp']
        rh = entry['main']['humidity']
        dew_point = entry['main']['dew_point']
        score = calculate_climbing_conditions_score(model, dew_point, rh, temp)
        value = {'score': score, 'temp': temp, 'humidity': rh}[value_type]

        values.append(value)
        colors.append('red' if dew_point >= temp else 'blue')

        icon = get_weather_icon(entry['weather'][0]['id'])
        time_str = dt.strftime('%A %I:%M %p')
        rain = entry.get('pop', 0) * 100

        x_labels.append(f"{icon} {time_str}")
        hover_text.append(
            f"{icon} {time_str}<br>"
            f"CCS: {score:.2f}<br>Temp: {temp:.2f}°F<br>"
            f"Humidity: {rh}%<br>Dew Point: {dew_point:.2f}°F<br>"
            f"Chance of Rain: {rain:.0f}%"
        )

    x_indices = list(range(len(adapted)))
    return x_indices, values, colors, x_labels, hover_text

def plot_data(x_indices, values, colors, x_labels, hover_text, title, yaxis_title, color_ranges):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_indices,
        y=values,
        mode='lines+markers',
        marker=dict(color=colors),
        text=hover_text,
        hovertemplate="<b>%{text}</b><extra></extra>"
    ))

    for i in range(len(values) - 1):
        fig.add_shape(
            type="rect",
            x0=i, x1=i + 1,
            y0=min(values), y1=max(values),
            line=dict(width=0),
            fillcolor=color_ranges(values[i]),
            opacity=0.3
        )

    fig.add_vline(x=48, line_dash="dot", line_color="black", opacity=0.5)
    fig.add_vline(x=71, line_dash="dot", line_color="black", opacity=0.5)

    fig.add_annotation(x=24, y=1.10, yref="paper", text="Hourly", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=60, y=1.10, yref="paper", text="3-Hour", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=73, y=1.10, yref="paper", text="Daily", showarrow=False, font=dict(size=12))

    fig.update_layout(
        title=title,
        xaxis=dict(title='Time', tickmode='array', tickvals=x_indices, ticktext=x_labels, tickangle=45),
        yaxis=dict(title=yaxis_title),
        showlegend=False
    )

    return fig

def plot_hourly_climbing_scores(model, adapted, destination):
    ts, vals, cols, labels, hover = process_hourly_data(adapted, model, 'score')
    return plot_data(ts, vals, cols, labels, hover, f'CCS - {destination}', 'CCS', color_range_for_ccs)

def plot_hourly_temp(model, adapted, destination):
    ts, vals, cols, labels, hover = process_hourly_data(adapted, model, 'temp')
    return plot_data(ts, vals, cols, labels, hover, f'Temperature - {destination}', 'Temp (°F)', color_range_for_temp)

def plot_hourly_humidity(model, adapted, destination):
    ts, vals, cols, labels, hover = process_hourly_data(adapted, model, 'humidity')
    return plot_data(ts, vals, cols, labels, hover, f'Humidity - {destination}', 'Humidity (%)', color_range_for_humidity)
