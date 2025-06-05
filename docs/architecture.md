# Architecture

## Tech Stack
- **Frontend:** Next.js, React, Tailwind CSS, shadcn/ui, TanStack Table
- **Backend:** Python FastAPI (PDF parsing, OCR, rule engine, AI)
- **Database:** PostgreSQL (managed)
- **Auth:** JWT or NextAuth.js
- **File Storage:** S3-compatible (AWS S3, MinIO)

## High-Level Architecture
1. **Frontend**
    - User authentication, file upload, and interactive refinement UI
    - REST API calls to backend for all data operations

2. **Backend**
    - FastAPI server for file handling, parsing, and rule management
    - PDF text extraction (pdfminer, PyMuPDF), OCR fallback (Tesseract)
    - Per-restaurant rule engine
    - AI/NER fallback for ambiguous fields

3. **Database**
    - PostgreSQL: restaurants, wine lists, wines, rules, users, logs

4. **Storage**
    - S3 or compatible bucket for file uploads

## Core Workflow
- User selects restaurant, uploads wine list PDF
- Backend parses file using restaurant’s rules + global heuristics
- Extracted wines shown in refinement table for user confirmation/correction
- User corrections are saved; rules are retrained for future files

## Deployment
- Dockerized frontend & backend
- CI/CD for auto-build and deploy to production cloud
- Managed PostgreSQL and S3

## Folder Structure
See `/docs` for planning, `/frontend` and `/backend` for code.
