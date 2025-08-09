from collections import defaultdict
from datetime import datetime
from .utils import calculate_climbing_conditions_score

def generate_daily_forecast(adapted, model):
    grouped = defaultdict(list)
    for entry in adapted:
        date = datetime.utcfromtimestamp(entry['dt']).strftime('%Y-%m-%d')
        grouped[date].append(entry)

    forecast = []
    for idx, date in enumerate(sorted(grouped)[:8]):
        entries = grouped[date]
        temps = [e['main']['temp'] for e in entries]
        hums = [e['main']['humidity'] for e in entries]
        dew_points = [e['main']['dew_point'] for e in entries]
        pops = [e.get('pop', 0) * 100 for e in entries]
        winds = [e.get('wind', 0) for e in entries if e.get('wind') is not None]
        rains = [e.get('rain_accumulation', 0) for e in entries if e.get('rain_accumulation') is not None]

        ccs_values = [
            calculate_climbing_conditions_score(model, e['main']['dew_point'], e['main']['humidity'], e['main']['temp'])
            for e in entries
        ]

        forecast.append({
            'date': date,
            'source': 'hourly' if idx < 2 else '3-hour' if idx < 5 else 'daily',
            'temp_low': round(min(temps), 1),
            'temp_high': round(max(temps), 1),
            'humidity_low': round(min(hums)),
            'humidity_high': round(max(hums)),
            'ccs_low': round(min(ccs_values), 1),
            'ccs_high': round(max(ccs_values), 1),
            'precip_high': round(max(pops), 1),
            'wind_low': round(min(winds)) if winds else None,
            'wind_high': round(max(winds)) if winds else None,
            'rain_accumulation': round(sum(rains) / 25.4, 2) if rains else 0
        })

    return forecast
