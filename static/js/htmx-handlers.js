// HTMX Handlers for TubeCMS

// Initialize HTMX extensions
document.addEventListener('DOMContentLoaded', function() {
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

    // Handle errors
    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error('HTMX Error:', evt.detail);
        showNotification('Произошла ошибка. Попробуйте еще раз.', 'error');
    });

    // Handle network errors
    document.body.addEventListener('htmx:sendError', function(evt) {
        console.error('HTMX Send Error:', evt.detail);
        showNotification('Ошибка сети. Проверьте подключение.', 'error');
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

// Search suggestions
function setupSearchSuggestions() {
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        let timeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const query = this.value.trim();
                if (query.length >= 2) {
                    fetch(`/videos/htmx/search-suggestions/?q=${encodeURIComponent(query)}`)
                        .then(response => response.json())
                        .then(data => {
                            showSearchSuggestions(data.suggestions);
                        })
                        .catch(error => console.error('Search suggestions error:', error));
                } else {
                    hideSearchSuggestions();
                }
            }, 300);
        });
    }
}

function showSearchSuggestions(suggestions) {
    hideSearchSuggestions();
    
    if (suggestions.length === 0) return;
    
    const container = document.createElement('div');
    container.className = 'search-suggestions';
    container.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        box-shadow: var(--shadow);
        z-index: 1000;
        max-height: 200px;
        overflow-y: auto;
    `;
    
    suggestions.forEach(suggestion => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.textContent = suggestion;
        item.style.cssText = `
            padding: 10px 15px;
            cursor: pointer;
            border-bottom: 1px solid var(--border-color);
        `;
        
        item.addEventListener('click', function() {
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.value = suggestion;
                searchInput.form.submit();
            }
        });
        
        container.appendChild(item);
    });
    
    const searchBar = document.querySelector('.search-bar');
    if (searchBar) {
        searchBar.style.position = 'relative';
        searchBar.appendChild(container);
    }
}

function hideSearchSuggestions() {
    const existing = document.querySelector('.search-suggestions');
    if (existing) {
        existing.remove();
    }
}

// Initialize search suggestions
document.addEventListener('DOMContentLoaded', setupSearchSuggestions);

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

// Close suggestions when clicking outside
document.addEventListener('click', function(e) {
    if (!e.target.closest('.search-bar')) {
        hideSearchSuggestions();
    }
});


