// app/static/js/chart.js
// Charting functionality for the crypto trading platform

/**
 * Initialize a market overview chart
 * @param {HTMLElement} container - The container element for the chart
 */
function initializeMarketChart(container) {
    // Generate chart data or load it from an API
    const chartData = generateChartData();
    
    // Create the chart
    const ctx = document.createElement('canvas');
    container.appendChild(ctx);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: chartData.symbol,
                data: chartData.prices,
                borderColor: '#0ea5e9',
                backgroundColor: 'rgba(14, 165, 233, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 2,
                pointBackgroundColor: '#0ea5e9'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    position: 'right',
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + formatNumber(value);
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return chartData.symbol + ': $' + formatNumber(context.raw);
                        }
                    }
                },
                legend: {
                    display: false
                }
            }
        }
    });
}

/**
 * Initialize a TradingView chart
 * @param {string} [symbol='BTCUSDT'] - Trading pair to show
 * @param {string} [interval='1D'] - Time interval
 */
function initializeTradingViewChart(symbol = 'BTCUSDT', interval = '1D') {
    const container = document.getElementById('tradingViewChart');
    
    if (!container) return;
    
    new TradingView.widget({
        "container_id": "tradingViewChart",
        "symbol": `BINANCE:${symbol}`,
        "interval": interval,
        "timezone": "Etc/UTC",
        "theme": "light",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "hide_top_toolbar": true,
        "hide_legend": false,
        "save_image": false,
        "studies": [
            "RSI@tv-basicstudies",
            "MASimple@tv-basicstudies"
        ],
        "show_popup_button": true,
        "popup_width": "1000",
        "popup_height": "650",
        "autosize": true,
    });
}

/**
 * Initialize a price chart for a specific coin
 * @param {string} coinId - Coin ID or symbol
 * @param {HTMLElement} container - The container element for the chart
 * @param {string} [interval='1d'] - Time interval
 * @param {number} [days=30] - Number of days of data to show
 */
function initializeCoinChart(coinId, container, interval = '1d', days = 30) {
    // Fetch chart data from API
    fetchCoinChartData(coinId, interval, days)
        .then(data => {
            // Create the chart
            const ctx = document.createElement('canvas');
            container.appendChild(ctx);
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: data.symbol + ' Price',
                        data: data.prices,
                        borderColor: '#0ea5e9',
                        backgroundColor: 'rgba(14, 165, 233, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 1,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#0ea5e9'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                maxTicksLimit: 6
                            }
                        },
                        y: {
                            position: 'right',
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return '$' + formatNumber(value);
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${data.symbol}: $${formatNumber(context.raw)}`;
                                }
                            }
                        },
                        legend: {
                            display: false
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
            container.innerHTML = '<div class="p-6 text-center text-red-500">Error loading chart data.</div>';
        });
}

/**
 * Initialize an announcement slider
 * @param {HTMLElement} slider - The slider element
 */
function initializeAnnouncementSlider(slider) {
    // Clone content for infinite scrolling
    const clone = slider.innerHTML;
    slider.innerHTML += clone;
    
    // Get the announcements
    const announcements = slider.querySelectorAll('div');
    
    // Calculate total width of first half of announcements
    const totalWidth = Array.from(announcements)
        .slice(0, announcements.length / 2)
        .reduce((sum, el) => sum + el.offsetWidth + 32, 0);
    
    // Set animation
    slider.style.animation = `slide ${totalWidth / 50}s linear infinite`;
    
    // Add animation keyframes
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slide {
            0% { transform: translateX(0); }
            100% { transform: translateX(-${totalWidth}px); }
        }
    `;
    document.head.appendChild(style);
}

/**
 * Generate sample chart data for development
 * @returns {Object} Chart data with labels, prices, and symbol
 */
function generateChartData() {
    // Generate dates for the last 14 days
    const labels = [];
    const prices = [];
    const symbol = 'BTC/USDT';
    
    // Start with a base price
    let price = 30000 + Math.random() * 10000;
    
    // Generate dates and prices
    for (let i = 13; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', {month: 'short', day: 'numeric'}));
        
        // Add some randomness to the price
        price = price * (1 + (Math.random() * 0.06 - 0.03));
        prices.push(price);
    }
    
    return {
        labels,
        prices,
        symbol
    };
}

/**
 * Fetch chart data for a specific coin
 * @param {string} coinId - Coin ID or symbol
 * @param {string} interval - Time interval
 * @param {number} days - Number of days of data
 * @returns {Promise<Object>} Chart data with labels, prices, and symbol
 */
async function fetchCoinChartData(coinId, interval, days) {
    try {
        const response = await fetch(`/market/chart/${coinId}?interval=${interval}&limit=${days}`);
        const data = await response.json();
        
        // Process data for chart format
        const labels = data.map(item => new Date(item[0]).toLocaleDateString());
        const prices = data.map(item => item[4]); // Close price
        
        return {
            labels,
            prices,
            symbol: coinId
        };
    } catch (error) {
        console.error('Error fetching chart data:', error);
        throw error;
    }
}

/**
 * Format a number for display
 * @param {number} num - Number to format
 * @returns {string} Formatted number
 */
function formatNumber(num) {
    if (num >= 1e9) {
        return (num / 1e9).toFixed(2) + 'B';
    }
    if (num >= 1e6) {
        return (num / 1e6).toFixed(2) + 'M';
    }
    if (num >= 1e3) {
        return (num / 1e3).toFixed(2) + 'K';
    }
    if (num >= 1) {
        return num.toFixed(2);
    }
    return num.toFixed(6);
}