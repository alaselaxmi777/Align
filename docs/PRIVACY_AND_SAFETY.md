# ALIGN: Privacy & Safety Manual

**Platform**: ALIGN (An Intent and Embedding-Based Framework for Personalized Community and Experience Discovery)  
**Version**: 2.0.0 (Production-Grade Prototype)  
**Scope**: Safety Architecture, User Privacy Guarantees, 18+ Access Control, and Location Obfuscation  

---

## 1. 18+ Young Adult Policy & Access Restrictions

ALIGN is strictly engineered and policy-bound as an **18+ young adult and professional community discovery platform**.
- **Onboarding Boundary:** The onboarding age selector starts strictly at the 18–24 cohort. Accounts for minors are not accepted.
- **No Minors Safeguard:** In the event that minor accounts are introduced in future revisions, the platform enforces mandatory policy gates:
  - Zero public posts: All uploads default strictly to private or `connections_only`.
  - Zero location tags: Geographic area tagging is permanently disabled.
  - Non-discoverability: Profiles are hidden from non-connections and excluded from public search indexing.

---

## 2. EXIF & Metadata Stripping Pipeline

Whenever users upload images or video content, embedded hardware, device, and GPS metadata present a critical privacy hazard.

### Media Processing Security:
1. **Magic-Byte Inspection:** The server inspects the first 16 bytes of the uploaded file payload to verify real binary headers (`\xFF\xD8\xFF` for JPEG, `\x89PNG\r\n\x1a\n` for PNG, `RIFF....WEBP` for WebP, and `ftypisom`/`ftypmp42` for MP4). Extensions are never trusted.
2. **Pillow Re-Encoding:** All uploaded images pass through Pillow (`PIL.Image`). The raw pixels are read, stripped entirely of all EXIF metadata (including camera model, date-time stamps, and embedded GPS coordinates), and re-encoded into optimized WebP/JPEG formats across three normalized display dimensions:
   - **Thumbnail:** 300 × 300 px
   - **Feed:** 1080 × 1080 px
   - **Original:** Max 2048 px
3. **FFmpeg Video Cleansing:** All video uploads are transcoded using FFmpeg with `-map_metadata -1`, eliminating all camera device metadata and location tags while converting audio to AAC and video to H.264 MP4 with `+faststart`.

---

## 3. Coarse-Grid Geospatial Obfuscation

ALIGN connects people through local activities, venues, and communities across Maharashtra (Pune, Mumbai, Kolhapur, Nagpur, etc.) without ever tracking, storing, or broadcasting raw GPS telemetry.

### Geographic Privacy Mechanics:
- **Never Store Exact GPS:** The database never stores high-precision coordinates for user accounts.
- **Randomized Coarse Discretization:** When approximate location is enabled by the user, coordinates are projected onto a coarse spatial grid with a randomized Gaussian offset:
  $$\phi_{\text{obf}} = \phi_{\text{raw}} + \delta_{\phi} \,,\quad \lambda_{\text{obf}} = \lambda_{\text{raw}} + \delta_{\lambda}$$
  where $\delta$ is bounded to ensure privacy without breaking regional discovery.
- **User Privacy Levels:**
  - `hidden` / `off`: Location is completely withheld from all discovery calculations ($b_{\text{geo}} = 0$).
  - `city`: Coarse city-level string only (e.g., "Pune, Maharashtra").
  - `approximate`: Obfuscated coordinate band displayed to peers as categorical distance bands (e.g., *"Within 10 km"*, *"Within 25 km"*).
- **Haversine Distance Bonuses:** Calculated over obfuscated centroids:
  $$d = 2 R \arcsin\left( \sqrt{ \sin^2\left(\frac{\phi_x - \phi_u}{2}\right) + \cos(\phi_u) \cos(\phi_x) \sin^2\left(\frac{\lambda_x - \lambda_u}{2}\right) } \right)$$
  - Distance $\le 25\text{ km}$: $+0.10$ bonus ($+0.15$ for physical places).
  - Distance $25\text{ km} < d \le 50\text{ km}$: $+0.05$ bonus ($+0.08$ for physical places).

---

## 4. Visibility Boundaries & Access Control

ALIGN enforces a strict two-tier privacy model:

| Boundary Level | Behavior on Feed | Behavior on Direct Access | Search Indexing |
| :--- | :--- | :--- | :--- |
| **`public`** | Visible in public global feeds to all authenticated users and unauthenticated visitors. | Accessible via `GET /api/v1/feed/{id}`. | Fully indexed in pgvector candidate pools. |
| **`connections_only`** | Visible **only** to the author and accepted 1st-degree connections. | `GET /api/v1/feed/{id}` raises `403 Forbidden` if caller is not an accepted connection or admin. | Excluded from stranger recommendation pools. |

### Private Metrics & Anti-Surveillance
- **Public Engagement:** Like counts are visible publicly to foster social feedback.
- **Private Impression Analytics:** View counts and impression metrics are strictly confidential and visible **only** to the content author.
- **Upload Quotas:** To prevent spam generation and bot abuse, daily uploads are capped at **20 posts/reels per calendar day (UTC)** per user account (`HTTP 429 Too Many Requests` enforced).
