"""RL Orchestrator Bridge - Safe action flow from Runtime → RL → Orchestration"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from integration.runtime_contract_validator import RuntimeContractValidator, ValidationResult
from integration.runtime_state_adapter import RuntimeStateAdapter
from integration.rl_agent import QLearningAgent

logger = logging.getLogger(__name__)

class ActionType(Enum):
    NOOP = "NOOP"
    SCALE_UP = "SCALE_UP"
    SCALE_DOWN = "SCALE_DOWN"
    RESTART = "RESTART"
    ROLLBACK = "ROLLBACK"

class SafetyLevel(Enum):
    SAFE = "safe"
    RISKY = "risky"
    UNSAFE = "unsafe"

class RLOrchestratorBridge:
    """Safe bridge between RL decisions and orchestration actions"""
    
    def __init__(self):
        self.contract_validator = RuntimeContractValidator()
        self.state_adapter = RuntimeStateAdapter()
        self.rl_agent = QLearningAgent()
        self.blocked_actions = []
        self.safe_downgrades = []
        
        # Safety rules: env -> allowed actions
        self.safety_rules = {
            "prod": [ActionType.NOOP, ActionType.SCALE_UP],  # Very conservative
            "stage": [ActionType.NOOP, ActionType.SCALE_UP, ActionType.SCALE_DOWN],
            "dev": list(ActionType)  # All actions allowed
        }
    
    def process_runtime_state(self, runtime_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: Runtime → RL → Safe Decision
        Returns validated decision intent (never throws)
        """
        try:
            # Step 1: Contract validation
            is_valid, validation_result, error_msg = self.contract_validator.validate_state(runtime_payload)
            
            if not is_valid:
                blocked_action = {
                    "reason": f"Contract validation failed: {error_msg}",
                    "validation_code": validation_result.value,
                    "payload": runtime_payload
                }
                self.blocked_actions.append(blocked_action)
                logger.warning(f"Blocked action due to contract failure: {error_msg}")
                return self.contract_validator.get_noop_response(error_msg)
            
            # Step 2: Convert to RL state format
            rl_state = self.state_adapter.convert_to_rl_state(runtime_payload)
            if not rl_state:
                reason = "Failed to convert runtime state to RL format"
                self.blocked_actions.append({"reason": reason, "payload": runtime_payload})
                logger.warning(f"Blocked action: {reason}")
                return self.contract_validator.get_noop_response(reason)
            
            # Step 3: RL decision (simplified for integration)
            proposed_action = self._get_rl_decision(rl_state)
            
            # Step 4: Safety guard
            safe_action = self._apply_safety_guard(proposed_action, rl_state)
            
            # Step 5: Return validated decision intent
            return self._create_decision_response(safe_action, rl_state)
            
        except Exception as e:
            error_msg = f"Bridge processing failed: {str(e)}"
            logger.error(error_msg)
            self.blocked_actions.append({"reason": error_msg, "exception": str(e)})
            return self.contract_validator.get_noop_response(error_msg)
    
    def _get_rl_decision(self, rl_state: Dict[str, Any]) -> ActionType:
        """Get decision from Q-Learning RL agent"""
        try:
            # Get action from RL agent
            action_str = self.rl_agent.choose_action(rl_state)
            action = ActionType(action_str)
            
            logger.info(f"RL Agent chose action: {action.value} for state: {rl_state}")
            return action
            
        except Exception as e:
            logger.warning(f"RL decision failed, falling back to rule-based: {e}")
            # Fallback to simple rule-based logic
            return self._rule_based_fallback(rl_state)
    
    def _rule_based_fallback(self, rl_state: Dict[str, Any]) -> ActionType:
        """Rule-based fallback when RL agent fails"""
        health_band = rl_state.get("health_band", "healthy")
        recent_failures = rl_state.get("recent_failures", 0)
        
        # Simple rule-based decisions
        if health_band == "failing" or recent_failures > 10:
            return ActionType.RESTART
        elif health_band == "degraded" or recent_failures > 3:
            return ActionType.SCALE_UP
        elif health_band == "healthy" and recent_failures == 0:
            return ActionType.SCALE_DOWN
        else:
            return ActionType.NOOP
    
    def _apply_safety_guard(self, proposed_action: ActionType, rl_state: Dict[str, Any]) -> ActionType:
        """Apply safety rules and downgrade unsafe actions"""
        env = rl_state.get("env", "dev")
        allowed_actions = self.safety_rules.get(env, [ActionType.NOOP])
        
        if proposed_action in allowed_actions:
            logger.info(f"Action {proposed_action.value} approved for {env}")
            return proposed_action
        
        # Downgrade to safe action
        safe_action = ActionType.NOOP
        downgrade_info = {
            "original_action": proposed_action.value,
            "safe_action": safe_action.value,
            "env": env,
            "reason": f"Action {proposed_action.value} not allowed in {env}",
            "rl_state": rl_state
        }
        
        self.safe_downgrades.append(downgrade_info)
        logger.warning(f"Downgraded {proposed_action.value} → {safe_action.value} for {env}")
        
        return safe_action
    
    def _create_decision_response(self, action: ActionType, rl_state: Dict[str, Any]) -> Dict[str, Any]:
        """Create final decision response"""
        return {
            "action": action.value,
            "app_id": rl_state.get("app_id"),
            "env": rl_state.get("env"),
            "confidence": self._calculate_confidence(rl_state),
            "reasoning": self._get_action_reasoning(action, rl_state),
            "safe_for_execution": True,
            "timestamp": self._get_timestamp()
        }
    
    def _calculate_confidence(self, rl_state: Dict[str, Any]) -> float:
        """Calculate decision confidence (0.0 - 1.0)"""
        # Simple confidence based on data completeness
        required_fields = ["health_band", "latency_bucket", "recent_failures"]
        present_fields = sum(1 for field in required_fields if rl_state.get(field) is not None)
        return present_fields / len(required_fields)
    
    def _get_action_reasoning(self, action: ActionType, rl_state: Dict[str, Any]) -> str:
        """Provide explainable reasoning for action"""
        health = rl_state.get("health_band", "unknown")
        failures = rl_state.get("recent_failures", 0)
        
        if action == ActionType.NOOP:
            return f"No action needed - health: {health}, failures: {failures}"
        elif action == ActionType.SCALE_UP:
            return f"Scale up due to degraded health: {health}, failures: {failures}"
        elif action == ActionType.RESTART:
            return f"Restart required - critical health: {health}, failures: {failures}"
        elif action == ActionType.SCALE_DOWN:
            return f"Scale down opportunity - healthy state: {health}, failures: {failures}"
        else:
            return f"Action {action.value} for health: {health}"
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_blocked_actions_log(self) -> List[Dict[str, Any]]:
        """Return log of blocked actions for debugging"""
        return self.blocked_actions.copy()
    
    def provide_feedback(self, previous_state: Dict[str, Any], action_taken: str,
                        outcome_state: Dict[str, Any], success: bool = True):
        """
        Provide feedback to RL agent for learning
        Call this after action execution to enable learning from real outcomes
        """
        try:
            reward = self.rl_agent.calculate_reward(previous_state, action_taken, outcome_state)
            if not success:
                reward += self.rl_agent.reward_weights["failed_action"]
            
            self.rl_agent.learn_from_experience(previous_state, action_taken, reward, outcome_state)
            logger.info(f"RL feedback provided: action={action_taken}, reward={reward:.2f}, success={success}")
            
        except Exception as e:
            logger.error(f"Failed to provide RL feedback: {e}")
    
    def get_rl_model_summary(self) -> Dict[str, Any]:
        """Get summary of RL learning progress"""
        return self.rl_agent.get_model_summary()
    
    def get_safe_downgrades_log(self) -> List[Dict[str, Any]]:
        """Return log of safety downgrades for debugging"""
        return self.safe_downgrades.copy()