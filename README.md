# Wine List Parser

A professional web application for extracting, refining, and managing wine list data from restaurant PDF menus.

## Key Features
- Drag-and-drop PDF upload with OCR extraction
- Handles complex, variable layouts and multi-line wine entries
- Custom parsing rules per restaurant (auto-learned and user-editable)
- User refinement UI for confirming and correcting extracted data
- Excludes by-the-glass and wine pairings; supports all bottle types/sizes
- AI fallback for ambiguous entries, with learning loop from user corrections
- Admin management of restaurants, wine lists, and parsing rules

## Tech Stack
- **Frontend:** Next.js, React, Tailwind CSS, shadcn/ui, TanStack Table
- **Backend:** Python FastAPI (PDF & OCR parsing, AI integration)
- **Database:** PostgreSQL (managed)
- **Auth:** JWT or NextAuth.js
- **Storage:** S3 or compatible

## Getting Started
_TODO: Setup and install instructions will go here._
