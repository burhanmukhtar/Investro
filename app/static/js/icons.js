// app/static/js/icons.js
// Simple icon alternatives when Lucide/React is not available

/**
 * Create a simple custom icon using SVG
 * This function provides fallbacks if the Lucide React library isn't loaded properly
 * 
 * @param {string} iconName - Name of the icon to create
 * @param {number} size - Size of the icon in pixels
 * @param {string} color - Color of the icon
 * @returns {HTMLElement} - The SVG icon element
 */
function createIcon(iconName, size = 24, color = 'currentColor') {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', size);
    svg.setAttribute('height', size);
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', color);
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.classList.add('icon', `icon-${iconName}`);

    // Define paths for common icons
    switch (iconName) {
        case 'bell':
            svg.innerHTML = `
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
            `;
            break;
        case 'arrow-right':
            svg.innerHTML = `
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
            `;
            break;
        case 'x':
            svg.innerHTML = `
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            `;
            break;
        case 'award':
            svg.innerHTML = `
                <circle cx="12" cy="8" r="7"></circle>
                <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline>
            `;
            break;
        case 'zap':
            svg.innerHTML = `
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            `;
            break;
        case 'bar-chart':
            svg.innerHTML = `
                <line x1="12" y1="20" x2="12" y2="10"></line>
                <line x1="18" y1="20" x2="18" y2="4"></line>
                <line x1="6" y1="20" x2="6" y2="16"></line>
            `;
            break;
        case 'rocket':
            svg.innerHTML = `
                <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path>
                <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path>
                <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"></path>
                <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"></path>
            `;
            break;
        default:
            // Default placeholder icon (circle)
            svg.innerHTML = `<circle cx="12" cy="12" r="10"></circle>`;
    }

    return svg;
}

/**
 * A simple banner component to replace React components when they fail to load
 * 
 * @param {Array} announcements - Array of announcement objects
 * @param {HTMLElement} container - Container element for the banner
 */
function createAnnouncementBanner(announcements, container) {
    if (!announcements || !announcements.length || !container) return;

    // Create banner element
    const banner = document.createElement('div');
    banner.className = 'w-full max-w-5xl mx-auto';
    
    // Create the first announcement (simple version)
    const announcement = announcements[0];
    
    // Create banner content
    banner.innerHTML = `
        <div class="relative rounded-lg shadow-sm border overflow-hidden bg-indigo-50 border-indigo-200 py-3 px-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3 flex-1">
                    <div class="flex-shrink-0" id="icon-placeholder"></div>
                    <div class="flex-1">
                        <h3 class="font-bold text-gray-900 flex items-center">
                            ${announcement.title || 'Announcement'}
                        </h3>
                        <p class="text-sm text-gray-700 line-clamp-1">${announcement.content || ''}</p>
                    </div>
                </div>
                
                <div class="flex items-center space-x-2 ml-2">
                    <button class="text-gray-500 hover:text-gray-700 flex-shrink-0" id="close-btn">
                        <span class="sr-only">Dismiss</span>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Append to container
    container.innerHTML = '';
    container.appendChild(banner);
    
    // Add icon
    const iconPlaceholder = banner.querySelector('#icon-placeholder');
    if (iconPlaceholder) {
        const icon = createIcon('bell', 20, '#6366f1');
        iconPlaceholder.appendChild(icon);
    }
    
    // Add close button icon
    const closeBtn = banner.querySelector('#close-btn');
    if (closeBtn) {
        const closeIcon = createIcon('x', 16);
        closeBtn.appendChild(closeIcon);
        
        // Add event listener
        closeBtn.addEventListener('click', function() {
            banner.remove();
        });
    }
}

// Fallback function to load announcements without React
function loadAnnouncementBanner() {
    const container = document.getElementById('announcement-container');
    if (!container) return;
    
    // Fetch announcements from API
    fetch('/api/announcements')
        .then(response => response.json())
        .then(data => {
            createAnnouncementBanner(data, container);
        })
        .catch(error => {
            console.error('Error loading announcements:', error);
            
            // Create a fallback announcement
            const fallbackAnnouncements = [{
                title: "Welcome to Investro",
                content: "Your trusted platform for cryptocurrency trading.",
                type: "feature",
                priority: "medium"
            }];
            
            createAnnouncementBanner(fallbackAnnouncements, container);
        });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if we need to use fallback icons
    try {
        // If lucide-react is properly loaded, it should have a global object
        if (typeof lucide === 'undefined') {
            loadAnnouncementBanner();
        }
    } catch (e) {
        console.warn("Using fallback icons due to missing dependencies:", e);
        loadAnnouncementBanner();
    }
});