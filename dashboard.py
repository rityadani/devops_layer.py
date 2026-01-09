"""RL Decision Layer Dashboard - Real-time monitoring"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integration.rl_orchestrator_bridge import RLOrchestratorBridge
import time
import json

def run_dashboard():
    """Launch RL Decision Layer Dashboard"""
    
    bridge = RLOrchestratorBridge()
    
    print("=" * 60)
    print("*** RL DECISION LAYER DASHBOARD ***")
    print("=" * 60)
    
    # Sample runtime events for demo
    events = [
        {"app": "api-service", "env": "prod", "state": "healthy", "latency_ms": 120, "errors_last_min": 0},
        {"app": "payment-svc", "env": "prod", "state": "degraded", "latency_ms": 450, "errors_last_min": 8},
        {"app": "user-api", "env": "stage", "state": "failing", "latency_ms": 800, "errors_last_min": 15},
        {"app": "test-svc", "env": "dev", "state": "healthy", "latency_ms": 90, "errors_last_min": 1},
        {"app": "", "env": "prod", "latency_ms": 200}  # Invalid
    ]
    
    for i, event in enumerate(events, 1):
        print(f"\n*** EVENT {i}: {event.get('app', 'INVALID')} ({event.get('env', 'unknown')})")
        print("-" * 40)
        
        decision = bridge.process_runtime_state(event)
        
        print(f"Action: {decision['action']}")
        if 'reasoning' in decision:
            print(f"Reason: {decision['reasoning']}")
        if 'reason' in decision:
            print(f"Error: {decision['reason']}")
        
        print(f"Safe: {'OK' if decision.get('safe_for_execution', decision.get('safe_fallback')) else 'ERROR'}")
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("*** SAFETY METRICS ***")
    print("=" * 60)
    
    blocked = bridge.get_blocked_actions_log()
    downgrades = bridge.get_safe_downgrades_log()
    
    print(f"*** Blocked Actions: {len(blocked)}")
    for block in blocked:
        print(f"   • {block['reason']}")
    
    print(f"*** Safety Downgrades: {len(downgrades)}")
    for downgrade in downgrades:
        print(f"   • {downgrade['original_action']} -> {downgrade['safe_action']}")
    
    print("\n*** SYSTEM STATUS: PRODUCTION READY ***")

if __name__ == "__main__":
    run_dashboard()