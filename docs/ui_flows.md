# UI Flows

## Overview

This document describes the user interface structure, main navigation, and user flows for all core app features.  
The design is desktop-first, highly user-friendly, and leverages a sidebar navigation and floating header bar.

---

## **Global Layout**

- **Sidebar:**  
    - Always visible on left  
    - Icons + labels for Dashboard, Upload, Restaurants, Search, Settings  
    - Collapsible to icons-only for more screen space
- **Header Bar:**  
    - Across top, right of sidebar  
    - App logo/name left, global search, notifications, user avatar right  
    - Floats above content with shadow/glass effect
- **Content Area:**  
    - All page-specific content displayed here
    - Cards, tables, forms as needed

---

## **Pages & Flows**

### 1. **Dashboard**

- Shows stat cards: Total Restaurants, Wine Lists Parsed, Pending Refinements, Parsing Accuracy
- Quick links/buttons: Upload Wine List, View All Restaurants, Global Search

---

### 2. **Upload Wine List**

- Central card: Drag & drop zone or click to browse
    - Fields:
        - Restaurant selector (autocomplete dropdown)
        - Date of file (auto-extracted, editable)
- Progress indicator on upload/parse
- Shows parse status, errors, or next step
- When complete, “Go to Refinement” button

**Flow:**
1. User selects restaurant
2. Uploads file (drag/drop or click)
3. Date auto-fills from file, user can edit
4. Upload triggers backend parse
5. After parse, UI links to Refinement page

---

### 3. **Refinement Page**

- Table view (TanStack Table)
    - Columns: Producer, Cuvee, Type, Vintage, Price, Bottle Size, Grape Variety, Country, Region, Subregion, Confidence, Actions
    - Row highlight for low-confidence or AI-extracted fields
    - Inline edit for every cell
    - Show current section/header context (sticky at top or in a column)
    - “Edit Rule” sidebar: live rule editing, preview impact
- Bulk actions: Approve all, Reject all, Auto-correct low confidence
- “Finalize” button for saving

**Flow:**
1. User lands on table after parse/upload
2. Reviews each entry, edits or approves as needed
3. Can open rule editor for ambiguous cases or recurring errors
4. Finalizes list when satisfied

---

### 4. **Restaurants Page**

- Grid/list of restaurant cards:
    - Each card: Name, stats, logo/avatar, actions
    - Buttons: View Wine Lists, Edit Rules, Delete Restaurant
- “Add Restaurant” button (modal with name, email, sample upload)
- Click restaurant to see its files, rules, and detail

**Flow:**
1. User lands on list of all restaurants
2. Can add, edit, or delete restaurants
3. Clicks a restaurant to see associated wine lists and rules

---

### 5. **Wine Lists Page (Per Restaurant)**

- Table of wine list files for that restaurant
    - Filename, parsed date, status, actions (View/Refine, Delete)
- “Upload new file” button (preselects restaurant)
- Delete file or view in refinement

---

### 6. **Rules Editor (Per Restaurant)**

- Sidebar/modal UI
    - List of current parsing rules (regex, keywords, exclusion zones)
    - Add/edit/delete rules
    - Live preview on sample text or file
    - “Apply to All” and versioning/history
    - Auto-suggestions from recent corrections

---

### 7. **Search Page**

- Floating search bar at top
- Results show as cards/rows:
    - Wine name, region, restaurant, price, confidence, actions
    - Filter by wine, restaurant, or file
    - Instant search as you type

---

### 8. **Onboarding (Restaurant Setup)**

- “Add Restaurant” flow:
    1. Enter basic details (name, email)
    2. Upload sample wine list file
    3. System parses and shows extracted rules for approval
    4. User can adjust rules or accept defaults

---

## **UI Details**

- Modals for confirms/deletes, rule editing, onboarding
- Snackbars/toasts for success/error feedback
- Dark/light mode toggle (optional for v1)
- Responsive, but desktop-first

---

## **Wireframes**

- Attach or link to Figma diagrams here as they are developed.
- Each page should have a simple block diagram showing layout (can add screenshots/mockups as images).

---

