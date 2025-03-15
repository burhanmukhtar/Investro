// app/static/js/app.js
// Main JavaScript file for the crypto trading platform

/**
 * Initialize the application when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeUI();
    setupEventListeners();
    
    // Initialize specific page functionality based on current page
    if (document.body.classList.contains('home-page')) {
        initializeHomePage();
    } else if (document.body.classList.contains('market-page')) {
        initializeMarketPage();
    } else if (document.body.classList.contains('future-page')) {
        initializeFuturePage();
    } else if (document.body.classList.contains('assets-page')) {
        initializeAssetsPage();
    }
});

/**
 * Initialize UI components that are common across all pages
 */
function initializeUI() {
    // Initialize mobile navigation
    initMobileNavigation();
    
    // Initialize flash messages auto-dismiss
    initFlashMessages();
    
    // Set active navigation item based on current page
    setActiveNavItem();
    
    // Handle any modals on the page
    initModals();
    
    // Initialize any clipboard copy functionality
    initClipboardCopy();
}

/**
 * Set up event listeners for interactive elements
 */
function setupEventListeners() {
    // Add event listeners for logout button
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (confirm('Are you sure you want to log out?')) {
                window.location.href = this.getAttribute('href');
            }
        });
    }
    
    // Add theme toggle if available
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('change', toggleDarkMode);
        
        // Set initial state based on saved preference
        if (localStorage.getItem('darkMode') === 'enabled') {
            document.documentElement.classList.add('dark');
            themeToggle.checked = true;
        }
    }
    
    // Add responsive table handling
    initResponsiveTables();
}

/**
 * Initialize mobile navigation
 */
function initMobileNavigation() {
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebarClose = document.getElementById('closeSidebar');
    const sidebar = document.getElementById('sidebar');
    
    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener('click', function() {
            sidebar.classList.remove('-translate-x-full');
        });
    }
    
    if (sidebarClose && sidebar) {
        sidebarClose.addEventListener('click', function() {
            sidebar.classList.add('-translate-x-full');
        });
        
        // Close sidebar when clicking outside
        sidebar.addEventListener('click', function(e) {
            if (e.target === sidebar) {
                sidebar.classList.add('-translate-x-full');
            }
        });
    }
}

/**
 * Initialize flash messages auto-dismiss
 */
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length > 0) {
        setTimeout(function() {
            flashMessages.forEach(message => {
                message.style.opacity = '0';
                setTimeout(function() {
                    message.remove();
                }, 300);
            });
        }, 5000);
        
        // Add close functionality to flash messages
        flashMessages.forEach(message => {
            const closeBtn = message.querySelector('.close-btn');
            if (closeBtn) {
                closeBtn.addEventListener('click', function() {
                    message.style.opacity = '0';
                    setTimeout(function() {
                        message.remove();
                    }, 300);
                });
            }
        });
    }
}

/**
 * Set active navigation item based on current page
 */
function setActiveNavItem() {
    // Get current URL path
    const path = window.location.pathname;
    
    // Find all navigation links
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === path) {
            link.classList.add('active-nav-link');
        }
    });
    
    // Set active bottom nav item
    const bottomNavLinks = document.querySelectorAll('.bottom-nav-link');
    bottomNavLinks.forEach(link => {
        if (link.getAttribute('href') === path) {
            link.classList.add('text-primary-600');
            link.classList.remove('text-gray-500');
        }
    });
}

/**
 * Initialize modals
 */
function initModals() {
    const modalTriggers = document.querySelectorAll('[data-modal-target]');
    const modalCloseButtons = document.querySelectorAll('[data-modal-close]');
    
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const modalId = this.dataset.modalTarget;
            const modal = document.getElementById(modalId);
            
            if (modal) {
                modal.classList.remove('scale-0', 'hidden');
                modal.classList.add('scale-100');
            }
        });
    });
    
    modalCloseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            
            if (modal) {
                modal.classList.remove('scale-100');
                modal.classList.add('scale-0');
                
                // Hide the modal after animation completes
                setTimeout(function() {
                    modal.classList.add('hidden');
                }, 300);
            }
        });
    });
    
    // Close modal when clicking outside content
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('scale-100');
            e.target.classList.add('scale-0');
            
            // Hide the modal after animation completes
            setTimeout(function() {
                e.target.classList.add('hidden');
            }, 300);
        }
    });
}

/**
 * Initialize clipboard copy functionality
 */
function initClipboardCopy() {
    const copyButtons = document.querySelectorAll('.copy-btn');
    
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.dataset.copyText || this.previousElementSibling.textContent;
            
            navigator.clipboard.writeText(textToCopy)
                .then(() => {
                    // Show success feedback
                    const originalContent = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check"></i>';
                    
                    // Restore original content after 2 seconds
                    setTimeout(() => {
                        this.innerHTML = originalContent;
                    }, 2000);
                })
                .catch(err => {
                    console.error('Could not copy text: ', err);
                });
        });
    });
}

/**
 * Toggle dark mode
 */
function toggleDarkMode() {
    if (document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('darkMode', 'disabled');
    } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('darkMode', 'enabled');
    }
}

/**
 * Initialize responsive tables
 */
function initResponsiveTables() {
    const tables = document.querySelectorAll('.responsive-table');
    
    tables.forEach(table => {
        // Get headers
        const headers = Array.from(table.querySelectorAll('thead th')).map(header => header.textContent);
        
        // Add data-label attribute to each cell
        table.querySelectorAll('tbody tr').forEach(row => {
            Array.from(row.querySelectorAll('td')).forEach((cell, index) => {
                if (headers[index]) {
                    cell.setAttribute('data-label', headers[index]);
                }
            });
        });
    });
}

/**
 * Initialize Home Page
 */
function initializeHomePage() {
    // Initialize market overview chart
    const marketChartElement = document.getElementById('marketChart');
    if (marketChartElement) {
        initializeMarketChart(marketChartElement);
    }
    
    // Initialize announcements slider
    const announcementSlider = document.querySelector('.announcement-slider');
    if (announcementSlider) {
        initializeAnnouncementSlider(announcementSlider);
    }
    
    // Initialize actions buttons
    const moreActionsBtn = document.getElementById('moreActionsBtn');
    const moreActionsPopup = document.getElementById('moreActionsPopup');
    
    if (moreActionsBtn && moreActionsPopup) {
        moreActionsBtn.addEventListener('click', function() {
            moreActionsPopup.classList.remove('translate-y-full');
        });
        
        // Close popup when clicking outside
        moreActionsPopup.addEventListener('click', function(e) {
            if (e.target === moreActionsPopup) {
                moreActionsPopup.classList.add('translate-y-full');
            }
        });
        
        const closeMoreActions = document.getElementById('closeMoreActions');
        if (closeMoreActions) {
            closeMoreActions.addEventListener('click', function() {
                moreActionsPopup.classList.add('translate-y-full');
            });
        }
    }
}

/**
 * Initialize Market Page
 */
function initializeMarketPage() {
    // Load market data
    loadMarketData();
    
    // Initialize search functionality
    const marketSearch = document.getElementById('marketSearch');
    if (marketSearch) {
        marketSearch.addEventListener('input', searchMarket);
    }
}

/**
 * Initialize Future Page
 */
function initializeFuturePage() {
    // Initialize TradingView chart
    initializeTradingViewChart();
    
    // Load positions, orders, and signals
    loadPositions();
    loadTradeSignals();
}

/**
 * Initialize Assets Page
 */
function initializeAssetsPage() {
    // Initialize wallet tabs
    const spotTab = document.getElementById('spotTab');
    const fundingTab = document.getElementById('fundingTab');
    
    if (spotTab && fundingTab) {
        spotTab.addEventListener('click', function() {
            switchWalletTab('spot');
        });
        
        fundingTab.addEventListener('click', function() {
            switchWalletTab('funding');
        });
    }
    
    // Initialize balance filter toggle
    const hideZeroBalances = document.getElementById('hideZeroBalances');
    if (hideZeroBalances) {
        hideZeroBalances.addEventListener('click', toggleZeroBalances);
    }
}

// Additional utility functions will be implemented as needed