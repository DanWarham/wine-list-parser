# Requirements

## Project Goal
Build a web app that allows restaurants to upload wine list PDFs and reliably extract, refine, and manage wine data for digital menus, inventory, or analysis.

## Core Features
- Restaurant onboarding with sample file upload for rule training
- Drag-and-drop PDF upload per restaurant (with date auto-detect)
- Robust PDF/OCR parsing, handling highly variable layouts and headers
- Only include full bottle listings; exclude "by the glass" and pairings
- Extract the following fields per wine:
    - Producer
    - Cuvee
    - Type
    - Vintage
    - Price
    - Bottle Size
    - Grape Variety
    - Country
    - Region
    - Subregion
- Section/header context handling (“stickiness”)
- User refinement UI with inline editing, confidence display, bulk actions
- Per-restaurant parsing rules, with global fallback and AI assist if needed
- Admin CRUD for restaurants, wine files, and rule management

## User Stories
- As an admin, I can manage all aspects of the system including restaurants, wine lists, uploaded files, parsing rules, and user accounts
- As an admin, I can perform all user-level search and filtering operations across the entire database
- As a user, I can search for wines across all uploaded wine lists using a unified search interface
- As a user, I can filter search results by any wine attribute (producer, type, vintage, price range, etc.)
- As a user, I can combine multiple filters to narrow down search results
- As a user, I can sort search results by any field (price, vintage, etc.)
- As a user, I can save frequently used search filters for quick access
- As a user, I can export filtered search results to CSV/Excel

