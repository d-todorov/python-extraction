// Financial Dashboard JavaScript

const API_BASE = '/api';
let rateChart = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();

    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', () => {
        loadDashboard();
    });

    // Auto-refresh every 24 hours (matches daily data collection)
    setInterval(loadDashboard, 24 * 60 * 60 * 1000);
});

// Load all dashboard data
async function loadDashboard() {
    await Promise.all([
        loadCurrentRates(),
        loadRateHistory(),
        loadNews(),
        loadHealthStatus()
    ]);
}

// Load current exchange rates
async function loadCurrentRates() {
    try {
        const response = await fetch(`${API_BASE}/rates`);
        const data = await response.json();

        if (data.error) {
            displayError('currentRates', data.error);
            return;
        }

        displayCurrentRates(data.rates);
    } catch (error) {
        console.error('Error loading rates:', error);
        displayError('currentRates', 'Failed to load exchange rates');
    }
}

// Display current rates
function displayCurrentRates(rates) {
    const container = document.getElementById('currentRates');
    container.innerHTML = '';

    for (const [currency, rate] of Object.entries(rates)) {
        const card = document.createElement('div');
        card.className = 'rate-card';

        card.innerHTML = `
            <div class="currency-code">${currency}</div>
            <div class="rate-value">${rate.toFixed(4)}</div>
        `;

        container.appendChild(card);
    }
}

// Load rate history and display chart
async function loadRateHistory() {
    try {
        const response = await fetch(`${API_BASE}/rates/history?days=7`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading history:', data.error);
            return;
        }

        displayRateChart(data.history);
    } catch (error) {
        console.error('Error loading rate history:', error);
    }
}

// Display rate history chart
function displayRateChart(history) {
    const ctx = document.getElementById('rateChart').getContext('2d');

    // Prepare data for Chart.js
    const dates = history.map(h => h.date).reverse();
    const currencies = Object.keys(history[0]?.rates || {});

    const datasets = currencies.map((currency, index) => {
        const colors = ['#667eea', '#f56565', '#48bb78'];
        const color = colors[index % colors.length];

        return {
            label: currency,
            data: history.map(h => h.rates[currency]?.rate).reverse(),
            borderColor: color,
            backgroundColor: color + '20',
            tension: 0.4
        };
    });

    // Destroy existing chart
    if (rateChart) {
        rateChart.destroy();
    }

    // Create new chart
    rateChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });
}

// Load news
async function loadNews() {
    try {
        const response = await fetch(`${API_BASE}/news?limit=10`);
        const data = await response.json();

        if (data.error) {
            displayError('newsList', data.error);
            return;
        }

        displayNews(data.news);
    } catch (error) {
        console.error('Error loading news:', error);
        displayError('newsList', 'Failed to load news');
    }
}

// Display news articles
function displayNews(newsItems) {
    const container = document.getElementById('newsList');
    container.innerHTML = '';

    if (newsItems.length === 0) {
        container.innerHTML = '<div class="loading">No news available</div>';
        return;
    }

    newsItems.forEach(item => {
        const article = document.createElement('div');
        article.className = 'news-item';

        const publishedDate = item.published_date ?
            new Date(item.published_date).toLocaleDateString() :
            'Unknown date';

        article.innerHTML = `
            <div class="news-title">
                <a href="${item.link}" target="_blank">${item.title}</a>
            </div>
            <div class="news-meta">
                <span class="news-source">${item.source.toUpperCase()}</span>
                <span>${publishedDate}</span>
            </div>
            ${item.description ? `<div class="news-description">${item.description}</div>` : ''}
        `;

        container.appendChild(article);
    });
}

// Load health status
async function loadHealthStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        const indicator = document.querySelector('.status-indicator');
        const statusText = document.getElementById('statusText');

        if (data.status === 'healthy') {
            indicator.className = 'status-indicator healthy';
            statusText.textContent = `System healthy • Uptime: ${formatUptime(data.uptime_seconds)}`;
        } else {
            indicator.className = 'status-indicator unhealthy';
            statusText.textContent = 'System unhealthy';
        }
    } catch (error) {
        console.error('Error loading health status:', error);
        const indicator = document.querySelector('.status-indicator');
        const statusText = document.getElementById('statusText');
        indicator.className = 'status-indicator unhealthy';
        statusText.textContent = 'Cannot connect to server';
    }
}

// Format uptime
function formatUptime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

// Display error message
function displayError(containerId, message) {
    const container = document.getElementById(containerId);
    container.innerHTML = `<div class="loading" style="color: #ef4444;">${message}</div>`;
}
