# Database Schema

## Overview

This schema is designed for flexibility, future-proofing, and clear separation between restaurants, wine list files, parsed wine entries, rules, and user actions.

---

## **Entities**

### **1. Restaurant**
- `id` (UUID, PK)
- `name` (string, unique)
- `date_created` (timestamp)
- `contact_email` (string)
- `notes` (text, optional)
- `ruleset_id` (UUID, FK → Ruleset)

### **2. WineListFile**
- `id` (UUID, PK)
- `restaurant_id` (UUID, FK → Restaurant)
- `filename` (string)
- `file_url` (string, S3 location)
- `uploaded_at` (timestamp)
- `parsed_date` (date, from filename/metadata)
- `status` (enum: uploaded, processing, parsed, refined, finalized)
- `notes` (text, optional)

### **3. WineEntry**
- `id` (UUID, PK)
- `wine_list_file_id` (UUID, FK → WineListFile)
- `restaurant_id` (UUID, FK → Restaurant)
- `producer` (string)
- `cuvee` (string)
- `type` (string)
- `vintage` (string)
- `price` (decimal/string, as in original)
- `bottle_size` (string)
- `grape_variety` (string)
- `country` (string)
- `region` (string)
- `subregion` (string)
- `row_confidence` (float)
- `field_confidence` (JSON: `{field: confidence}`)
- `section_header` (string)
- `subheader` (string, nullable)
- `raw_text` (text, for traceability)
- `status` (enum: auto, user_edited, confirmed, rejected)
- `last_modified` (timestamp)

### **4. Ruleset**
- `id` (UUID, PK)
- `restaurant_id` (UUID, FK → Restaurant)
- `rules_json` (JSONB: all current regexes, heuristics, and settings)
- `date_created` (timestamp)
- `last_updated` (timestamp)
- `active` (boolean)

### **5. User**
- `id` (UUID, PK)
- `email` (string, unique)
- `password_hash` (string)
- `name` (string)
- `role` (enum: admin, restaurant_admin, staff)
- `restaurant_id` (UUID, FK, nullable for admins)
- `date_joined` (timestamp)

### **6. AuditLog** *(optional but recommended)*
- `id` (UUID, PK)
- `user_id` (UUID, FK → User)
- `wine_entry_id` (UUID, FK → WineEntry, nullable)
- `wine_list_file_id` (UUID, FK → WineListFile, nullable)
- `action` (string)
- `old_value` (JSON, nullable)
- `new_value` (JSON, nullable)
- `timestamp` (timestamp)

---

## **Relationships**
- **Restaurant** `1—*` **WineListFile**
- **WineListFile** `1—*` **WineEntry**
- **Restaurant** `1—1` **Ruleset**
- **User** `*—*` **Restaurant** (many users may belong to many restaurants if you ever want, but start with 1—* for simplicity)
- **AuditLog** links changes by user to specific entries/files

---

## **Diagram (Text)**
```text
Restaurant
  |--< WineListFile
         |--< WineEntry
  |--1 Ruleset
  |--< User

User --< AuditLog >-- WineEntry/WineListFile
