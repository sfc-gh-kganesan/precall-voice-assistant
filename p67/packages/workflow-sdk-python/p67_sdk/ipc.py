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
    notify: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Send an interrupt message and return the interrupt ID.
    
    Args:
        payload: The data to send with the interrupt
        node_id: Optional node identifier
        notify: Optional notification config (e.g. Slack)
        
    Returns:
        The interrupt ID (UUID)
    """
    interrupt_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    msg: Dict[str, Any] = {
        "type": "Interrupt",
        "interruptId": interrupt_id,
        "payload": payload,
        "nodeId": node_id,
        "timestamp": timestamp,
    }
    if notify is not None:
        msg["notify"] = notify

    send_message(msg)
    
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


# Global registry for pending OAuth requests
_pending_oauth: Dict[str, threading.Event] = {}
_oauth_responses: Dict[str, Any] = {}
_oauth_lock = threading.Lock()


def request_oauth_token(oauth_ref: str, timeout: float = 30.0) -> str:
    """
    Request an OAuth access token from the parent process via IPC.

    Sends a RequestOAuthToken message and blocks until the parent
    responds with OAuthTokenResponse containing the access token.
    """
    request_id = str(uuid.uuid4())
    event = threading.Event()

    with _oauth_lock:
        _pending_oauth[request_id] = event

    send_message({
        "type": "RequestOAuthToken",
        "requestId": request_id,
        "oauthRef": oauth_ref,
    })

    try:
        if not event.wait(timeout=timeout):
            raise TimeoutError(f"OAuth token request timed out for: {oauth_ref}")

        with _oauth_lock:
            response = _oauth_responses.pop(request_id, None)

        if response is None:
            raise RuntimeError(f"No OAuth token response received for: {oauth_ref}")

        if "error" in response and response["error"]:
            raise RuntimeError(f'Failed to resolve OAuth token "{oauth_ref}": {response["error"]}')

        access_token = response.get("accessToken")
        if not access_token:
            raise RuntimeError("Invalid OAuthTokenResponse: no token or error")

        return access_token
    finally:
        with _oauth_lock:
            _pending_oauth.pop(request_id, None)
            _oauth_responses.pop(request_id, None)


def _handle_oauth_token_response(message: Dict[str, Any]) -> None:
    """
    Handle an OAuthTokenResponse message from the parent process.
    Called by the host when it receives an OAuthTokenResponse message.
    """
    request_id = message.get("requestId")
    if not request_id:
        return

    with _oauth_lock:
        event = _pending_oauth.get(request_id)
        if event:
            _oauth_responses[request_id] = message
            event.set()
