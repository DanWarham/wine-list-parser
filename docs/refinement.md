# Refinement Process

## Overview

The refinement process is where the user reviews, corrects, and confirms the wines and details extracted from an uploaded wine list file. It is designed for speed, clarity, and rule learning, so the system gets better with each use.

---

## **Key UI Elements**

- **TanStack Table UI** for displaying all extracted wine entries.
    - Columns: Producer, Cuvee, Type, Vintage, Price, Bottle Size, Grape Variety, Country, Region, Subregion, Confidence, Actions.
    - Confidence shown as a colored badge (green, yellow, red).
    - Inline editing for every cell (click to edit, auto-save on blur/confirm).
    - “Raw text” preview for each entry (optional drawer/expand).
    - Context columns for section/header/subheader as detected in parsing.
- **Bulk Actions**:
    - Approve all
    - Reject all
    - Apply “Auto-correct” to low-confidence entries
- **Row Actions**:
    - Approve, Reject, Edit, “AI Suggest” (request fallback from AI)
    - Mark as excluded/included (if wrong section detected)
- **Rule Editor Sidebar**:
    - Live editing of extraction rules (regex, header patterns, exclusions)
    - Preview rule effect on sample or full file
    - “Apply to All” to fix recurring format issues quickly

---

## **Refinement Flow**

1. **User lands on refinement table after upload and parsing**
    - All entries displayed, sorted by confidence (low-confidence highlighted first)
    - User can filter/sort by confidence, field value, or context

2. **User reviews each entry**
    - Edits any incorrect fields (producer, price, etc.)
    - Can accept/approve correct entries quickly
    - Rejects or excludes entries that do not belong (e.g., pairings, by-the-glass that slipped through)
    - For ambiguous rows, can view raw text and section context

3. **Rule Learning**
    - User corrections are logged:
        - Fixes to field extraction
        - Edits to headers, bottle size, etc.
        - Exclusion/inclusion changes
    - Corrections suggest rule updates in the sidebar (e.g., “detected new header: Chablis”, “new exclusion keyword: Tasting Menu”)
    - User can accept rule suggestions or edit further
    - Rules are versioned (can rollback/see history)

4. **AI Fallback**
    - For stubborn, ambiguous, or new formats:
        - User can click “AI Suggest” to trigger advanced NER/LLM extraction for a row or block
        - Result is shown for user to accept/edit
        - Use of AI is logged for review and to improve future fallback

5. **Bulk Actions**
    - Approve all, reject all, auto-correct low confidence in one click (to speed up large lists)

6. **Finalize**
    - Once user is satisfied, clicks “Finalize & Save”
    - All changes and new rules are stored, wine list is marked as refined
    - Optionally export as CSV/JSON

---

## **Audit & Traceability**

- All corrections, rule edits, and bulk actions are logged per user.
- Audit log available to admins for traceability and quality improvement.

---

## **User Experience Goals**

- Keep low-confidence and ambiguous entries “front and center” for fast review.
- Make editing, approving, or excluding any entry as quick as possible.
- Give instant feedback when rules are changed.
- Make it easy to retrain rules or reprocess a file if necessary.

---

