"""Advanced RL Decision Layer Dashboard with real-time monitoring"""

from flask import Flask, render_template_string, jsonify, request
import json
import random
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

# Global state for dashboard
dashboard_state = {
    'events': [],
    'metrics': {
        'total_decisions': 0,
        'blocked_actions': 0,
        'safety_downgrades': 0,
        'uptime': datetime.now()
    },
    'system_health': 'healthy'
}

ADVANCED_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Advanced RL Decision Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f1419; color: #fff; }
        .dashboard { display: grid; grid-template-columns: 250px 1fr; height: 100vh; }
        
        .sidebar { background: #1a1f2e; padding: 20px; border-right: 1px solid #2d3748; }
        .sidebar h2 { color: #4fd1c7; margin-bottom: 20px; font-size: 18px; }
        .nav-item { padding: 10px; margin: 5px 0; background: #2d3748; border-radius: 6px; cursor: pointer; transition: all 0.3s; }
        .nav-item:hover { background: #4a5568; }
        .nav-item.active { background: #4fd1c7; color: #000; }
        
        .main-content { padding: 20px; overflow-y: auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .header h1 { color: #4fd1c7; font-size: 28px; }
        .status-badge { padding: 8px 16px; border-radius: 20px; font-weight: bold; }
        .status-healthy { background: #48bb78; }
        .status-degraded { background: #ed8936; }
        .status-failing { background: #f56565; }
        
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: #1a202c; padding: 20px; border-radius: 12px; border: 1px solid #2d3748; }
        .metric-value { font-size: 32px; font-weight: bold; color: #4fd1c7; }
        .metric-label { color: #a0aec0; margin-top: 5px; }
        .metric-change { font-size: 14px; margin-top: 5px; }
        .positive { color: #48bb78; }
        .negative { color: #f56565; }
        
        .charts-section { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 30px; }
        .chart-container { background: #1a202c; padding: 20px; border-radius: 12px; border: 1px solid #2d3748; }
        .chart-title { color: #e2e8f0; margin-bottom: 15px; font-size: 18px; }
        
        .events-section { background: #1a202c; border-radius: 12px; border: 1px solid #2d3748; }
        .events-header { padding: 20px; border-bottom: 1px solid #2d3748; display: flex; justify-content: between; align-items: center; }
        .events-table { width: 100%; }
        .events-table th { background: #2d3748; padding: 15px; text-align: left; color: #e2e8f0; }
        .events-table td { padding: 12px 15px; border-bottom: 1px solid #2d3748; }
        .events-table tr:hover { background: #2d3748; }
        
        .action-badge { padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: bold; }
        .action-noop { background: #4a5568; }
        .action-scale_up { background: #3182ce; }
        .action-scale_down { background: #805ad5; }
        .action-restart { background: #e53e3e; }
        
        .controls { display: flex; gap: 10px; margin-bottom: 20px; }
        .btn { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; transition: all 0.3s; }
        .btn-primary { background: #4fd1c7; color: #000; }
        .btn-secondary { background: #4a5568; color: #fff; }
        .btn:hover { transform: translateY(-2px); }
        
        .alert { padding: 15px; margin: 10px 0; border-radius: 8px; }
        .alert-warning { background: #fed7aa; color: #9c4221; border-left: 4px solid #f6ad55; }
        .alert-danger { background: #fed7d7; color: #742a2a; border-left: 4px solid #fc8181; }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .live-indicator { width: 8px; height: 8px; background: #48bb78; border-radius: 50%; animation: pulse 2s infinite; }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="sidebar">
            <h2>🎯 RL Dashboard</h2>
            <div class="nav-item active" onclick="showSection('overview')">📊 Overview</div>
            <div class="nav-item" onclick="showSection('events')">📋 Live Events</div>
            <div class="nav-item" onclick="showSection('safety')">🛡️ Safety Metrics</div>
            <div class="nav-item" onclick="showSection('config')">⚙️ Configuration</div>
        </div>
        
        <div class="main-content">
            <div class="header">
                <h1>RL Decision Layer Control Center</h1>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div class="live-indicator"></div>
                    <span>Live</span>
                    <div class="status-badge status-healthy" id="systemStatus">System Healthy</div>
                </div>
            </div>
            
            <div id="overviewSection">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value" id="totalDecisions">0</div>
                        <div class="metric-label">Total Decisions</div>
                        <div class="metric-change positive" id="decisionsChange">+12 this hour</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="blockedActions">0</div>
                        <div class="metric-label">Blocked Actions</div>
                        <div class="metric-change negative" id="blockedChange">+3 this hour</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="safetyDowngrades">0</div>
                        <div class="metric-label">Safety Downgrades</div>
                        <div class="metric-change negative" id="downgradesChange">+1 this hour</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="uptime">0h</div>
                        <div class="metric-label">System Uptime</div>
                        <div class="metric-change positive">99.9% availability</div>
                    </div>
                </div>
                
                <div class="charts-section">
                    <div class="chart-container">
                        <div class="chart-title">Decision Timeline</div>
                        <canvas id="timelineChart" width="400" height="200"></canvas>
                    </div>
                    <div class="chart-container">
                        <div class="chart-title">Action Distribution</div>
                        <canvas id="actionChart" width="200" height="200"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="events-section">
                <div class="events-header">
                    <h3>🔴 Live Runtime Events</h3>
                    <div class="controls">
                        <button class="btn btn-primary" onclick="refreshEvents()">Refresh</button>
                        <button class="btn btn-secondary" onclick="clearEvents()">Clear</button>
                    </div>
                </div>
                <table class="events-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Application</th>
                            <th>Environment</th>
                            <th>Health State</th>
                            <th>Latency</th>
                            <th>Errors</th>
                            <th>RL Decision</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="eventsTableBody">
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let timelineChart, actionChart;
        let eventData = [];
        
        function initCharts() {
            // Timeline Chart
            const timelineCtx = document.getElementById('timelineChart').getContext('2d');
            timelineChart = new Chart(timelineCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Decisions per Minute',
                        data: [],
                        borderColor: '#4fd1c7',
                        backgroundColor: 'rgba(79, 209, 199, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { labels: { color: '#e2e8f0' } } },
                    scales: {
                        x: { ticks: { color: '#a0aec0' }, grid: { color: '#2d3748' } },
                        y: { ticks: { color: '#a0aec0' }, grid: { color: '#2d3748' } }
                    }
                }
            });
            
            // Action Distribution Chart
            const actionCtx = document.getElementById('actionChart').getContext('2d');
            actionChart = new Chart(actionCtx, {
                type: 'doughnut',
                data: {
                    labels: ['NOOP', 'SCALE_UP', 'SCALE_DOWN', 'RESTART'],
                    datasets: [{
                        data: [0, 0, 0, 0],
                        backgroundColor: ['#4a5568', '#3182ce', '#805ad5', '#e53e3e']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { labels: { color: '#e2e8f0' } } }
                }
            });
        }
        
        function updateMetrics(data) {
            document.getElementById('totalDecisions').textContent = data.total_decisions;
            document.getElementById('blockedActions').textContent = data.blocked_actions;
            document.getElementById('safetyDowngrades').textContent = data.safety_downgrades;
            
            const uptime = Math.floor((Date.now() - new Date(data.uptime)) / (1000 * 60 * 60));
            document.getElementById('uptime').textContent = uptime + 'h';
        }
        
        function updateEventsTable(events) {
            const tbody = document.getElementById('eventsTableBody');
            tbody.innerHTML = '';
            
            events.slice(-10).reverse().forEach(event => {
                const row = tbody.insertRow();
                const time = new Date(event.timestamp).toLocaleTimeString();
                
                row.innerHTML = `
                    <td>${time}</td>
                    <td><strong>${event.app || 'N/A'}</strong></td>
                    <td><span class="status-badge status-${event.env}">${(event.env || 'unknown').toUpperCase()}</span></td>
                    <td><span class="status-badge status-${event.state || 'unknown'}">${(event.state || 'unknown').toUpperCase()}</span></td>
                    <td>${event.latency_ms || 'N/A'}ms</td>
                    <td>${event.errors_last_min || 0}</td>
                    <td><span class="action-badge action-${(event.decision?.action || 'noop').toLowerCase()}">${event.decision?.action || 'NOOP'}</span></td>
                    <td>${event.decision?.safe_for_execution ? '✅ Safe' : '⚠️ Blocked'}</td>
                `;
            });
        }
        
        function refreshEvents() {
            fetch('/api/dashboard-data')
                .then(response => response.json())
                .then(data => {
                    updateMetrics(data.metrics);
                    updateEventsTable(data.events);
                    
                    // Update charts
                    const actionCounts = [0, 0, 0, 0];
                    data.events.forEach(event => {
                        const action = event.decision?.action || 'NOOP';
                        switch(action) {
                            case 'NOOP': actionCounts[0]++; break;
                            case 'SCALE_UP': actionCounts[1]++; break;
                            case 'SCALE_DOWN': actionCounts[2]++; break;
                            case 'RESTART': actionCounts[3]++; break;
                        }
                    });
                    
                    actionChart.data.datasets[0].data = actionCounts;
                    actionChart.update();
                });
        }
        
        function clearEvents() {
            fetch('/api/clear-events', { method: 'POST' });
            setTimeout(refreshEvents, 100);
        }
        
        function showSection(section) {
            // Update nav
            document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
            event.target.classList.add('active');
        }
        
        // Initialize
        initCharts();
        refreshEvents();
        
        // Auto-refresh every 3 seconds
        setInterval(refreshEvents, 3000);
    </script>
</body>
</html>
"""

def generate_sample_event():
    """Generate realistic runtime events"""
    apps = ['api-gateway', 'user-service', 'payment-api', 'notification-svc', 'auth-service']
    envs = ['prod', 'stage', 'dev']
    states = ['healthy', 'degraded', 'failing']
    
    app = random.choice(apps)
    env = random.choice(envs)
    state = random.choice(states)
    
    # Realistic latency based on state
    latency_ranges = {'healthy': (50, 200), 'degraded': (200, 600), 'failing': (600, 2000)}
    latency = random.randint(*latency_ranges[state])
    
    # Error count based on state
    error_ranges = {'healthy': (0, 2), 'degraded': (3, 10), 'failing': (10, 30)}
    errors = random.randint(*error_ranges[state])
    
    return {
        'app': app,
        'env': env,
        'state': state,
        'latency_ms': latency,
        'workers': random.randint(1, 5),
        'errors_last_min': errors,
        'timestamp': datetime.now().isoformat()
    }

def process_rl_decision(event):
    """Process event through RL pipeline"""
    state = event.get('state', 'unknown')
    errors = event.get('errors_last_min', 0)
    env = event.get('env', 'dev')
    
    # RL decision logic
    if state == 'failing' or errors > 15:
        proposed = 'RESTART'
    elif state == 'degraded' or errors > 5:
        proposed = 'SCALE_UP'
    elif state == 'healthy' and errors == 0:
        proposed = 'SCALE_DOWN'
    else:
        proposed = 'NOOP'
    
    # Safety rules
    safety_rules = {
        'prod': ['NOOP', 'SCALE_UP'],
        'stage': ['NOOP', 'SCALE_UP', 'SCALE_DOWN'],
        'dev': ['NOOP', 'SCALE_UP', 'SCALE_DOWN', 'RESTART']
    }
    
    allowed = safety_rules.get(env, ['NOOP'])
    final_action = proposed if proposed in allowed else 'NOOP'
    
    # Update metrics
    dashboard_state['metrics']['total_decisions'] += 1
    if final_action != proposed:
        dashboard_state['metrics']['safety_downgrades'] += 1
    if not event.get('app') or not event.get('env'):
        dashboard_state['metrics']['blocked_actions'] += 1
    
    return {
        'action': final_action,
        'proposed': proposed,
        'safe_for_execution': True,
        'reasoning': f"State: {state}, Errors: {errors}"
    }

def event_generator():
    """Background thread to generate events"""
    while True:
        if len(dashboard_state['events']) < 100:  # Keep last 100 events
            event = generate_sample_event()
            decision = process_rl_decision(event)
            event['decision'] = decision
            dashboard_state['events'].append(event)
        else:
            dashboard_state['events'].pop(0)  # Remove oldest
            event = generate_sample_event()
            decision = process_rl_decision(event)
            event['decision'] = decision
            dashboard_state['events'].append(event)
        
        time.sleep(random.uniform(2, 8))  # Random interval

@app.route('/')
def dashboard():
    return render_template_string(ADVANCED_HTML)

@app.route('/api/dashboard-data')
def get_dashboard_data():
    return jsonify(dashboard_state)

@app.route('/api/clear-events', methods=['POST'])
def clear_events():
    dashboard_state['events'] = []
    dashboard_state['metrics']['total_decisions'] = 0
    dashboard_state['metrics']['blocked_actions'] = 0
    dashboard_state['metrics']['safety_downgrades'] = 0
    return jsonify({'status': 'cleared'})

if __name__ == '__main__':
    # Start background event generator
    event_thread = threading.Thread(target=event_generator, daemon=True)
    event_thread.start()
    
    print("🚀 Advanced RL Dashboard Starting...")
    print("📊 Dashboard URL: http://localhost:8080")
    print("🔴 Live events will start generating automatically")
    
    app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False)