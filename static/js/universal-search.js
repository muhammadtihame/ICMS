/**
 * Universal Search Suggestions Component
 * Provides real-time search suggestions for all search bars in the CMS
 * Features: Case-insensitive, space/dot handling, real-time suggestions
 */

class UniversalSearch {
    constructor(searchInput, options = {}) {
        this.searchInput = searchInput;
        this.options = {
            minLength: 2,
            delay: 300,
            maxSuggestions: 20,
            apiUrl: '/search-suggestions/',
            ...options
        };
        
        this.suggestionsContainer = null;
        this.debounceTimer = null;
        this.currentQuery = '';
        
        this.init();
    }
    
    init() {
        this.createSuggestionsContainer();
        this.bindEvents();
    }
    
    createSuggestionsContainer() {
        // Create suggestions dropdown container
        this.suggestionsContainer = document.createElement('div');
        this.suggestionsContainer.className = 'universal-search-suggestions';
        this.suggestionsContainer.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 8px 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            max-height: 400px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        `;
        
        // Insert after search input
        this.searchInput.parentNode.style.position = 'relative';
        this.searchInput.parentNode.insertBefore(this.suggestionsContainer, this.searchInput.nextSibling);
    }
    
    bindEvents() {
        // Input event with debouncing
        this.searchInput.addEventListener('input', (e) => {
            this.currentQuery = e.target.value.trim();
            this.debounceSearch();
        });
        
        // Focus event
        this.searchInput.addEventListener('focus', () => {
            if (this.currentQuery.length >= this.options.minLength) {
                this.showSuggestions();
            }
        });
        
        // Click outside to hide suggestions
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.suggestionsContainer.contains(e.target)) {
                this.hideSuggestions();
            }
        });
        
        // Keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateSuggestions('down');
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateSuggestions('up');
            } else if (e.key === 'Enter') {
                e.preventDefault();
                this.selectCurrentSuggestion();
            } else if (e.key === 'Escape') {
                this.hideSuggestions();
            }
        });
    }
    
    debounceSearch() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            if (this.currentQuery.length >= this.options.minLength) {
                this.fetchSuggestions();
            } else {
                this.hideSuggestions();
            }
        }, this.options.delay);
    }
    
    async fetchSuggestions() {
        try {
            const response = await fetch(`${this.options.apiUrl}?q=${encodeURIComponent(this.currentQuery)}`);
            const data = await response.json();
            
            if (data.suggestions && data.suggestions.length > 0) {
                this.renderSuggestions(data.suggestions);
                this.showSuggestions();
            } else {
                this.hideSuggestions();
            }
        } catch (error) {
            console.error('Search suggestions error:', error);
            this.hideSuggestions();
        }
    }
    
    renderSuggestions(suggestions) {
        this.suggestionsContainer.innerHTML = '';
        
        suggestions.forEach((suggestion, index) => {
            const suggestionElement = document.createElement('div');
            suggestionElement.className = 'search-suggestion-item';
            suggestionElement.dataset.index = index;
            suggestionElement.style.cssText = `
                padding: 12px 16px;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
                display: flex;
                align-items: center;
                gap: 12px;
                transition: background-color 0.2s;
            `;
            
            suggestionElement.innerHTML = `
                <span style="font-size: 18px;">${suggestion.icon}</span>
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #333; margin-bottom: 2px;">${suggestion.title}</div>
                    <div style="font-size: 12px; color: #666;">${suggestion.subtitle}</div>
                </div>
                <span style="font-size: 12px; color: #999; text-transform: uppercase;">${suggestion.type}</span>
            `;
            
            // Hover effects
            suggestionElement.addEventListener('mouseenter', () => {
                suggestionElement.style.backgroundColor = '#f8f9fa';
            });
            
            suggestionElement.addEventListener('mouseleave', () => {
                suggestionElement.style.backgroundColor = 'white';
            });
            
            // Click to navigate
            suggestionElement.addEventListener('click', () => {
                window.location.href = suggestion.url;
            });
            
            this.suggestionsContainer.appendChild(suggestionElement);
        });
    }
    
    showSuggestions() {
        this.suggestionsContainer.style.display = 'block';
    }
    
    hideSuggestions() {
        this.suggestionsContainer.style.display = 'none';
    }
    
    navigateSuggestions(direction) {
        const items = this.suggestionsContainer.querySelectorAll('.search-suggestion-item');
        if (items.length === 0) return;
        
        const currentIndex = parseInt(this.suggestionsContainer.querySelector('.search-suggestion-item.selected')?.dataset.index || -1);
        let newIndex;
        
        if (direction === 'down') {
            newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        } else {
            newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        }
        
        // Remove previous selection
        items.forEach(item => item.classList.remove('selected'));
        
        // Add new selection
        items[newIndex].classList.add('selected');
        items[newIndex].style.backgroundColor = '#e3f2fd';
        
        // Scroll into view if needed
        items[newIndex].scrollIntoView({ block: 'nearest' });
    }
    
    selectCurrentSuggestion() {
        const selectedItem = this.suggestionsContainer.querySelector('.search-suggestion-item.selected');
        if (selectedItem) {
            selectedItem.click();
        }
    }
}

// Auto-initialize for search inputs with data-universal-search attribute
document.addEventListener('DOMContentLoaded', function() {
    const searchInputs = document.querySelectorAll('input[data-universal-search="true"]');
    searchInputs.forEach(input => {
        new UniversalSearch(input);
    });
});

// Export for manual initialization
window.UniversalSearch = UniversalSearch;
