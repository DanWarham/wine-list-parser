# 📝 Parsing & Refinement Pipeline

## **Overview**
The Wine List Parser app is designed to extract, structure, and refine wine list data from restaurant PDFs, supporting highly variable layouts. It uses a hybrid approach: rule-based parsing, per-restaurant model learning, AI/LWIN-assisted correction, and user-in-the-loop refinement.

---

## **Technical Stack**

- **PDF Extraction:**  
  - [`PyMuPDF`](https://pymupdf.readthedocs.io/) (primary, for text, font, and position extraction)
  - [`pytesseract`](https://pypi.org/project/pytesseract/) (fallback OCR for images/unextractable text)
- **Preprocessing:**  
  - Python (`re`, `pandas`), Unicode normalization
- **Header/Section Detection:**  
  - Heuristics, indentation analysis, font/size detection, custom models (`scikit-learn`/`OpenVINO`/`GGML`)
- **Field Extraction:**  
  - Regex, spaCy NER, and rule-based parsing (Producer, Cuvee, Type, Vintage, Price, Size, etc.)
- **Per-Restaurant Learning:**  
  - Lightweight layout classifiers (`scikit-learn`, deploy via `OpenVINO` or `GGML`)
- **AI Assistance:**  
  - [OpenAI GPT-3.5 Turbo](https://platform.openai.com/docs/guides/gpt), for sparse, on-demand parsing/learning
  - [LWIN API](https://api.liv-ex.com/) for wine matching, data enrichment
- **Frontend UI:**  
  - React (Vite), Tailwind, shadcn/ui, `pdf.js` for live, interactive PDF overlays
- **State & Data:**  
  - Supabase (auth, database, storage)
  - REST API (FastAPI, Python)

---

## **Processing Pipeline**

1. **File Upload**
   - User uploads a PDF to a specific restaurant in the app (frontend: drag-and-drop UI).
   - File is saved in Supabase Storage; entry is created in the `wine_lists` table.

2. **PDF Extraction**
   - Backend uses PyMuPDF to extract:
     - Raw text lines (with line breaks as in the PDF)
     - Positional metadata (page, bbox: x, y, width, height)
     - Font/size/style (if available)
   - If text extraction fails (scanned or image-only), fallback to OCR using Tesseract.

3. **Preprocessing**
   - Clean up extracted text:
     - Normalize whitespace, fix hyphenation, Unicode normalization
     - Remove or flag non-content pages (title, index, notes)
   - Tokenize by lines, attach metadata

4. **Layout Classification (Per-Restaurant Model)**
   - For each restaurant, apply a lightweight model/classifier (trained on past uploads):
     - Detects layout style (single-line, multi-line, grouped, header style, etc.)
     - Guides which parsing rules or heuristics to apply
   - Model is trained with user-refined data (sklearn/transformer, deployed via OpenVINO or GGML)

5. **Header & Section Detection**
   - Detect headers/subheaders (region, country, type, etc.) by:
     - Font size/style, indentation, keywords
     - “Sticky” assignment: all subsequent lines inherit current header context until next header
   - Supports nested headers (multi-level context)

6. **Initial Field Extraction (Rule-based)**
   - Parse each wine entry using **global rules** (regex, NER, heuristics):
     - Extract: Producer, Cuvee, Type, Vintage, Price, Size, Region, Country, etc.
   - Exclude entries from known exclusion zones (“by the glass”, pairings, etc.), based on header/context/position.

7. **Refinement Loop**
   - **Step 1: Display raw text vs. parsed fields in the UI** (with confidence scores)
   - **Step 2: User reviews/corrects fields.**
     - On each correction:
       - Analyze delta (change) between raw and corrected
       - Propose new regex/rule for similar future entries (user can approve/edit/decline)
   - **Step 3: Save new/updated rules to restaurant’s ruleset.**
   - **Step 4: Optionally, re-parse next wine using improved rules.**

8. **Interactive PDF Overlay**
   - Render original PDF in-browser using `pdf.js`
   - Overlay clickable/highlightable bounding boxes for each extracted line/field
   - User can click a line/region to assign it to a wine entry or field
   - Multi-line merge/split supported via selection

9. **AI/LWIN Assistance (On-Demand)**
   - If a field/entry is still low-confidence, user can trigger:
     - **AI Parsing** (OpenAI GPT-3.5 Turbo): Suggest fields, propose parsing logic
     - **LWIN Search:** Lookup extracted text in LWIN API, fetch possible matches and metadata
     - **Rule Generation:** Use AI to summarize parsing patterns in the current file
   - Results are only saved/applied if user approves

10. **Bulk Edits & Validation**
    - After refinement, show table of all parsed wines
    - User can bulk-edit (e.g., assign region, correct bottle size), approve, or mark as verified/unverified

11. **Save & Export**
    - All parsed wines, with their fields and source mapping, are saved in Supabase
    - Option to export as CSV, JSON, or re-parse with new rules on future uploads

---

## **Rule Management**

- **Global rules** (for new restaurants/unknown formats)
- **Per-restaurant rules** (created/refined by user actions, stored in DB as JSON)
- **Rules include:** Regex patterns, parsing heuristics, exclusion logic, section mapping
- **User-driven refinement**: UI prompts user to accept/modify proposed rules

---

## **User Workflow**

1. **Upload a wine list PDF to a restaurant**
2. **Review and refine first parsed wine**
   - Accept/correct fields, approve suggested rules
3. **Refine next wines using improved rules**
   - Repeat until user satisfied (can skip to full-parse at any time)
4. **Bulk review, approve, or correct parsed data**
5. **Save results and optionally export**

---

## **AI & LWIN Integration**

- **OpenAI GPT-3.5 Turbo**:
   - Used for:
     - On-demand parsing help (“Help me parse this row”)
     - Rule suggestion/extraction from corrected examples
   - NOT used for full-file parsing (cost/speed constraints)

- **LWIN API**:
   - Used to:
     - Match parsed wines with official LWIN entries
     - Enrich fields (region, producer, etc.)
     - Validate or auto-fill unknowns (on-demand, user-triggered)

- **Local Model (OpenVINO/GGML):**
   - For structure/layout parsing
   - Fast inference on most files, no API cost

---

---

<!-- ## **References**
- See `/docs/architecture.md` for overall architecture
- See `/docs/tasks.md` for actionable tasks and progress
- See `/backend/` for FastAPI parsing endpoints and rule management code
- See `/frontend/` for interactive refinement UI and Supabase integration -->

---

