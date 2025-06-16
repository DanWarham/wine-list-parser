# Development Plan: Phase 2 — Parsing & Refinement Pipeline Refactor

## 1. Comparison: Current vs. Proposed System

### Current System
- Modular FastAPI backend, MinIO/S3 storage, basic rule-based and AI parsing, LWIN enrichment.
- User refinement via admin UI, some rule learning, no per-restaurant layout model.
- Frontend: Next.js/React, admin UI for upload/review/refinement, no interactive PDF overlay or advanced user-in-the-loop refinement.

### Proposed System (from parsing-refinement.md)
- Supabase for storage/auth/db, modular pipeline, per-restaurant layout classification, multi-level header detection.
- User-in-the-loop refinement with rule suggestion/approval, interactive PDF overlay, on-demand AI/LWIN, bulk edits, export.

---

## 2. Key Differences & Gaps

| Area                        | Current System                        | Proposed System         |
|-----------------------------|---------------------------------------|-------------------------|
| Storage                     | MinIO/S3, local DB                    | Supabase               |
| Layout Classification       | None/basic                            | Per-restaurant model    |
| Header/Section Detection    | Basic, single-level                   | Multi-level, sticky     |
| Field Extraction            | Regex, some AI, LWIN                  | Regex, NER, AI, LWIN   |
| Refinement Loop             | User edits, some rule learning        | User edits, rule engine |
| Interactive Overlay         | None                                  | PDF.js overlay         |
| AI/LWIN                     | Used for parsing/enrichment           | On-demand, user-driven |
| Bulk Edits                  | Basic                                 | Table, validation      |
| Rule Management             | Per-restaurant, basic                 | Global/per-restaurant  |
| Export                      | CSV/JSON possible                     | Explicit, mapped       |

---

## 3. Proposed New System Design

### Backend Pipeline
1. Upload to Supabase Storage, create DB entry.
2. PDF extraction (PyMuPDF, Tesseract fallback).
3. Preprocessing (normalize, tokenize, clean).
4. Per-restaurant layout classification (model/heuristics).
5. Multi-level header/section detection (sticky context).
6. Initial field extraction (global rules, NER, heuristics).
7. Save initial parse to DB, expose for review.
8. User-in-the-loop refinement: UI shows raw/parsed, user corrects, system proposes rules, user approves/edits, rules saved per restaurant.
9. AI/LWIN on-demand for low-confidence fields, rule suggestion, enrichment.
10. Bulk edits, validation, export.

### Frontend Features
- Admin dashboard: upload, review/refinement, interactive PDF overlay, table view for bulk edits, rule management UI, on-demand AI/LWIN, export.
- User workflow: upload → review/correct → approve/edit rules → refine → bulk review/edit → save/export.

### Rule Management
- Global and per-restaurant rules, user-driven refinement, rules stored as JSON.
- Rule suggestion engine, UI for approval/editing.

### AI/LWIN Integration
- OpenAI: On-demand parsing help, rule suggestion.
- LWIN: On-demand enrichment, validation.

---

## 4. Implementation Steps

### Step 1: Foundation & Planning ✅
- [x] Finalize new DB schema for Supabase (wine_lists, wine_entries, rulesets, users, etc.).
- [x] Set up Supabase project, migrate data.

### Step 2: Backend Refactor (In Progress)
- [x] Refactor file upload to use Supabase Storage.
- [ ] Modularize PDF extraction, preprocessing, and field extraction.
  - [ ] Refactor and cleanup PDF extraction using PyMuPDF with Tesseract fallback
  - [ ] Refactor and cleanup preprocessing pipeline (normalize, tokenize, clean)
  - [ ] Refactor field extraction to be more modular and configurable
  - [ ] Add support for different extraction strategies (regex, NER, AI)
- [ ] Implement per-restaurant layout classification (start with heuristics, add model later).
- [ ] Refactor header/section detection to support multi-level, sticky context.
- [ ] Refactor field extraction to be modular (global rules, NER, AI, LWIN).
- [ ] Implement confidence scoring and exclusion logic.
- [ ] Build rule suggestion engine (propose regex/rules from user corrections).
- [ ] Store rules as JSON per restaurant in DB.
- [ ] Expose endpoints for rule management, AI/LWIN on-demand actions.
- [ ] Clean up and remaining code/files which are no longer used


### Step 3: Frontend Refactor (In Progress)
- [x] Update upload UI to use Supabase.
- [x] Implement basic admin authentication and role-based access.
- [x] Set up admin dashboard layout and navigation.
- [ ] Build interactive PDF overlay (PDF.js) for field assignment, merge/split.
- [ ] Build review/refinement UI: show raw vs. parsed, confidence, allow corrections.
- [ ] Implement rule approval/editing UI.
- [ ] Add on-demand AI/LWIN actions for low-confidence fields.
- [ ] Add table view for bulk edits/validation.
- [ ] Add export options (CSV/JSON).

### Step 4: User-in-the-Loop & Rule Learning
- [ ] Implement backend logic for rule suggestion from corrections.
- [ ] Implement frontend prompts for rule approval/editing.
- [ ] Save new rules and optionally re-parse with improved rules.

### Step 5: Testing & Validation
- [ ] Unit/integration tests for each pipeline stage.
- [ ] End-to-end tests for upload → parse → refine → export.

### Step 6: Documentation & Training
- [ ] Update technical docs for new pipeline.
- [ ] Create user/admin guides for new UI/workflow.

---

## Summary Table: Old vs. New

| Feature                | Current System         | New System (Proposed)         |
|------------------------|-----------------------|-------------------------------|
| Storage                | MinIO/S3, local DB    | Supabase                      |
| Layout Classification  | None/basic            | Per-restaurant model          |
| Header Detection       | Basic                 | Multi-level, sticky context   |
| Field Extraction       | Regex/AI/LWIN         | Modular, NER, AI, LWIN        |
| Refinement Loop        | Basic                 | User-in-the-loop, rule learning|
| PDF Overlay            | None                  | Interactive, field assignment |
| AI/LWIN                | Used, not on-demand   | On-demand, user-triggered     |
| Bulk Edits             | Basic                 | Table, validation, export     |
| Rule Management        | Basic                 | Global/per-restaurant, UI     |

---

## Current Progress (Updated)

### Completed ✅
1. Supabase integration for auth and storage
2. Basic admin authentication and role-based access
3. Admin dashboard layout and navigation
4. File upload to Supabase Storage
5. Initial database schema and migrations

### In Progress 🚧
1. Backend pipeline refactoring
   - PDF extraction and preprocessing
   - Field extraction system
   - Layout classification
2. Frontend admin interface improvements
3. PDF processing and parsing logic
4. Rule management system

### Next Steps 📋
1. Refactor PDF extraction and preprocessing pipeline
2. Implement new field extraction system
3. Build layout classification system
4. Implement interactive PDF overlay
5. Build review/refinement UI
6. Add rule suggestion engine
7. Implement bulk edit functionality
8. Add export capabilities 