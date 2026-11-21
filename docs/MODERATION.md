# ALIGN: Moderation & Safety Architecture Manual

**Platform**: ALIGN (An Intent and Embedding-Based Framework for Personalized Community and Experience Discovery)  
**Version**: 2.0.0 (Production-Grade Prototype)  
**Scope**: Ingestion Pipelines, Reporting Endpoints, Admin Review Queue, Content Masking, and Policy Enforcement  

---

## 1. Moderation Philosophy & Scope

ALIGN employs a human-in-the-loop, administrative moderation model. Because generative or automated AI content classifiers are prone to high false-positive rates (especially on regional linguistic nuances and Hinglish slang), the platform does not utilize automated black-box bans. 

Instead, ALIGN combines:
1. **User-Driven Signal Reporting:** Fast, accessible reporting mechanisms on all posts, reels, comments, and user profiles.
2. **Administrative Takedown Desk:** A centralized review queue located at `/admin` accessible only to accounts with `is_admin=True` or `role="admin"`.
3. **Real-Time Database Content Masking:** Zero-latency removal of reported items from public feeds via indexed boolean flags (`is_hidden`).
4. **Audit Trail Logging:** Permanent record of reporter identity, target IDs, administrative action notes, and resolution timestamps.

---

## 2. Ingestion & Reporting API

### Endpoint Specification
```http
POST /api/v1/reports
Authorization: Bearer <user_jwt_token>
Content-Type: application/json
```

### Request Payload (`CreateReportRequest`)
```json
{
  "target_type": "post",
  "target_id": 4,
  "reason": "Spam or Commercial Solicitation",
  "details": "Malicious crypto phishing link in public feed."
}
```

### Supported Target Types & Integrity Safeguards:
- `target_type`: `"post" | "reel" | "user" | "comment"`
- **Anti-Self-Report Validation:** Users attempting to report themselves or their own posts/reels receive `HTTP 400 Bad Request` (`"You cannot report your own post."`).
- **Entity Resolution:** The API verifies the existence of the target in PostgreSQL, extracts the underlying author ID, and persists a `UserReport` record with `status="pending"`.

---

## 3. Administrative Actions & Review Queue

The review queue is queried via `GET /api/v1/admin/reports?status_filter=pending`. Each pending item surfaces:
- Target classification (`POST`, `REEL`, `USER`)
- Reporter identity and timestamp
- Target user / author details
- Extracted content snippet preview
- Optional reporter notes

### Action Endpoint
```http
POST /api/v1/admin/reports/{report_id}/action
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
  "action": "remove_content",
  "note": "Confirmed commercial phishing link."
}
```

### The 4 Standard Moderation Decisions:

| Action Identifier | System Mechanics | User Impact | Report Lifecycle |
| :--- | :--- | :--- | :--- |
| **`remove_content`** | Sets `post.is_hidden = True` or `reel.is_hidden = True`. | Immediately masked from all feeds; returns `404 Not Found` to regular callers. Creates formal `Notification` to the author. | Marked `resolved`. |
| **`warn_user`** | Dispatches an official platform warning `Notification` to the author's account (`"Official Community Warning"`). | Account remains active; user is informed of specific guideline violation. | Marked `resolved`. |
| **`suspend_user`** | Sets `user.is_active = False` in the database. | User's JWT session is blocked from all stateful actions; cannot post, comment, or interact. | Marked `resolved`. |
| **`dismiss_report`** | Leaves content and user status unaffected. | No impact on user or content. | Marked `dismissed`. |

---

## 4. Real-Time Content Masking

Content masking is enforced at the database query layer:
- **Feed Queries (`GET /api/v1/feed`):**
  ```python
  stmt = select(Post).join(User, Post.author_id == User.id).where(User.is_test == False)
  if not user or getattr(user, "role", "user") != "admin":
      stmt = stmt.where(Post.is_hidden == False)
  ```
- **Reels Queries (`GET /api/v1/reels`):**
  ```python
  stmt = select(Reel).where(Reel.is_test == False)
  if not user or getattr(user, "role", "user") != "admin":
      stmt = stmt.where(Reel.is_hidden == False)
  ```
- **Direct Detail Endpoints:**
  Calls to `GET /api/v1/feed/{post_id}` evaluate `post.is_hidden`. If `True` and the caller is not an administrator, the server raises `HTTP 404 Not Found` to prevent URL scraping or cache leaks, while administrators retain full `HTTP 200 OK` audit inspection privileges.

---

## 5. Contact & Takedown Desk

For demo and testing purposes, takedown requests and community inquiries are directed to the designated desk placeholder:
- **Takedown & Safety Desk:** `takedown@align.internal`
- **Response SLA:** Within 24 hours of ticket submission.
