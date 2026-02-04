"""
IPC (Inter-Process Communication) utilities for the P67 SDK.

Handles stdin/stdout JSON messaging with the parent process.
"""

import sys
import json
import uuid
import threading
from datetime import datetime
from typing import Any, Callable, Dict, Optional

# Global registry for pending interrupts
_pending_interrupts: Dict[str, threading.Event] = {}
_interrupt_responses: Dict[str, Any] = {}
_interrupt_lock = threading.Lock()


def send_message(msg: Dict[str, Any]) -> None:
    """Send a JSON message to the parent process via stdout."""
    sys.stdout.write(json.dumps(msg) + '\n')
    sys.stdout.flush()


def send_interrupt(
    payload: Any,
    node_id: Optional[str] = None,
) -> str:
    """
    Send an interrupt message and return the interrupt ID.
    
    Args:
        payload: The data to send with the interrupt
        node_id: Optional node identifier
        
    Returns:
        The interrupt ID (UUID)
    """
    interrupt_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    send_message({
        "type": "Interrupt",
        "interruptId": interrupt_id,
        "payload": payload,
        "nodeId": node_id,
        "timestamp": timestamp,
    })
    
    return interrupt_id


def wait_for_resume(interrupt_id: str, timeout: Optional[float] = None) -> Any:
    """
    Wait for a resume message for the given interrupt ID.
    
    Args:
        interrupt_id: The interrupt ID to wait for
        timeout: Optional timeout in seconds
        
    Returns:
        The response data from the resume message
        
    Raises:
        TimeoutError: If timeout is reached
    """
    event = threading.Event()
    
    with _interrupt_lock:
        _pending_interrupts[interrupt_id] = event
    
    try:
        if not event.wait(timeout=timeout):
            raise TimeoutError(f"Interrupt {interrupt_id} timed out")
        
        with _interrupt_lock:
            response = _interrupt_responses.pop(interrupt_id, None)
        return response
    finally:
        with _interrupt_lock:
            _pending_interrupts.pop(interrupt_id, None)


def _handle_resume_interrupt(message: Dict[str, Any]) -> None:
    """
    Handle a ResumeInterrupt message from the parent process.
    
    This is called by the host when it receives a ResumeInterrupt message.
    
    Args:
        message: The ResumeInterrupt message
    """
    interrupt_id = message.get("interruptId")
    response = message.get("response")
    
    if not interrupt_id:
        return
    
    with _interrupt_lock:
        event = _pending_interrupts.get(interrupt_id)
        if event:
            _interrupt_responses[interrupt_id] = response
            event.set()
