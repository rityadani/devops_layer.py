"""Runtime State Adapter - Converts real runtime events to RL Decision Layer format"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class HealthBand(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    FAILING = "failing"

class LatencyBucket(Enum):
    LOW = "low"      # < 200ms
    MEDIUM = "medium" # 200-500ms
    HIGH = "high"    # > 500ms

class RuntimeStateAdapter:
    """Converts runtime events/metrics to deterministic RL state format"""
    
    def __init__(self):
        self.latency_thresholds = {
            "low": 200,
            "medium": 500
        }
        self.error_thresholds = {
            "healthy": 0,
            "degraded": 5,
            "failing": 15
        }
    
    def convert_to_rl_state(self, runtime_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert runtime event to RL state format
        Returns None if conversion fails (missing critical data)
        """
        try:
            # Extract required fields with safe defaults
            app_id = runtime_payload.get("app", "").strip()
            env = runtime_payload.get("env", "").strip()
            
            if not app_id or not env:
                logger.warning("Missing app_id or env in runtime payload")
                return None
            
            # Convert health state
            health_band = self._determine_health_band(runtime_payload)
            if not health_band:
                logger.warning("Could not determine health band from runtime data")
                return None
            
            # Convert latency
            latency_bucket = self._determine_latency_bucket(runtime_payload)
            
            # Convert failure count
            recent_failures = self._extract_failure_count(runtime_payload)
            
            rl_state = {
                "app_id": app_id,
                "env": env,
                "health_band": health_band.value,
                "latency_bucket": latency_bucket.value if latency_bucket else "unknown",
                "recent_failures": recent_failures
            }
            
            logger.info(f"Converted runtime state for {app_id}:{env} -> {health_band.value}")
            return rl_state
            
        except Exception as e:
            logger.error(f"Failed to convert runtime state: {e}")
            return None
    
    def _determine_health_band(self, payload: Dict[str, Any]) -> Optional[HealthBand]:
        """Determine health band from runtime state"""
        # Direct state mapping
        state = payload.get("state", "").lower()
        if state in ["healthy", "degraded", "failing"]:
            return HealthBand(state)
        
        # Fallback: derive from error count
        errors = payload.get("errors_last_min", 0)
        if errors <= self.error_thresholds["healthy"]:
            return HealthBand.HEALTHY
        elif errors <= self.error_thresholds["degraded"]:
            return HealthBand.DEGRADED
        else:
            return HealthBand.FAILING
    
    def _determine_latency_bucket(self, payload: Dict[str, Any]) -> Optional[LatencyBucket]:
        """Determine latency bucket from metrics"""
        latency_ms = payload.get("latency_ms")
        if latency_ms is None:
            return None
        
        try:
            latency = float(latency_ms)
            if latency < self.latency_thresholds["low"]:
                return LatencyBucket.LOW
            elif latency < self.latency_thresholds["medium"]:
                return LatencyBucket.MEDIUM
            else:
                return LatencyBucket.HIGH
        except (ValueError, TypeError):
            logger.warning(f"Invalid latency value: {latency_ms}")
            return None
    
    def _extract_failure_count(self, payload: Dict[str, Any]) -> int:
        """Extract recent failure count with safe default"""
        errors = payload.get("errors_last_min", 0)
        try:
            return max(0, int(errors))
        except (ValueError, TypeError):
            logger.warning(f"Invalid error count: {errors}")
            return 0
    
    def log_conversion_mapping(self, before: Dict[str, Any], after: Optional[Dict[str, Any]]) -> None:
        """Log before/after conversion for debugging"""
        logger.info(f"Runtime conversion mapping:")
        logger.info(f"  Before: {before}")
        logger.info(f"  After: {after}")