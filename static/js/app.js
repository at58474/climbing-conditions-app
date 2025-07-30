// Wait for the DOM to fully load before executing scripts
document.addEventListener('DOMContentLoaded', () => {

  // Get previously selected destination from localStorage (if any)
  let destination = localStorage.getItem('selectedDestination');

  if (!destination) {
    destination = 'Red River Gorge'; // ✅ Default destination
    localStorage.setItem('selectedDestination', destination);
  }

  updateSelectedDestination(destination); // Set it as active

  // Attach click listeners to each destination dropdown item
  document.querySelectorAll('#destination-menu .dropdown-item').forEach(item => {
    item.addEventListener('click', event => {
      event.preventDefault();  // Prevent default anchor behavior
      const destination = item.getAttribute('data-destination');  // Get destination from data attribute
      updateSelectedDestination(destination);  // Update graphs and UI
    });
  });

  // Handle window resize: resize all Plotly graphs responsively
  window.addEventListener('resize', () => {
    ['conditions-graph', 'temp-graph', 'humidity-graph'].forEach(id => {
      Plotly.Plots.resize(document.getElementById(id));
    });
  });

  // Add fullscreen toggle buttons to graphs (if present)
  ['conditions', 'temperature', 'humidity', 'dew-point'].forEach(type => {
    const btn = document.getElementById(`toggle-${type}-fullscreen`);
    if (btn) {
      btn.addEventListener('click', () => toggleFullscreen(`${type}-graph-container`));
    }
  });
});

// =====================
// Core Functionality
// =====================

// Update destination: save to localStorage, update label, and fetch graphs/conditions
function updateSelectedDestination(destination) {
  localStorage.setItem('selectedDestination', destination);
  document.getElementById('selected-destination-label').textContent = destination;

  fetchCurrentClimbingConditions(destination);  // API call for latest metrics
  fetchAndRenderGraph(`/graph?destination=${destination}`, 'conditions-graph', 'conditions-button-container');
  fetchAndRenderGraph(`/graphtemp?destination=${destination}`, 'temp-graph', 'temperature-button-container');
  fetchAndRenderGraph(`/graphhumidity?destination=${destination}`, 'humidity-graph', 'humidity-button-container');
}

// Get current weather & climbing conditions from server and update UI
function fetchCurrentClimbingConditions(destination) {
  axios.get(`/current_conditions?destination=${destination}`)
    .then(response => {
      const c = response.data;

      // Update each metric on the page with color-coded feedback
      updateMetric('climbing-conditions-score', c.climbing_conditions_score.toFixed(1), getCCSColor(c.climbing_conditions_score), 'ccs-circle');
      updateMetric('temperature', `${c.temperature.toFixed(2)} °F`, getTempColor(c.temperature));
      updateMetric('humidity', `${c.humidity}%`, getHumidityColor(c.humidity));
      updateMetric('dew-point', `${c.dew_point.toFixed(2)} °F`, c.temperature <= c.dew_point ? 'metric-red' : '');

      // Render upcoming forecast if available
      if (Array.isArray(c.forecast)) {
        renderForecastCards(c.forecast);
      }
    })
    .catch(error => console.error('Error fetching climbing conditions:', error));
}

// Helper to update a single metric's text and styling
function updateMetric(id, value, colorClass = '', baseClass = '') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value;
  el.className = baseClass || '';  // Reset class
  if (colorClass) el.classList.add(colorClass);  // Add condition-based class
}

// =====================
// Color Helpers
// =====================

// Get color class for Climbing Conditions Score (CCS)
function getCCSColor(score) {
  if (score < 4) return 'ccs-red';
  if (score <= 6) return 'ccs-yellow';
  return 'ccs-green';
}

// Get color class based on temperature value
function getTempColor(temp) {
  if (temp < 25) return 'metric-red';
  if (temp <= 35) return 'metric-yellow';
  if (temp <= 65) return 'metric-green';
  if (temp <= 80) return 'metric-yellow';
  return 'metric-red';
}

// Get color class for humidity levels
function getHumidityColor(h) {
  if (h < 35) return 'metric-green';
  if (h <= 45) return 'metric-yellow';
  return 'metric-red';
}

// =====================
// Graph Rendering
// =====================

// Fetch Plotly graph data from backend and render it
function fetchAndRenderGraph(url, graphId, buttonContainerId) {
  axios.get(url)
    .then(response => {
      const graphContainer = document.getElementById(graphId);
      const data = response.data.data || response.data;
      const layout = { ...response.data.layout, dragmode: false };

      // Clear and draw new graph
      Plotly.purge(graphContainer);
      Plotly.newPlot(graphContainer, data, layout, {
        displayModeBar: false,
        responsive: true,
        scrollZoom: false
      });

      // Show the button container (used for toggles/fullscreen)
      const buttonContainer = document.getElementById(buttonContainerId);
      if (buttonContainer) buttonContainer.style.display = 'block';
    })
    .catch(error => console.error(`Error fetching data for ${graphId}:`, error));
}

// =====================
// Fullscreen Toggle
// =====================

// Toggle fullscreen view of a graph container
function toggleFullscreen(graphContainerId) {
  const container = document.getElementById(graphContainerId);
  if (!container) return;

  if (!document.fullscreenElement) {
    container.requestFullscreen().catch(err => console.error('Error entering fullscreen:', err));
  } else {
    document.exitFullscreen();
  }

  // Wait a moment and resize the Plotly chart to fill fullscreen
  setTimeout(() => Plotly.Plots.resize(container), 1000);
}

// =====================
// Forecast Cards
// =====================

// Render forecast summary cards dynamically from array
function renderForecastCards(forecast) {
  const container = document.getElementById('forecast-cards');
  container.innerHTML = '';  // Clear previous cards
  document.getElementById('forecast-container').style.display = 'block';

  const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const cardWidth = 250;
  const cardGap = 16;

  // Build cards for up to 5 days
  const cards = forecast.slice(0, 5).map(day => {
    const [year, month, dayNum] = day.date.split('-');
    const dateObj = new Date(Date.UTC(year, month - 1, dayNum));
    const weekday = weekdays[dateObj.getUTCDay()];
    const ccs = day.ccs_high;

    // Choose background and text colors based on CCS
    const [bg, text] = ccs < 4
      ? ['linear-gradient(135deg, #f8d7da 0%, #f1b0b7 100%)', '#721c24']
      : ccs <= 6
        ? ['linear-gradient(135deg, #fff3cd 0%, #ffe69e 100%)', '#856404']
        : ['linear-gradient(135deg, #d4edda 0%, #a8d5a3 100%)', '#155724'];

    // Build forecast card HTML
    const card = document.createElement('div');
    card.style.flex = '0 0 auto';
    card.style.width = `${cardWidth}px`;
    card.innerHTML = `
      <div class="card h-100 shadow-sm text-center" style="
        background: ${bg};
        color: ${text};
        border-radius: 12px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        padding: 1rem;">
        <div class="card-body d-flex flex-column justify-content-center align-items-center px-2 py-3">
          <h5 class="card-title mb-2" style="font-weight: 700;">${weekday}</h5>
          <p class="mb-1 fw-semibold"><i class="bi bi-speedometer2 me-1"></i> CCS: ${day.ccs_low.toFixed(1)}–${day.ccs_high.toFixed(1)}</p>
          <p class="mb-1"><i class="bi bi-thermometer-half me-1"></i> Temp: ${day.temp_low.toFixed(1)}–${day.temp_high.toFixed(1)} °F</p>
          <p class="mb-0"><i class="bi bi-droplet-half me-1"></i> Humidity: ${day.humidity_low}%–${day.humidity_high}%</p>
          <p class="mb-0"><i class="bi bi-cloud-rain me-1"></i> Rain: ${day.precip_high}%</p>
        </div>
      </div>
    `;

    // Add hover effect for interaction
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

  // Add all cards to the container
  cards.forEach(card => container.appendChild(card));

  // Dynamically adjust layout depending on screen size
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

  updateLayout();  // Run on initial render
  window.addEventListener('resize', updateLayout);  // Re-run on window resize
}
