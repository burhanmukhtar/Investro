// This code should be added to your market.js file or included in your market.html template

document.addEventListener('DOMContentLoaded', function() {
    const marketData = document.getElementById('marketData');
    const marketSearch = document.getElementById('marketSearch');
    const coinDetailModal = document.getElementById('coinDetailModal');
    const closeCoinDetail = document.getElementById('closeCoinDetail');
    
    // Get the filter tabs
    const filterTabs = document.querySelectorAll('.flex.border-b button');
    let activeTab = 'all'; // Default active tab
    
    // Add click event listeners to tabs
    if (filterTabs && filterTabs.length > 0) {
        filterTabs.forEach((tab, index) => {
            tab.addEventListener('click', function() {
                // Remove active class from all tabs
                filterTabs.forEach(t => {
                    t.classList.remove('text-primary-600', 'border-b-2', 'border-primary-600');
                    t.classList.add('text-gray-500');
                });
                
                // Add active class to clicked tab
                this.classList.add('text-primary-600', 'border-b-2', 'border-primary-600');
                this.classList.remove('text-gray-500');
                
                // Load appropriate data based on tab
                switch(index) {
                    case 0: // All
                        activeTab = 'all';
                        loadMarketData();
                        break;
                    case 1: // Gainers
                        activeTab = 'gainers';
                        loadGainersData();
                        break;
                    case 2: // Losers
                        activeTab = 'losers';
                        loadLosersData();
                        break;
                    case 3: // Volume
                        activeTab = 'volume';
                        loadVolumeData();
                        break;
                }
            });
        });
    }
    
    // Load market data on page load
    loadMarketData();
    
    // Initialize search
    if (marketSearch) {
        marketSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = marketData.querySelectorAll('.market-row');
            
            rows.forEach(row => {
                const coinName = row.querySelector('.coin-name').textContent.toLowerCase();
                const coinSymbol = row.querySelector('.coin-symbol').textContent.toLowerCase();
                
                if (coinName.includes(searchTerm) || coinSymbol.includes(searchTerm)) {
                    row.classList.remove('hidden');
                } else {
                    row.classList.add('hidden');
                }
            });
        });
    }
    
    // Coin detail modal
    if (closeCoinDetail) {
        closeCoinDetail.addEventListener('click', function() {
            coinDetailModal.classList.add('scale-0');
        });
        
        coinDetailModal.addEventListener('click', function(e) {
            if (e.target === coinDetailModal) {
                coinDetailModal.classList.add('scale-0');
            }
        });
    }
    
    function loadMarketData() {
        showLoading();
        
        fetch('/market/data?limit=100')
            .then(response => response.json())
            .then(data => {
                displayCoinData(data);
            })
            .catch(error => {
                console.error('Error fetching market data:', error);
                marketData.innerHTML = '<div class="p-6 text-center text-red-500">Error loading market data. Please try again.</div>';
            });
    }
    
    function loadGainersData() {
        showLoading();
        
        fetch('/market/gainers?limit=20')
            .then(response => response.json())
            .then(response => {
                if (response.success) {
                    displayCoinData(response.data);
                } else {
                    throw new Error(response.message || 'Failed to load gainers data');
                }
            })
            .catch(error => {
                console.error('Error fetching gainers data:', error);
                marketData.innerHTML = '<div class="p-6 text-center text-red-500">Error loading gainers data. Please try again.</div>';
            });
    }
    
    function loadLosersData() {
        showLoading();
        
        fetch('/market/losers?limit=20')
            .then(response => response.json())
            .then(response => {
                if (response.success) {
                    displayCoinData(response.data);
                } else {
                    throw new Error(response.message || 'Failed to load losers data');
                }
            })
            .catch(error => {
                console.error('Error fetching losers data:', error);
                marketData.innerHTML = '<div class="p-6 text-center text-red-500">Error loading losers data. Please try again.</div>';
            });
    }
    
    function loadVolumeData() {
        showLoading();
        
        fetch('/market/volume?limit=20')
            .then(response => response.json())
            .then(response => {
                if (response.success) {
                    displayCoinData(response.data);
                } else {
                    throw new Error(response.message || 'Failed to load volume data');
                }
            })
            .catch(error => {
                console.error('Error fetching volume data:', error);
                marketData.innerHTML = '<div class="p-6 text-center text-red-500">Error loading volume data. Please try again.</div>';
            });
    }
    
    function showLoading() {
        marketData.innerHTML = `
            <div class="p-6 text-center text-gray-500">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-4"></div>
                <p>Loading data...</p>
            </div>
        `;
    }
    
    function displayCoinData(data) {
        marketData.innerHTML = '';
        
        if (data.length === 0) {
            marketData.innerHTML = '<div class="p-6 text-center text-gray-500">No data available.</div>';
            return;
        }
        
        data.forEach(coin => {
            const row = document.createElement('div');
            row.className = 'market-row p-3 hover:bg-gray-50 cursor-pointer';
            row.dataset.coin = coin.symbol;
            
            const changeColor = (coin.price_change_percentage_24h >= 0) ? 'text-green-600' : 'text-red-600';
            const changeSign = (coin.price_change_percentage_24h >= 0) ? '+' : '';
            const changeValue = coin.price_change_percentage_24h !== null ? 
                `${changeSign}${coin.price_change_percentage_24h.toFixed(2)}%` : 'N/A';
            
            // Use the image from the coin data if available, otherwise show a fallback
            const imageSrc = coin.image || '';
            const imageHtml = imageSrc ? 
                `<img src="${imageSrc}" alt="${coin.symbol}" class="w-8 h-8 rounded-full object-cover mr-2">` : 
                `<div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center mr-2">
                    <span class="text-xs font-bold">${coin.symbol.charAt(0)}</span>
                </div>`;
            
            row.innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="w-1/2 flex items-center">
                        ${imageHtml}
                        <div>
                            <div class="text-sm font-medium coin-name">${coin.name}</div>
                            <div class="text-xs text-gray-500 coin-symbol">${coin.symbol}</div>
                        </div>
                    </div>
                    <div class="w-1/4 text-right">
                        <div class="text-sm font-medium">$${formatNumber(coin.current_price)}</div>
                    </div>
                    <div class="w-1/4 text-right">
                        <div class="text-sm font-medium ${changeColor}">
                            ${changeValue}
                        </div>
                    </div>
                </div>
            `;
            
            row.addEventListener('click', function() {
                showCoinDetail(coin.symbol);
            });
            
            marketData.appendChild(row);
        });
    }
    
    function showCoinDetail(symbol) {
        fetch(`/market/coin/${symbol}`)
            .then(response => response.json())
            .then(response => {
                if (!response.success) {
                    throw new Error(response.message || 'Failed to load coin details');
                }
                
                const coin = response.data;
                
                // Update coin icon - use image if available
                if (coin.image) {
                    document.getElementById('coinIcon').innerHTML = `
                        <img src="${coin.image}" alt="${coin.symbol}" class="w-10 h-10 rounded-full object-cover">
                    `;
                } else {
                    document.getElementById('coinIcon').innerHTML = `
                        <div class="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                            <span id="coinSymbolIcon" class="text-sm font-bold">${coin.symbol.charAt(0)}</span>
                        </div>
                    `;
                }
                
                // Update other coin details
                document.getElementById('coinName').textContent = coin.name;
                document.getElementById('coinSymbol').textContent = coin.symbol;
                document.getElementById('coinRank').textContent = `Rank #${coin.market_cap_rank || 'N/A'}`;
                document.getElementById('coinPrice').textContent = `$${formatNumber(coin.current_price)}`;
                
                const changeElement = document.getElementById('coinChange');
                const changeValue = coin.price_change_percentage_24h !== null ?
                    `${coin.price_change_percentage_24h >= 0 ? '+' : ''}${coin.price_change_percentage_24h.toFixed(2)}% (24h)` :
                    'N/A';
                    
                changeElement.textContent = changeValue;
                changeElement.className = coin.price_change_percentage_24h >= 0 ? 
                    'text-sm text-green-600' : 'text-sm text-red-600';
                
                document.getElementById('coinMarketCap').textContent = `$${formatNumber(coin.market_cap)}`;
                document.getElementById('coinVolume').textContent = `$${formatNumber(coin.total_volume)}`;
                document.getElementById('coinSupply').textContent = `${formatNumber(coin.circulating_supply)} ${coin.symbol}`;
                
                const athValue = coin.ath ? 
                    `$${formatNumber(coin.ath)} ${coin.ath_date ? `(${new Date(coin.ath_date).toLocaleDateString()})` : ''}` :
                    'N/A';
                document.getElementById('coinATH').textContent = athValue;
                
                document.getElementById('tradeCoinButton').href = `/user/future?coin=${coin.symbol}/USDT`;
                
                // Load chart
                loadCoinChart(coin.symbol);
                
                // Show modal
                coinDetailModal.classList.remove('scale-0');
            })
            .catch(error => {
                console.error('Error fetching coin data:', error);
                alert('Error loading coin data. Please try again.');
            });
    }
    
    function loadCoinChart(symbol) {
        fetch(`/market/chart/${symbol}?interval=1d&limit=30`)
            .then(response => response.json())
            .then(response => {
                let data;
                if (response.success) {
                    data = response.data;
                } else if (Array.isArray(response)) {
                    data = response;
                } else {
                    throw new Error('Invalid chart data format');
                }
                
                const chartContainer = document.getElementById('coinChartContainer');
                chartContainer.innerHTML = '';
                
                const canvas = document.createElement('canvas');
                chartContainer.appendChild(canvas);
                
                // Format chart data
                const labels = data.map(item => new Date(item[0]).toLocaleDateString());
                const prices = data.map(item => item[4]); // Close price
                
                new Chart(canvas, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: `${symbol} Price`,
                            data: prices,
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
                                        return `${symbol}: $${formatNumber(context.raw)}`;
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
                document.getElementById('coinChartContainer').innerHTML = '<div class="p-6 text-center text-red-500">Error loading chart data.</div>';
            });
    }
    
    function formatNumber(num) {
        if (num === null || num === undefined) return 'N/A';
        
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
});