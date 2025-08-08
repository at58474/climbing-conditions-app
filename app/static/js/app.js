document.addEventListener('DOMContentLoaded', () => {
  const defaultDestination = 'Red River Gorge';
  const stored = localStorage.getItem('selectedDestination') || defaultDestination;
  updateSelectedDestination(stored);

  document.querySelectorAll('#destination-menu .dropdown-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      updateSelectedDestination(item.getAttribute('data-destination'));
    });
  });

  window.addEventListener('resize', () => {
    ['conditions-graph', 'temp-graph', 'humidity-graph'].forEach(id => {
      Plotly.Plots.resize(document.getElementById(id));
    });
  });

  ['conditions', 'temperature', 'humidity', 'dew-point'].forEach(type => {
    const btn = document.getElementById(`toggle-${type}-fullscreen`);
    if (btn) {
      btn.addEventListener('click', () => toggleFullscreen(`${type}-graph-container`));
    }
  });


});

function getUserTimezoneOffset() {
  return new Date().getTimezoneOffset();  // returns offset in minutes (e.g., -240 for EDT)
}

function degreesToCardinal(num) {
    var val = Math.floor((num / 22.5) + 0.5);
    var arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
    return arr[(val % 16)];
}

function updateSelectedDestination(destination) {
  localStorage.setItem('selectedDestination', destination);
  document.getElementById('selected-destination-label').textContent = destination;

  // Update submit CCS link with current destination
  const submitLink = document.getElementById('submit-ccs-link');
  if (submitLink) {
    submitLink.href = `/submit-ccs?destination=${encodeURIComponent(destination)}`;
  }

  const tzOffset = getUserTimezoneOffset();  // <--- capture offset

  axios.get(`/all_data?destination=${encodeURIComponent(destination)}&tz_offset=${tzOffset}`)  // <--- pass it
    .then(res => {
      const c = res.data.conditions;
      const current = c.current;

      updateMetric('climbing-conditions-score', c.climbing_conditions_score.toFixed(1), getCCSColor(c.climbing_conditions_score), 'ccs-circle');
      updateMetric('temperature', `${current.temp.toFixed(2)} °F`, getTempColor(current.temp));
      updateMetric('humidity', `${current.humidity}%`, getHumidityColor(current.humidity));
      updateMetric('dew-point', `${current.dew_point.toFixed(2)} °F`, current.temp <= current.dew_point ? 'metric-red' : '');
      updateMetric('wind-speed', `${current.wind_speed.toFixed(0)} mph`);
      updateMetric('wind-gust', `${current.wind_gust.toFixed(0)} mph`);
      updateMetric('wind-direction', `${degreesToCardinal(current.wind_direction)}`);

      if (Array.isArray(c.forecast)) {
        renderForecastCards(c.forecast);
      }

      renderPlotlyGraphFromJSON(res.data.graphs.ccs, 'conditions-graph', 'conditions-button-container');
      renderPlotlyGraphFromJSON(res.data.graphs.temperature, 'temp-graph', 'temperature-button-container');
      renderPlotlyGraphFromJSON(res.data.graphs.humidity, 'humidity-graph', 'humidity-button-container');
    })
    .catch(err => console.error('Error loading all data:', err));
}



function renderPlotlyGraphFromJSON(jsonStr, graphId, buttonContainerId) {
  const graph = document.getElementById(graphId);
  const obj = JSON.parse(jsonStr);
  Plotly.purge(graph);
  Plotly.newPlot(graph, obj.data, { ...obj.layout, dragmode: false }, {
    displayModeBar: false,
    responsive: true,
    scrollZoom: false
  });
  const btn = document.getElementById(buttonContainerId);
  if (btn) btn.style.display = 'block';
}

function updateMetric(id, value, colorClass = '', baseClass = '') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value;
  el.className = baseClass || '';
  if (colorClass) el.classList.add(colorClass);
}

function getCCSColor(score) {
  return score < 4 ? 'ccs-red' : score <= 6 ? 'ccs-yellow' : 'ccs-green';
}
function getTempColor(temp) {
  if (temp < 25) return 'metric-red';
  if (temp <= 35) return 'metric-yellow';
  if (temp <= 65) return 'metric-green';
  if (temp <= 80) return 'metric-yellow';
  return 'metric-red';
}
function getHumidityColor(h) {
  if (h < 35) return 'metric-green';
  if (h <= 45) return 'metric-yellow';
  return 'metric-red';
}

function toggleFullscreen(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (!document.fullscreenElement) {
    container.requestFullscreen().catch(err => console.error('Error entering fullscreen:', err));
  } else {
    document.exitFullscreen();
  }
  setTimeout(() => Plotly.Plots.resize(container), 1000);
}

function renderForecastCards(forecast) {
  const container = document.getElementById('forecast-cards');
  container.innerHTML = '';
  document.getElementById('forecast-container').style.display = 'block';

  const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const cardWidth = 250;
  const cardGap = 16;

  const cards = forecast.slice(0, 8).map(day => {
    const [year, month, dayNum] = day.date.split('-');
    const dateObj = new Date(Date.UTC(year, month - 1, dayNum));
    const weekday = weekdays[dateObj.getUTCDay()];
    const ccs = day.ccs_high;

    const [bg, text] = ccs < 4
      ? ['linear-gradient(135deg, #f8d7da 0%, #f1b0b7 100%)', '#721c24']
      : ccs <= 6
        ? ['linear-gradient(135deg, #fff3cd 0%, #ffe69e 100%)', '#856404']
        : ['linear-gradient(135deg, #d4edda 0%, #a8d5a3 100%)', '#155724'];

    const card = document.createElement('div');
    card.style.flex = '0 0 auto';
    card.style.width = `${cardWidth}px`;
    card.innerHTML = `
      <div class="card h-100 shadow-sm text-center" style="
        background: ${bg};
        color: ${text};
        border-radius: 12px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        padding: 1rem;">
        <div class="card-body d-flex flex-column justify-content-center align-items-center px-2 py-3">
          <h5 class="card-title mb-2 fw-bold">${weekday}</h5>
          <p class="mb-1"><i class="bi bi-speedometer2 me-1"></i> CCS: ${day.ccs_low.toFixed(1)}–${day.ccs_high.toFixed(1)}</p>
          <p class="mb-1"><i class="bi bi-thermometer-half me-1"></i> Temp: ${day.temp_low.toFixed(1)}–${day.temp_high.toFixed(1)} °F</p>
          <p class="mb-0"><i class="bi bi-droplet-half me-1"></i> Humidity: ${day.humidity_low}%–${day.humidity_high}%</p>
          <p class="mb-0"><i class="bi bi-cloud-rain me-1"></i> Rain: ${day.precip_high}%</p>
          <p class="mb-0"><i class="bi bi-wind me-1"></i> Wind: ${day.wind_low}–${day.wind_high}mph</p>
          <p class="mb-0"><i class="bi bi-beaker me-1"></i> Rain Total: ${day.rain_accumulation}"</p>
        </div>
      </div>
    `;

    const cardInner = card.querySelector('.card');
    cardInner.addEventListener('mouseenter', () => {
      cardInner.style.transform = 'scale(1.05)';
      cardInner.style.boxShadow = '0 12px 30px rgba(0,0,0,0.25)';
    });
    cardInner.addEventListener('mouseleave', () => {
      cardInner.style.transform = 'scale(1)';
      cardInner.style.boxShadow = '0 8px 20px rgba(0,0,0,0.12)';
    });

    return card;
  });

  cards.forEach(card => container.appendChild(card));

  function updateLayout() {
    const totalWidth = (cardWidth * cards.length) + (cardGap * (cards.length - 1));
    const containerWidth = container.clientWidth;

    Object.assign(container.style, {
      display: 'flex',
      flexWrap: totalWidth <= containerWidth ? 'wrap' : 'nowrap',
      justifyContent: totalWidth <= containerWidth ? 'center' : 'flex-start',
      overflowX: totalWidth <= containerWidth ? 'visible' : 'auto',
      gap: '1rem',
      paddingBottom: totalWidth <= containerWidth ? '0' : '0.5rem'
    });
  }

  updateLayout();
  window.addEventListener('resize', updateLayout);
}
