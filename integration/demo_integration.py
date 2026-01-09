"""Demonstration of RL Decision Layer integration with real runtime events"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integration.rl_orchestrator_bridge import RLOrchestratorBridge

def demonstrate_integration():
    """Show RL consuming real runtime states and making safe decisions"""
    
    bridge = RLOrchestratorBridge()
    
    print("=== RL Decision Layer - Runtime Integration Demo ===\n")
    
    # Test Case 1: Valid healthy state
    print("1. VALID HEALTHY STATE")
    healthy_runtime = {
        "app": "api-service",
        "env": "stage",
        "state": "healthy", 
        "latency_ms": 150,
        "workers": 3,
        "errors_last_min": 0
    }
    
    decision = bridge.process_runtime_state(healthy_runtime)
    print(f"   Runtime: {json.dumps(healthy_runtime, indent=2)}")
    print(f"   Decision: {decision['action']}")
    print(f"   Reasoning: {decision['reasoning']}")
    print(f"   Safe: {decision['safe_for_execution']}\n")
    
    # Test Case 2: Degraded state requiring action
    print("2. DEGRADED STATE - SCALE UP NEEDED")
    degraded_runtime = {
        "app": "backend-service", 
        "env": "prod",
        "state": "degraded",
        "latency_ms": 600,
        "workers": 2,
        "errors_last_min": 8
    }
    
    decision = bridge.process_runtime_state(degraded_runtime)
    print(f"   Runtime: {json.dumps(degraded_runtime, indent=2)}")
    print(f"   Decision: {decision['action']}")
    print(f"   Reasoning: {decision['reasoning']}")
    print(f"   Safe: {decision['safe_for_execution']}\n")
    
    # Test Case 3: Contract violation - missing required field
    print("3. CONTRACT VIOLATION - Missing Required Field")
    invalid_runtime = {
        "app": "broken-service",
        "latency_ms": 300,
        "workers": 1
        # Missing 'env' and 'state' - should trigger NOOP
    }
    
    decision = bridge.process_runtime_state(invalid_runtime)
    print(f"   Runtime: {json.dumps(invalid_runtime, indent=2)}")
    print(f"   Decision: {decision['action']}")
    print(f"   Reason: {decision['reason']}")
    print(f"   Safe Fallback: {decision['safe_fallback']}\n")
    
    # Test Case 4: Safety downgrade - risky action in prod
    print("4. SAFETY DOWNGRADE - Risky Action Blocked")
    failing_runtime = {
        "app": "critical-service",
        "env": "prod", 
        "state": "failing",
        "latency_ms": 2000,
        "workers": 1,
        "errors_last_min": 25
    }
    
    decision = bridge.process_runtime_state(failing_runtime)
    print(f"   Runtime: {json.dumps(failing_runtime, indent=2)}")
    print(f"   Decision: {decision['action']}")
    print(f"   Reasoning: {decision['reasoning']}")
    print(f"   Safe: {decision['safe_for_execution']}\n")
    
    # Show safety logs
    print("=== SAFETY LOGS ===")
    blocked = bridge.get_blocked_actions_log()
    downgrades = bridge.get_safe_downgrades_log()
    
    print(f"Blocked Actions: {len(blocked)}")
    for i, block in enumerate(blocked, 1):
        print(f"  {i}. {block['reason']}")
    
    print(f"\nSafe Downgrades: {len(downgrades)}")
    for i, downgrade in enumerate(downgrades, 1):
        print(f"  {i}. {downgrade['original_action']} → {downgrade['safe_action']} ({downgrade['reason']})")

if __name__ == "__main__":
    demonstrate_integration()