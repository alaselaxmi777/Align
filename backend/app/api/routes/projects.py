from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMilestone, ProjectApplication, ProjectDiscussion
from app.models.notification import Notification
from app.services.embeddings import generate_embedding
from app.services.gamification_service import award_xp, check_and_unlock_badge, get_or_create_gamification
from app.services.github_service import fetch_github_good_first_issues

router = APIRouter(prefix="/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    tagline: str = Field(default="", max_length=255)
    description: str = Field(min_length=10, max_length=5000)
    category: str = "AI & Machine Learning"
    stage: str = "idea"
    required_roles: str = ""  # "Frontend Developer, ML Engineer"
    skills_needed: str = ""   # "Python, PyTorch, React"
    github_repo_url: str | None = None
    live_demo_url: str | None = None

    @field_validator("github_repo_url", "live_demo_url")
    @classmethod
    def validate_external_urls(cls, v: str | None) -> str | None:
        if not v:
            return v
        trimmed = v.strip()
        if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise ValueError("URL must use http:// or https:// scheme")
        return trimmed

class ApplicationCreate(BaseModel):
    desired_role: str = Field(min_length=2, max_length=100)
    pitch_message: str = Field(min_length=5, max_length=2000)

class ProjectMilestoneCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    step_order: int = 1

class ProjectMilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    is_completed: bool | None = None
    step_order: int | None = None

class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    tagline: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    category: str | None = None
    stage: str | None = None  # idea, prototyping, mvp, active
    status: str | None = None  # recruiting, in_progress, completed
    required_roles: str | None = None
    skills_needed: str | None = None
    github_repo_url: str | None = None
    live_demo_url: str | None = None

    @field_validator("github_repo_url", "live_demo_url")
    @classmethod
    def validate_external_urls(cls, v: str | None) -> str | None:
        if not v:
            return v
        trimmed = v.strip()
        if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise ValueError("URL must use http:// or https:// scheme")
        return trimmed

class ProjectDiscussionCreate(BaseModel):
    title: str = Field(default="", max_length=160)
    content: str = Field(min_length=2, max_length=3000)

def serialize_project(p: Project, user: User | None) -> dict:
    is_owner = (user and user.id == p.created_by_id)
    is_mem = False
    if user:
        is_mem = any(m.user_id == user.id for m in p.members)

    return {
        "id": p.id,
        "title": p.title,
        "tagline": p.tagline,
        "description": p.description,
        "category": p.category,
        "stage": p.stage,
        "status": p.status,
        "required_roles": [r.strip() for r in p.required_roles.split(",") if r.strip()],
        "skills_needed": [s.strip() for s in p.skills_needed.split(",") if s.strip()],
        "github_repo_url": p.github_repo_url,
        "live_demo_url": p.live_demo_url,
        "is_test": getattr(p, "is_test", False),
        "creator_id": p.created_by_id,
        "creator_name": p.creator.name if p.creator else "ALIGN Creator",
        "creator_avatar": p.creator.profile.avatar_url if (p.creator and p.creator.profile) else None,
        "team_size": len(p.members),
        "is_owner": is_owner,
        "is_member": is_mem,
        "created_at": p.created_at,
        "members": [
            {
                "id": m.user.id,
                "name": m.user.name,
                "avatar_url": m.user.profile.avatar_url if m.user.profile else None,
                "role": m.role,
                "joined_at": m.joined_at,
            }
            for m in p.members
        ],
        "milestones": [
            {
                "id": ms.id,
                "step_order": ms.step_order,
                "title": ms.title,
                "description": ms.description,
                "is_completed": ms.is_completed,
                "completed_at": ms.completed_at,
            }
            for ms in p.milestones
        ],
        "discussions_count": len(p.discussions),
    }

@router.get("")
def list_projects(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=80),
    stage: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=24, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    stmt = select(Project).where(Project.is_test == False).order_by(Project.created_at.desc())
    if category:
        stmt = stmt.where(Project.category.ilike(f"%{category.strip()}%"))
    if stage:
        stmt = stmt.where(Project.stage == stage.strip())
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Project.title.ilike(term),
                Project.tagline.ilike(term),
                Project.description.ilike(term),
                Project.required_roles.ilike(term),
                Project.skills_needed.ilike(term),
            )
        )
    stmt = stmt.limit(limit)
    projects = list(db.scalars(stmt))
    return [serialize_project(p, user) for p in projects]

@router.get("/github/good-first-issues")
def get_github_good_first_issues(
    query: str = Query(default="python", max_length=80),
    limit: int = Query(default=8, ge=1, le=20),
):
    """Retrieves real beginner-friendly open-source issues from active GitHub repositories."""
    return fetch_github_good_first_issues(query=query, limit=limit)

@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ctx = f"{payload.title} {payload.tagline} {payload.description} {payload.category} {payload.skills_needed}"
    emb = generate_embedding(ctx)

    project = Project(
        title=payload.title.strip(),
        tagline=payload.tagline.strip(),
        description=payload.description.strip(),
        category=payload.category,
        stage=payload.stage,
        status="recruiting",
        required_roles=payload.required_roles,
        skills_needed=payload.skills_needed,
        github_repo_url=payload.github_repo_url,
        live_demo_url=payload.live_demo_url,
        is_test=getattr(user, "is_test", False),
        created_by_id=user.id,
        embedding=emb,
    )
    db.add(project)
    db.flush()

    # Creator is Lead Collaborator
    member = ProjectMember(project_id=project.id, user_id=user.id, role="Lead Architect")
    db.add(member)

    # Award XP & Badge with dedup key
    award_xp(db, user.id, "project_published", 100, f"Published Collaboration Project: {project.title[:30]}", dedup_key=f"project_create:{project.id}")
    game = get_or_create_gamification(db, user.id)
    check_and_unlock_badge(db, game, "TEAM_PLAYER")

    db.commit()
    db.refresh(project)
    return serialize_project(project, user)

@router.patch("/{project_id}")
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if p.created_by_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only project leads can update project settings.")

    content_changed = False
    if payload.title is not None:
        p.title = payload.title.strip()
        content_changed = True
    if payload.tagline is not None:
        p.tagline = payload.tagline.strip()
        content_changed = True
    if payload.description is not None:
        p.description = payload.description.strip()
        content_changed = True
    if payload.category is not None:
        p.category = payload.category.strip()
        content_changed = True
    if payload.stage is not None:
        p.stage = payload.stage.strip()
    if payload.status is not None:
        p.status = payload.status.strip()
    if payload.required_roles is not None:
        p.required_roles = payload.required_roles.strip()
    if payload.skills_needed is not None:
        p.skills_needed = payload.skills_needed.strip()
        content_changed = True
    if payload.github_repo_url is not None:
        p.github_repo_url = payload.github_repo_url.strip() if payload.github_repo_url else None
    if payload.live_demo_url is not None:
        p.live_demo_url = payload.live_demo_url.strip() if payload.live_demo_url else None

    if content_changed:
        ctx = f"{p.title} {p.tagline} {p.description} {p.category} {p.skills_needed}"
        p.embedding = generate_embedding(ctx)

    db.commit()
    db.refresh(p)
    return serialize_project(p, user)

@router.get("/{project_id}")
def get_project_details(
    project_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return serialize_project(p, user)

@router.post("/{project_id}/apply", status_code=status.HTTP_201_CREATED)
def apply_to_project(
    project_id: int,
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if any(m.user_id == user.id for m in p.members):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are already a team member of this project.")

    app_record = ProjectApplication(
        project_id=p.id,
        applicant_id=user.id,
        desired_role=payload.desired_role.strip(),
        pitch_message=payload.pitch_message.strip(),
        status="pending",
    )
    db.add(app_record)
    award_xp(db, user.id, "project_application", 20, f"Applied to Project: {p.title[:30]}", dedup_key=f"project_apply:{p.id}:{user.id}")

    # Notify project lead
    if p.created_by_id and p.created_by_id != user.id:
        db.add(
            Notification(
                user_id=p.created_by_id,
                title="New Contributor Application",
                message=f"{user.name} applied to join '{p.title}' as {payload.desired_role.strip()}.",
                link=f"/projects/{p.id}",
            )
        )

    db.commit()
    return {"status": "ok", "message": "Application submitted to project lead successfully."}

@router.get("/{project_id}/applications")
def list_project_applications(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if p.created_by_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only project leads can review applications.")

    return [
        {
            "id": a.id,
            "applicant_id": a.applicant_id,
            "applicant_name": a.applicant.name if a.applicant else "ALIGN Member",
            "applicant_avatar": a.applicant.profile.avatar_url if (a.applicant and a.applicant.profile) else None,
            "applicant_skills": a.applicant.profile.skills if (a.applicant and a.applicant.profile) else "",
            "desired_role": a.desired_role,
            "pitch_message": a.pitch_message,
            "status": a.status,
            "created_at": a.created_at,
        }
        for a in p.applications
    ]

@router.post("/{project_id}/applications/{app_id}/review")
def review_project_application(
    project_id: int,
    app_id: int,
    action: str = Query(default="accepted"),  # accepted, rejected
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.get(Project, project_id)
    if not p or (p.created_by_id != user.id and not user.is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only project leads can review applications.")

    app_rec = db.get(ProjectApplication, app_id)
    if not app_rec or app_rec.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    app_rec.status = action
    if action == "accepted":
        # Add to project_members
        existing = db.scalar(
            select(ProjectMember).where(
                (ProjectMember.project_id == project_id) & (ProjectMember.user_id == app_rec.applicant_id)
            )
        )
        if not existing:
            db.add(ProjectMember(project_id=project_id, user_id=app_rec.applicant_id, role=app_rec.desired_role))
            award_xp(db, app_rec.applicant_id, "joined_team", 50, f"Joined project team for {p.title[:30]}", dedup_key=f"project_join:{project_id}:{app_rec.applicant_id}")
            game = get_or_create_gamification(db, app_rec.applicant_id)
            check_and_unlock_badge(db, game, "TEAM_PLAYER")

        # Notify applicant
        db.add(
            Notification(
                user_id=app_rec.applicant_id,
                title="Project Application Accepted! 🎉",
                message=f"You have been accepted to join '{p.title}' as {app_rec.desired_role}!",
                link=f"/projects/{p.id}",
            )
        )
    elif action == "rejected":
        # Notify applicant
        db.add(
            Notification(
                user_id=app_rec.applicant_id,
                title="Project Application Update",
                message=f"Your application to join '{p.title}' was not accepted at this time.",
                link=f"/projects/{p.id}",
            )
        )

    db.commit()
    return {"status": "ok", "message": f"Application marked as {action}."}

@router.post("/{project_id}/applications/{app_id}/accept")
def accept_project_application(
    project_id: int,
    app_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return review_project_application(project_id, app_id, action="accepted", db=db, user=user)

@router.post("/{project_id}/applications/{app_id}/reject")
def reject_project_application(
    project_id: int,
    app_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return review_project_application(project_id, app_id, action="rejected", db=db, user=user)

@router.post("/{project_id}/milestones", status_code=status.HTTP_201_CREATED)
def add_project_milestone(
    project_id: int,
    payload: ProjectMilestoneCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.get(Project, project_id)
    if not p or (p.created_by_id != user.id and not user.is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only project leads can add milestones.")

    ms = ProjectMilestone(
        project_id=project_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        step_order=payload.step_order,
    )
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return {"id": ms.id, "title": ms.title, "is_completed": ms.is_completed}

@router.patch("/{project_id}/milestones/{milestone_id}")
def update_project_milestone(
    project_id: int,
    milestone_id: int,
    payload: ProjectMilestoneUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    is_team_member = (p.created_by_id == user.id) or any(m.user_id == user.id for m in p.members)
    if not is_team_member and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only project team members can update milestones.")

    ms = db.get(ProjectMilestone, milestone_id)
    if not ms or ms.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    if payload.title is not None:
        ms.title = payload.title.strip()
    if payload.description is not None:
        ms.description = payload.description.strip()
    if payload.step_order is not None:
        ms.step_order = payload.step_order
    if payload.is_completed is not None:
        was_completed = ms.is_completed
        ms.is_completed = payload.is_completed
        if payload.is_completed and not was_completed:
            ms.completed_at = datetime.now(timezone.utc)
            # Award verified XP with dedup key
            award_xp(db, user.id, "milestone_completed", 40, f"Completed milestone: {ms.title[:30]}", dedup_key=f"milestone_completed:{ms.id}")
            # Notify owner if completed by team member
            if p.created_by_id and p.created_by_id != user.id:
                db.add(
                    Notification(
                        user_id=p.created_by_id,
                        title="Project Milestone Completed! 🎯",
                        message=f"{user.name} completed milestone '{ms.title}' for {p.title}.",
                        link=f"/projects/{p.id}",
                    )
                )

    db.commit()
    db.refresh(ms)
    return {
        "id": ms.id,
        "title": ms.title,
        "description": ms.description,
        "is_completed": ms.is_completed,
        "completed_at": ms.completed_at,
        "step_order": ms.step_order,
    }

@router.get("/{project_id}/discussions")
def list_project_discussions(
    project_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return [
        {
            "id": d.id,
            "project_id": d.project_id,
            "user_id": d.user_id,
            "author_name": d.author.name if d.author else "ALIGN Member",
            "author_avatar": d.author.profile.avatar_url if (d.author and d.author.profile) else None,
            "title": d.title,
            "content": d.content,
            "created_at": d.created_at,
        }
        for d in p.discussions
    ]

@router.post("/{project_id}/discussions", status_code=status.HTTP_201_CREATED)
def create_project_discussion(
    project_id: int,
    payload: ProjectDiscussionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    disc = ProjectDiscussion(
        project_id=project_id,
        user_id=user.id,
        title=payload.title.strip(),
        content=payload.content.strip(),
    )
    db.add(disc)
    db.flush()

    # Award XP for active contribution
    award_xp(db, user.id, "project_discussion", 15, f"Posted update for project: {p.title[:25]}", dedup_key=f"project_discussion:{disc.id}")

    # Notify creator if discussion started by someone else
    if p.created_by_id and p.created_by_id != user.id:
        db.add(
            Notification(
                user_id=p.created_by_id,
                title="New Project Discussion / Update",
                message=f"{user.name} posted an update on '{p.title}'.",
                link=f"/projects/{p.id}",
            )
        )

    db.commit()
    db.refresh(disc)

    return {
        "id": disc.id,
        "project_id": disc.project_id,
        "user_id": disc.user_id,
        "author_name": user.name,
        "author_avatar": user.profile.avatar_url if user.profile else None,
        "title": disc.title,
        "content": disc.content,
        "created_at": disc.created_at,
    }

@router.delete("/{project_id}/members/{member_user_id}")
def remove_project_member(
    project_id: int,
    member_user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    is_self = (user.id == member_user_id)
    is_owner = (p.created_by_id == user.id)
    if not is_self and not is_owner and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to remove this member.")

    if member_user_id == p.created_by_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project lead cannot be removed from members.")

    member = db.scalar(
        select(ProjectMember).where(
            (ProjectMember.project_id == project_id) & (ProjectMember.user_id == member_user_id)
        )
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in project.")

    db.delete(member)
    db.commit()
    return {"status": "ok", "message": "Member removed from project successfully."}
