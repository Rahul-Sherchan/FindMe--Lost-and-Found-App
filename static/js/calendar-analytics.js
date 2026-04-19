/**
 * Calendar Analytics - Interactive JavaScript
 * Handles calendar rendering, AJAX data fetching, and UI interactions
 */

class CalendarAnalytics {
    constructor() {
        // Use UTC date to avoid timezone issues
        const today = new Date();
        this.currentDate = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), 1));
        this.monthData = {};
        this.selectedDate = null;
        this.isLoading = false;

        // Elements with null checks
        this.monthYearDisplay = document.getElementById('monthYearDisplay');
        this.calendarDatesContainer = document.getElementById('calendarDates');
        this.prevMonthBtn = document.getElementById('prevMonthBtn');
        this.nextMonthBtn = document.getElementById('nextMonthBtn');
        this.todayBtn = document.getElementById('todayBtn');
        this.dataPanel = document.getElementById('dataPanel');
        this.closePanelBtn = document.getElementById('closePanelBtn');
        this.panelDate = document.getElementById('panelDate');
        this.loadingSpinner = document.getElementById('loadingSpinner');

        // Stat elements
        this.statElements = {
            posts: document.getElementById('statPosts'),
            lost: document.getElementById('statLost'),
            found: document.getElementById('statFound'),
        };

        // Validate all elements exist
        if (!this.validateElements()) {
            console.error('CalendarAnalytics: Missing required DOM elements');
            return;
        }

        this.init();
    }

    /**
     * Validate all required DOM elements exist
     */
    validateElements() {
        const requiredElements = [
            this.monthYearDisplay,
            this.calendarDatesContainer,
            this.prevMonthBtn,
            this.nextMonthBtn,
            this.todayBtn,
            this.dataPanel,
            this.closePanelBtn,
            this.panelDate,
            this.loadingSpinner
        ];

        const requiredStats = Object.values(this.statElements);

        const allElements = [...requiredElements, ...requiredStats];
        const allValid = allElements.every(el => el !== null && el !== undefined);

        if (!allValid) {
            const missingElements = [];
            if (!this.monthYearDisplay) missingElements.push('monthYearDisplay');
            if (!this.calendarDatesContainer) missingElements.push('calendarDatesContainer');
            if (!this.prevMonthBtn) missingElements.push('prevMonthBtn');
            if (!this.nextMonthBtn) missingElements.push('nextMonthBtn');
            if (!this.todayBtn) missingElements.push('todayBtn');
            if (!this.dataPanel) missingElements.push('dataPanel');
            if (!this.closePanelBtn) missingElements.push('closePanelBtn');
            if (!this.panelDate) missingElements.push('panelDate');
            if (!this.loadingSpinner) missingElements.push('loadingSpinner');
            Object.entries(this.statElements).forEach(([key, el]) => {
                if (!el) missingElements.push(`statElements.${key}`);
            });
            console.error('Missing elements:', missingElements);
            return false;
        }

        return true;
    }

    /**
     * Initialize the calendar with event listeners
     */
    init() {
        try {
            this.prevMonthBtn.addEventListener('click', () => this.previousMonth());
            this.nextMonthBtn.addEventListener('click', () => this.nextMonth());
            this.todayBtn.addEventListener('click', () => {
                const today = new Date();
                this.currentDate = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), 1));
                this.render();
            });
            this.closePanelBtn.addEventListener('click', () => this.closePanel());

            // Close panel when clicking outside
            document.addEventListener('click', (e) => {
                if (this.dataPanel && 
                    !this.dataPanel.contains(e.target) && 
                    e.target !== this.closePanelBtn &&
                    !e.target.classList.contains('calendar-date') &&
                    this.dataPanel.classList.contains('hidden') === false) {
                    // Only close if panel is visible
                    // this.closePanel();
                }
            });

            // Initial render
            this.render();
        } catch (error) {
            console.error('CalendarAnalytics init error:', error);
        }
    }

    /**
     * Format date to readable month/year
     */
    formatMonthYear(date) {
        const options = { month: 'long', year: 'numeric' };
        return date.toLocaleDateString('en-US', options);
    }

    /**
     * Get number of days in a month
     */
    getDaysInMonth(date) {
        return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
    }

    /**
     * Get first day of the month (0 = Sunday, 6 = Saturday)
     */
    getFirstDayOfMonth(date) {
        return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
    }

    /**
     * Render the calendar
     */
    render() {
        this.renderCalendarDates();
        this.updateMonthYear();
        this.fetchMonthData();
    }

    /**
     * Update month/year display
     */
    updateMonthYear() {
        this.monthYearDisplay.textContent = this.formatMonthYear(this.currentDate);
    }

    /**
     * Render calendar dates
     */
    renderCalendarDates() {
        this.calendarDatesContainer.innerHTML = '';

        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        const daysInMonth = this.getDaysInMonth(this.currentDate);
        const firstDay = this.getFirstDayOfMonth(this.currentDate);

        // Previous month's dates (dimmed)
        const prevMonthDate = new Date(year, month, 0);
        const daysInPrevMonth = prevMonthDate.getDate();

        for (let i = firstDay - 1; i >= 0; i--) {
            const day = daysInPrevMonth - i;
            const dateStr = new Date(year, month - 1, day);
            this.createDateElement(day, dateStr, true);
        }

        // Current month's dates
        const today = new Date();
        const todayYear = today.getFullYear();
        const todayMonth = today.getMonth();
        const todayDay = today.getDate();

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = new Date(year, month, day);
            const isToday = (year === todayYear && month === todayMonth && day === todayDay);
            this.createDateElement(day, dateStr, false, isToday);
        }

        // Next month's dates (dimmed)
        const totalCells = this.calendarDatesContainer.children.length;
        const nextMonthDays = Math.max(0, 42 - totalCells); // 6 weeks ├ù 7 days
        for (let day = 1; day <= nextMonthDays; day++) {
            const dateStr = new Date(year, month + 1, day);
            this.createDateElement(day, dateStr, true);
        }
    }

    /**
     * Create a single date element
     */
    createDateElement(day, dateObj, isOtherMonth = false, isToday = false) {
        const dateElement = document.createElement('div');
        dateElement.className = 'calendar-date';
        dateElement.textContent = day;

        if (isOtherMonth) {
            dateElement.classList.add('other-month');
        } else {
            const dateStr = this.formatDateForAPI(dateObj);

            // Add activity class if data is available
            if (this.monthData[day]) {
                dateElement.classList.add(`activity-${this.monthData[day].category}`);
                
                // Add tooltip
                dateElement.title = `Activity Level: ${this.monthData[day].level}%`;
            }

            if (isToday) {
                dateElement.classList.add('today');
            }

            // Add click event to fetch detailed data
            dateElement.addEventListener('click', () => {
                this.showDateData(dateStr, day);
            });

            // Add hover effect to show tooltip
            dateElement.addEventListener('mouseenter', () => {
                if (this.monthData[day]) {
                    const activity = this.monthData[day];
                    dateElement.title = `${activity.level}% Activity (${activity.category})`;
                }
            });
        }

        this.calendarDatesContainer.appendChild(dateElement);
    }

    /**
     * Format date to YYYY-MM-DD
     */
    formatDateForAPI(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    /**
     * Fetch activity data for the entire month
     */
    async fetchMonthData() {
        try {
            const year = this.currentDate.getFullYear();
            const month = this.currentDate.getMonth() + 1;

            // Clear old month data
            this.monthData = {};

            const url = `/admin/api/calendar-month-data/?year=${year}&month=${month}`;
            
            const response = await fetch(url);

            if (!response.ok) {
                console.error(`Failed to fetch month data: ${response.status} ${response.statusText}`);
                // Continue with empty data instead of failing
                this.updateCalendarColors();
                return;
            }

            const data = await response.json();
            
            // Validate response structure
            if (!data.data || typeof data.data !== 'object') {
                console.error('Invalid month data response:', data);
                this.updateCalendarColors();
                return;
            }

            // Convert string keys to numbers and store
            this.monthData = {};
            Object.keys(data.data).forEach(day => {
                const dayNum = parseInt(day, 10);
                if (!isNaN(dayNum) && dayNum >= 1 && dayNum <= 31) {
                    this.monthData[dayNum] = data.data[day];
                }
            });

            // Update calendar colors based on new data
            this.updateCalendarColors();
        } catch (error) {
            console.error('Error fetching month data:', error);
            // Continue gracefully - calendar will still display without colors
            this.updateCalendarColors();
        }
    }

    /**
     * Update calendar dates with activity colors
     */
    updateCalendarColors() {
        const dates = document.querySelectorAll('.calendar-date:not(.other-month)');
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();

        dates.forEach((dateElement, index) => {
            const day = parseInt(dateElement.textContent);

            // Skip if it's not in the current month
            if (dateElement.classList.contains('other-month')) return;

            if (this.monthData[day]) {
                // Remove old activity classes
                dateElement.classList.remove('activity-high', 'activity-medium', 'activity-low');

                // Add new activity class
                const activity = this.monthData[day];
                dateElement.classList.add(`activity-${activity.category}`);
                dateElement.title = `${activity.level}% Activity`;
            }
        });
    }

    /**
     * Show data panel for a specific date
     */
    async showDateData(dateStr, day) {
        if (this.isLoading) return; // Prevent duplicate requests
        
        try {
            // Validate date string
            if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
                console.error('Invalid date string:', dateStr);
                this.showError('Invalid date format');
                return;
            }

            this.selectedDate = dateStr;
            this.isLoading = true;
            this.showLoadingState(true);
            this.dataPanel.classList.remove('hidden');

            const response = await fetch(`/admin/api/calendar-data/?date=${encodeURIComponent(dateStr)}`);

            if (!response.ok) {
                throw new Error(`API returned ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Validate response
            if (data.error) {
                throw new Error(data.error);
            }

            this.populateDataPanel(data);
            this.showLoadingState(false);
            this.isLoading = false;
        } catch (error) {
            console.error('Error fetching date data:', error);
            this.showLoadingState(false);
            this.isLoading = false;
            this.showError(`Failed to load analytics data: ${error.message}`);
        }
    }

    /**
     * Populate the data panel with statistics
     */
    populateDataPanel(data) {
        try {
            // Validate data
            if (!data || typeof data !== 'object') {
                console.error('Invalid data received:', data);
                this.showError('Invalid data format');
                return;
            }

            // Parse date safely - split to avoid timezone issues
            const dateParts = data.date.split('-');
            const dateObj = new Date(
                parseInt(dateParts[0], 10),
                parseInt(dateParts[1], 10) - 1,
                parseInt(dateParts[2], 10)
            );

            const options = { weekday: 'short', month: 'short', day: '2-digit', year: 'numeric' };
            const formattedDate = dateObj.toLocaleDateString('en-US', options);

            this.panelDate.textContent = `­ƒôà ${formattedDate}`;

            // Check if the selected date is in the future
            const today = new Date();
            const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
            const selectedDate = new Date(dateObj.getFullYear(), dateObj.getMonth(), dateObj.getDate());

            if (selectedDate > todayDate) {
                // Future date - show "No entries detected" message
                this.showNoEntriesMessage();
                return;
            }

            // Update stats with safe number conversion
            const newUsers = Math.max(0, parseInt(data.new_users || 0, 10));
            const totalPosts = Math.max(0, parseInt(data.total_posts || 0, 10));
            const lostPosts = Math.max(0, parseInt(data.lost_posts || 0, 10));
            const foundPosts = Math.max(0, parseInt(data.found_posts || 0, 10));
            
            // Check if there are no entries for this date
            const hasNoEntries = totalPosts === 0;
            if (hasNoEntries) {
                // No entries detected - show "No entries detected" message
                this.showNoEntriesMessage();
                return;
            }

            // Hide the no-entries message if visible
            const noEntriesMsg = this.dataPanel.querySelector('.no-entries-message');
            if (noEntriesMsg) {
                noEntriesMsg.style.display = 'none';
            }

            // Show stats
            document.querySelectorAll('.stat-item, .activity-indicator-container').forEach(el => {
                el.style.display = 'block';
            });

            this.statElements.posts.textContent = totalPosts;
            this.statElements.lost.textContent = lostPosts;
            this.statElements.found.textContent = foundPosts;
        } catch (error) {
            console.error('Error populating data panel:', error);
            this.showError('Error displaying analytics data');
        }
    }

    /**
     * Show "No entries detected" message for future dates
     */
    showNoEntriesMessage() {
        try {
            // Hide all stat items and activity indicator
            document.querySelectorAll('.stat-item, .activity-indicator-container').forEach(el => {
                el.style.display = 'none';
            });

            // Check if message already exists
            let noEntriesMsg = this.dataPanel.querySelector('.no-entries-message');
            if (!noEntriesMsg) {
                // Create the message element
                noEntriesMsg = document.createElement('div');
                noEntriesMsg.className = 'no-entries-message';
                noEntriesMsg.innerHTML = `
                    <div style="text-align: center; padding: 2rem 1rem; color: #9ca3af;">
                        <p style="font-size: 3rem; margin-bottom: 1rem;">­ƒô¡</p>
                        <p style="font-size: 1.1rem; font-weight: 500; margin-bottom: 0.5rem;">No entries detected</p>
                        <p style="font-size: 0.9rem; color: #6b7280;">This date is in the future. No data available yet.</p>
                    </div>
                `;
                // Insert after panel header
                const panelHeader = this.dataPanel.querySelector('.panel-header');
                if (panelHeader && panelHeader.nextSibling) {
                    panelHeader.parentNode.insertBefore(noEntriesMsg, panelHeader.nextSibling);
                } else {
                    this.dataPanel.querySelector('.panel-content').parentNode.insertBefore(noEntriesMsg, this.dataPanel.querySelector('.panel-content'));
                }
            } else {
                noEntriesMsg.style.display = 'block';
            }
        } catch (error) {
            console.error('Error showing no entries message:', error);
        }
    }

    /**
     * Toggle loading spinner
     */
    showLoadingState(isLoading) {
        try {
            if (isLoading) {
                if (this.loadingSpinner) {
                    this.loadingSpinner.classList.add('show');
                }
                document.querySelectorAll('.stat-item, .activity-indicator-container').forEach(el => {
                    el.style.opacity = '0.5';
                    el.style.pointerEvents = 'none';
                });
            } else {
                if (this.loadingSpinner) {
                    this.loadingSpinner.classList.remove('show');
                }
                document.querySelectorAll('.stat-item, .activity-indicator-container').forEach(el => {
                    el.style.opacity = '1';
                    el.style.pointerEvents = 'auto';
                });
            }
        } catch (error) {
            console.error('Error showing loading state:', error);
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        try {
            const errorMsg = String(message || 'An error occurred');
            console.error('Calendar Error:', errorMsg);
            
            // Try to show in alert, but don't fail if it doesn't work
            if (typeof alert === 'function') {
                // Use a more subtle notification in the future
                // For now, just log to console since alert is invasive
            }
        } catch (error) {
            console.error('Error showing error message:', error);
        }
    }

    /**
     * Close the data panel
     */
    closePanel() {
        try {
            if (this.dataPanel) {
                this.dataPanel.classList.add('hidden');
            }
            this.selectedDate = null;
            this.isLoading = false;
        } catch (error) {
            console.error('Error closing panel:', error);
        }
    }

    /**
     * Navigate to previous month
     */
    previousMonth() {
        try {
            // Safely handle month navigation with year transition
            if (this.currentDate.getMonth() === 0) {
                // January -> December of previous year
                this.currentDate = new Date(this.currentDate.getFullYear() - 1, 11, 1);
            } else {
                // Any other month -> previous month
                this.currentDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() - 1, 1);
            }
            this.render();
        } catch (error) {
            console.error('Error navigating to previous month:', error);
        }
    }

    /**
     * Navigate to next month
     */
    nextMonth() {
        try {
            // Safely handle month navigation with year transition
            if (this.currentDate.getMonth() === 11) {
                // December -> January of next year
                this.currentDate = new Date(this.currentDate.getFullYear() + 1, 0, 1);
            } else {
                // Any other month -> next month
                this.currentDate = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth() + 1, 1);
            }
            this.render();
        } catch (error) {
            console.error('Error navigating to next month:', error);
        }
    }
}

/**
 * Initialize calendar when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    try {
        // Small delay to ensure all DOM elements are fully loaded
        setTimeout(() => {
            window.calendarInstance = new CalendarAnalytics();
        }, 100);
    } catch (error) {
        console.error('Failed to initialize CalendarAnalytics:', error);
    }
});
