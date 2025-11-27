// HTMX Handlers for TubeCMS

// Initialize HTMX extensions
document.addEventListener('DOMContentLoaded', function() {
    // CSRF token handling for HTMX requests
    document.body.addEventListener('htmx:configRequest', function(evt) {
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfTokenMeta) {
            evt.detail.headers['X-CSRFToken'] = csrfTokenMeta.content;
        } else {
            // Fallback to cookie
            const csrfCookie = document.cookie.match(/csrftoken=([^;]+)/);
            if (csrfCookie) {
                evt.detail.headers['X-CSRFToken'] = csrfCookie[1];
            }
        }
    });
    
    // Add loading indicators
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        const target = evt.target;
        if (target.hasAttribute('hx-indicator')) {
            const indicator = document.querySelector(target.getAttribute('hx-indicator'));
            if (indicator) {
                indicator.style.display = 'block';
            }
        }
    });

    document.body.addEventListener('htmx:afterRequest', function(evt) {
        const target = evt.target;
        if (target.hasAttribute('hx-indicator')) {
            const indicator = document.querySelector(target.getAttribute('hx-indicator'));
            if (indicator) {
                indicator.style.display = 'none';
            }
        }
    });

    // Handle form submissions
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        if (evt.detail.xhr.status === 200) {
            // Clear form if it's a comment form
            const form = evt.target;
            if (form.tagName === 'FORM' && form.querySelector('textarea[name="content"]')) {
                form.reset();
            }
        }
    });

    // Prevent HTMX from swapping JSON responses
    document.body.addEventListener('htmx:beforeSwap', function(evt) {
        const xhr = evt.detail.xhr;
        const target = evt.target;
        
        if (xhr && target && target.hasAttribute('hx-swap') && target.getAttribute('hx-swap') === 'none') {
            const contentType = xhr.getResponseHeader('Content-Type') || '';
            if (contentType.includes('application/json')) {
                // Prevent HTMX from swapping JSON
                evt.detail.shouldSwap = false;
            }
        }
    });
    
    // Handle JSON responses for friend requests and subscriptions
    // Try both afterRequest and afterSwap events
    function handleJsonResponse(evt) {
        const xhr = evt.detail.xhr;
        const target = evt.target;
        
        if (!xhr) return;
        
        // Check if response is JSON (by content-type or by trying to parse)
        let response = null;
        const contentType = xhr.getResponseHeader('Content-Type') || '';
        const responseText = xhr.responseText || '';
        
        // Try to parse JSON if content-type indicates JSON or if hx-swap is none
        if (contentType.includes('application/json') || (target && target.hasAttribute('hx-swap') && target.getAttribute('hx-swap') === 'none')) {
            try {
                if (responseText.trim()) {
                    response = JSON.parse(responseText);
                } else {
                    return;
                }
            } catch (e) {
                // Not JSON, ignore
                console.log('Failed to parse as JSON:', e, responseText.substring(0, 100));
                return;
            }
        } else {
            // Try to parse anyway if it looks like JSON
            try {
                const text = responseText.trim();
                if (text.startsWith('{') || text.startsWith('[')) {
                    response = JSON.parse(text);
                } else {
                    return;
                }
            } catch (e) {
                return;
            }
        }
        
        if (!response) return;
        
        console.log('JSON response received:', response);
        
        // Handle friend request response
        if (response.status === 'sent' && response.message) {
            showNotification(JSON.stringify(response), 'success');
            // Update button state
            if (target && target.closest('.friend-button-container')) {
                const container = target.closest('.friend-button-container');
                container.innerHTML = '<button class="btn btn-secondary" disabled><i class="fas fa-clock"></i> Запрос отправлен</button>';
            }
            return;
        }
        
        // Handle subscription response
        if (response.status === 'subscribed' && response.subscribers_count !== undefined) {
            showNotification(JSON.stringify(response), 'success');
            // Update button text
            if (target && target.classList.contains('subscribe-btn')) {
                target.innerHTML = '<i class="fas fa-user-check"></i> Отписаться';
                const currentUrl = target.getAttribute('hx-post');
                if (currentUrl) {
                    target.setAttribute('hx-post', currentUrl.replace('subscribe', 'unsubscribe'));
                }
            }
            // Update subscribers count if element exists
            const subscribersEl = document.querySelector('.subscribers-count, .subscribers');
            if (subscribersEl) {
                subscribersEl.textContent = response.subscribers_count + ' подписчиков';
            }
            return;
        }
        
        // Handle unsubscribe response
        if (response.status === 'unsubscribed' && response.subscribers_count !== undefined) {
            showNotification(JSON.stringify(response), 'info');
            if (target && target.classList.contains('subscribe-btn')) {
                target.innerHTML = '<i class="fas fa-user-plus"></i> Подписаться';
                const currentUrl = target.getAttribute('hx-post');
                if (currentUrl) {
                    target.setAttribute('hx-post', currentUrl.replace('unsubscribe', 'subscribe'));
                }
            }
            const subscribersEl = document.querySelector('.subscribers-count, .subscribers');
            if (subscribersEl) {
                subscribersEl.textContent = response.subscribers_count + ' подписчиков';
            }
            return;
        }
        
        // Handle other JSON responses (like errors)
        if (response.error) {
            showNotification(response.error, 'error');
            return;
        }
    }
    
    // Attach to both events
    document.body.addEventListener('htmx:afterRequest', handleJsonResponse);
    document.body.addEventListener('htmx:afterSwap', handleJsonResponse);

    // Handle errors - improved error handling
    document.body.addEventListener('htmx:responseError', function(evt) {
        console.log('HTMX Response Error:', evt.detail);
        const xhr = evt.detail.xhr;
        if (xhr) {
            console.log('XHR Status:', xhr.status);
            console.log('XHR Response:', xhr.responseText.substring(0, 200));
            
            // Handle specific HTTP status codes
            if (xhr.status === 403) {
                showNotification('Доступ запрещен', 'error');
                return;
            } else if (xhr.status === 404) {
                showNotification('Ресурс не найден', 'error');
                return;
            } else if (xhr.status >= 500) {
                showNotification('Ошибка сервера. Попробуйте позже.', 'error');
                return;
            }
            
            // Try to parse JSON error response
            try {
                const response = JSON.parse(xhr.responseText);
                if (response.error) {
                    showNotification(response.error, 'error');
                    return;
                }
            } catch (e) {
                // Not JSON, show generic error
                if (xhr.status !== 200) {
                    showNotification('Произошла ошибка. Попробуйте еще раз.', 'error');
                }
            }
        } else if (evt.detail.failed) {
            showNotification('Произошла ошибка. Попробуйте еще раз.', 'error');
        }
    });

    // Handle network errors
    document.body.addEventListener('htmx:sendError', function(evt) {
        console.error('HTMX Send Error:', evt.detail);
        showNotification('Ошибка сети. Проверьте подключение.', 'error');
    });

    // Debug successful requests
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        const xhr = evt.detail.xhr;
        const target = evt.target;
        
        // Log search requests specifically
        if (target && target.name === 'q' && xhr.status === 200) {
            console.log('Search request successful:', {
                url: xhr.responseURL,
                status: xhr.status,
                contentLength: xhr.responseText.length,
                target: target
            });
        }
    });
});

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    if (type === 'success') {
        notification.style.backgroundColor = '#28a745';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#dc3545';
    } else {
        notification.style.backgroundColor = '#17a2b8';
    }
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Video upload progress
function updateUploadProgress(progress) {
    const progressBar = document.querySelector('.upload-progress-bar');
    if (progressBar) {
        progressBar.style.width = progress + '%';
        progressBar.textContent = Math.round(progress) + '%';
    }
}

// Like/Dislike functionality
function toggleLike(videoId, value) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/videos/${videoId}/like/`;
    
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'value';
    input.value = value;
    
    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
}


// Video preview hover functionality
document.addEventListener('DOMContentLoaded', function() {
    const videoCards = document.querySelectorAll('.video-card');
    
    videoCards.forEach(card => {
        const previewVideo = card.querySelector('.preview-video');
        if (!previewVideo) return;
        
        let isPlaying = false;
        
        // Ensure video is ready
        previewVideo.addEventListener('loadedmetadata', function() {
            console.log('Video metadata loaded');
        });
        
        // Handle video load errors
        previewVideo.addEventListener('error', function(e) {
            console.log('Video load error:', e);
        });
        
        card.addEventListener('mouseenter', function() {
            if (previewVideo && !isPlaying) {
                previewVideo.currentTime = 0;
                // Try to play the video
                previewVideo.play().then(() => {
                    isPlaying = true;
                    console.log('Video started playing');
                }).catch(e => {
                    console.log('Video autoplay prevented:', e);
                    // Try to play again after a short delay
                    setTimeout(() => {
                        previewVideo.play().then(() => {
                            isPlaying = true;
                            console.log('Video started playing after delay');
                        }).catch(() => {
                            console.log('Video still cannot play');
                        });
                    }, 100);
                });
            }
        });
        
        card.addEventListener('mouseleave', function() {
            if (previewVideo && isPlaying) {
                previewVideo.pause();
                previewVideo.currentTime = 0;
                isPlaying = false;
            }
        });
    });
});

// Close search dropdown when clicking outside
document.addEventListener('click', function(e) {
    if (!e.target.closest('.search-bar')) {
        const dropdown = document.getElementById('search-dropdown-results');
        if (dropdown) {
            dropdown.innerHTML = '';
        }
    }
});

// Handle search input events
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('.search-form input[name="q"]');
    if (searchInput) {
        // Handle Enter key to navigate to full results
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && this.value.trim().length >= 2) {
                e.preventDefault();
                const form = this.closest('form');
                if (form) {
                    form.action = form.getAttribute('action');
                    form.submit();
                }
            }
            // Close dropdown on Escape
            if (e.key === 'Escape') {
                const dropdown = document.getElementById('search-dropdown-results');
                if (dropdown) {
                    dropdown.innerHTML = '';
                }
                this.blur();
            }
        });
        
        // Close dropdown when input loses focus (but keep it open while hovering dropdown)
        searchInput.addEventListener('blur', function(e) {
            // Delay to allow clicks on dropdown items
            setTimeout(function() {
                const dropdown = document.getElementById('search-dropdown-results');
                if (dropdown && !document.activeElement.closest('.search-dropdown-results')) {
                    dropdown.innerHTML = '';
                }
            }, 200);
        });
    }
    
    // Handle clicks on search results
    document.addEventListener('click', function(e) {
        const resultItem = e.target.closest('.search-result-item');
        if (resultItem) {
            // Allow navigation and close dropdown
            const dropdown = document.getElementById('search-dropdown-results');
            if (dropdown) {
                dropdown.innerHTML = '';
            }
        }
    });
});


document.addEventListener('DOMContentLoaded', function() {
    const list = document.getElementById('categories-list');
    const expand = document.getElementById('expand-btn');
    const collapse = document.getElementById('collapse-btn');
    if (list && expand && collapse) {
        expand.addEventListener('click', function() {
            list.classList.add('expanded');
            expand.style.display = 'none';
            collapse.style.display = 'block';
        });
        collapse.addEventListener('click', function() {
            list.classList.remove('expanded');
            expand.style.display = 'block';
            collapse.style.display = 'none';
        });
    }
});



// Enhanced Search Functionality
document.addEventListener('DOMContentLoaded', function() {
    let currentSearchType = 'all';
    
    // Handle search type filter buttons
    function handleSearchTypeFilter(type) {
        currentSearchType = type;
        const searchInput = document.querySelector('.search-form input[name="q"]');
        if (searchInput && searchInput.value.trim().length >= 2) {
            // Trigger search with new type
            const url = new URL(searchInput.getAttribute('hx-get'), window.location.origin);
            url.searchParams.set('type', type);
            url.searchParams.set('q', searchInput.value);
            
            // Update hx-get attribute temporarily
            const originalUrl = searchInput.getAttribute('hx-get');
            searchInput.setAttribute('hx-get', url.toString());
            
            // Trigger HTMX request
            htmx.trigger(searchInput, 'input');
            
            // Restore original URL
            setTimeout(() => {
                searchInput.setAttribute('hx-get', originalUrl);
            }, 100);
        }
        
        // Update active button
        document.querySelectorAll('.search-type-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-type="${type}"]`)?.classList.add('active');
    }
    
    // Add search type filters to dropdown when it appears
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        if (evt.target.id === 'search-dropdown-results') {
            const dropdown = evt.target;
            const query = document.querySelector('.search-form input[name="q"]')?.value || '';
            
            if (query.length >= 2 && dropdown.innerHTML.trim()) {
                // Add filter buttons at the top
                const filtersHtml = `
                    <div class="search-type-filters">
                        <button class="search-type-btn ${currentSearchType === 'all' ? 'active' : ''}" data-type="all">Все</button>
                        <button class="search-type-btn ${currentSearchType === 'videos' ? 'active' : ''}" data-type="videos">Видео</button>
                        <button class="search-type-btn ${currentSearchType === 'users' ? 'active' : ''}" data-type="users">Пользователи</button>
                        <button class="search-type-btn ${currentSearchType === 'categories' ? 'active' : ''}" data-type="categories">Категории</button>
                        <button class="search-type-btn ${currentSearchType === 'tags' ? 'active' : ''}" data-type="tags">Теги</button>
                    </div>
                `;
                dropdown.innerHTML = filtersHtml + dropdown.innerHTML;
                
                // Add event listeners to filter buttons
                dropdown.querySelectorAll('.search-type-btn').forEach(btn => {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        const type = this.getAttribute('data-type');
                        handleSearchTypeFilter(type);
                    });
                });
            }
        }
    });
    
    // Enhanced search input handling
    const searchInput = document.querySelector('.search-form input[name="q"]');
    if (searchInput) {
        // Modify HTMX request to include search type
        searchInput.addEventListener('htmx:configRequest', function(evt) {
            if (currentSearchType !== 'all') {
                evt.detail.parameters.type = currentSearchType;
            }
        });
        
        // Reset search type when input is cleared
        searchInput.addEventListener('input', function() {
            if (this.value.trim().length < 2) {
                currentSearchType = 'all';
            }
        });
    }
});

// Watch Later functionality
function toggleWatchLater(videoId, button) {
    const isActive = button.classList.contains('active');
    const url = isActive ? `/videos/${videoId}/remove-watch-later/` : `/videos/${videoId}/add-watch-later/`;
    
    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content,
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            button.classList.toggle('active');
            button.title = isActive ? 'Add to Watch Later' : 'Remove from Watch Later';
            showNotification(data.message, 'success');
        } else {
            showNotification(data.error || 'Error occurred', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Network error', 'error');
    });
}

// Favorites functionality
function toggleFavorite(videoId, button) {
    const isActive = button.classList.contains('active');
    const url = isActive ? `/videos/${videoId}/remove-favorite/` : `/videos/${videoId}/add-favorite/`;
    
    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content,
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            button.classList.toggle('active');
            button.title = isActive ? 'Add to Favorites' : 'Remove from Favorites';
            showNotification(data.message, 'success');
        } else {
            showNotification(data.error || 'Error occurred', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Network error', 'error');
    });
}

// Enhanced keyboard navigation for search
document.addEventListener('keydown', function(e) {
    const dropdown = document.getElementById('search-dropdown-results');
    if (!dropdown || !dropdown.innerHTML.trim()) return;
    
    const items = dropdown.querySelectorAll('.search-result-item');
    if (items.length === 0) return;
    
    let currentIndex = -1;
    items.forEach((item, index) => {
        if (item.classList.contains('highlighted')) {
            currentIndex = index;
        }
    });
    
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        items.forEach(item => item.classList.remove('highlighted'));
        currentIndex = (currentIndex + 1) % items.length;
        items[currentIndex].classList.add('highlighted');
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        items.forEach(item => item.classList.remove('highlighted'));
        currentIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
        items[currentIndex].classList.add('highlighted');
    } else if (e.key === 'Enter' && currentIndex >= 0) {
        e.preventDefault();
        items[currentIndex].click();
    }
});

// Add CSS for highlighted search results
const searchStyle = document.createElement('style');
searchStyle.textContent = `
    .search-result-item.highlighted {
        background-color: var(--bg-secondary) !important;
    }
`;
document.head.appendChild(searchStyle);

// Language Selector functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Language selector initializing...');
    
    // Handle language selector for authenticated users
    const langToggle = document.getElementById('langToggle');
    const langDropdown = document.getElementById('langDropdown');
    
    // Handle language selector for guest users
    const langToggleGuest = document.getElementById('langToggleGuest');
    const langDropdownGuest = document.getElementById('langDropdownGuest');
    
    console.log('Found elements:', {
        langToggle: !!langToggle,
        langDropdown: !!langDropdown,
        langToggleGuest: !!langToggleGuest,
        langDropdownGuest: !!langDropdownGuest
    });
    
    // Function to toggle dropdown
    function toggleLangDropdown(toggle, dropdown, name) {
        if (!toggle || !dropdown) {
            console.log(`Missing elements for ${name}:`, { toggle: !!toggle, dropdown: !!dropdown });
            return;
        }
        
        console.log(`Setting up ${name} dropdown`);
        
        toggle.addEventListener('click', function(e) {
            console.log(`${name} toggle clicked`);
            e.preventDefault();
            e.stopPropagation();
            
            // Close other dropdowns
            document.querySelectorAll('.lang-dropdown.show').forEach(dd => {
                if (dd !== dropdown) {
                    dd.classList.remove('show');
                }
            });
            
            dropdown.classList.toggle('show');
            console.log(`${name} dropdown toggled, show class:`, dropdown.classList.contains('show'));
        });
    }
    
    // Function to handle language selection
    function handleLangSelection(dropdown) {
        if (!dropdown) return;
        
        dropdown.addEventListener('click', function(e) {
            if (e.target.classList.contains('lang-dropdown-item')) {
                e.preventDefault();
                const selectedLang = e.target.getAttribute('data-lang');
                changeLanguage(selectedLang);
            }
        });
    }
    
    // Initialize dropdowns
    toggleLangDropdown(langToggle, langDropdown);
    toggleLangDropdown(langToggleGuest, langDropdownGuest);
    
    // Handle language selection
    handleLangSelection(langDropdown);
    handleLangSelection(langDropdownGuest);
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.lang-selector')) {
            document.querySelectorAll('.lang-dropdown.show').forEach(dropdown => {
                dropdown.classList.remove('show');
            });
        }
    });
});

// Function to change language
function changeLanguage(langCode) {
    // Create form and submit to change language
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/set-language/';
    
    // Add CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                     document.querySelector('meta[name="csrf-token"]')?.content ||
                     document.cookie.match(/csrftoken=([^;]+)/)?.[1];
    
    if (csrfToken) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
    }
    
    // Add language parameter
    const langInput = document.createElement('input');
    langInput.type = 'hidden';
    langInput.name = 'language';
    langInput.value = langCode;
    form.appendChild(langInput);
    
    // Add next parameter to redirect back to current page
    const nextInput = document.createElement('input');
    nextInput.type = 'hidden';
    nextInput.name = 'next';
    nextInput.value = window.location.pathname + window.location.search;
    form.appendChild(nextInput);
    
    document.body.appendChild(form);
    form.submit();
}

// Sha
re video functionality
function shareVideo(title, url) {
    const fullUrl = window.location.origin + url;
    
    // Check if Web Share API is available
    if (navigator.share) {
        navigator.share({
            title: title,
            url: fullUrl
        }).catch(err => {
            // User cancelled or error - fallback to copy
            copyToClipboard(fullUrl);
        });
    } else {
        // Fallback: copy to clipboard
        copyToClipboard(fullUrl);
    }
}

// Copy to clipboard helper
function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Link copied to clipboard!', 'success');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

// Fallback for older browsers
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();
    try {
        document.execCommand('copy');
        showNotification('Link copied to clipboard!', 'success');
    } catch (err) {
        showNotification('Failed to copy link', 'error');
    }
    document.body.removeChild(textArea);
}
