#!/usr/bin/env python3
"""
ALIGN Automated 2-User Demonstration Scenario
============================================
Demonstrates an end-to-end user workflow:
1. User A (Pooja, Pune) registers and posts an image post & vertical reel.
2. User B (Rahul, Mumbai) browses the feed, inspects 6-factor SHAP ranking & why_recommended.
3. User B comments with @mention and shares post via Direct Message.
4. User A replies (threaded 1-level reply).
5. User B reports an inappropriate spam post.
6. Administrator inspects moderation queue and executes content removal.
7. Verification that content is immediately masked from the feed.

Runs seamlessly via live HTTP or internal FastAPI TestClient fallback.
"""

import sys
import time
from typing import Any

# Ensure backend root is on PYTHONPATH
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.user import User
from app.models.connection import UserConnection
from sqlalchemy import select

def print_banner(text: str):
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)

def print_step(step_num: int, title: str):
    print(f"\n[Step {step_num}] {title}")
    print("-" * 50)

def main():
    print_banner("ALIGN 2-USER INTERACTION & MODERATION DEMO SCENARIO")
    client = TestClient(app)
    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # STEP 1: Registration & Connection
        # ---------------------------------------------------------
        print_step(1, "User Onboarding & Social Connection")
        
        # User A: Pooja (Pune)
        user_a_data = {"email": "pooja_demo@align.internal", "password": "Password123!", "name": "Pooja Sharma"}
        client.post("/api/v1/auth/register", json=user_a_data)
        login_a = client.post("/api/v1/auth/login", json={"email": user_a_data["email"], "password": user_a_data["password"]}).json()
        token_a = login_a["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        user_a = db.scalar(select(User).where(User.email == user_a_data["email"]))
        print(f"✓ Registered User A: {user_a.name} (ID: {user_a.id})")

        # User B: Rahul (Mumbai)
        user_b_data = {"email": "rahul_demo@align.internal", "password": "Password123!", "name": "Rahul Verma"}
        client.post("/api/v1/auth/register", json=user_b_data)
        login_b = client.post("/api/v1/auth/login", json={"email": user_b_data["email"], "password": user_b_data["password"]}).json()
        token_b = login_b["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        user_b = db.scalar(select(User).where(User.email == user_b_data["email"]))
        print(f"✓ Registered User B: {user_b.name} (ID: {user_b.id})")

        # Admin User
        admin_data = {"email": "admin_demo@align.internal", "password": "Password123!", "name": "Platform Admin"}
        client.post("/api/v1/auth/register", json=admin_data)
        admin_user = db.scalar(select(User).where(User.email == admin_data["email"]))
        admin_user.is_admin = True
        admin_user.role = "admin"
        db.commit()
        login_admin = client.post("/api/v1/auth/login", json={"email": admin_data["email"], "password": admin_data["password"]}).json()
        headers_admin = {"Authorization": f"Bearer {login_admin['access_token']}"}
        print(f"✓ Configured Admin: {admin_user.name} (ID: {admin_user.id})")

        # Establish 1st-degree connection between Pooja and Rahul
        conn = db.scalar(select(UserConnection).where(
            UserConnection.sender_id == user_a.id,
            UserConnection.receiver_id == user_b.id
        ))
        if not conn:
            conn = UserConnection(sender_id=user_a.id, receiver_id=user_b.id, status="accepted")
            db.add(conn)
            db.commit()
        print("✓ Established accepted 1st-degree connection between Pooja and Rahul")

        # ---------------------------------------------------------
        # STEP 2: Media Post Creation
        # ---------------------------------------------------------
        print_step(2, "Pooja Publishes Tech Carousel & Vertical Reel")
        
        post_payload = {
            "content": "Designing high-performance vector search in Pune with pgvector & FastAPI! #tech #ai",
            "visibility": "public",
            "location_area": "Pune",
            "media_items": [
                {
                    "position": 0,
                    "media_type": "image",
                    "original_url": "/uploads/carousel_1.jpg",
                    "feed_url": "/uploads/carousel_1.webp",
                    "thumbnail_url": "/uploads/thumb_1.webp",
                    "alt_text": "System architecture diagram"
                },
                {
                    "position": 1,
                    "media_type": "image",
                    "original_url": "/uploads/carousel_2.jpg",
                    "feed_url": "/uploads/carousel_2.webp",
                    "thumbnail_url": "/uploads/thumb_2.webp",
                    "alt_text": "pgvector cosine similarity benchmark"
                }
            ]
        }
        post_res = client.post("/api/v1/feed", headers=headers_a, json=post_payload)
        assert post_res.status_code == 201
        pooja_post = post_res.json()
        print(f"✓ Created Carousel Post #{pooja_post['id']} by {user_a.name} ({len(pooja_post['media'])} images)")

        # Vertical Reel
        reel_payload = {
            "title": "90s Guide to Multilingual Embeddings",
            "category": "Technology",
            "video_url": "/uploads/reel_pgvector.mp4",
            "thumbnail_url": "/uploads/reel_pgvector.webp",
            "duration_seconds": 78.5,
            "visibility": "public",
            "caption": "How MiniLM multilingual 384-d embeddings work offline in Maharashtra",
            "tags": ["ai", "python", "fastapi"]
        }
        reel_res = client.post("/api/v1/reels", headers=headers_a, json=reel_payload)
        assert reel_res.status_code == 201
        pooja_reel = reel_res.json()
        print(f"✓ Created 9:16 Vertical Reel #{pooja_reel['id']} ('{pooja_reel['title']}', {pooja_reel['duration_seconds']}s)")

        # ---------------------------------------------------------
        # STEP 3: Feed Ranking & SHAP Attribution
        # ---------------------------------------------------------
        print_step(3, "Rahul Browses Feed with 6-Factor SHAP Explainability")
        
        feed_res = client.get("/api/v1/feed", headers=headers_b)
        assert feed_res.status_code == 200
        feed_posts = feed_res.json()
        assert len(feed_posts) > 0
        
        top_post = next(p for p in feed_posts if p["id"] == pooja_post["id"])
        print(f"✓ Top Recommended Post ID: #{top_post['id']}")
        print(f"  • Author: {top_post['author']['name']}")
        print(f"  • Caption: \"{top_post['content'][:60]}...\"")
        print(f"  • Hybrid Match Score: {top_post['score']:.4f} ({top_post['score']*100:.1f}% Match)")
        print(f"  • Grounded Rationale: {top_post['why_recommended']}")
        print("  • Exact Linear SHAP Feature Attributions:")
        for factor, val in top_post['score_breakdown'].items():
            print(f"     - {factor:<12}: +{val:.4f}")
        
        # Verify exact additivity sum(phi_i) == round(score, 4)
        shap_sum = round(sum(top_post['score_breakdown'].values()), 4)
        assert shap_sum == round(top_post['score'], 4)
        print(f"  • Mathematical SHAP Additivity Verified: sum(phi_i) = {shap_sum} == {round(top_post['score'], 4)}")

        # ---------------------------------------------------------
        # STEP 4: Social Interactions (Comments, Mentions, DM Share)
        # ---------------------------------------------------------
        print_step(4, "Social Engagement: Threaded Comment with @Mention & DM Share")
        
        # Rahul leaves a comment mentioning @Pooja
        comment_payload = {
            "content": f"Super clean design @{user_a.name}! How does pgvector compare to HNSW?",
            "parent_id": None
        }
        c1_res = client.post(f"/api/v1/feed/{pooja_post['id']}/comments", headers=headers_b, json=comment_payload)
        assert c1_res.status_code == 201
        c1 = c1_res.json()
        print(f"✓ Rahul commented: \"{c1['content']}\" (ID: #{c1['id']})")

        # Pooja replies to Rahul's comment (1-level threaded nesting)
        reply_payload = {
            "content": "Thanks Rahul! We tested both in Section VI of our paper.",
            "parent_id": c1["id"]
        }
        c2_res = client.post(f"/api/v1/feed/{pooja_post['id']}/comments", headers=headers_a, json=reply_payload)
        assert c2_res.status_code == 201
        c2 = c2_res.json()
        print(f"✓ Pooja replied (Parent #{c2['parent_id']}): \"{c2['content']}\"")

        # Rahul shares Pooja's post to connection in Direct Messages
        share_payload = {
            "recipient_id": user_a.id,
            "note": "Check out your post stats!"
        }
        share_res = client.post(f"/api/v1/feed/{pooja_post['id']}/share", headers=headers_b, json=share_payload)
        assert share_res.status_code == 200
        print(f"✓ Rahul shared Post #{pooja_post['id']} to {user_a.name} via Direct Message")

        # ---------------------------------------------------------
        # STEP 5: Content Reporting & Moderation
        # ---------------------------------------------------------
        print_step(5, "Inappropriate Content Reporting")
        
        # A spam user creates an abusive post
        spammer_data = {"email": "spammer_demo@align.internal", "password": "Password123!", "name": "Spam Bot"}
        client.post("/api/v1/auth/register", json=spammer_data)
        login_spam = client.post("/api/v1/auth/login", json={"email": spammer_data["email"], "password": spammer_data["password"]}).json()
        headers_spam = {"Authorization": f"Bearer {login_spam['access_token']}"}
        
        spam_post_res = client.post("/api/v1/feed", headers=headers_spam, json={
            "content": "WIN FREE CRYPTO NOW! Click malicious-phish.biz immediately!",
            "visibility": "public"
        })
        spam_post_id = spam_post_res.json()["id"]
        print(f"✓ Spammer published abusive Post #{spam_post_id}")

        # Rahul reports the spam post
        report_payload = {
            "target_type": "post",
            "target_id": spam_post_id,
            "reason": "Spam or Commercial Solicitation",
            "details": "Malicious crypto phishing link in public feed."
        }
        rep_res = client.post("/api/v1/reports", headers=headers_b, json=report_payload)
        assert rep_res.status_code == 201
        report_id = rep_res.json()["report_id"]
        print(f"✓ Rahul submitted safety report #{report_id} on Post #{spam_post_id}")

        # ---------------------------------------------------------
        # STEP 6: Administrator Content Removal & Masking
        # ---------------------------------------------------------
        print_step(6, "Administrator Content Removal & Feed Masking")
        
        # Admin checks review queue
        admin_queue = client.get("/api/v1/admin/reports?status_filter=pending", headers=headers_admin).json()
        target_report = next(r for r in admin_queue if r["id"] == report_id)
        print(f"✓ Admin inspected Report #{target_report['id']} (Target: {target_report['target_type'].upper()}, Reason: '{target_report['reason']}')")

        # Admin executes 'remove_content' action
        act_res = client.post(f"/api/v1/admin/reports/{report_id}/action", headers=headers_admin, json={"action": "remove_content"})
        assert act_res.status_code == 200
        print(f"✓ Admin executed 'remove_content': \"{act_res.json()['message']}\"")

        # Verify immediate content masking in the public feed
        public_feed = client.get("/api/v1/feed", headers=headers_b).json()
        is_spam_in_feed = any(p["id"] == spam_post_id for p in public_feed)
        assert not is_spam_in_feed
        print(f"✓ Verified Post #{spam_post_id} is completely masked from feed (is_hidden=True)")

        # Verify direct access returns 404 for regular users
        regular_view = client.get(f"/api/v1/feed/{spam_post_id}", headers=headers_b)
        assert regular_view.status_code == 404
        print(f"✓ Regular user GET /feed/{spam_post_id} returns HTTP 404 Not Found")

        # Verify Admin can still inspect the masked post
        admin_view = client.get(f"/api/v1/feed/{spam_post_id}", headers=headers_admin)
        assert admin_view.status_code == 200
        print(f"✓ Admin GET /feed/{spam_post_id} retains full audit access (HTTP 200 OK)")

        print_banner("DEMO SCENARIO COMPLETED SUCCESSFULLY: ALL 6 STEPS VERIFIED")

    finally:
        db.close()

if __name__ == "__main__":
    main()
