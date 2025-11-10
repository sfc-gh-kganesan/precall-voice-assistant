"""API routes for project management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.api.schemas import (
    ProjectCreate,
    ProjectResponse,
    SimulationResponse,
    PersonaTemplateCreate,
    PersonaTemplateResponse,
)
from backend.models.models import Project, AuthType, Simulation, PersonaTemplate

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    db_project = Project(
        name=project.name,
        description=project.description,
        business_context=project.business_context,
        agent_endpoint=project.agent_endpoint,
        auth_type=AuthType(project.auth_type),
        auth_credentials=project.auth_credentials,
        custom_headers=project.custom_headers,
        conversation_examples=project.conversation_examples,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """List all projects."""
    projects = db.query(Project).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a specific project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/simulations", response_model=List[SimulationResponse])
async def get_project_simulations(project_id: int, db: Session = Depends(get_db)):
    """Get all simulations for a specific project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    simulations = (
        db.query(Simulation)
        .filter(Simulation.project_id == project_id)
        .order_by(Simulation.created_at.desc())
        .all()
    )
    return simulations


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}


# Persona Template endpoints
@router.get("/{project_id}/personas", response_model=List[PersonaTemplateResponse])
async def list_project_personas(project_id: int, db: Session = Depends(get_db)):
    """List all persona templates for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    personas = (
        db.query(PersonaTemplate)
        .filter(PersonaTemplate.project_id == project_id)
        .order_by(PersonaTemplate.created_at.desc())
        .all()
    )
    return personas


@router.post(
    "/{project_id}/personas", response_model=PersonaTemplateResponse, status_code=201
)
async def create_persona_template(
    project_id: int, persona: PersonaTemplateCreate, db: Session = Depends(get_db)
):
    """Create a new persona template for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_persona = PersonaTemplate(
        project_id=project_id,
        name=persona.name,
        goal=persona.goal,
        tone=persona.tone,
        personality_traits=persona.personality_traits,
        technical_level=persona.technical_level,
        edge_case=persona.edge_case,
        default_query=persona.default_query,
        expected_outcome=persona.expected_outcome,
        complexity=persona.complexity,
        category=persona.category,
        knowledge_base=persona.knowledge_base,
    )
    db.add(db_persona)
    db.commit()
    db.refresh(db_persona)
    return db_persona


@router.delete("/{project_id}/personas/{persona_id}")
async def delete_persona_template(
    project_id: int, persona_id: int, db: Session = Depends(get_db)
):
    """Delete a persona template."""
    persona = (
        db.query(PersonaTemplate)
        .filter(
            PersonaTemplate.id == persona_id, PersonaTemplate.project_id == project_id
        )
        .first()
    )
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    db.delete(persona)
    db.commit()
    return {"message": "Persona deleted successfully"}
