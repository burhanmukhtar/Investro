document.addEventListener('DOMContentLoaded', function() {
    // Variables
    let currentPage = 1;
    let totalPages = 1;
    let sortField = 'date';
    let sortDirection = 'desc';
    let transactions = [];
    
    // Elements
    const transactionsTableBody = document.getElementById('transactionsTableBody');
    const currentPageSpan = document.getElementById('currentPage');
    const totalPagesSpan = document.getElementById('totalPages');
    const prevPageBtn = document.getElementById('prevPageBtn');
    const nextPageBtn = document.getElementById('nextPageBtn');
    const filterForm = document.getElementById('filterForm');
    const exportButton = document.getElementById('exportButton');
    const sortButtons = document.querySelectorAll('[data-sort]');
    
    // Modal elements
    const transactionDetailsModal = document.getElementById('transactionDetailsModal');
    const closeModal = document.getElementById('closeModal');
    const txId = document.getElementById('txId');
    const txDate = document.getElementById('txDate');
    const txType = document.getElementById('txType');
    const txAmount = document.getElementById('txAmount');
    const txStatus = document.getElementById('txStatus');
    const txFrom = document.getElementById('txFrom');
    const txTo = document.getElementById('txTo');
    const txFee = document.getElementById('txFee');
    const txBlockchainId = document.getElementById('txBlockchainId');
    const txNotes = document.getElementById('txNotes');
    const txFromContainer = document.getElementById('txFromContainer');
    const txToContainer = document.getElementById('txToContainer');
    const txFeeContainer = document.getElementById('txFeeContainer');
    const txBlockchainContainer = document.getElementById('txBlockchainContainer');
    const txNotesContainer = document.getElementById('txNotesContainer');
    
    // Initialize
    loadTransactions();
    
    // Event listeners
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            currentPage = 1;
            loadTransactions();
        });
    }
    
    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', function() {
            if (currentPage > 1) {
                currentPage--;
                loadTransactions();
            }
        });
    }
    
    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', function() {
            if (currentPage < totalPages) {
                currentPage++;
                loadTransactions();
            }
        });
    }
    
    if (sortButtons) {
        sortButtons.forEach(button => {
            button.addEventListener('click', function() {
                const field = this.dataset.sort;
                
                if (sortField === field) {
                    // Toggle sort direction
                    sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    // New sort field
                    sortField = field;
                    sortDirection = 'asc';
                }
                
                // Update sort icons
                sortButtons.forEach(btn => {
                    const icon = btn.querySelector('i');
                    if (btn.dataset.sort === sortField) {
                        icon.className = `fas fa-sort-${sortDirection === 'asc' ? 'up' : 'down'} ml-1`;
                    } else {
                        icon.className = 'fas fa-sort ml-1';
                    }
                });
                
                loadTransactions();
            });
        });
    }
    
    if (closeModal) {
        closeModal.addEventListener('click', function() {
            transactionDetailsModal.classList.add('scale-0');
        });
    }
    
    if (transactionDetailsModal) {
        transactionDetailsModal.addEventListener('click', function(e) {
            if (e.target === transactionDetailsModal) {
                transactionDetailsModal.classList.add('scale-0');
            }
        });
    }
    
    if (exportButton) {
        exportButton.addEventListener('click', function() {
            exportTransactions();
        });
    }
    
    // Function to load transactions from API
    function loadTransactions() {
        // Show loading state
        if (transactionsTableBody) {
            transactionsTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-12 text-center text-gray-500">
                        <i class="fas fa-spinner fa-spin text-4xl mb-3"></i>
                        <p>Loading transactions...</p>
                    </td>
                </tr>
            `;
        }
        
        // Get filter values
        const type = document.getElementById('type')?.value || 'all';
        const status = document.getElementById('status')?.value || 'all';
        const currency = document.getElementById('currency')?.value || 'all';
        const dateRange = document.getElementById('dateRange')?.value || 'all';
        
        // Build the API query parameters
        const params = new URLSearchParams({
            page: currentPage,
            per_page: 20,
            sort_field: sortField,
            sort_dir: sortDirection
        });
        
        if (type !== 'all') params.append('type', type);
        if (status !== 'all') params.append('status', status);
        if (currency !== 'all') params.append('currency', currency);
        if (dateRange !== 'all') params.append('date_range', dateRange);
        
        // Fetch data from our API
        fetch(`/user/api/transactions?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    transactions = data.transactions;
                    totalPages = data.pagination.total_pages;
                    
                    // Update pagination
                    if (currentPageSpan) currentPageSpan.textContent = currentPage;
                    if (totalPagesSpan) totalPagesSpan.textContent = totalPages;
                    
                    // Enable/disable pagination buttons
                    if (prevPageBtn) {
                        prevPageBtn.disabled = currentPage <= 1;
                        prevPageBtn.className = `relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md ${
                            prevPageBtn.disabled ? 'text-gray-300 bg-gray-50 cursor-not-allowed' : 'text-gray-700 bg-white hover:bg-gray-50'
                        }`;
                    }
                    
                    if (nextPageBtn) {
                        nextPageBtn.disabled = currentPage >= totalPages;
                        nextPageBtn.className = `relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md ${
                            nextPageBtn.disabled ? 'text-gray-300 bg-gray-50 cursor-not-allowed' : 'text-gray-700 bg-white hover:bg-gray-50'
                        }`;
                    }
                    
                    // Render transactions
                    renderTransactions(transactions);
                } else {
                    // Show error message
                    if (transactionsTableBody) {
                        transactionsTableBody.innerHTML = `
                            <tr>
                                <td colspan="5" class="px-6 py-12 text-center text-gray-500">
                                    <p>Error loading transactions: ${data.message}</p>
                                </td>
                            </tr>
                        `;
                    }
                }
            })
            .catch(error => {
                console.error('Error fetching transaction data:', error);
                // Show error message
                if (transactionsTableBody) {
                    transactionsTableBody.innerHTML = `
                        <tr>
                            <td colspan="5" class="px-6 py-12 text-center text-gray-500">
                                <p>Error loading transactions. Please try again later.</p>
                            </td>
                        </tr>
                    `;
                }
            });
    }
    
    function renderTransactions(transactions) {
        if (!transactionsTableBody) return;
        
        if (transactions.length === 0) {
            transactionsTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-12 text-center text-gray-500">
                        <p>No transactions found.</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        let html = '';
        
        transactions.forEach(tx => {
            const statusClass = tx.status === 'completed' ? 'bg-green-100 text-green-800' : 
                               tx.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 
                               'bg-red-100 text-red-800';
            
            html += `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-900">${formatDate(tx.created_at)}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-900">${capitalizeFirstLetter(tx.type)}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-900">${tx.amount} ${tx.currency}</div>
                        ${tx.fee ? `<div class="text-xs text-gray-500">Fee: ${tx.fee} ${tx.currency}</div>` : ''}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">
                            ${capitalizeFirstLetter(tx.status)}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="view-transaction-btn text-primary-600 hover:text-primary-900" data-id="${tx.id}">
                            View
                        </button>
                    </td>
                </tr>
            `;
        });
        
        transactionsTableBody.innerHTML = html;
        
        // Add event listeners to view buttons
        const viewButtons = document.querySelectorAll('.view-transaction-btn');
        viewButtons.forEach(button => {
            button.addEventListener('click', function() {
                const txId = this.dataset.id;
                fetchTransactionDetails(txId);
            });
        });
    }
    
    function fetchTransactionDetails(transactionId) {
        // Show loading in modal
        showTransactionDetails({
            transaction_id: 'Loading...',
            created_at: new Date().toISOString(),
            transaction_type: 'Loading...',
            status: 'loading',
            currency: '',
            amount: '',
            from_wallet: '',
            to_wallet: '',
            fee: '',
            blockchain_txid: '',
            notes: 'Loading transaction details...'
        });
        
        // Fetch transaction details
        fetch(`/user/api/transactions/${transactionId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showTransactionDetails(data.transaction);
                } else {
                    showTransactionDetails({
                        transaction_id: 'Error',
                        created_at: new Date().toISOString(),
                        transaction_type: 'Error',
                        status: 'error',
                        currency: '',
                        amount: '',
                        from_wallet: '',
                        to_wallet: '',
                        fee: '',
                        blockchain_txid: '',
                        notes: `Error loading transaction details: ${data.message}`
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching transaction details:', error);
                showTransactionDetails({
                    transaction_id: 'Error',
                    created_at: new Date().toISOString(),
                    transaction_type: 'Error',
                    status: 'error',
                    currency: '',
                    amount: '',
                    from_wallet: '',
                    to_wallet: '',
                    fee: '',
                    blockchain_txid: '',
                    notes: 'Error loading transaction details. Please try again later.'
                });
            });
    }
    
    function showTransactionDetails(transaction) {
        if (!transactionDetailsModal) return;
        
        // Update modal content
        if (txId) txId.textContent = transaction.transaction_id;
        if (txDate) txDate.textContent = formatDate(transaction.created_at);
        if (txType) txType.textContent = capitalizeFirstLetter(transaction.transaction_type);
        if (txAmount) txAmount.textContent = `${transaction.amount} ${transaction.currency}`;
        if (txStatus) txStatus.textContent = capitalizeFirstLetter(transaction.status);
        
        // From wallet
        if (transaction.from_wallet) {
            if (txFromContainer) txFromContainer.classList.remove('hidden');
            if (txFrom) txFrom.textContent = capitalizeFirstLetter(transaction.from_wallet);
        } else {
            if (txFromContainer) txFromContainer.classList.add('hidden');
        }
        
        // To wallet
        if (transaction.to_wallet) {
            if (txToContainer) txToContainer.classList.remove('hidden');
            if (txTo) txTo.textContent = capitalizeFirstLetter(transaction.to_wallet);
        } else {
            if (txToContainer) txToContainer.classList.add('hidden');
        }
        
        // Fee
        if (transaction.fee) {
            if (txFeeContainer) txFeeContainer.classList.remove('hidden');
            if (txFee) txFee.textContent = `${transaction.fee} ${transaction.currency}`;
        } else {
            if (txFeeContainer) txFeeContainer.classList.add('hidden');
        }
        
        // Blockchain TxID
        if (transaction.blockchain_txid) {
            if (txBlockchainContainer) txBlockchainContainer.classList.remove('hidden');
            if (txBlockchainId) txBlockchainId.textContent = transaction.blockchain_txid;
        } else {
            if (txBlockchainContainer) txBlockchainContainer.classList.add('hidden');
        }
        
        // Notes
        if (transaction.notes) {
            if (txNotesContainer) txNotesContainer.classList.remove('hidden');
            if (txNotes) txNotes.textContent = transaction.notes;
        } else {
            if (txNotesContainer) txNotesContainer.classList.add('hidden');
        }
        
        // Show modal
        transactionDetailsModal.classList.remove('scale-0');
    }
    
    function exportTransactions() {
        // Get filter values
        const type = document.getElementById('type')?.value || 'all';
        const status = document.getElementById('status')?.value || 'all';
        const currency = document.getElementById('currency')?.value || 'all';
        const dateRange = document.getElementById('dateRange')?.value || 'all';
        
        // Build the API query parameters
        const params = new URLSearchParams({
            export: 'csv',
            type: type,
            status: status,
            currency: currency,
            date_range: dateRange
        });
        
        // Redirect to export endpoint
        window.location.href = `/user/api/transactions/export?${params.toString()}`;
    }
    
    // Helper functions
    function formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString();
    }
    
    function capitalizeFirstLetter(string) {
        if (!string) return '';
        return string.charAt(0).toUpperCase() + string.slice(1);
    }
});