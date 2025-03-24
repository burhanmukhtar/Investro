// app/static/js/market.js
// Market page functionality for the crypto trading platform

/**
 * Load market data from the API
 */
function loadMarketData() {
    const marketTable = document.getElementById('marketTable');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessage = document.getElementById('errorMessage');
    
    if (!marketTable) return;
    
    // Show loading indicator
    if (loadingIndicator) {
        loadingIndicator.classList.remove('hidden');
    }
    
    // Hide error message
    if (errorMessage) {
        errorMessage.classList.add('hidden');
    }
    
    // Fetch market data from API
    fetch('/market/data')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.classList.add('hidden');
            }
            
            // Check if data is valid
            if (!data || !Array.isArray(data)) {
                throw new Error('Invalid data format received');
            }
            
            // Populate table with market data
            populateMarketTable(data);
        })
        .catch(error => {
            console.error('Error fetching market data:', error);
            
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.classList.add('hidden');
            }
            
            // Show error message
            if (errorMessage) {
                errorMessage.classList.remove('hidden');
                errorMessage.textContent = 'Error loading market data. Please try again.';
            }
        });
}

/**
 * Populate the market table with data
 * @param {Array} data - Market data array
 */
function populateMarketTable(data) {
    const tableBody = document.querySelector('#marketTable tbody');
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Sort data by market cap
    data.sort((a, b) => (b.market_cap || 0) - (a.market_cap || 0));
    
    // Create rows for each coin
    data.forEach(coin => {
        if (!coin) return; // Skip if coin data is missing
        
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 dark:hover:bg-gray-800';
        
        // Format the price change
        const priceChange = coin.price_change_percentage_24h || 0;
        const priceChangeClass = priceChange >= 0 ? 'text-green-600' : 'text-red-600';
        const priceChangePrefix = priceChange >= 0 ? '+' : '';
        
        // Safe getters for coin properties
        const getSymbol = () => coin.symbol || '?';
        const getName = () => coin.name || 'Unknown';
        const getPrice = () => formatCurrency(coin.current_price || 0);
        const getMarketCap = () => formatCurrency(coin.market_cap || 0, true);
        const getVolume = () => formatCurrency(coin.total_volume || 0, true);
        
        // Create row content
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <div class="flex-shrink-0 h-8 w-8">
                        <img class="h-8 w-8 rounded-full" src="${coin.image || '/static/images/placeholder.png'}" alt="${getSymbol()}">
                    </div>
                    <div class="ml-4">
                        <div class="font-medium text-gray-900 dark:text-white">${getSymbol()}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${getName()}</div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900 dark:text-white">${getPrice()}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="text-sm font-medium ${priceChangeClass}">
                    ${priceChangePrefix}${priceChange.toFixed(2)}%
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                ${getMarketCap()}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                ${getVolume()}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <a href="/market/view/${getSymbol()}" class="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300">Details</a>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Add data-symbol attribute to each row
    tableBody.querySelectorAll('tr').forEach((row, index) => {
        if (data[index] && data[index].symbol) {
            row.setAttribute('data-symbol', data[index].symbol);
        }
    });
}

/**
 * Format currency values
 * @param {number} value - Currency value to format
 * @param {boolean} compact - Whether to use compact notation for large numbers
 * @returns {string} Formatted currency string
 */
function formatCurrency(value, compact = false) {
    // Handle non-numeric values
    if (typeof value !== 'number') {
        return '$0.00';
    }
    
    // For large numbers, use compact notation
    if (compact && value >= 1e9) {
        return `$${(value / 1e9).toFixed(2)}B`;
    } else if (compact && value >= 1e6) {
        return `$${(value / 1e6).toFixed(2)}M`;
    } else if (compact && value >= 1e3) {
        return `$${(value / 1e3).toFixed(2)}K`;
    }
    
    // Format based on value size
    if (value >= 1) {
        return `$${value.toFixed(2)}`;
    } else if (value >= 0.01) {
        return `$${value.toFixed(4)}`;
    } else {
        return `$${value.toFixed(8)}`;
    }
}

/**
 * Search the market table
 * @param {Event} event - Input event
 */
function searchMarket(event) {
    const searchTerm = event.target.value.toLowerCase().trim();
    const tableRows = document.querySelectorAll('#marketTable tbody tr');
    
    tableRows.forEach(row => {
        const symbol = (row.getAttribute('data-symbol') || '').toLowerCase();
        const name = row.querySelector('td:first-child .text-gray-500')?.textContent.toLowerCase() || '';
        
        if (symbol.includes(searchTerm) || name.includes(searchTerm)) {
            row.classList.remove('hidden');
        } else {
            row.classList.add('hidden');
        }
    });
    
    // Check if no results found
    const visibleRows = document.querySelectorAll('#marketTable tbody tr:not(.hidden)');
    const noResultsMessage = document.getElementById('noResultsMessage');
    
    if (noResultsMessage) {
        if (visibleRows.length === 0 && searchTerm.length > 0) {
            noResultsMessage.classList.remove('hidden');
        } else {
            noResultsMessage.classList.add('hidden');
        }
    }
}

/**
 * Load and display coin details
 * @param {string} symbol - Coin symbol
 */
function loadCoinDetails(symbol) {
    const detailsContainer = document.getElementById('coinDetails');
    const chartContainer = document.getElementById('coinChart');
    const loadingIndicator = document.getElementById('detailsLoading');
    const errorMessage = document.getElementById('detailsError');
    
    if (!detailsContainer || !chartContainer) return;
    
    // Show loading indicator
    if (loadingIndicator) {
        loadingIndicator.classList.remove('hidden');
    }
    
    // Hide error message
    if (errorMessage) {
        errorMessage.classList.add('hidden');
    }
    
    // Fetch coin details from API
    fetch(`/market/coin/${symbol}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(result => {
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.classList.add('hidden');
            }
            
            // Check if result is valid and has data property
            if (!result || !result.data) {
                throw new Error('Invalid data format received');
            }
            
            const data = result.data;
            
            // Populate details
            populateCoinDetails(data, detailsContainer);
            
            // Initialize chart
            initializeCoinChart(symbol, chartContainer);
        })
        .catch(error => {
            console.error('Error fetching coin data:', error);
            
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.classList.add('hidden');
            }
            
            // Show error message
            if (errorMessage) {
                errorMessage.classList.remove('hidden');
                errorMessage.textContent = 'Error loading coin details. Please try again.';
            }
        });
}

/**
 * Populate coin details container
 * @param {Object} data - Coin data
 * @param {HTMLElement} container - Container element
 */
function populateCoinDetails(data, container) {
    // Format price change values with proper classes
    const formatChange = (change) => {
        if (!change && change !== 0) return '<span class="text-gray-500">N/A</span>';
        
        const isPositive = change >= 0;
        const colorClass = isPositive ? 'text-green-600' : 'text-red-600';
        const prefix = isPositive ? '+' : '';
        
        return `<span class="${colorClass}">${prefix}${change.toFixed(2)}%</span>`;
    };
    
    // Safe accessors for potentially missing data
    const safe = {
        name: data.name || 'Unknown Coin',
        symbol: data.symbol || '?',
        currentPrice: formatCurrency(data.current_price || 0),
        marketCap: formatCurrency(data.market_cap || 0, true),
        volume: formatCurrency(data.total_volume || 0, true),
        change24h: formatChange(data.price_change_percentage_24h),
        change7d: formatChange(data.price_change_percentage_7d),
        change30d: formatChange(data.price_change_percentage_30d),
        circulatingSupply: data.circulating_supply ? 
            `${new Intl.NumberFormat().format(data.circulating_supply)} ${data.symbol}` : 
            'N/A',
        totalSupply: data.total_supply ? 
            `${new Intl.NumberFormat().format(data.total_supply)} ${data.symbol}` : 
            'N/A',
        maxSupply: data.max_supply ? 
            `${new Intl.NumberFormat().format(data.max_supply)} ${data.symbol}` : 
            'N/A',
        ath: data.ath ? formatCurrency(data.ath) : 'N/A',
        atl: data.atl ? formatCurrency(data.atl) : 'N/A'
    };
    
    // Create the HTML content
    container.innerHTML = `
        <div class="bg-white dark:bg-gray-800 shadow-sm rounded-lg p-6">
            <div class="flex items-center mb-6">
                <img src="${data.image || '/static/images/placeholder.png'}" alt="${safe.symbol}" class="w-16 h-16 rounded-full">
                <div class="ml-4">
                    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">${safe.name} (${safe.symbol})</h1>
                    <div class="text-3xl font-semibold mt-1 text-gray-900 dark:text-white">${safe.currentPrice}</div>
                    <div class="text-sm mt-1">${safe.change24h} (24h)</div>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h2 class="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Market Stats</h2>
                    <table class="w-full text-sm">
                        <tr>
                            <td class="py-2 text-gray-500 dark:text-gray-400">Market Cap</td>
                            <td class="py-2 text-right text-gray-900 dark:text-white">${safe.marketCap}</td>
                        </tr>
                        <tr>
                            <td class="py-2 text-gray-500 dark:text-gray-400">Trading Volume (24h)</td>
                            <td class="py-2 text-right text-gray-900 dark:text-white">${safe.volume}</td>
                        </tr>
                        <tr>
                            <td class="py-2 text-gray-500 dark:text-gray-400">Circulating Supply</td>
                            <td class="py-2 text-right text-gray-900 dark:text-white">${safe.circulatingSupply}</td>
                        </tr>
                        <tr>
                            <td class="py-2 text-gray-500 dark:text-gray-400">Total Supply</td>
                            <td class="py-2 text-right text-gray-900 dark:text-white">${safe.totalSupply}</td>
                        </tr>
                        <tr>
                            <td class="py-2 text-gray-500 dark:text-gray-400">Max Supply</td>
                            <td class="py-2 text-right text-gray-900 dark:text-white">${safe.maxSupply}</td>
                        </tr>
                    </table>
                </div>
                
                <div>
                    <h2 class="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Price History</h2>
                    <table class="w-full text-sm">
                        <tr>
                            <td class="py-2 text-gray-500 dark:text-gray-400">7-day Change</td>
                            <td class="py-2 text-right">${safe.change7d}</td>
                        </tr>
                        <tr>
                            <td class="py-2 text-gray-500 dark:text-gray-400">30-day Change</td>
                            <td class="py-2 text-right">${safe.change30d}</td>
                        </tr>
                        <tr>
                            <td class="py-2 text-gray-500 dark:text-gray-400">All-Time High</td>
                            <td class="py-2 text-right text-gray-900 dark:text-white">${safe.ath}</td>
                        </tr>
                        <tr>
                            <td class="py-2 text-gray-500 dark:text-gray-400">All-Time Low</td>
                            <td class="py-2 text-right text-gray-900 dark:text-white">${safe.atl}</td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <div class="mt-6">
                <h2 class="text-lg font-semibold mb-2 text-gray-900 dark:text-white">Description</h2>
                <div class="text-gray-700 dark:text-gray-300 text-sm">
                    ${data.description ? data.description : 'No description available.'}
                </div>
            </div>
        </div>
    `;
}