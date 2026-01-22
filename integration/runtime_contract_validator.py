"""Runtime Contract Validator - Ensures RL never acts on invalid orchestration states"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationResult(Enum):
    VALID = "valid"
    INVALID_APP = "invalid_app"
    INVALID_ENV = "invalid_env"
    UNKNOWN_STATE = "unknown_state"
    MISSING_LIFECYCLE = "missing_lifecycle"
    INCOMPLETE_DATA = "incomplete_data"

class RuntimeContractValidator:
    """Validates runtime state before RL decision making"""
    
    REQUIRED_FIELDS = ["app", "env", "state"]
    VALID_STATES = ["healthy", "degraded", "failing"]
    VALID_ENVS = ["dev", "stage", "prod"]
    
    def __init__(self):
        self.validation_failures = []
    
    def validate_state(self, state_payload: Dict[str, Any]) -> tuple[bool, ValidationResult, str]:
        """
        Validate runtime state payload before RL processing
        Returns: (is_valid, result_code, error_message)
        """
        if not isinstance(state_payload, dict):
            return False, ValidationResult.INCOMPLETE_DATA, "Payload must be dict"
        
        # Check required fields
        missing_fields = [f for f in self.REQUIRED_FIELDS if f not in state_payload]
        if missing_fields:
            error = f"Missing required fields: {missing_fields}"
            logger.warning(f"Contract validation failed: {error}")
            return False, ValidationResult.INCOMPLETE_DATA, error
        
        # Validate app exists and is non-empty
        app = state_payload.get("app", "").strip()
        if not app:
            logger.warning("Contract validation failed: Empty app name")
            return False, ValidationResult.INVALID_APP, "App name cannot be empty"
        
        # Validate environment
        env = state_payload.get("env", "").strip()
        if env not in self.VALID_ENVS:
            error = f"Invalid env '{env}'. Must be one of: {self.VALID_ENVS}"
            logger.warning(f"Contract validation failed: {error}")
            return False, ValidationResult.INVALID_ENV, error
        
        # Validate state
        state = state_payload.get("state", "").strip()
        if state not in self.VALID_STATES:
            error = f"Invalid state '{state}'. Must be one of: {self.VALID_STATES}"
            logger.warning(f"Contract validation failed: {error}")
            return False, ValidationResult.UNKNOWN_STATE, error
        
        logger.info(f"Contract validation passed for {app}:{env}")
        return True, ValidationResult.VALID, "Valid state"
    
    def get_noop_response(self, reason: str) -> Dict[str, Any]:
        """Return safe NOOP response when validation fails"""
        logger.info(f"Returning NOOP due to: {reason}")
        return {
            "action": "NOOP",
            "reason": reason,
            "safe_fallback": True,
            "timestamp": self._get_timestamp()
        }
    
    def _get_timestamp(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()