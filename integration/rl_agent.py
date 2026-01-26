"""Q-Learning RL Agent for DevOps Decision Making"""

import numpy as np
import json
import os
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class QLearningAgent:
    """Q-Learning agent for autonomous DevOps decisions"""

    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.9,
                 exploration_rate: float = 0.1, save_path: str = "rl_model.json"):
        self.alpha = learning_rate  # Learning rate
        self.gamma = discount_factor  # Discount factor
        self.epsilon = exploration_rate  # Exploration rate

        # State space: (health_band, latency_bucket, recent_failures_bucket)
        # Actions: NOOP, SCALE_UP, SCALE_DOWN, RESTART, ROLLBACK
        self.actions = ["NOOP", "SCALE_UP", "SCALE_DOWN", "RESTART", "ROLLBACK"]

        # Initialize Q-table
        self.q_table = {}
        self.save_path = save_path

        # Load existing model if available
        self.load_model()

        # Reward function parameters
        self.reward_weights = {
            "latency_improvement": 10,
            "error_reduction": 15,
            "successful_action": 5,
            "failed_action": -20,
            "unsafe_action": -50,
            "no_change_needed": 2,
            "time_penalty": -1
        }

    def get_state_key(self, rl_state: Dict[str, Any]) -> str:
        """Convert RL state to discrete state key for Q-table"""
        health = rl_state.get("health_band", "unknown")
        latency = rl_state.get("latency_bucket", "unknown")
        failures = min(rl_state.get("recent_failures", 0) // 5, 3)  # Bucket failures: 0, 1-4, 5-9, 10+

        return f"{health}_{latency}_{failures}"

    def choose_action(self, rl_state: Dict[str, Any]) -> str:
        """Choose action using epsilon-greedy policy"""
        state_key = self.get_state_key(rl_state)

        # Initialize state if not seen before
        if state_key not in self.q_table:
            self.q_table[state_key] = {action: 0.0 for action in self.actions}

        # Epsilon-greedy action selection
        if np.random.random() < self.epsilon:
            # Explore: random action
            action = np.random.choice(self.actions)
            logger.info(f"RL Exploration: {action} for state {state_key}")
        else:
            # Exploit: best action
            action = max(self.q_table[state_key], key=self.q_table[state_key].get)
            logger.info(f"RL Exploitation: {action} for state {state_key}")

        return action

    def calculate_reward(self, rl_state: Dict[str, Any], action: str,
                        next_state: Optional[Dict[str, Any]] = None) -> float:
        """Calculate reward for state-action pair"""
        reward = 0

        health = rl_state.get("health_band", "unknown")
        failures = rl_state.get("recent_failures", 0)

        # Base rewards by health state
        if health == "healthy":
            if action == "NOOP":
                reward += self.reward_weights["no_change_needed"]
            elif action == "SCALE_DOWN":
                reward += self.reward_weights["successful_action"]
            else:
                reward += self.reward_weights["failed_action"]  # Unnecessary action
        elif health == "degraded":
            if action in ["SCALE_UP", "NOOP"]:
                reward += self.reward_weights["successful_action"]
            elif action == "RESTART":
                reward += self.reward_weights["successful_action"] * 0.5  # Partial credit
            else:
                reward += self.reward_weights["failed_action"]
        elif health == "failing":
            if action == "RESTART":
                reward += self.reward_weights["successful_action"] * 2  # Critical action
            elif action == "SCALE_UP":
                reward += self.reward_weights["successful_action"]
            else:
                reward += self.reward_weights["failed_action"]

        # Penalty for high failure rates
        if failures > 10:
            reward += self.reward_weights["time_penalty"] * 2

        # Reward for reducing errors (if next state available)
        if next_state:
            next_failures = next_state.get("recent_failures", 0)
            if next_failures < failures:
                reward += self.reward_weights["error_reduction"]

        # Time penalty for any action (encourage efficiency)
        if action != "NOOP":
            reward += self.reward_weights["time_penalty"]

        return reward

    def update_q_value(self, state: Dict[str, Any], action: str,
                      reward: float, next_state: Optional[Dict[str, Any]] = None):
        """Update Q-value using Q-learning update rule"""
        state_key = self.get_state_key(state)

        # Initialize states if not seen
        if state_key not in self.q_table:
            self.q_table[state_key] = {action: 0.0 for action in self.actions}

        current_q = self.q_table[state_key][action]

        # Calculate max Q for next state
        if next_state:
            next_state_key = self.get_state_key(next_state)
            if next_state_key not in self.q_table:
                self.q_table[next_state_key] = {action: 0.0 for action in self.actions}
            max_next_q = max(self.q_table[next_state_key].values())
        else:
            max_next_q = 0

        # Q-learning update
        new_q = current_q + self.alpha * (reward + self.gamma * max_next_q - current_q)
        self.q_table[state_key][action] = new_q

        logger.debug(f"Updated Q[{state_key}][{action}]: {current_q:.3f} -> {new_q:.3f}")

    def learn_from_experience(self, state: Dict[str, Any], action: str,
                            reward: float, next_state: Optional[Dict[str, Any]] = None):
        """Learn from a single experience tuple"""
        self.update_q_value(state, action, reward, next_state)

        # Save model periodically (every 10 updates)
        if len(self.q_table) % 10 == 0:
            self.save_model()

    def save_model(self):
        """Save Q-table and reward function to file"""
        try:
            model_data = {
                "q_table": self.q_table,
                "reward_weights": self.reward_weights,
                "parameters": {
                    "alpha": self.alpha,
                    "gamma": self.gamma,
                    "epsilon": self.epsilon
                },
                "last_updated": datetime.utcnow().isoformat(),
                "total_states_learned": len(self.q_table)
            }

            with open(self.save_path, 'w') as f:
                json.dump(model_data, f, indent=2)

            logger.info(f"RL model saved to {self.save_path} ({len(self.q_table)} states)")

        except Exception as e:
            logger.error(f"Failed to save RL model: {e}")

    def load_model(self):
        """Load Q-table and reward function from file"""
        try:
            if os.path.exists(self.save_path):
                with open(self.save_path, 'r') as f:
                    model_data = json.load(f)

                self.q_table = model_data.get("q_table", {})
                self.reward_weights = model_data.get("reward_weights", self.reward_weights)

                params = model_data.get("parameters", {})
                self.alpha = params.get("alpha", self.alpha)
                self.gamma = params.get("gamma", self.gamma)
                self.epsilon = params.get("epsilon", self.epsilon)

                logger.info(f"RL model loaded from {self.save_path} ({len(self.q_table)} states)")
            else:
                logger.info("No existing RL model found, starting fresh")

        except Exception as e:
            logger.error(f"Failed to load RL model: {e}")

    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of current RL model"""
        return {
            "total_states": len(self.q_table),
            "total_experiences": sum(len(actions) for actions in self.q_table.values()),
            "parameters": {
                "learning_rate": self.alpha,
                "discount_factor": self.gamma,
                "exploration_rate": self.epsilon
            },
            "reward_weights": self.reward_weights,
            "last_updated": datetime.utcnow().isoformat()
        }

    def get_state_action_values(self, rl_state: Dict[str, Any]) -> Dict[str, float]:
        """Get Q-values for all actions in current state"""
        state_key = self.get_state_key(rl_state)

        if state_key not in self.q_table:
            return {action: 0.0 for action in self.actions}

        return self.q_table[state_key].copy()