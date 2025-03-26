// global-dark-mode.js - Add to static/js folder and include in base.html

/**
 * Global Dark Mode Implementation
 * This script handles dark mode across the entire application
 */

// Initialize dark mode as soon as possible to prevent flash of light mode
(function() {
    // Check for dark mode in localStorage or from server settings
    function initializeDarkMode() {
      const darkModeEnabled = localStorage.getItem('darkMode') === 'true';
      
      if (darkModeEnabled) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
    
    // Initialize immediately
    initializeDarkMode();
    
    // Also initialize when DOM is ready for any event handlers
    document.addEventListener('DOMContentLoaded', function() {
      // Find dark mode toggle if it exists on this page
      const darkModeToggle = document.getElementById('themeToggle');
      if (darkModeToggle) {
        darkModeToggle.checked = localStorage.getItem('darkMode') === 'true';
        
        // Add event listener to toggle
        darkModeToggle.addEventListener('change', function() {
          toggleDarkMode(this.checked);
        });
      }
      
      // Re-apply dark mode (in case CSS loads after this script)
      initializeDarkMode();
    });
  })();
  
  /**
   * Toggle dark mode across the application
   * @param {boolean} enable - Whether to enable dark mode
   */
  function toggleDarkMode(enable) {
    // Save setting to localStorage for persistence
    localStorage.setItem('darkMode', enable);
    
    // Apply dark mode to HTML root element
    if (enable) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    
    // Dispatch a custom event so other scripts can react to dark mode changes
    const event = new CustomEvent('darkModeChange', { detail: { darkMode: enable } });
    document.dispatchEvent(event);
    
    // If we're on the settings page, update the setting in the database
    const isSettingsPage = window.location.pathname.includes('/settings');
    if (isSettingsPage && typeof saveAllSettings === 'function') {
      // Don't save immediately to avoid excessive API calls
      if (window.darkModeTimeout) {
        clearTimeout(window.darkModeTimeout);
      }
      
      // Save after a brief delay
      window.darkModeTimeout = setTimeout(function() {
        saveAllSettings();
      }, 500);
    }
  }