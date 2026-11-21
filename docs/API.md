# ALIGN REST API Reference Manual (`/api/v1`)

**Protocol**: HTTP/1.1 & HTTP/2 with JSON payloads and Server-Sent Events (SSE)  
**Base URL**: `http://localhost:8000/api/v1` (Development) | `/api/v1` (Production via Nginx)  
**Authentication**: HTTP `Authorization: Bearer <access_token>` header  

---

## 1. Authentication & Session Management (`/auth`)

### `POST /auth/register`
Creates a new user account with Argon2id password hashing.
- **Request Body**:
  ```json
  {
    "name": "Alice Innovator",
    "email": "alice@align.local",
    "password": "SuperSecurePass123!"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "id": 1,
    "name": "Alice Innovator",
    "email": "alice@align.local",
    "is_verified": false
  }
  ```

### `POST /auth/login`
Exchanges user credentials for short-lived access token and long-lived refresh token.
- **Request Body**:
  ```json
  {
    "email": "alice@align.local",
    "password": "SuperSecurePass123!"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "8fbc71a...",
    "token_type": "bearer",
    "user": { "id": 1, "name": "Alice Innovator", "email": "alice@align.local" }
  }
  ```

### `POST /auth/refresh`
Rotates and issues a new access token using a valid, unrevoked refresh token.
- **Request Body**: `{"refresh_token": "8fbc71a..."}`
- **Response (200 OK)**: `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`

---

## 2. Users, Profiles & Connections (`/users`)

### `GET /users/me`
Fetches authenticated user profile, real follower counts, connection counts, and total verified XP.
- **Headers**: `Authorization: Bearer <token>`
- **Response (200 OK)**:
  ```json
  {
    "id": 1,
    "name": "Alice Innovator",
    "email": "alice@align.local",
    "bio": "AI Systems Architect",
    "location": "San Francisco, CA",
    "skills": "Python, PyTorch, FastAPI",
    "interests": "Deep Learning, Robotics",
    "goals": "Build Open Source Intelligence",
    "connections_count": 12,
    "followers_count": 45,
    "total_xp": 450,
    "level": 5
  }
  ```

### `PUT /users/me/profile`
Updates profile details and recalculates dense profile embedding vector in PostgreSQL.
- **Request Body**:
  ```json
  {
    "bio": "Principal Full-Stack & AI Systems Architect",
    "location": "San Francisco, CA",
    "skills": "Python, React, TypeScript, Docker",
    "interests": "Generative AI, Graph Databases",
    "goals": "Scale Multi-Agent Networks"
  }
  ```
- **Response (200 OK)**: Updated user object.

### `GET /users?q={query}&limit=24`
Searches users using semantic similarity and skill/location matching.

### `POST /users/{user_id}/connect`
Sends a connection request to another user.
- **Response (200 OK)**: `{"status": "ok", "message": "Connection request sent", "connection_id": 74}`

### `POST /users/connections/{connection_id}/accept`
Accepts a pending incoming connection request. Updates mutual connection counts and syncs edge in Neo4j.

---

## 3. Communities (`/communities`)

### `GET /communities?category={cat}&search={q}&limit=20`
Lists active communities with DB-calculated live member counts.

### `POST /communities`
Creates a new community. Creator is automatically designated as Admin.
- **Request Body**:
  ```json
  {
    "name": "Autonomous Agents Collective",
    "description": "Exploration circle for distributed agent orchestration.",
    "category": "AI & Machine Learning",
    "purpose": "Collaborative Research"
  }
  ```
- **Response (201 Created)**: Created community object.

### `GET /communities/{community_id}`
Returns community details, active admin, and real member count.

### `POST /communities/{community_id}/join`
Joins a community. Increments DB member count and awards first-time join XP.

### `POST /communities/{community_id}/leave`
Leaves a community. Decrements DB member count.

### `GET /communities/{community_id}/discussions` & `POST /communities/{community_id}/discussions`
Retrieves and creates discussion posts within a community thread.

---

## 4. Events (`/events`)

### `GET /events?category={cat}&location={city}&time_filter=upcoming`
Searches real events with date, category, and location filters. Results include source verification flags (`align` vs `eventbrite`).

### `POST /events`
Creates an organizer-hosted event with capacity limits.
- **Request Body**:
  ```json
  {
    "title": "Bay Area AI Summit",
    "description": "Annual gathering of machine learning practitioners.",
    "category": "Technology",
    "location": "San Francisco, CA",
    "starts_at": "2026-11-20T18:00:00Z",
    "ends_at": "2026-11-20T22:00:00Z",
    "max_attendees": 100
  }
  ```
- **Response (201 Created)**: Event details with initial `registered_count: 0`.

### `POST /events/{event_id}/register`
RSVPs for an event. Validates seat capacity, issues a unique cryptographic ticket code, and prevents duplicate registration.
- **Response (200 OK)**: `{"ticket_code": "TCK-8f92-a1", "status": "confirmed"}`

---

## 5. Places & Venues (`/places`)

### `GET /places?city={city}&category={cat}&limit=20`
Returns curated and validated venues (Google Places / OpenStreetMap) with real coordinates (`latitude`, `longitude`), authentic photography, and ratings.

---

## 6. Discovery & Recommendations (`/discovery`)

### `GET /discovery/recommendations?limit=10`
Generates personalized, grounded recommendations across people, communities, events, places, and projects.
- **Response (200 OK)**:
  ```json
  [
    {
      "id": 88,
      "result_type": "community",
      "title": "Autonomous Agents Collective",
      "why_recommended": "Matched your declared interest in 'Deep Learning' and 'Generative AI'",
      "score": 0.89,
      "source": "align_db",
      "is_verified": true
    }
  ]
  ```

### `POST /discovery/feedback`
Submits explicit user feedback to continuously optimize the ranking algorithm.
- **Request Body**:
  ```json
  {
    "item_type": "community",
    "item_id": 88,
    "feedback": "relevant",
    "notes": "Highly aligned with my AI architecture goals"
  }
  ```
- **Feedback Options**: `"relevant"`, `"not_relevant"`, `"already_done"`, `"save_for_later"`.

---

## 7. Assistant V2 Intelligence (`/assistant`)

### `GET /assistant/conversations` & `POST /assistant/conversations`
Lists and creates user-scoped multi-turn conversation sessions.

### `POST /assistant/chat`
Synchronous turn processing with tool-calling execution and grounded recommendation card generation.
- **Request Body**:
  ```json
  {
    "conversation_id": 83,
    "message": "Find collaborators interested in machine learning and Python."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "conversation_id": 83,
    "content": "Here are the most active and relevant communities tailored to your interests:",
    "action_cards": [
      {
        "card_type": "community",
        "id": 90,
        "title": "Autonomous Agents Collective",
        "link": "/communities/90"
      }
    ],
    "citations": ["ALIGN Database Verification: Community #90"]
  }
  ```

### `POST /assistant/chat/stream`
Server-Sent Events (SSE) streaming endpoint delivering token-by-token deltas, tool status events, action cards, and completion signals.

### `GET /assistant/memories` & `PATCH /assistant/memories/{mem_id}`
Lists, updates, or deletes user-approved persistent facts and preferences stored by the assistant.

---

## 8. Goal Journeys (`/goals`)

### `POST /goals/generate`
Generates a structured multi-stage career and technical learning roadmap with milestones.
- **Request Body**:
  ```json
  {
    "title": "Master Production LLM Infrastructure",
    "category": "Career & Learning",
    "timeframe": "3-6 months"
  }
  ```
- **Response (201 Created)**: Goal journey object with numbered milestones, suggested resources, and recommended communities.

### `PATCH /goals/{journey_id}/milestones/{milestone_id}`
Toggles milestone completion. Updates journey progress percentage and awards verified XP.

---

## 9. Project Collaboration (`/projects`)

### `GET /projects` & `POST /projects`
Browses recruiting projects and publishes new collaboration proposals with required skill criteria.

### `POST /projects/{project_id}/apply`
Submits an application for a specific role.

### `POST /projects/{project_id}/applications/{app_id}/accept`
Creator accepts applicant into the project team, updating role and notifying member.

### `GET /projects/{project_id}/discussions` & `POST /projects/{project_id}/discussions`
Fetches and publishes real-time discussion messages within the project workspace.

---

## 10. Direct Messaging (`/messages`)

### `GET /messages?other_user_id={id}`
Retrieves persistent chronological message history between the authenticated user and another peer. Automatically marks incoming messages as read.

### `POST /messages`
Sends a direct message to a recipient.
- **Request Body**: `{"receiver_id": 2, "content": "Hey! Ready to collaborate?"}`

### `GET /messages/unread/count`
Returns total number of unread incoming messages across all conversations.

---

## 11. Gamification & XP (`/gamification`)

### `GET /gamification/profile`
Returns current level, total XP, next level threshold, and earned badges.

### `GET /gamification/history`
Returns paginated, immutable audit trail of all XP-awarded transactions, including verification timestamps and anti-duplicate keys (`dedup_key`).

---

## 12. Instagram Integration (`/instagram`)

Optional integration behind the `INSTAGRAM_ENABLED` feature flag using official Meta "Instagram API with Instagram Login". Requires an Instagram Business or Creator account. All tokens are encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256).

### `GET /instagram/status`
Returns integration status, connection health, account metadata, and pending suggestions count.
- **Headers**: `Authorization: Bearer <token>`
- **Response (200 OK)**:
  ```json
  {
    "enabled": true,
    "connected": true,
    "user_id": 1,
    "instagram_user_id": "99887766",
    "username": "creator_studio",
    "account_type": "CREATOR",
    "status": "connected",
    "media_count": 24,
    "last_synced_at": "2026-05-12T10:00:00Z",
    "recommendations_enabled": true,
    "profile_visible": true,
    "pending_suggested_interests_count": 3
  }
  ```

### `GET /instagram/connect`
Returns official Meta OAuth 2.0 authorization URL with a signed, expiring state parameter for CSRF mitigation.
- **Headers**: `Authorization: Bearer <token>`
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "authorize_url": "https://www.instagram.com/oauth/authorize?client_id=...&scope=instagram_business_basic&response_type=code&state=...",
    "note": "Meta requires an Instagram Business or Creator account for API access."
  }
  ```

### `GET /instagram/callback`
OAuth redirect URI. Validates state signature, exchanges code for short-lived token, upgrades to 60-day long-lived token, stores encrypted token at rest, and redirects user to `/settings?instagram=connected`.

### `POST /instagram/sync`
Fetches user's latest Instagram profile and media from Meta Graph API. Idempotently stores photos/videos, extracts hashtags, generates 384-dimensional embeddings, and creates pending suggested interests if opt-in recommendations are enabled.
- **Headers**: `Authorization: Bearer <token>`
- **Rate Limit**: 10 requests / 60 seconds

### `GET /instagram/media`
Returns stored media items for authenticated user or target user (if target has `instagram_profile_visible=true`).
- **Query Params**: `user_id` (optional), `limit` (default: 24, max: 50)
- **Response (200 OK)**: Array of media objects (`id`, `media_type`, `media_url`, `permalink`, `caption`, `timestamp`, `hashtags`).

### `POST /instagram/preferences`
Updates user's opt-in consent for recommendation engine and public profile tab visibility.
- **Request Body**: `{"recommendations_enabled": true, "profile_visible": true}`

### `GET /instagram/suggested-interests`
Lists pending, accepted, or rejected interests inferred from user's synced posts.
- **Query Params**: `status` (default: `"pending"`, `"accepted"`, or `"rejected"`)

### `POST /instagram/suggested-interests/{id}/accept` & `/reject`
Explicit user consent flow: accepts or rejects an inferred interest. Accepted interests are immediately added to the user's profile and synchronized to the Neo4j knowledge graph (`HAS_INTEREST`).

### `DELETE /instagram/disconnect`
Permanently deletes all encrypted tokens, account records, cached media, and pending suggested interests.

### `POST /instagram/deauthorize` & `POST /instagram/data-deletion`
Meta-required compliance callbacks. Validates HMAC-SHA256 `signed_request` from Meta and permanently purges user data. Data deletion returns Meta confirmation code and tracking URL.

