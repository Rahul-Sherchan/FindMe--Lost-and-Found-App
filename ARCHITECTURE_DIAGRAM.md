# Calendar Analytics - Architecture & Data Flow

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User's Browser                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────┐         ┌──────────────────────────┐  │
│  │  calendar_analytics.html   │         │  calendar-analytics.css  │  │
│  │  (Template with layout)     │         │  (Dark glassmorphism)    │  │
│  │  - Calendar grid           │         │  - Colors & transitions  │  │
│  │  - Month navigation        │         │  - Responsive layout     │  │
│  │  - Data panel              │         │  - Activity indicators   │  │
│  └────────────────────────────┘         └──────────────────────────┘  │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │           calendar-analytics.js (CalendarAnalytics)            │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │ Class Methods:                                          │  │  │
│  │  │ - init()                    (Setup events)             │  │  │
│  │  │ - render()                  (Calendar rendering)       │  │  │
│  │  │ - renderCalendarDates()     (Generate date elements)   │  │  │
│  │  │ - fetchMonthData()          (AJAX to API #2)          │  │  │
│  │  │ - showDateData()            (AJAX to API #1)          │  │  │
│  │  │ - populateDataPanel()       (Update statistics)        │  │  │
│  │  │ - previousMonth/nextMonth() (Navigation)              │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                    ↕ AJAX Fetch API / HTTP
                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                      Django Backend                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  admin_dashboard/urls.py                                         │  │
│  │  GET /admin/calendar/                                            │  │
│  │  GET /admin/api/calendar-data/?date=YYYY-MM-DD                 │  │
│  │  GET /admin/api/calendar-month-data/?year=YYYY&month=MM        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  admin_dashboard/views.py                                        │  │
│  │                                                                   │  │
│  │  ┌─ API #1: calendar_data_api() ──────────────────────┐        │  │
│  │  │ Input: date=2026-04-05                             │        │  │
│  │  │ Output: JSON with statistics                       │        │  │
│  │  │ - new_users (filter date_joined__date)            │        │  │
│  │  │ - lost_posts (filter item_type='lost')            │        │  │
│  │  │ - found_posts (filter item_type='found')          │        │  │
│  │  │ - recovered_items (filter status='resolved'|...)  │        │  │
│  │  │ - messages_count (count by created_at__date)      │        │  │
│  │  │ - activity_level (scoring calculation)            │        │  │
│  │  │ - activity_category (high/medium/low)             │        │  │
│  │  └────────────────────────────────────────────────────┘        │  │
│  │                                                                   │  │
│  │  ┌─ API #2: calendar_month_data_api() ────────────────┐        │  │
│  │  │ Input: year=2026, month=4                          │        │  │
│  │  │ Output: JSON for all dates in month                │        │  │
│  │  │ {                                                  │        │  │
│  │  │   '1': {level: 20, category: 'low'},              │        │  │
│  │  │   '5': {level: 67, category: 'high'},             │        │  │
│  │  │   '10': {level: 35, category: 'medium'},          │        │  │
│  │  │   ...                                              │        │  │
│  │  │ }                                                  │        │  │
│  │  └────────────────────────────────────────────────────┘        │  │
│  │                                                                   │  │
│  │  ┌─ View: calendar_analytics() ───────────────────────┐        │  │
│  │  │ Renders: calendar_analytics.html template          │        │  │
│  │  └────────────────────────────────────────────────────┘        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                    ↕ SQL Queries (Django ORM)
                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                        Database (SQLite/PostgreSQL)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Table: accounts_user                                            │  │
│  │  - id, username, email, date_joined (↑ indexed)                │  │
│  │  Query: COUNT(*) WHERE date_joined__date = target_date          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Table: items_item                                               │  │
│  │  - id, user_id, item_type, status, created_at (↑), updated_at  │  │
│  │  Queries:                                                        │  │
│  │  - COUNT(*) WHERE item_type='lost' AND created_at__date=...    │  │
│  │  - COUNT(*) WHERE item_type='found' AND created_at__date=...   │  │
│  │  - COUNT(*) WHERE status IN ('resolved','claimed') AND ...     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Table: messaging_message                                        │  │
│  │  - id, conversation_id, sender_id, created_at (↑)               │  │
│  │  Query: COUNT(*) WHERE created_at__date = target_date           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Sequence

```
┌─────────────────────────────────────────────────────────────────────┐
│ User Action                    Backend Logic                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ 1. Visit /admin/calendar/                                           │
│    └─→ calendar_analytics() view                                    │
│        └─→ Render calendar_analytics.html                          │
│            └─→ JavaScript CalendarAnalytics.init()                 │
│                                                                      │
│ 2. Calendar loads on Page                                           │
│    └─→ fetchMonthData() AJAX call                                   │
│        └─→ GET /admin/api/calendar-month-data/?year=2026&month=4  │
│            └─→ calendar_month_data_api() view                      │
│                └─→ Query all dates: User, Item, Message counts      │
│                    └─→ Calculate activity_level (0-100)             │
│                        └─→ Return JSON with month activity data    │
│                            └─→ updateCalendarColors()              │
│                                └─→ Apply color-coded classes       │
│                                                                      │
│ 3. User clicks date (e.g., April 5)                                 │
│    └─→ showDateData('2026-04-05') method                            │
│        └─→ Show loading spinner                                     │
│            └─→ GET /admin/api/calendar-data/?date=2026-04-05       │
│                └─→ calendar_data_api() view                         │
│                    └─→ Query statistics for single date:            │
│                        • User.filter(date_joined__date='2026-04-05')│
│                        • Item.filter(created_at__date='2026-04-05') │
│                        • Message.filter(created_at__date='...')     │
│                        └─→ Calculate activity_level                 │
│                            └─→ Return JSON with all stats           │
│                                └─→ populateDataPanel()              │
│                                    └─→ Update panel HTML            │
│                                    └─→ Hide spinner                 │
│                                                                      │
│ 4. User closes panel                                                │
│    └─→ closePanel() method                                          │
│        └─→ Add 'hidden' class                                       │
│            └─→ Panel disappears with animation                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Activity Scoring Calculation

```
For date: 2026-04-05

Step 1: Count Aggregates
────────────────────────
New Users        = 3
Lost Posts       = 5
Found Posts      = 2
Recovered Items  = 2
Messages         = 12

Step 2: Apply Weights
─────────────────────
Users Score       = 3 × 2 = 6
Posts Score       = (5+2) × 3 = 21
Recovered Score   = 2 × 5 = 10
Messages Score    = 12 × 1 = 12

Total Score       = 6 + 21 + 10 + 12 = 49

Step 3: Normalize to 0-100%
───────────────────────────
Activity Level = min((49 / 100) × 100, 100)
               = min(49%, 100)
               = 49 %

Step 4: Determine Category
──────────────────────────
49% >= 60 ? NO
49% >= 30 ? YES  → Category = "medium" (Yellow)

Step 5: Return
──────────────
{
    "activity_level": 49,
    "activity_category": "medium"
}
```

---

## File Interaction Map

```
Templates
├── base.html (parent)
│   └── calendar_analytics.html (extends)
│       ├── uses calendar-analytics.css
│       └── uses calendar-analytics.js

Static Files
├── css/
│   └── calendar-analytics.css (1000+ lines)
│       ├── Color variables
│       ├── Layout & grid
│       └── Responsive breakpoints
├── js/
│   └── calendar-analytics.js (300+ lines)
│       └── CalendarAnalytics class
│           ├── Rendering methods
│           ├── AJAX methods
│           └── Event handlers

Views
├── admin_dashboard/views.py
│   ├── calendar_analytics() → Renders HTML
│   ├── calendar_data_api() → Returns JSON
│   └── calendar_month_data_api() → Returns JSON

URLs
├── admin_dashboard/urls.py
│   ├── /admin/calendar/
│   ├── /admin/api/calendar-data/
│   └── /admin/api/calendar-month-data/
```

---

## Request/Response Examples

### Request 1: Initial Page Load
```
GET /admin/calendar/ HTTP/1.1
Host: localhost:8000
Authorization: [Admin User Cookie]
```

**Response:** HTML page with calendar layout

---

### Request 2: Fetch Month Activity Data
```
GET /admin/api/calendar-month-data/?year=2026&month=4 HTTP/1.1
Host: localhost:8000
Authorization: [Admin User Cookie]
```

**Response:**
```json
{
    "year": 2026,
    "month": 4,
    "data": {
        "1": {"level": 20, "category": "low"},
        "2": {"level": 35, "category": "medium"},
        "3": {"level": 25, "category": "low"},
        "4": {"level": 40, "category": "medium"},
        "5": {"level": 49, "category": "medium"},
        "6": {"level": 70, "category": "high"},
        "7": {"level": 10, "category": "low"},
        ...
    }
}
```

---

### Request 3: Click a Date (Fetch Details)
```
GET /admin/api/calendar-data/?date=2026-04-05 HTTP/1.1
Host: localhost:8000
Authorization: [Admin User Cookie]
```

**Response:**
```json
{
    "date": "2026-04-05",
    "new_users": 3,
    "lost_posts": 5,
    "found_posts": 2,
    "total_posts": 7,
    "recovered_items": 2,
    "messages_count": 12,
    "activity_level": 49,
    "activity_category": "medium"
}
```

---

## Error Handling Flow

```
User Action
    ↓
Try AJAX Fetch
    ↓
Network Error? → Catch → showError("Failed to load...")
    ↓ No
Response OK?
    ↓
400/500 Error? → showError("Failed to fetch...")
    ↓ No
Parse JSON
    ↓
Parse Error? → showError("Invalid response...")
    ↓ No
Success!
    ↓
populateDataPanel()
showLoadingState(false)
```

---

## CSS Cascade & Specificity

```
Global Styles
├── :root variables
├── body baseline
└── .calendar-analytics-container

Navigation
├── .admin-nav (always visible)
└── .nav-links

Calendar Grid
├── .calendar-wrapper
├── .calendar-grid
└── .calendar-date
    ├── .calendar-date:hover
    ├── .calendar-date.other-month
    ├── .calendar-date.activity-high
    ├── .calendar-date.activity-medium
    ├── .calendar-date.activity-low
    └── .calendar-date.today

Data Panel
├── .data-panel
├── .data-panel.hidden
├── .panel-header
├── .stat-item
├── .activity-indicator-container
└── .loading-spinner

Responsive
├── @media (max-width: 1024px)
├── @media (max-width: 768px)
└── @media (max-width: 480px)
```

---

## Performance Optimization

```
Rendering
├── Virtual Calendar (only renders visible dates)
├── CSS Grid (GPU accelerated)
└── No excessive DOM manipulation

Data Loading
├── Single fetch per month (calendar_month_data_api)
├── Single fetch per date (calendar_data_api)
├── Minimal payload (JSON only)
└── No full page reload

Database
├── Indexed fields: created_at, date_joined, updated_at
├── Aggregation at DB level (COUNT, Q objects)
└── No N+1 queries

Frontend
├── Event delegation for date clicks
├── CSS animations (GPU accelerated)
├── Request debouncing on month nav
└── Minimal reflows/repaints
```

---

This architecture ensures:
- ✅ Clean separation of concerns
- ✅ Scalable and maintainable code
- ✅ Optimal database performance
- ✅ Responsive user experience
- ✅ Security with admin-only access
