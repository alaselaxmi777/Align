import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends, status
from app.main import app
from app.api.deps import require_role, get_current_admin
from app.models.user import User

client = TestClient(app)

# Helper test route to verify require_role
sample_rbac_app = FastAPI()

@sample_rbac_app.get("/test-admin-only")
def admin_only_endpoint(admin: User = Depends(require_role("admin"))):
    return {"message": "welcome admin", "role": admin.role}

@sample_rbac_app.get("/test-mod-or-admin")
def mod_or_admin_endpoint(user: User = Depends(require_role("moderator", "admin"))):
    return {"message": "welcome mod/admin", "role": user.role}


def test_health_details_endpoint():
    resp = client.get("/health/details")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"]["engine"] == "postgresql"
    assert data["database"]["pgvector_extension"] == "active"
    assert "entity_counts" in data["database"]
    assert data["embeddings"]["dimension"] == 384
    assert data["privacy"]["grid_snapping_precision_deg"] == 0.01


def test_system_metrics_endpoint():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "align_embedding_cache_hits_total" in data
    assert "align_embedding_cache_size" in data
    assert "align_users_total" in data
    assert "align_communities_total" in data
    assert "align_events_total" in data


def test_user_model_role_and_has_role():
    user = User(
        name="Test User",
        email="test_rbac@example.com",
        role="user",
        is_admin=False,
    )
    assert user.role == "user"
    assert user.has_role("user") is True
    assert user.has_role("admin") is False
    assert user.has_role("moderator") is False

    mod = User(
        name="Test Moderator",
        email="test_mod@example.com",
        role="moderator",
        is_admin=False,
    )
    assert mod.role == "moderator"
    assert mod.has_role("moderator") is True
    assert mod.has_role("admin") is False
    assert mod.has_role("moderator", "admin") is True

    admin = User(
        name="Test Administrator",
        email="test_admin@example.com",
        role="admin",
        is_admin=True,
    )
    assert admin.role == "admin"
    assert admin.has_role("admin") is True
    assert admin.has_role("moderator") is True  # Admin inherits all roles
    assert admin.has_role("user") is True


def test_require_role_dependency_logic():
    # Test role checker directly
    admin_user = User(name="Admin", email="admin@example.com", role="admin", is_admin=True)
    regular_user = User(name="User", email="user@example.com", role="user", is_admin=False)
    mod_user = User(name="Mod", email="mod@example.com", role="moderator", is_admin=False)

    checker_admin = require_role("admin")
    checker_mod = require_role("moderator", "admin")

    # Admin passes both
    assert checker_admin(user=admin_user) == admin_user
    assert checker_mod(user=admin_user) == admin_user

    # Mod passes mod checker, fails admin checker
    assert checker_mod(user=mod_user) == mod_user
    with pytest.raises(Exception) as excinfo:
        checker_admin(user=mod_user)
    assert "403" in str(excinfo.value)

    # Regular user fails both
    with pytest.raises(Exception) as excinfo:
        checker_admin(user=regular_user)
    assert "403" in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        checker_mod(user=regular_user)
    assert "403" in str(excinfo.value)
