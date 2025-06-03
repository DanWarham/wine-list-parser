# API Design

## Overview

The backend provides a RESTful API for file uploads, parsing, wine entry management, rules, users, and authentication.  
All endpoints are authenticated with JWT (or NextAuth for frontend).  
All payloads are JSON unless otherwise noted.

---

## **Authentication**

- `POST /api/auth/login`  
    - Body: `{ email, password }`
    - Response: `{ token, user }`

- `POST /api/auth/register`
    - Body: `{ email, password, name, restaurant_id? }`
    - Response: `{ token, user }`

---

## **Restaurant Management**

- `GET /api/restaurants`
    - Response: `[ { id, name, ... } ]`

- `POST /api/restaurants`
    - Body: `{ name, contact_email }`
    - Response: `{ id, name, ... }`

- `GET /api/restaurants/:id`
    - Response: `{ id, name, ... }`

- `PUT /api/restaurants/:id`
    - Body: `{ name, contact_email, notes }`
    - Response: `{ ... }`

- `DELETE /api/restaurants/:id`
    - Response: `204 No Content`

---

## **Ruleset Management**

- `GET /api/restaurants/:id/ruleset`
    - Response: `{ id, rules_json, last_updated }`

- `PUT /api/restaurants/:id/ruleset`
    - Body: `{ rules_json }`
    - Response: `{ ... }`

- `POST /api/restaurants/:id/ruleset/train`
    - Body: `{ wine_list_file_id }`
    - Response: `{ rules_json, training_log }`

---

## **Wine List File Upload & Parsing**

- `POST /api/wine-lists/upload`
    - Multipart/form-data: `file`, `restaurant_id`, `parsed_date?`
    - Response: `{ file_id, status, upload_url }`

- `GET /api/wine-lists/:file_id`
    - Response: `{ ...file metadata..., status, restaurant, wines: [...] }`

- `DELETE /api/wine-lists/:file_id`
    - Response: `204 No Content`

- `GET /api/restaurants/:id/wine-lists`
    - Response: `[ { file_id, filename, uploaded_at, status, ... } ]`

---

## **Wine Entry Management**

- `GET /api/wine-entries/:file_id`
    - Response: `[ { ...fields, confidence, section_header, ... } ]`

- `PUT /api/wine-entries/:wine_entry_id`
    - Body: `{ ...fields to update... }`
    - Response: `{ ...updated entry... }`

- `PUT /api/wine-entries/bulk`
    - Body: `{ entries: [ { id, fields... } ] }`
    - Response: `{ updated: [ ... ] }`

- `POST /api/wine-entries/:wine_entry_id/reject`
    - Response: `{ status: "rejected" }`

---

## **Refinement & Rule Feedback**

- `POST /api/wine-lists/:file_id/refine`
    - Body: `{ corrections: [ { wine_entry_id, field, new_value } ] }`
    - Response: `{ updated: [ ... ] }`

- `POST /api/wine-lists/:file_id/ai-suggest`
    - Body: `{ wine_entry_id }`
    - Response: `{ suggestions: { field: value, ... }, confidence: { field: score } }`

---

## **User Management (Admin Only)**

- `GET /api/users`
- `POST /api/users`
- `PUT /api/users/:id`
- `DELETE /api/users/:id`

---

## **Sample Payloads**

### **Wine Entry**
```json
{
  "id": "uuid",
  "wine_list_file_id": "uuid",
  "restaurant_id": "uuid",
  "producer": "Domaine Leroy",
  "cuvee": "Musigny Grand Cru",
  "type": "Red",
  "vintage": "2018",
  "price": "€2500",
  "bottle_size": "750ml",
  "grape_variety": "Pinot Noir",
  "country": "France",
  "region": "Burgundy",
  "subregion": "Côte de Nuits",
  "row_confidence": 0.95,
  "field_confidence": { "producer": 0.98, "vintage": 0.85 },
  "section_header": "Red Burgundy",
  "subheader": "Grand Cru",
  "raw_text": "...original text...",
  "status": "user_edited"
}
