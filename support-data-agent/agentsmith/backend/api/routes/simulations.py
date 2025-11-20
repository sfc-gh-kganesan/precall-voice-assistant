"""API routes for simulation management."""

import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db, SessionLocal
from backend.api.schemas import (
    SimulationCreate,
    SimulationResponse,
    SimulationResultsResponse,
)
from backend.models.models import (
    Simulation,
    Project,
    SimulationStatus,
    Conversation,
    ConversationMetric,
)
from backend.services.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)
router = APIRouter()


async def run_simulation_in_background(simulation_id: int):
    """Run a simulation in a separate async task."""
    db = SessionLocal()
    try:
        runner = SimulationRunner(db)
        await runner.run_simulation(simulation_id)
    except Exception as e:
        logger.error(f"Error in background simulation task: {e}", exc_info=True)
    finally:
        db.close()


@router.post("/", response_model=SimulationResponse, status_code=202)
async def create_simulation(
    simulation: SimulationCreate,
    db: Session = Depends(get_db),
):
    """Create and start a new simulation (conversation analysis)."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == simulation.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Set default date range if not provided (last 7 days)
    from datetime import timedelta

    date_to = simulation.date_to or datetime.utcnow()
    date_from = simulation.date_from or (date_to - timedelta(days=7))

    # Create simulation record
    db_simulation = Simulation(
        project_id=simulation.project_id,
        num_simulations=simulation.num_simulations,
        concurrency=simulation.concurrency,
        max_turns=simulation.max_turns,
        timeout_seconds=simulation.timeout_seconds,
        conversation_timeout_seconds=simulation.conversation_timeout_seconds,
        stop_conditions=simulation.stop_conditions,
        metrics_config=simulation.metrics_config,
        custom_scenarios=simulation.custom_scenarios,
        # Analysis filters (AgentSmith)
        date_from=date_from,
        date_to=date_to,
        conversation_ids=simulation.conversation_ids,
        triggered_by=simulation.triggered_by,
        include_errors_only=simulation.include_errors_only,
        status=SimulationStatus.PENDING,
    )
    db.add(db_simulation)
    db.commit()
    db.refresh(db_simulation)

    # Start simulation in background using asyncio.create_task
    asyncio.create_task(run_simulation_in_background(db_simulation.id))

    return db_simulation


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(simulation_id: int, db: Session = Depends(get_db)):
    """Get simulation status."""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation


@router.get("/{simulation_id}/results", response_model=SimulationResultsResponse)
async def get_simulation_results(simulation_id: int, db: Session = Depends(get_db)):
    """Get simulation results."""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status != SimulationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Simulation not completed yet")

    # Get all conversations for this simulation
    conversations = (
        db.query(Conversation).filter(Conversation.simulation_id == simulation_id).all()
    )

    # Calculate aggregate metrics
    successful = sum(1 for c in conversations if c.success)
    failed = len(conversations) - successful

    aggregate_metrics = {}
    if conversations:
        # Calculate averages
        aggregate_metrics["avg_turns"] = sum(c.num_turns for c in conversations) / len(
            conversations
        )
        aggregate_metrics["avg_duration_ms"] = sum(
            c.total_duration_ms for c in conversations
        ) / len(conversations)
        aggregate_metrics["success_rate"] = successful / len(conversations)

        # Aggregate conversation metrics
        all_metrics = (
            db.query(ConversationMetric)
            .join(Conversation)
            .filter(Conversation.simulation_id == simulation_id)
            .all()
        )

        # Group by metric name and calculate averages
        metric_groups = {}
        for metric in all_metrics:
            if metric.metric_name not in metric_groups:
                metric_groups[metric.metric_name] = []
            metric_groups[metric.metric_name].append(metric.metric_value)

        for metric_name, values in metric_groups.items():
            if values:
                aggregate_metrics[f"avg_{metric_name}"] = sum(values) / len(values)

    return SimulationResultsResponse(
        id=simulation.id,
        project_id=simulation.project_id,
        num_simulations=simulation.num_simulations,
        status=simulation.status.value,
        successful=successful,
        failed=failed,
        aggregate_metrics=aggregate_metrics,
    )


@router.delete("/{simulation_id}")
async def delete_simulation(simulation_id: int, db: Session = Depends(get_db)):
    """Delete a simulation and all related data."""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Can't delete a running simulation - must stop it first
    if simulation.status == SimulationStatus.RUNNING:
        raise HTTPException(
            status_code=400, detail="Cannot delete running simulation. Stop it first."
        )

    # Delete related conversations (cascade should handle metrics/messages)
    db.query(Conversation).filter(Conversation.simulation_id == simulation_id).delete()

    # Delete simulation
    db.delete(simulation)
    db.commit()

    return {"message": "Simulation deleted successfully"}


@router.post("/{simulation_id}/stop")
async def stop_simulation(simulation_id: int, db: Session = Depends(get_db)):
    """Stop a running simulation and mark it as failed."""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Can only stop running simulations
    if simulation.status != SimulationStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot stop simulation with status: {simulation.status.value}",
        )

    # Mark as failed with cancellation message
    simulation.status = SimulationStatus.FAILED
    simulation.error_message = "Manually stopped by user"
    simulation.completed_at = datetime.utcnow()
    db.commit()

    # Note: We can't actually kill the background asyncio task from here
    # The task will continue but when it tries to update the simulation,
    # it will see status is FAILED and should handle gracefully

    return {"message": "Simulation stopped successfully"}
