/**
 * Video Processing Progress Tracker
 * Polls server for video processing progress and updates UI
 */

class VideoProgressTracker {
    constructor(videoId, options = {}) {
        this.videoId = videoId;
        this.options = {
            pollInterval: 2000, // 2 seconds
            maxRetries: 3,
            onProgress: null,
            onComplete: null,
            onError: null,
            ...options
        };
        
        this.isPolling = false;
        this.retryCount = 0;
        this.pollTimer = null;
    }
    
    /**
     * Start polling for progress updates
     */
    start() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.retryCount = 0;
        this.poll();
    }
    
    /**
     * Stop polling
     */
    stop() {
        this.isPolling = false;
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
    }
    
    /**
     * Poll server for progress
     */
    async poll() {
        if (!this.isPolling) return;
        
        try {
            const response = await fetch(`/videos/api/progress/${this.videoId}/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.retryCount = 0; // Reset retry count on success
            
            // Call progress callback
            if (this.options.onProgress) {
                this.options.onProgress(data);
            }
            
            // Check if processing is complete
            if (data.is_completed) {
                this.stop();
                if (this.options.onComplete) {
                    this.options.onComplete(data);
                }
                return;
            }
            
            // Check if processing failed
            if (data.is_failed) {
                this.stop();
                if (this.options.onError) {
                    this.options.onError(data);
                }
                return;
            }
            
            // Schedule next poll
            this.scheduleNextPoll();
            
        } catch (error) {
            console.error('Progress poll error:', error);
            this.retryCount++;
            
            if (this.retryCount >= this.options.maxRetries) {
                this.stop();
                if (this.options.onError) {
                    this.options.onError({
                        error_message: 'Failed to get progress after multiple retries'
                    });
                }
            } else {
                // Retry with exponential backoff
                const delay = this.options.pollInterval * Math.pow(2, this.retryCount);
                this.pollTimer = setTimeout(() => this.poll(), delay);
            }
        }
    }
    
    /**
     * Schedule next poll
     */
    scheduleNextPoll() {
        this.pollTimer = setTimeout(() => this.poll(), this.options.pollInterval);
    }
    
    /**
     * Retry failed processing
     */
    async retry() {
        try {
            const response = await fetch(`/videos/api/retry/${this.videoId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json',
                },
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Restart polling
                this.start();
                return true;
            } else {
                console.error('Retry failed:', data.error);
                return false;
            }
            
        } catch (error) {
            console.error('Retry request failed:', error);
            return false;
        }
    }
    
    /**
     * Get CSRF token from meta tag or cookie
     */
    getCSRFToken() {
        // Try meta tag first
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        
        // Fallback to cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        return '';
    }
}

/**
 * Initialize progress tracking for video upload/processing pages
 */
document.addEventListener('DOMContentLoaded', function() {
    // Look for video progress containers
    const progressContainers = document.querySelectorAll('[data-video-progress]');
    
    progressContainers.forEach(container => {
        const videoId = container.dataset.videoId;
        if (!videoId) return;
        
        const progressBar = container.querySelector('.progress-bar');
        const progressText = container.querySelector('.progress-text');
        const retryButton = container.querySelector('.retry-button');
        
        const tracker = new VideoProgressTracker(videoId, {
            onProgress: (data) => {
                // Update progress bar
                if (progressBar) {
                    progressBar.style.width = `${data.progress}%`;
                    progressBar.setAttribute('aria-valuenow', data.progress);
                }
                
                // Update progress text
                if (progressText) {
                    progressText.textContent = `${data.progress}% - ${data.status}`;
                }
                
                // Update container class
                container.className = `video-progress processing`;
            },
            
            onComplete: (data) => {
                // Update UI for completion
                if (progressBar) {
                    progressBar.style.width = '100%';
                    progressBar.classList.add('progress-complete');
                }
                
                if (progressText) {
                    progressText.textContent = 'Processing completed!';
                }
                
                container.className = 'video-progress completed';
                
                // Redirect or refresh after delay
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            },
            
            onError: (data) => {
                // Update UI for error
                if (progressBar) {
                    progressBar.classList.add('progress-error');
                }
                
                if (progressText) {
                    progressText.textContent = data.error_message || 'Processing failed';
                }
                
                container.className = 'video-progress error';
                
                // Show retry button
                if (retryButton) {
                    retryButton.style.display = 'inline-block';
                }
            }
        });
        
        // Handle retry button
        if (retryButton) {
            retryButton.addEventListener('click', async () => {
                retryButton.disabled = true;
                retryButton.textContent = 'Retrying...';
                
                const success = await tracker.retry();
                
                if (success) {
                    retryButton.style.display = 'none';
                    container.className = 'video-progress processing';
                } else {
                    retryButton.disabled = false;
                    retryButton.textContent = 'Retry';
                }
            });
        }
        
        // Start tracking if video is in processing state
        const initialStatus = container.dataset.processingStatus;
        if (initialStatus === 'pending' || initialStatus === 'processing') {
            tracker.start();
        }
    });
});

// Export for use in other scripts
window.VideoProgressTracker = VideoProgressTracker;