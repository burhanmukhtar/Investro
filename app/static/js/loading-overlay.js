// app/static/js/loading-overlay.js

/**
 * Loading Overlay Utility
 * 
 * A simple utility to show/hide a loading overlay during user actions
 * This makes use of the loading component from templates/components/loading.html
 */

const LoadingOverlay = {
    /**
     * Create the loading overlay element if it doesn't exist
     * @returns {HTMLElement} The loading overlay element
     */
    _createOverlay: function() {
        // Check if overlay already exists
        let overlay = document.getElementById('loading-overlay');
        if (overlay) {
            return overlay;
        }

        // Create the overlay element
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'fixed inset-0 bg-black bg-opacity-50 z-[9999] flex items-center justify-center transform scale-0 transition-transform duration-300';
        
        // Create the loading container
        const loadingContainer = document.createElement('div');
        loadingContainer.className = 'bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg max-w-sm mx-auto';
        
        // Create the loading spinner and message
        const loadingContent = document.createElement('div');
        loadingContent.className = 'flex flex-col items-center justify-center';
        loadingContent.innerHTML = `
            <div class="loader ease-linear rounded-full border-4 border-t-4 border-gray-200 h-12 w-12 mb-4 animate-spin"></div>
            <p class="text-gray-700 dark:text-gray-300" id="loading-message">Loading...</p>
        `;
        
        // Assemble the overlay
        loadingContainer.appendChild(loadingContent);
        overlay.appendChild(loadingContainer);
        document.body.appendChild(overlay);
        
        return overlay;
    },
    
    /**
     * Show the loading overlay
     * @param {string} message - Optional message to display
     */
    show: function(message = 'Loading...') {
        const overlay = this._createOverlay();
        
        // Update the message if provided
        const messageElement = overlay.querySelector('#loading-message');
        if (messageElement) {
            messageElement.textContent = message;
        }
        
        // Show the overlay with animation
        setTimeout(() => {
            overlay.classList.remove('scale-0');
        }, 10); // Small delay for the animation to work
    },
    
    /**
     * Hide the loading overlay
     */
    hide: function() {
        const overlay = document.getElementById('loading-overlay');
        if (!overlay) return;
        
        // Hide with animation
        overlay.classList.add('scale-0');
    },
    
    /**
     * Show loading for a specific element (button, form, etc)
     * @param {HTMLElement} element - Element to show loading state for
     * @param {string} loadingText - Optional loading text
     * @returns {Function} Function to restore the element to its original state
     */
    showElementLoading: function(element, loadingText = 'Loading...') {
        if (!element) return () => {};
        
        // Save original content and disabled state
        const originalContent = element.innerHTML;
        const originalDisabled = element.disabled;
        
        // Set loading state
        element.disabled = true;
        
        // Show loading spinner in the element
        if (element.tagName === 'BUTTON') {
            element.innerHTML = `
                <span class="inline-block h-4 w-4 border-2 border-t-2 border-white rounded-full animate-spin mr-2"></span>
                ${loadingText}
            `;
        } else {
            // For non-button elements, just add a loading class
            element.classList.add('opacity-50');
        }
        
        // Return function to restore original state
        return function() {
            if (element.tagName === 'BUTTON') {
                element.innerHTML = originalContent;
            } else {
                element.classList.remove('opacity-50');
            }
            element.disabled = originalDisabled;
        };
    },
    
    /**
     * Automatically handle loading state for forms
     * Shows loading overlay when form is submitted
     */
    setupFormLoading: function() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', function() {
                // Ignore forms with data-no-loading attribute
                if (this.hasAttribute('data-no-loading')) return;
                
                // Find submit button
                const submitButton = this.querySelector('button[type="submit"]');
                
                // Show loading on button if present, otherwise show overlay
                if (submitButton) {
                    LoadingOverlay.showElementLoading(submitButton, 'Submitting...');
                } else {
                    LoadingOverlay.show('Submitting...');
                }
            });
        });
    },
    
    /**
     * Setup AJAX loading indicators
     * Shows loading overlay for fetch and XMLHttpRequest calls
     */
    setupAjaxLoading: function() {
        // Intercept fetch API
        const originalFetch = window.fetch;
        window.fetch = function() {
            // Show loading unless the URL includes 'no-loading'
            const url = arguments[0];
            const showLoading = typeof url === 'string' && !url.includes('no-loading');
            
            if (showLoading) {
                LoadingOverlay.show();
            }
            
            return originalFetch.apply(this, arguments)
                .then(response => {
                    if (showLoading) LoadingOverlay.hide();
                    return response;
                })
                .catch(error => {
                    if (showLoading) LoadingOverlay.hide();
                    throw error;
                });
        };
        
        // Intercept XMLHttpRequest
        const originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function() {
            const url = arguments[1];
            const showLoading = typeof url === 'string' && !url.includes('no-loading');
            
            if (showLoading) {
                this.addEventListener('loadstart', () => LoadingOverlay.show());
                this.addEventListener('loadend', () => LoadingOverlay.hide());
            }
            
            return originalOpen.apply(this, arguments);
        };
    },
    
    /**
     * Initialize loading overlay functionality
     */
    init: function() {
        // Create the style for the loading spinner
        const style = document.createElement('style');
        style.textContent = `
            @keyframes spinner {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .loader {
                border-top-color: #3498db;
            }
            
            .dark .loader {
                border-top-color: #60a5fa;
            }
        `;
        document.head.appendChild(style);
        
        // Setup form loading indicators
        this.setupFormLoading();
        
        // Setup AJAX loading indicators
        this.setupAjaxLoading();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    LoadingOverlay.init();
});

// Expose globally
window.LoadingOverlay = LoadingOverlay;