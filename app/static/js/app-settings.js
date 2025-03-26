// app-settings.js - Global app settings handler
// Place this file in your static/js directory

/**
 * Global App Settings
 * This script initializes and manages app settings across all pages
 * Default settings: Dark mode enabled, medium font size, English language
 */

// Initialize settings as soon as possible to prevent flashes of unstyled content
(function() {
    // Apply dark mode - default to true (dark mode)
    const darkModeEnabled = localStorage.getItem('darkMode') !== 'false'; // Default to true
    if (darkModeEnabled) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    
    // Apply font size - default to medium
    const fontSize = localStorage.getItem('fontSize') || 'medium';
    applyFontSize(fontSize);
    
    // Apply language - default to 'en'
    const language = localStorage.getItem('language') || 'en';
    document.documentElement.setAttribute('lang', language);
    
    // When DOM is ready, set up event listeners and fully initialize
    document.addEventListener('DOMContentLoaded', function() {
      // Initialize all settings properly
      initializeAppSettings();
      
      // Set up the settings toggles if they exist on this page
      setupSettingsControls();
    });
  })();
  
  /**
   * Initialize all application settings
   */
  function initializeAppSettings() {
    // This will be called when the DOM is ready
    // Try to get settings from the server if the user is logged in
    const isLoggedIn = document.body.classList.contains('logged-in');
    
    if (isLoggedIn) {
      // Fetch user settings from the server
      fetch('/user/api/settings')
        .then(response => response.json())
        .then(data => {
          if (data.success && data.settings) {
            // Apply and save all settings
            applyAllSettings(data.settings);
            saveSettingsToLocalStorage(data.settings);
          } else {
            // Fall back to localStorage
            applySettingsFromLocalStorage();
          }
        })
        .catch(error => {
          console.error('Error loading settings:', error);
          // Fall back to localStorage if API fails
          applySettingsFromLocalStorage();
        });
    } else {
      // Not logged in, just use localStorage
      applySettingsFromLocalStorage();
    }
  }
  
  /**
   * Apply all settings from localStorage
   */
  function applySettingsFromLocalStorage() {
    // Dark mode - default to true
    const darkMode = localStorage.getItem('darkMode') !== 'false'; // Default to true
    toggleDarkMode(darkMode);
    
    // Font size - default to medium
    const fontSize = localStorage.getItem('fontSize') || 'medium';
    applyFontSize(fontSize);
    
    // Language - default to 'en'
    const language = localStorage.getItem('language') || 'en';
    applyLanguage(language);
  }
  
  /**
   * Apply all settings from a settings object
   * @param {Object} settings - The settings object from the server or localStorage
   */
  function applyAllSettings(settings) {
    // Dark mode
    if (typeof settings.darkMode !== 'undefined') {
      toggleDarkMode(settings.darkMode);
    } else {
      toggleDarkMode(true); // Default to dark mode
    }
    
    // Font size
    if (settings.display && settings.display.fontSize) {
      applyFontSize(settings.display.fontSize);
    }
    
    // Language
    if (settings.language) {
      applyLanguage(settings.language);
    }
  }
  
  /**
   * Save settings to localStorage for persistence across pages
   * @param {Object} settings - The settings object to save
   */
  function saveSettingsToLocalStorage(settings) {
    // Save individual settings to localStorage for easy access
    if (typeof settings.darkMode !== 'undefined') {
      localStorage.setItem('darkMode', settings.darkMode);
    }
    
    if (settings.display && settings.display.fontSize) {
      localStorage.setItem('fontSize', settings.display.fontSize);
    }
    
    if (settings.language) {
      localStorage.setItem('language', settings.language);
    }
    
    // Also save the whole settings object for reference
    try {
      localStorage.setItem('userSettings', JSON.stringify(settings));
    } catch (e) {
      console.error('Error saving settings to localStorage:', e);
    }
  }
  
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
    
    // Update themeToggle if it exists on this page
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
      themeToggle.checked = enable;
    }
    
    // Dispatch a custom event so other scripts can react to dark mode changes
    const event = new CustomEvent('darkModeChange', { detail: { darkMode: enable } });
    document.dispatchEvent(event);
  }
  
  /**
   * Apply font size to the entire application
   * @param {string} size - The font size to apply (small, medium, large, xlarge)
   */
  function applyFontSize(size) {
    // Save setting to localStorage for persistence
    localStorage.setItem('fontSize', size);
    
    const html = document.documentElement;
    
    // Remove existing size classes
    html.classList.remove('text-xs', 'text-sm', 'text-base', 'text-lg');
    
    // Add appropriate size class
    switch(size) {
      case 'small':
        html.classList.add('text-xs');
        break;
      case 'medium':
        html.classList.add('text-sm');
        break;
      case 'large':
        html.classList.add('text-base');
      break;
    case 'xlarge':
      html.classList.add('text-lg');
      break;
    default:
      html.classList.add('text-sm'); // Default to medium
  }
  
  // Update font size selector if it exists on this page
  const fontSizeSelect = document.getElementById('fontSizeSelect');
  if (fontSizeSelect) {
    fontSizeSelect.value = size;
  }
  
  // Dispatch a custom event
  const event = new CustomEvent('fontSizeChange', { detail: { fontSize: size } });
  document.dispatchEvent(event);
}

/**
 * Apply language setting to the entire application
 * @param {string} lang - The language code to apply
 */
function applyLanguage(lang) {
  // Save setting to localStorage for persistence
  localStorage.setItem('language', lang);
  
  // Set HTML lang attribute
  document.documentElement.setAttribute('lang', lang);
  
  // Update language selector if it exists on this page
  const languageSelect = document.getElementById('languageSelect');
  if (languageSelect) {
    languageSelect.value = lang;
  }
  
  // Dispatch a custom event
  const event = new CustomEvent('languageChange', { detail: { language: lang } });
  document.dispatchEvent(event);
}

/**
 * Setup settings controls on the settings page
 */
function setupSettingsControls() {
  // Theme toggle
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    // Set initial state
    themeToggle.checked = localStorage.getItem('darkMode') !== 'false'; // Default to true
    
    // Add event listener
    themeToggle.addEventListener('change', function() {
      toggleDarkMode(this.checked);
      
      // If we're on the settings page, save to database
      if (window.location.pathname.includes('/settings') && typeof saveAllSettings === 'function') {
        // Debounce to avoid excessive API calls
        if (window.themeTimeout) clearTimeout(window.themeTimeout);
        window.themeTimeout = setTimeout(saveAllSettings, 500);
      }
    });
  }
  
  // Font size selector
  const fontSizeSelect = document.getElementById('fontSizeSelect');
  if (fontSizeSelect) {
    // Set initial state
    fontSizeSelect.value = localStorage.getItem('fontSize') || 'medium';
    
    // Add event listener
    fontSizeSelect.addEventListener('change', function() {
      applyFontSize(this.value);
      
      // If we're on the settings page, save to database
      if (window.location.pathname.includes('/settings') && typeof saveAllSettings === 'function') {
        // Debounce to avoid excessive API calls
        if (window.fontSizeTimeout) clearTimeout(window.fontSizeTimeout);
        window.fontSizeTimeout = setTimeout(saveAllSettings, 500);
      }
    });
  }
  
  // Language selector
  const languageSelect = document.getElementById('languageSelect');
  if (languageSelect) {
    // Set initial state
    languageSelect.value = localStorage.getItem('language') || 'en';
    
    // Add event listener
    languageSelect.addEventListener('change', function() {
      applyLanguage(this.value);
      
      // If we're on the settings page, save to database
      if (window.location.pathname.includes('/settings') && typeof saveAllSettings === 'function') {
        // Debounce to avoid excessive API calls
        if (window.languageTimeout) clearTimeout(window.languageTimeout);
        window.languageTimeout = setTimeout(saveAllSettings, 500);
      }
    });
  }
}

/**
 * Helper function to save all settings to the server via the settings API
 * This is called from the settings page
 */
function saveAllSettings() {
  // Check if we're logged in
  const isLoggedIn = document.body.classList.contains('logged-in');
  if (!isLoggedIn) return;
  
  // Get settings to save
  const settings = {
    darkMode: localStorage.getItem('darkMode') !== 'false',
    language: localStorage.getItem('language') || 'en',
    display: {
      fontSize: localStorage.getItem('fontSize') || 'medium'
    }
  };
  
  // On the settings page, other values will be gathered through the form
  // This is just for direct settings changes via toggle/select
  
  // Send to server
  fetch('/user/api/settings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
    },
    body: JSON.stringify(settings)
  })
  .then(response => response.json())
  .then(data => {
    // Optional: handle server response here
    if (!data.success) {
      console.error('Failed to save settings:', data.message);
    }
  })
  .catch(error => {
    console.error('Error saving settings:', error);
  });
}

// Export functions for use in other scripts
window.appSettings = {
  toggleDarkMode,
  applyFontSize,
  applyLanguage,
  applyAllSettings,
  saveSettingsToLocalStorage,
  saveAllSettings
};