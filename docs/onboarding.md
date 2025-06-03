# Onboarding Flow (Restaurant Setup & Training)

## Overview

The onboarding process for new restaurants is designed to be simple, guided, and immediately beneficial. The goal is to ensure that, from the very start, the system can learn and adapt to each restaurant’s unique wine list formatting.

---

## **Step-by-Step Onboarding**

### 1. **Initiate Restaurant Creation**
- User clicks “Add Restaurant” from the Restaurants page
- Modal or page form:
    - Restaurant Name (required)
    - Contact Email (optional, for notifications)
    - Notes (optional)
    - "Next" button to continue

---

### 2. **Upload Sample Wine List File**
- Prompted to upload a sample PDF wine list (required for training)
    - Drag & drop area or click to select
    - Progress indicator on upload
    - Date auto-filled from file name or PDF metadata (editable)
    - Preview file name and metadata before proceeding

---

### 3. **Initial Parsing and Rule Generation**
- System parses the sample file:
    - Extracts text and layout using PDF parser/OCR
    - Detects headers, sections, and example wine entries
    - Suggests initial rules for field extraction, section headers, and exclusion zones
    - Populates sample extracted wines for user review

---

### 4. **Review and Confirm Training**
- User sees:
    - Table of sample extracted wines (fields filled by parsing/rules)
    - List of detected rules (header patterns, exclusion keywords, etc.)
    - Highlighted low-confidence fields or ambiguous extractions
- User can:
    - Edit/correct extracted wines inline (as in main refinement UI)
    - Edit/add/remove parsing rules (with live preview)
    - Mark exclusions as needed (e.g., “this section is by the glass”)
    - Accept/approve when satisfied

---

### 5. **Finalize Onboarding**
- On confirmation:
    - Restaurant is created and saved in database
    - Parsing rules and example wines are stored
    - User is directed to the restaurant's dashboard or file upload page for ongoing use

---

## **Special Notes**

- **No restaurant can be fully enabled without a training sample.**  
    - This ensures best possible parsing results from the start.
- **Rules are always user-editable later** (from the restaurant’s rules editor page)
- **Admin can restart onboarding at any time** (e.g., to add more training files if menu format changes)

---

## **Future Enhancements**
- Allow multiple training files for more robust rule generation.
- Provide onboarding hints/tutorial for new users.

---

