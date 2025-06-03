# Parsing Strategy

## Goals

- Reliably extract structured wine data from PDFs with highly variable formats.
- Handle multi-line wine entries, nested headers, contents/index pages, and context “stickiness.”
- Exclude "by the glass," wine pairings, and other non-listing items.
- Include all bottle sizes and variants.
- Minimize manual user correction via strong rules and targeted AI fallback.
- Make the system robust and self-improving as more files and corrections are processed.

---

## Pipeline Overview

1. **PDF Extraction**
    - Attempt native text extraction using `pdfminer.six` or `PyMuPDF`.
    - If text extraction fails or is poor, fallback to OCR (Tesseract).
    - Capture raw lines and their positional data where possible.

2. **Preprocessing**
    - Remove or flag non-content pages (title, notes, etc).
    - If a contents/index page is detected, use it to map headers to pages for more accurate section assignment.
    - Normalize text: whitespace cleanup, hyphen repair, unicode normalization.

3. **Header & Section Detection**
    - Identify main headers and subheaders using:
        - Font size/style (if available)
        - Line content and indentation
        - Known section names (from training/user feedback)
    - Assign all subsequent lines to current header/subheader (“sticky” context) until the next one is detected.
    - Support for multi-level/nested headers (e.g., Region > Subregion > Grape)

4. **Wine Entry Segmentation**
    - Group lines between headers into candidate wine entries.
    - Detect and merge multi-line entries using:
        - Indentation
        - Leading/trailing characters (e.g. price always at end)
        - Heuristics from training samples (per-restaurant rules)
    - Keep track of “raw” multi-line blocks for later correction if needed.

5. **Field Extraction**
    - Use combination of:
        - Restaurant-specific rules (regex patterns for known formats)
        - Global fallback rules (regexes, NER, spaCy pipelines)
        - Context from current headers/subheaders (e.g. region, country)
    - For each wine, extract:
        - Producer, Cuvee, Type, Vintage, Price, Bottle Size, Grape Variety, Country, Region, Subregion
    - Assign inherited header values if field is missing (e.g. all wines under "Burgundy" get region=Burgundy)
    - If field is ambiguous or missing, mark as low-confidence.

6. **Exclusion Filtering**
    - Mark and skip any entries under:
        - "By the Glass"
        - "Wine Pairings"
        - Known pairings, set menus, or non-bottle listings (as per rules)
    - Use both header context and pattern matching in lines themselves.

7. **Bottle Size/Variant Handling**
    - Support detection of all bottle sizes/types (750ml, magnum, half, etc).
    - Merge bottle variants under same wine as needed, or keep separate if price/size varies.

8. **AI/NLP Fallback**
    - For ambiguous, multi-line, or low-confidence cases:
        - Use AI models (spaCy NER, custom ML, or LLM call) to attempt better parsing.
        - Prompt LLM only with raw text block and current context to minimize cost.
    - Log all AI uses for review and future training.

9. **Rule Learning & Updates**
    - User corrections in the refinement UI are logged per field/entry.
    - Corrections automatically update per-restaurant rules:
        - New regexes
        - Header recognition patterns
        - Multi-line merge strategies
    - Corrections can also be used to periodically retrain global fallback models.

---

## Rule Engine

- **Per-Restaurant:**  
    - JSONB rule objects store known header formats, exclusion keywords, extraction regexes, and merging patterns.
    - Can be edited by user in UI (with live preview and “apply to all”)
    - Each new file is parsed first with these, then global rules if needed.

- **Global Rules:**  
    - Maintained by system, improved with user feedback across restaurants.
    - Includes “best guess” regexes, NER models, exclusion lists.

- **Rule Application Priority:**  
    1. Restaurant-specific rules (learned from training file and user corrections)
    2. Global rules/heuristics
    3. AI fallback (spaCy/LLM/NER)

---

## Data Confidence

- Every extracted field gets a confidence score:
    - Regex match: high
    - Inherited from section: medium
    - AI/LLM fallback: lower (unless model gives high certainty)
    - User-edited: 1.0 (highest)

---

## Refinement & Feedback

- After parsing, all extracted wines are shown in the refinement UI.
- Low-confidence or AI-extracted fields are highlighted for user review.
- User corrections are logged and fed back into rule/AI retraining.

---

## Extensibility

- Rules can be versioned for rollback or audit.
- Parsing pipeline can be updated independently of core API.
- New bottle sizes, field types, or exclusion logic can be added with minimal code changes.

---

