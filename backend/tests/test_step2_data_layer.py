import pytest
from sqlalchemy import select
from app.models.user import User, Profile
from app.models.community import Community
from app.models.project import Project
from app.scripts.cleanup_test_data import is_test_string, run_cleanup

def test_models_have_is_test_field(db):
    """Verify is_test field exists and defaults to False when persisted."""
    user = User(name="Regular Member", email="regular_step2@example.com")
    comm = Community(name="Regular Guild", description="A guild for builders")
    proj = Project(title="Open Source Platform", description="Building collaborative systems")

    assert hasattr(user, "is_test")
    assert hasattr(comm, "is_test")
    assert hasattr(proj, "is_test")

    db.add_all([user, comm, proj])
    db.commit()
    db.refresh(user)
    db.refresh(comm)
    db.refresh(proj)

    assert user.is_test is False
    assert comm.is_test is False
    assert proj.is_test is False

def test_is_test_string_detection():
    """Test string helper identifies synthetic test and timestamped audit patterns."""
    assert is_test_string("Audit User 1794580185") is True
    assert is_test_string("test_user_99@align.local") is True
    assert is_test_string("Autonomous Agent Harness 1794580186") is True
    assert is_test_string("AI Recommendation Tester") is True
    assert is_test_string("rec_test_ebcc95@align.local") is True

    # Real names should not be marked
    assert is_test_string("Aria Sharma") is False
    assert is_test_string("Laxmi Alase") is False
    assert is_test_string("AI Explorers Circle") is False
    assert is_test_string("Weekend Trail & Outdoor Club") is False

def test_cleanup_script_dry_run_non_destructive(db):
    """Ensure dry-run audit does not mutate the database."""
    real_user = User(name="Genuine Builder", email="genuine_step2@example.com", is_test=False)
    test_user = User(name="Audit Tester 99999999", email="audit99999999@test.local", is_test=False)
    db.add_all([real_user, test_user])
    db.commit()

    # Run dry run
    res = run_cleanup(dry_run=True, db=db)
    assert res["dry_run"] is True
    assert res["users_flagged"] >= 1

    # Verify test_user is_test was NOT modified in dry run
    db.refresh(test_user)
    assert test_user.is_test is False
