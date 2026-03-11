const API_URL = window.location.protocol === 'file:' ? 'http://localhost:5000' : '';

// State
let logChart = null;

// DOM Elements
const totalLogsEl = document.getElementById('total-logs');
const anomalyCountEl = document.getElementById('anomaly-count');
const activeServicesEl = document.getElementById('active-services');
const logListEl = document.getElementById('log-list');
const anomalyListEl = document.getElementById('anomaly-list');
const simulateBtn = document.getElementById('simulate-btn');

// Chat Elements
const chatInput = document.getElementById('chat-input');
const chatBtn = document.getElementById('chat-btn');
const chatBox = document.getElementById('chat-box');
const resultsContainer = document.getElementById('query-results');

// Tab Navigation
const navItems = document.querySelectorAll('.nav-item');
const tabContents = document.querySelectorAll('.tab-content');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        // Remove active class from all
        navItems.forEach(nav => nav.classList.remove('active'));
        tabContents.forEach(tab => tab.classList.remove('active'));

        // Add active class to clicked
        item.classList.add('active');
        const tabId = item.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
    });
});

// Initialize Chart
function initChart() {
    const ctx = document.getElementById('logChart').getContext('2d');
    logChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Log Volume',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// Fetch Data
async function fetchData() {
    try {
        const logsRes = await fetch(`${API_URL}/logs`);
        const logs = await logsRes.json();

        const anomalyRes = await fetch(`${API_URL}/anomaly`);
        const anomalyData = await anomalyRes.json();

        updateDashboard(logs, anomalyData);
    } catch (error) {
        console.error("Error fetching data:", error);
    }
}

function updateDashboard(logs, anomalyData) {
    if (totalLogsEl) totalLogsEl.textContent = logs.length;
    if (anomalyCountEl) anomalyCountEl.textContent = anomalyData.count;

    if (activeServicesEl) {
        const services = new Set(logs.map(l => l.service));
        activeServicesEl.textContent = services.size;
    }

    if (logListEl) renderList(logListEl, logs.slice().reverse(), createLogItem);
    if (anomalyListEl) renderList(anomalyListEl, anomalyData.anomalies, createAnomalyItem);

    if (logChart) updateChart(logs.length);
}

function renderList(container, items, createFn) {
    container.innerHTML = '';
    if (items.length === 0) {
        container.innerHTML = '<div class="empty-state">No data available.</div>';
        return;
    }
    items.forEach(item => {
        container.appendChild(createFn(item));
    });
}

function createLogItem(log) {
    const div = document.createElement('div');
    div.className = `log-item ${log.level}`;
    div.innerHTML = `
        <span class="timestamp">${new Date(log.timestamp).toLocaleTimeString()}</span>
        <span class="service">${log.service}</span>
        <span class="message">${log.message}</span>
    `;
    return div;
}

function createAnomalyItem(log) {
    const div = document.createElement('div');
    div.className = 'log-item anomaly-item';
    div.style.borderLeft = "3px solid #ef4444";
    div.innerHTML = `
        <span class="timestamp">${new Date(log.timestamp).toLocaleTimeString()}</span>
        <span class="service" style="color:#ef4444">Score: ${log.anomaly_score.toFixed(2)}</span>
        <span class="message">${log.message}</span>
    `;
    return div;
}

function updateChart(count) {
    const now = new Date().toLocaleTimeString();
    logChart.data.labels.push(now);
    logChart.data.datasets[0].data.push(count);

    if (logChart.data.labels.length > 10) {
        logChart.data.labels.shift();
        logChart.data.datasets[0].data.shift();
    }
    logChart.update();
}

// Chat Logic
async function sendQuery() {
    const query = chatInput.value.trim();
    if (!query) return;

    addMessage(query, 'user');
    chatInput.value = '';

    // Show loading state in results
    resultsContainer.innerHTML = '<div class="empty-state">Analyzing logs...</div>';

    try {
        const res = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();

        if (data.results && data.results.length > 0) {
            const source = data.es_query === "FALLBACK_IN_MEMORY" ? "(Memory)" : "(ES)";
            addMessage(`Found ${data.results.length} logs matching your query. ${source}`, 'system');
            
            // Render results in the dedicated container
            renderList(resultsContainer, data.results, createLogItem);
        } else {
            addMessage("No logs found matching that query.", 'system');
            resultsContainer.innerHTML = '<div class="empty-state">No results found.</div>';
        }
    } catch (error) {
        addMessage("Error processing query.", 'system');
        resultsContainer.innerHTML = '<div class="empty-state">Error processing query.</div>';
        console.error(error);
    }
}

function addMessage(text, type) {
    const div = document.createElement('div');
    div.className = `chat-message ${type}`;
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

if (chatBtn) chatBtn.addEventListener('click', sendQuery);
if (chatInput) chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendQuery();
});

// Simulate Traffic
async function simulateTraffic() {
    if (!simulateBtn) return;
    simulateBtn.disabled = true;
    simulateBtn.textContent = "Simulating...";

    const services = ["booking-api", "auth-service", "payment-gateway"];
    const components = ["db", "cache", "queue"];
    const levels = ["INFO", "INFO", "INFO", "WARN", "ERROR"];
    const messages = [
        "User logged in", "Payment processed", "Database connection established",
        "Cache miss", "Timeout waiting for response", "Invalid credentials", "Transaction failed"
    ];

    const logs = [];
    for (let i = 0; i < 5; i++) {
        logs.push({
            timestamp: new Date().toISOString(),
            service: services[Math.floor(Math.random() * services.length)],
            component: components[Math.floor(Math.random() * components.length)],
            level: levels[Math.floor(Math.random() * levels.length)],
            message: messages[Math.floor(Math.random() * messages.length)]
        });
    }
    
    // Add an anomaly sometimes
    if (Math.random() > 0.7) {
        logs.push({
            timestamp: new Date().toISOString(),
            service: "payment-gateway",
            component: "db",
            level: "FATAL",
            message: "CRITICAL FAILURE: DATA CORRUPTION DETECTED"
        });
    }

    await fetch(`${API_URL}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logs)
    });

    await fetchData();
    simulateBtn.disabled = false;
    simulateBtn.textContent = "Simulate Traffic";
}

if (simulateBtn) simulateBtn.addEventListener('click', simulateTraffic);

// Init
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    fetchData();
    setInterval(fetchData, 5000); // Poll every 5s
});
