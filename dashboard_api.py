"""
Kalshi Bot Dashboard API
Real-time monitoring and performance tracking
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime
import json
import os

app = FastAPI(title="Kalshi Bot Dashboard", version="1.0.0")

# Mount static files
# app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")


class TradeRecord(BaseModel):
    """Single trade record"""
    timestamp: str
    market: str
    side: str
    size: float
    price: float
    pnl: float


class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    total_pnl: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    active_positions: int


@app.get("/")
async def root():
    """Serve dashboard HTML"""
    return HTMLResponse(content=get_dashboard_html())


@app.get("/api/status")
async def get_status():
    """Get bot status"""
    return {
        "status": "running",
        "uptime": "2h 34m",
        "last_trade": "2026-01-06 16:15:23"
    }


@app.get("/api/performance")
async def get_performance():
    """Get performance metrics"""
    try:
        from trade_db import TradeDB
        db = TradeDB()
        stats = db.get_performance_stats()
        return stats
    except Exception as e:
        # Fallback to demo data
        return {
            "total_pnl": 0.00,
            "win_rate": 0.00,
            "sharpe_ratio": 0.00,
            "max_drawdown": 0.00,
            "total_trades": 0,
            "active_positions": 0
        }


@app.get("/api/trades")
async def get_trades():
    """Get recent trades"""
    try:
        from trade_db import TradeDB
        db = TradeDB()
        trades = db.get_recent_trades(20)
        return {"trades": trades}
    except Exception as e:
        return {"trades": []}


@app.get("/api/chart-data")
async def get_chart_data():
    """Get data for performance charts"""
    # TODO: Load actual P&L history
    return {
        "timestamps": ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"],
        "pnl": [0, 15, 12, 25, 30, 22, 35],
        "drawdown": [0, -0.02, -0.05, -0.03, 0, -0.04, -0.01]
    }


def get_dashboard_html():
    """Return dashboard HTML"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Kalshi Bot Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            margin-bottom: 30px;
            text-align: center;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        .metric-label {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .metric-value.positive { color: #10b981; }
        .metric-value.negative { color: #ef4444; }
        .charts {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .chart-container {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        }
        .chart-container h3 {
            margin-bottom: 20px;
            color: #333;
        }
        .trades-table {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        th {
            background: #f9fafb;
            color: #374151;
            font-weight: 600;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .status-running {
            background: #d1fae5;
            color: #065f46;
        }
        .pnl-positive { color: #10b981; font-weight: 600; }
        .pnl-negative { color: #ef4444; font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Kalshi Trading Bot Dashboard</h1>
        
        <div class="metrics" id="metrics">
            <div class="metric-card">
                <div class="metric-label">Total P&L</div>
                <div class="metric-value positive" id="total-pnl">$0.00</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value" id="win-rate">0%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Sharp Ratio</div>
                <div class="metric-value" id="sharpe">0.00</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value negative" id="drawdown">0%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Trades</div>
                <div class="metric-value" id="total-trades">0</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Active Positions</div>
                <div class="metric-value" id="active-positions">0</div>
            </div>
        </div>
        
        <div class="charts">
            <div class="chart-container">
                <h3>📈 P&L Over Time</h3>
                <canvas id="pnl-chart"></canvas>
            </div>
            <div class="chart-container">
                <h3>📉 Drawdown Curve</h3>
                <canvas id="drawdown-chart"></canvas>
            </div>
        </div>
        
        <div class="trades-table">
            <h3>Recent Trades <span class="status-badge status-running">RUNNING</span></h3>
            <table id="trades-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Market</th>
                        <th>Side</th>
                        <th>Size</th>
                        <th>Price</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody id="trades-body">
                    <tr><td colspan="6" style="text-align:center;color:#999;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Fetch and display metrics
        async function updateMetrics() {
            const perf = await fetch('/api/performance').then(r => r.json());
            
            document.getElementById('total-pnl').textContent = `$${perf.total_pnl.toFixed(2)}`;
            document.getElementById('total-pnl').className = 'metric-value ' + (perf.total_pnl >= 0 ? 'positive' : 'negative');
            document.getElementById('win-rate').textContent = `${(perf.win_rate * 100).toFixed(1)}%`;
            document.getElementById('sharpe').textContent = perf.sharpe_ratio.toFixed(2);
            document.getElementById('drawdown').textContent = `${(perf.max_drawdown * 100).toFixed(1)}%`;
            document.getElementById('total-trades').textContent = perf.total_trades;
            document.getElementById('active-positions').textContent = perf.active_positions;
        }
        
        // Fetch and display trades
        async function updateTrades() {
            const data = await fetch('/api/trades').then(r => r.json());
            const tbody = document.getElementById('trades-body');
            
            tbody.innerHTML = data.trades.map(t => `
                <tr>
                    <td>${t.timestamp}</td>
                    <td>${t.market}</td>
                    <td>${t.side}</td>
                    <td>${t.size}</td>
                    <td>$${t.price.toFixed(2)}</td>
                    <td class="${t.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">$${t.pnl.toFixed(2)}</td>
                </tr>
            `).join('');
        }
        
        // Create charts
        async function createCharts() {
            const chartData = await fetch('/api/chart-data').then(r => r.json());
            
            // P&L Chart
            new Chart(document.getElementById('pnl-chart'), {
                type: 'line',
                data: {
                    labels: chartData.timestamps,
                    datasets: [{
                        label: 'P&L ($)',
                        data: chartData.pnl,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } }
                }
            });
            
            // Drawdown Chart
            new Chart(document.getElementById('drawdown-chart'), {
                type: 'line',
                data: {
                    labels: chartData.timestamps,
                    datasets: [{
                        label: 'Drawdown',
                        data: chartData.drawdown,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } }
                }
            });
        }
        
        // Initialize
        updateMetrics();
        updateTrades();
        createCharts();
        
        // Auto-refresh every 5 seconds
        setInterval(() => {
            updateMetrics();
            updateTrades();
        }, 5000);
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
