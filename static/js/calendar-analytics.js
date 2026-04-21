/**
 * Calendar Analytics - Interactive JavaScript
 * Handles calendar rendering, AJAX data fetching, and UI interactions
 */

class CalendarAnalytics {
    constructor() {
        const today = new Date();
        this.currentDate = new Date(today.getFullYear(), today.getMonth(), 1);
        this.monthData = {};
        this.selectedDate = null;
        this.isLoading = false;

        this.monthYearDisplay = document.getElementById('monthYearDisplay');
        this.calendarDatesContainer = document.getElementById('calendarDates');
        this.prevMonthBtn = document.getElementById('prevMonthBtn');
        this.nextMonthBtn = document.getElementById('nextMonthBtn');
        this.todayBtn = document.getElementById('todayBtn');
        this.dataPanel = document.getElementById('dataPanel');
        this.closePanelBtn = document.getElementById('closePanelBtn');
        this.panelDate = document.getElementById('panelDate');
        this.loadingSpinner = document.getElementById('loadingSpinner');

        this.statElements = {
            posts: document.getElementById('statPosts'),
            lost: document.getElementById('statLost'),
            found: document.getElementById('statFound'),
        };

        if (!this.validateElements()) {
            console.error('CalendarAnalytics: Missing required DOM elements');
            return;
        }

        this.init();
    }

    validateElements() {
        const required = [
            this.monthYearDisplay, this.calendarDatesContainer,
            this.prevMonthBtn, this.nextMonthBtn, this.todayBtn,
            this.dataPanel, this.closePanelBtn, this.panelDate, this.loadingSpinner
        ];
        const stats = Object.values(this.statElements);
        return [...required, ...stats].every(el => el !== null && el !== undefined);
    }

    init() {
        this.prevMonthBtn.addEventListener('click', () => this.previousMonth());
        this.nextMonthBtn.addEventListener('click', () => this.nextMonth());
        this.todayBtn.addEventListener('click', () => {
            const today = new Date();
            this.currentDate = new Date(today.getFullYear(), today.getMonth(), 1);
            this.render();
        });
        this.closePanelBtn.addEventListener('click', () => this.closePanel());
        this.render();
    }

    formatMonthYear(date) {
        return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    }

    getDaysInMonth(date) {
        return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
    }

    getFirstDayOfMonth(date) {
        return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
    }

    render() {
        this.renderCalendarDates();
        this.updateMonthYear();
        this.fetchMonthData();
    }

    updateMonthYear() {
        this.monthYearDisplay.textContent = this.formatMonthYear(this.currentDate);
    }

    renderCalendarDates() {
        this.calendarDatesContainer.innerHTML = '';

        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        const daysInMonth = this.getDaysInMonth(this.currentDate);
        const firstDay = this.getFirstDayOfMonth(this.currentDate);

        // Previous month's filler days
        const daysInPrevMonth = new Date(year, month, 0).getDate();
        for (let i = firstDay - 1; i >= 0; i--) {
            const day = daysInPrevMonth - i;
            this.createDateElement(day, new Date(year, month - 1, day), true);
        }

        // Current month days
        const today = new Date();
        for (let day = 1; day <= daysInMonth; day++) {
            const dateObj = new Date(year, month, day);
            const isToday = (year === today.getFullYear() && month === today.getMonth() && day === today.getDate());
            this.createDateElement(day, dateObj, false, isToday);
        }

        // Next month's filler days
        const totalCells = this.calendarDatesContainer.children.length;
        const nextDays = Math.max(0, 42 - totalCells);
        for (let day = 1; day <= nextDays; day++) {
            this.createDateElement(day, new Date(year, month + 1, day), true);
        }
    }

    /**
     * Create a single calendar date cell
     */
    createDateElement(day, dateObj, isOtherMonth = false, isToday = false) {
        const el = document.createElement('div');
        el.className = 'calendar-date';
        el.dataset.day = day;

        // Number span
        const numSpan = document.createElement('span');
        numSpan.className = 'date-num';
        numSpan.textContent = day;
        el.appendChild(numSpan);

        if (isOtherMonth) {
            el.classList.add('other-month');
        } else {
            const dateStr = this.formatDateForAPI(dateObj);

            if (isToday) el.classList.add('today');

            el.addEventListener('click', () => this.showDateData(dateStr, day));
        }

        this.calendarDatesContainer.appendChild(el);
    }

    formatDateForAPI(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    }

    /**
     * Fetch activity data for whole month
     */
    async fetchMonthData() {
        try {
            const year = this.currentDate.getFullYear();
            const month = this.currentDate.getMonth() + 1;
            this.monthData = {};

            const response = await fetch(`/admin-panel/api/calendar-month-data/?year=${year}&month=${month}`);
            if (!response.ok) { this.updateCalendarColors(); return; }

            const data = await response.json();
            if (!data.data || typeof data.data !== 'object') { this.updateCalendarColors(); return; }

            Object.keys(data.data).forEach(day => {
                const dayNum = parseInt(day, 10);
                if (!isNaN(dayNum) && dayNum >= 1 && dayNum <= 31) {
                    this.monthData[dayNum] = data.data[day];
                }
            });

            this.updateCalendarColors();
        } catch (error) {
            console.error('Error fetching month data:', error);
            this.updateCalendarColors();
        }
    }

    /**
     * Apply activity colors + dots to calendar cells
     */
    updateCalendarColors() {
        const cells = document.querySelectorAll('.calendar-date:not(.other-month)');

        cells.forEach(el => {
            const day = parseInt(el.dataset.day, 10);
            const activity = this.monthData[day];

            // Remove old classes
            el.classList.remove('activity-high', 'activity-medium', 'activity-low');

            // Remove old dot
            const oldDot = el.querySelector('.activity-dot');
            if (oldDot) oldDot.remove();

            if (activity && activity.has_activity) {
                // Apply color highlight only for active days
                if (activity.category !== 'none') {
                    el.classList.add(`activity-${activity.category}`);
                }
                el.title = `${activity.total_posts} post${activity.total_posts !== 1 ? 's' : ''} on this day`;

                // Add green dot if there are posts
                if (activity.total_posts > 0) {
                    const dot = document.createElement('span');
                    dot.className = 'activity-dot';
                    el.appendChild(dot);
                }
            }
        });
    }

    /**
     * Show data panel for a clicked date
     */
    async showDateData(dateStr, day) {
        if (this.isLoading) return;

        try {
            if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return;

            this.selectedDate = dateStr;
            this.isLoading = true;
            this.showLoadingState(true);
            this.dataPanel.classList.remove('hidden');

            const response = await fetch(`/admin-panel/api/calendar-data/?date=${encodeURIComponent(dateStr)}`);
            if (!response.ok) throw new Error(`API returned ${response.status}`);

            const data = await response.json();
            if (data.error) throw new Error(data.error);

            this.populateDataPanel(data);
            this.showLoadingState(false);
            this.isLoading = false;
        } catch (error) {
            console.error('Error fetching date data:', error);
            this.showLoadingState(false);
            this.isLoading = false;
        }
    }

    /**
     * Populate the side panel with statistics
     */
    populateDataPanel(data) {
        try {
            // Format date for display
            const parts = data.date.split('-');
            const dateObj = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            const formatted = dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: '2-digit', year: 'numeric' });

            const totalPosts = Math.max(0, parseInt(data.total_posts || 0, 10));
            const lostPosts  = Math.max(0, parseInt(data.lost_posts  || 0, 10));
            const foundPosts = Math.max(0, parseInt(data.found_posts || 0, 10));

            // Panel title: show date + post count
            this.panelDate.innerHTML = `
                <span style="display:block; font-size:0.85rem; color:#6366f1; margin-bottom:0.25rem;">📅 ${formatted}</span>
                <span style="font-size:1.6rem; font-weight:800; color:#f1f5f9;">${totalPosts}</span>
                <span style="font-size:0.9rem; color:#94a3b8; font-weight:500;"> post${totalPosts !== 1 ? 's' : ''} reported</span>
            `;

            // Future date check
            const today = new Date();
            const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
            const selected = new Date(dateObj.getFullYear(), dateObj.getMonth(), dateObj.getDate());
            if (selected > todayMidnight) {
                this.showNoEntriesMessage('This date is in the future. No data yet.');
                return;
            }

            if (totalPosts === 0) {
                this.showNoEntriesMessage('No posts reported on this date.');
                return;
            }

            // Hide no-entries message if present
            const msg = this.dataPanel.querySelector('.no-entries-message');
            if (msg) msg.style.display = 'none';

            // Show stats
            document.querySelectorAll('.stat-item').forEach(el => el.style.display = 'flex');

            this.statElements.posts.textContent = totalPosts;
            this.statElements.lost.textContent  = lostPosts;
            this.statElements.found.textContent = foundPosts;

        } catch (error) {
            console.error('populateDataPanel error:', error);
        }
    }

    showNoEntriesMessage(text = 'No entries for this date.') {
        document.querySelectorAll('.stat-item').forEach(el => el.style.display = 'none');

        let msg = this.dataPanel.querySelector('.no-entries-message');
        if (!msg) {
            msg = document.createElement('div');
            msg.className = 'no-entries-message';
            const panelContent = this.dataPanel.querySelector('.panel-content');
            if (panelContent) panelContent.before(msg);
            else this.dataPanel.appendChild(msg);
        }
        msg.style.display = 'block';
        msg.innerHTML = `
            <div style="text-align:center; padding:1.5rem 1rem; color:#9ca3af;">
                <p style="font-size:2rem; margin-bottom:0.5rem;">📭</p>
                <p style="font-size:0.9rem;">${text}</p>
            </div>
        `;
    }

    showLoadingState(isLoading) {
        if (isLoading) {
            if (this.loadingSpinner) this.loadingSpinner.classList.add('show');
        } else {
            if (this.loadingSpinner) this.loadingSpinner.classList.remove('show');
        }
    }

    closePanel() {
        if (this.dataPanel) this.dataPanel.classList.add('hidden');
        this.selectedDate = null;
        this.isLoading = false;
    }

    previousMonth() {
        const m = this.currentDate.getMonth();
        const y = this.currentDate.getFullYear();
        this.currentDate = m === 0 ? new Date(y - 1, 11, 1) : new Date(y, m - 1, 1);
        this.render();
    }

    nextMonth() {
        const m = this.currentDate.getMonth();
        const y = this.currentDate.getFullYear();
        this.currentDate = m === 11 ? new Date(y + 1, 0, 1) : new Date(y, m + 1, 1);
        this.render();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => { window.calendarInstance = new CalendarAnalytics(); }, 100);
});
