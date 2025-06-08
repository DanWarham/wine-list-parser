# Tasks & Milestones

## Version 0.1 (MVP)
- [x] Database schema created and migrated (PostgreSQL)
- [x] Auth (JWT for API, NextAuth.js for frontend)
- [x] Admin CRUD UI (restaurants, users, wine lists, wine entries, rules) — backend and frontend CRUD implemented and wired up
- [ ] Restaurant onboarding flow (form, sample file upload, rule training)
- [x] File upload endpoint and S3 integration (basic upload working; S3/MinIO integration in place)
- [ ] PDF & OCR parsing pipeline (including AI fallback)
- [ ] Wine entry extraction with per-field confidence
- [ ] Basic refinement UI (TanStack Table, inline edit, approve/reject)
- [x] Restaurant admin UI (CRUD, rule editor, list files) — fully styled and professional dashboard, cards, and navigation
- [x] Frontend and UI styling (user menu, login, registration, dashboard, search pages) — consistent Tailwind/shadcn/ui styling throughout admin
- [x] Authentication/session issues resolved (NextAuth, token refresh, error handling)
- [ ] Wine lists stat on dashboard (blocked: no global wine lists endpoint; only per-restaurant for now)

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
