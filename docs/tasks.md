# Tasks & Milestones

## Version 0.1 (MVP)
- [x] Database schema created and migrated (PostgreSQL)
- [ ] Auth (JWT for API, NextAuth.js for frontend)
- [ ] Restaurant onboarding flow (form, sample file upload, rule training)
- [ ] File upload endpoint and S3 integration
- [ ] PDF & OCR parsing pipeline (including AI fallback)
- [ ] Wine entry extraction with per-field confidence
- [ ] Basic refinement UI (TanStack Table, inline edit, approve/reject)
- [ ] Restaurant admin UI (CRUD, rule editor, list files)

---

## Version 0.2 (Core Product)
- [ ] Robust rule engine (restaurant-specific, global fallback, editable in UI)
- [ ] Advanced parsing: header stickiness, multi-line merge, exclusion logic
- [ ] Bulk actions in refinement UI (approve all, auto-correct low confidence, export)
- [ ] Contents/index page handling in parsing pipeline
- [ ] AI/NLP fallback for low-confidence or ambiguous rows
- [ ] Audit logging for corrections, rule changes, deletions

---

## Version 1.0 (Launch)
- [ ] Full error handling & user feedback
- [ ] CI/CD setup for automated testing and deploys
- [ ] Production S3 and managed Postgres integration
- [ ] Documentation and onboarding guides
- [ ] Comprehensive E2E tests and UX polish
- [ ] Prepare for first production deployment

---

## Stretch/Optional Features
- [ ] Dark mode toggle
- [ ] Multi-user roles and permissions
- [ ] Multiple sample/training files per restaurant
- [ ] Multi-language support for parsing/extraction
- [ ] Advanced analytics and reporting
