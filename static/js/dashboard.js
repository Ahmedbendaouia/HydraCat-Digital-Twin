/**
 * Marine Surveillance Dashboard JavaScript
 * Handles real-time updates and user interactions
 */

class MarineDashboard {
    constructor() {
        this.updateInterval = 3000; // 3 seconds
        this.timeInterval = 1000;   // 1 second
        this.isUpdating = true;
        
        this.init();
    }
    
    init() {
        console.log('🌊 Initializing Marine Surveillance Dashboard...');
        
        // Start initial updates
        this.updateTime();
        this.updateAllData();
        
        // Set up intervals
        this.startUpdateIntervals();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('✅ Dashboard initialized successfully');
    }
    
    startUpdateIntervals() {
        // Update time every second
        setInterval(() => {
            this.updateTime();
        }, this.timeInterval);
        
        // Update data every 3 seconds
        setInterval(() => {
            if (this.isUpdating) {
                this.updateAllData();
            }
        }, this.updateInterval);
    }
    
    updateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('fr-FR');
        const timeElement = document.getElementById('current-time');
        
        if (timeElement) {
            timeElement.textContent = timeString;
        }
    }
    
    async updateAllData() {
        try {
            await Promise.all([
                this.updateSystemStats(),
                this.updateDetections(),
                this.updateActivity(),
                this.updateCameraStats()
            ]);
        } catch (error) {
            console.error('Error updating dashboard data:', error);
        }
    }
    
    async updateSystemStats() {
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) throw new Error('Failed to fetch stats');
            
            const stats = await response.json();
            
            // Update overview cards
            this.updateElement('total-today', stats.total_detections_today);
            this.updateElement('session-count', stats.session_detections);
            this.updateElement('alert-count', stats.active_alerts);
            this.updateElement('uptime', stats.system_uptime + '%');
            
            // Add smooth animation to numbers
            this.animateCounters();
            
        } catch (error) {
            console.error('Error updating system stats:', error);
            this.showError('Failed to update system statistics');
        }
    }
    
    async updateDetections() {
        try {
            const response = await fetch('/api/detections');
            if (!response.ok) throw new Error('Failed to fetch detections');
            
            const detections = await response.json();
            
            const tbody = document.getElementById('detection-tbody');
            if (!tbody) return;
            
            tbody.innerHTML = '';
            
            detections.forEach(detection => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${detection.source}</td>
                    <td>${detection.type}</td>
                    <td>${detection.distance}</td>
                    <td>
                        <span style="color: ${this.getStatusColor(detection.status)}; font-weight: 500;">
                            ${detection.status}
                        </span>
                    </td>
                `;
                
                // Add hover effect
                row.addEventListener('mouseenter', () => {
                    row.style.background = 'rgba(0, 212, 170, 0.1)';
                    row.style.transform = 'scale(1.01)';
                });
                
                row.addEventListener('mouseleave', () => {
                    row.style.background = '';
                    row.style.transform = '';
                });
                
                tbody.appendChild(row);
            });
            
        } catch (error) {
            console.error('Error updating detections:', error);
        }
    }
    
    async updateActivity() {
        try {
            const response = await fetch('/api/activity');
            if (!response.ok) throw new Error('Failed to fetch activity');
            
            const activities = await response.json();
            
            const feed = document.getElementById('activity-feed');
            if (!feed) return;
            
            feed.innerHTML = '';
            
            activities.slice(0, 8).forEach((activity, index) => {
                const item = document.createElement('div');
                item.className = 'activity-item';
                item.style.animationDelay = `${index * 0.1}s`;
                item.innerHTML = `
                    <div class="activity-time">${activity.time}</div>
                    <div class="activity-icon ${activity.type}">
                        <i class="fas fa-${activity.icon}"></i>
                    </div>
                    <div class="activity-content">
                        <strong>${activity.title}</strong>
                        <small>${activity.description}<br><em>${activity.details}</em></small>
                    </div>
                `;
                
                // Add slide-in animation
                item.style.opacity = '0';
                item.style.transform = 'translateX(-20px)';
                
                setTimeout(() => {
                    item.style.transition = 'all 0.3s ease';
                    item.style.opacity = '1';
                    item.style.transform = 'translateX(0)';
                }, index * 100);
                
                feed.appendChild(item);
            });
            
        } catch (error) {
            console.error('Error updating activity:', error);
        }
    }
    
    async updateCameraStats() {
        try {
            // Update PC camera stats
            const pcResponse = await fetch('/api/camera/1/stats');
            if (pcResponse.ok) {
                const pcStats = await pcResponse.json();
                this.updateElement('pc-objects', pcStats.active_objects);
                this.updateElement('pc-accuracy', 
                    pcStats.connected ? 'Ready' : 'Offline'
                );
            }
            
            // Update underwater camera stats
            const underwaterResponse = await fetch('/api/camera/2/stats');
            if (underwaterResponse.ok) {
                const underwaterStats = await underwaterResponse.json();
                this.updateElement('underwater-fish', underwaterStats.active_objects);
                this.updateElement('underwater-accuracy', underwaterStats.accuracy + '%');
            }
            
        } catch (error) {
            console.error('Error updating camera stats:', error);
        }
    }
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element && element.textContent !== value.toString()) {
            element.textContent = value;
            
            // Add update animation
            element.style.transform = 'scale(1.1)';
            element.style.transition = 'transform 0.2s ease';
            
            setTimeout(() => {
                element.style.transform = 'scale(1)';
            }, 200);
        }
    }
    
    getStatusColor(status) {
        const colors = {
            'Active': '#00d4aa',
            'Tracking': '#74b9ff',
            'Monitoring': '#fdcb6e',
            'Warning': '#ff4757',
            'Alert': '#ff4757'
        };
        return colors[status] || '#ffffff';
    }
    
    animateCounters() {
        // Add subtle glow effect to counter elements
        const counters = ['total-today', 'session-count', 'alert-count'];
        
        counters.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.textShadow = '0 0 15px rgba(0, 212, 170, 0.8)';
                
                setTimeout(() => {
                    element.style.textShadow = '0 0 10px rgba(0, 212, 170, 0.5)';
                }, 300);
            }
        });
    }
    
    setupEventListeners() {
        // Handle video stream errors
        const videoStreams = document.querySelectorAll('.video-stream');
        videoStreams.forEach(stream => {
            stream.addEventListener('error', (e) => {
                console.warn('Video stream error:', e);
                this.handleVideoError(stream);
            });
            
            stream.addEventListener('load', () => {
                console.log('Video stream loaded:', stream.src);
            });
        });
        
        // Handle window visibility change
        document.addEventListener('visibilitychange', () => {
            this.isUpdating = !document.hidden;
            
            if (this.isUpdating) {
                console.log('Dashboard resumed updates');
                this.updateAllData();
            } else {
                console.log('Dashboard paused updates');
            }
        });
        
        // Handle online/offline status
        window.addEventListener('online', () => {
            this.showNotification('Connection restored', 'success');
            this.updateAllData();
        });
        
        window.addEventListener('offline', () => {
            this.showNotification('Connection lost', 'error');
        });
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'r':
                        e.preventDefault();
                        this.refreshData();
                        break;
                    case 'p':
                        e.preventDefault();
                        this.toggleUpdates();
                        break;
                }
            }
        });
    }
    
    handleVideoError(streamElement) {
        const container = streamElement.closest('.video-display');
        if (container) {
            container.style.background = 'linear-gradient(45deg, #ff4757, #ff3838)';
            container.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: white;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>Camera Unavailable</p>
                    <small>Attempting to reconnect...</small>
                </div>
            `;
            
            // Attempt to reconnect after 5 seconds
            setTimeout(() => {
                location.reload();
            }, 5000);
        }
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(26, 26, 46, 0.95);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 10px;
            border-left: 4px solid ${this.getNotificationColor(type)};
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            z-index: 10000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            max-width: 300px;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
    
    getNotificationColor(type) {
        const colors = {
            'success': '#00b894',
            'error': '#ff4757',
            'warning': '#fdcb6e',
            'info': '#74b9ff'
        };
        return colors[type] || '#74b9ff';
    }
    
    showError(message) {
        console.error(message);
        this.showNotification(message, 'error');
    }
    
    refreshData() {
        this.showNotification('Refreshing data...', 'info');
        this.updateAllData();
    }
    
    toggleUpdates() {
        this.isUpdating = !this.isUpdating;
        this.showNotification(
            this.isUpdating ? 'Auto-updates enabled' : 'Auto-updates paused',
            this.isUpdating ? 'success' : 'warning'
        );
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.marineDashboard = new MarineDashboard();
});

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MarineDashboard;
}