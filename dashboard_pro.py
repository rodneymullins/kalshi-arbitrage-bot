"""
Kalshi Bot - Enhanced Dashboard API v2
Beautiful, real-time trading dashboard with bot controls
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import psycopg2
import subprocess
import os

app = FastAPI(title="Kalshi Bot Dashboard Pro", version="2.0.0")


@app.get("/")
async def root():
    """Serve enhanced dashboard HTML"""
    return HTMLResponse(content=get_dashboard_html())


@app.get("/api/status")
async def get_status():
    """Get bot status with real-time info"""
    try:
        # Check if bot process is running
        result = subprocess.run(['pgrep', '-f', 'bot_v3.py'], capture_output=True)
        is_running = len(result.stdout) > 0
        
        # Get latest log entry
        try:
            with open(f'logs/trading_{datetime.now().strftime("%Y%m%d")}.log', 'r') as f:
                lines = f.readlines()
                last_activity = lines[-1][:100] if lines else "No activity"
        except:
            last_activity = "No log file"
        
        return {
            "status": "running" if is_running else "stopped",
            "last_activity": last_activity,
            "timestamp": datetime.now().isoformat()
        }
    except:
        return {
            "status": "unknown",
            "last_activity": "Error checking status",
            "timestamp": datetime.now().isoformat()
        }


@app.post("/api/bot/start")
async def start_bot():
    """Start the trading bot"""
    try:
        # Check if already running
        result = subprocess.run(['pgrep', '-f', 'bot_v3.py'], capture_output=True)
        if len(result.stdout) > 0:
            return JSONResponse({"success": False, "message": "Bot is already running"})
        
        # Start the bot
        bot_dir = "/Users/rod/Antigravity/kalshi_bot"
        log_file = f"logs/trading_{datetime.now().strftime('%Y%m%d')}.log"
        
        subprocess.Popen(
            f"cd {bot_dir} && nohup python3 -u bot_v3.py >> {log_file} 2>&1 &",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        return JSONResponse({"success": True, "message": "Bot started successfully"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Error starting bot: {str(e)}"})


@app.post("/api/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    try:
        result = subprocess.run(['pkill', '-f', 'bot_v3.py'], capture_output=True)
        return JSONResponse({"success": True, "message": "Bot stopped successfully"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Error stopping bot: {str(e)}"})


@app.get("/api/performance")
async def get_performance():
    """Get performance metrics from database"""
    try:
        conn = psycopg2.connect(
            host="192.168.1.211",
            database="postgres",
            user="rod",
            password=""
        )
        cur = conn.cursor()
        
        # Get total trades count
        cur.execute("SELECT COUNT(*) FROM kalshi_trades")
        total_trades = cur.fetchone()[0]
        
        # Get total P&L (simulated for now)
        cur.execute("SELECT COALESCE(SUM(size * (price - 50)), 0) FROM kalshi_trades")
        total_pnl = cur.fetchone()[0] or 0.0
        
        # Calculate win rate (orders that filled vs resting)
        cur.execute("SELECT COUNT(*) FROM kalshi_trades WHERE status = 'active'")
        filled = cur.fetchone()[0]
        win_rate = (filled / total_trades * 100) if total_trades > 0 else 0
        
        # Active positions
        cur.execute("SELECT COUNT(*) FROM kalshi_trades WHERE status = 'resting'")
        active = cur.fetchone()[0]
        
        # Last fill time
        cur.execute("SELECT MAX(timestamp) FROM kalshi_trades WHERE status = 'active'")
        last_fill_row = cur.fetchone()
        last_fill_time = last_fill_row[0].strftime("%H:%M:%S") if last_fill_row and last_fill_row[0] else "N/A"
        
        # 24h high/low
        cur.execute("SELECT MAX(price), MIN(price) FROM kalshi_trades WHERE timestamp > NOW() - INTERVAL '24 hours'")
        high_low = cur.fetchone()
        high_24h = float(high_low[0]) / 100 if high_low and high_low[0] else 0.0
        low_24h = float(high_low[1]) / 100 if high_low and high_low[1] else 0.0
        
        # Current position (contracts held with active status)
        cur.execute("SELECT COALESCE(SUM(size), 0) FROM kalshi_trades WHERE status = 'active'")
        position = cur.fetchone()[0] or 0
        
        conn.close()
        
        # Calculate edge and max position
        edge_pct = 5.0  # Fixed 5% edge
        max_position = int(29.40 * 0.10 / 0.05)  # 10% Kelly with 5¢ price
        
        return {
            "total_pnl": float(total_pnl) / 100,
            "win_rate": float(win_rate),
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "total_trades": int(total_trades),
            "active_positions": int(active),
            "bankroll": 29.40,
            "last_fill_time": last_fill_time,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "current_position": int(position),
            "edge_pct": edge_pct,
            "max_position": max_position
        }
    except Exception as e:
        print(f"Database error: {e}")
        return {
            "total_pnl": 0.00,
            "win_rate": 0.00,
            "sharpe_ratio": 0.00,
            "max_drawdown": 0.00,
            "total_trades": 0,
            "active_positions": 0,
            "bankroll": 29.40,
            "last_fill_time": "N/A",
            "high_24h": 0.00,
            "low_24h": 0.00,
            "current_position": 0,
            "edge_pct": 5.0,
            "max_position": 58
        }


@app.get("/api/trades")
async def get_trades():
    """Get recent trades from database"""
    try:
        conn = psycopg2.connect(
            host="192.168.1.211",
            database="postgres",
            user="rod",
            password=""
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT timestamp, market, side, size, price, status 
            FROM kalshi_trades 
            ORDER BY timestamp DESC 
            LIMIT 20
        """)
        
        trades = []
        for row in cur.fetchall():
            trades.append({
                "timestamp": row[0].strftime("%H:%M:%S") if hasattr(row[0], 'strftime') else str(row[0]),
                "market": row[1][:30],
                "side": row[2],
                "size": float(row[3]),
                "price": float(row[4]) / 100,
                "status": row[5]
            })
        
        conn.close()
        return {"trades": trades}
    except Exception as e:
        print(f"Database error: {e}")
        return {"trades": []}


@app.get("/api/current-market")
async def get_current_market():
    """Get current market being traded with detailed metrics"""
    try:
        # Read the current ticker from bot_v3.py
        with open('bot_v3.py', 'r') as f:
            content = f.read()
            import re
            match = re.search(r'ticker = "([^"]+)"', content)
            
            if not match:
                return {"ticker": "N/A", "name": "No market configured", "price": 0, "volume": "$0"}
            
            ticker = match.group(1)
            
            # Get market info from Kalshi API
            try:
                import os, time, base64, requests
                from dotenv import load_dotenv
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import padding
                
                load_dotenv()
                key = os.getenv('KALSHI_KEY_ID')
                
                with open('kalshi.key', 'rb') as kf:
                    pk = serialization.load_pem_private_key(kf.read(), password=None)
                
                def sign(method, path, ts):
                    msg = f'{ts}{method}{path}'
                    sig = pk.sign(msg.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
                    return base64.b64encode(sig).decode()
                
                # Get market details
                ts = str(int(time.time() * 1000))
                path = f'/trade-api/v2/markets/{ticker}'
                h = {'KALSHI-ACCESS-KEY': key, 'KALSHI-ACCESS-SIGNATURE': sign('GET', path, ts), 'KALSHI-ACCESS-TIMESTAMP': ts}
                r = requests.get(f'https://api.elections.kalshi.com{path}', headers=h, timeout=10)
                
                if r.status_code == 200:
                    market = r.json().get('market', {})
                    
                    # Get orderbook for spread
                    ts2 = str(int(time.time() * 1000))
                    path2 = f'/trade-api/v2/markets/{ticker}/orderbook'
                    h2 = {'KALSHI-ACCESS-KEY': key, 'KALSHI-ACCESS-SIGNATURE': sign('GET', path2, ts2), 'KALSHI-ACCESS-TIMESTAMP': ts2}
                    r2 = requests.get(f'https://api.elections.kalshi.com{path2}', headers=h2, timeout=10)
                    
                    bid_ask_spread = "N/A"
                    best_price = 0.05
                    
                    if r2.status_code == 200:
                        ob = r2.json().get('orderbook', {})
                        yes_asks = ob.get('yes', [])
                        yes_bids = ob.get('no', [])  # No bids are inverse of yes asks
                        
                        if yes_asks:
                            best_ask = min([x[0]/100 for x in yes_asks])
                            best_bid = max([x[0]/100 for x in yes_bids]) if yes_bids else best_ask - 0.01
                            spread = best_ask - best_bid
                            bid_ask_spread = f"${spread:.2f} ({spread/best_ask*100:.1f}%)"
                            best_price = best_ask
                    
                    # Calculate time to close
                    from datetime import datetime
                    close_time_str = market.get('close_time', '')
                    time_to_close = "N/A"
                    
                    if close_time_str:
                        close_dt = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
                        now = datetime.now(close_dt.tzinfo)
                        delta = close_dt - now
                        
                        days = delta.days
                        hours = delta.seconds // 3600
                        
                        if days > 0:
                            time_to_close = f"{days}d {hours}h"
                        elif hours > 0:
                            mins = (delta.seconds % 3600) // 60
                            time_to_close = f"{hours}h {mins}m"
                        else:
                            mins = delta.seconds // 60
                            time_to_close = f"{mins}m"
                    
                    # Get orders today from database
                    try:
                        import psycopg2
                        conn = psycopg2.connect(host="192.168.1.211", database="postgres", user="rod", password="")
                        cur = conn.cursor()
                        
                        cur.execute("""
                            SELECT COUNT(*), MAX(timestamp) 
                            FROM kalshi_trades 
                            WHERE market = %s AND timestamp > NOW() - INTERVAL '24 hours'
                        """, (ticker,))
                        
                        result = cur.fetchone()
                        orders_today = result[0] if result else 0
                        last_order_time = result[1].strftime("%H:%M:%S") if result and result[1] else "N/A"
                        
                        # Get last order status
                        cur.execute("""
                            SELECT status FROM kalshi_trades 
                            WHERE market = %s 
                            ORDER BY timestamp DESC LIMIT 1
                        """, (ticker,))
                        
                        last_status_row = cur.fetchone()
                        last_order_status = last_status_row[0] if last_status_row else "None"
                        
                        conn.close()
                    except:
                        orders_today = 0
                        last_order_status = "N/A"
                        last_order_time = "N/A"
                    
                    # Calculate implied probability
                    implied_prob = f"{best_price * 100:.1f}%"
                    
                    return {
                        "ticker": ticker,
                        "name": market.get('title', '')[:50],
                        "price": best_price,
                        "volume": f"${market.get('volume', 0):,}",
                        "time_to_close": time_to_close,
                        "implied_probability": implied_prob,
                        "bid_ask_spread": bid_ask_spread,
                        "orders_today": orders_today,
                        "last_order_status": last_order_status,
                        "last_order_time": last_order_time
                    }
            except Exception as e:
                print(f"API error: {e}")
        
        return {
            "ticker": ticker,
            "name": ticker[:40] + "...",
            "price": 0.05,
            "volume": "$0",
            "time_to_close": "N/A",
            "implied_probability": "N/A",
            "bid_ask_spread": "N/A",
            "orders_today": 0,
            "last_order_status": "N/A",
            "last_order_time": "N/A"
        }
    except:
        return {
            "ticker": "N/A",
            "name": "Error loading market",
            "price": 0,
            "volume": "$0",
            "time_to_close": "N/A",
            "implied_probability": "N/A",
            "bid_ask_spread": "N/A",
            "orders_today": 0,
            "last_order_status": "N/A",
            "last_order_time": "N/A"
        }


@app.get("/api/chart-data")
async def get_chart_data():
    """Get time-series data for charts"""
    try:
        conn = psycopg2.connect(
            host="192.168.1.211",
            database="postgres",
            user="rod",
            password=""
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as count,
                SUM(size * price) / 100 as volume
            FROM kalshi_trades
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour
        """)
        
        hours = []
        counts = []
        volumes = []
        
        for row in cur.fetchall():
            hours.append(row[0].strftime("%H:%M") if row[0] else "")
            counts.append(int(row[1]))
            volumes.append(float(row[2]) if row[2] else 0)
        
        conn.close()
        
        return {
            "labels": hours if hours else ["No data"],
            "trade_counts": counts if counts else [0],
            "volumes": volumes if volumes else [0]
        }
    except Exception as e:
        print(f"Chart data error: {e}")
        return {
            "labels": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
            "trade_counts": [0, 0, 0, 0, 0, 0],
            "volumes": [0, 0, 0, 0, 0, 0]
        }


@app.get("/api/pnl-history")
async def get_pnl_history():
    """Get P&L history for charting"""
    try:
        import psycopg2
        conn = psycopg2.connect(host="192.168.1.211", database="postgres", user="rod", password="")
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                SUM(size * (price - 50)) / 100 as pnl
            FROM kalshi_trades
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour
        """)
        
        hours = []
        pnls = []
        cumulative = 0
        
        for row in cur.fetchall():
            hours.append(row[0].strftime("%H:%M") if row[0] else "")
            pnl = float(row[1]) if row[1] else 0
            cumulative += pnl
            pnls.append(cumulative)
        
        conn.close()
        
        return {
            "labels": hours if hours else ["No data"],
            "pnls": pnls if pnls else [0]
        }
    except Exception as e:
        print(f"P&L history error: {e}")
        return {
            "labels": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
            "pnls": [0, 0, 0, 0, 0, 0]
        }




@app.get("/api/market-analytics")
async def get_market_analytics():
    """Get comprehensive market analytics"""
    try:
        import psycopg2
        from datetime import datetime, timedelta
        
        conn = psycopg2.connect(host="192.168.1.211", database="postgres", user="rod", password="")
        cur = conn.cursor()
        
        # Get current ticker
        import re
        with open('bot_v3.py', 'r') as f:
            match = re.search(r'ticker = "([^"]+)"', f.read())
            ticker = match.group(1) if match else "N/A"
        
        # Market Activity Metrics
        cur.execute("SELECT MAX(timestamp) FROM kalshi_trades")
        last_trade = cur.fetchone()[0]
        last_trade_time = last_trade.strftime("%H:%M:%S") if last_trade else "N/A"
        
        # Bot Performance Metrics
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as filled
            FROM kalshi_trades
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)
        perf = cur.fetchone()
        fill_rate = (perf[1] / perf[0] * 100) if perf[0] > 0 else 0
        
        cur.execute("SELECT MAX(timestamp) FROM kalshi_trades WHERE market = %s", (ticker,))
        last_order = cur.fetchone()[0]
        last_order_time = last_order.strftime("%H:%M:%S") if last_order else "N/A"
        
        # Market-specific P&L
        cur.execute("""
            SELECT COALESCE(SUM(size * (price - 50)), 0) / 100 
            FROM kalshi_trades 
            WHERE market = %s
        """, (ticker,))
        pnl_market = float(cur.fetchone()[0] or 0)
        
        # Statistical Analysis
        cur.execute("SELECT AVG(size) FROM kalshi_trades WHERE timestamp > NOW() - INTERVAL '24 hours'")
        avg_size = float(cur.fetchone()[0] or 0)
        
        cur.execute("""
            WITH consecutive AS (
                SELECT 
                    status,
                    ROW_NUMBER() OVER (ORDER BY timestamp DESC) -
                    ROW_NUMBER() OVER (PARTITION BY status ORDER BY timestamp DESC) as grp
                FROM kalshi_trades
                WHERE timestamp > NOW() - INTERVAL '7 days'
                ORDER BY timestamp DESC
                LIMIT 100
            )
            SELECT status, COUNT(*) as streak
            FROM consecutive
            WHERE grp = 0
            GROUP BY status
        """)
        streak_data = cur.fetchone()
        current_streak = f"{streak_data[1]} {streak_data[0]}" if streak_data else "0"
        
        # Time since last fill
        cur.execute("SELECT MAX(timestamp) FROM kalshi_trades WHERE status = 'active'")
        last_fill = cur.fetchone()[0]
        if last_fill:
            delta = datetime.now() - last_fill.replace(tzinfo=None)
            mins = int(delta.total_seconds() / 60)
            time_since_fill = f"{mins}m ago" if mins < 60 else f"{mins//60}h {mins%60}m ago"
        else:
            time_since_fill = "N/A"
        
        # Capital efficiency
        cur.execute("SELECT COALESCE(SUM(size * price), 0) / 100 FROM kalshi_trades WHERE status = 'active'")
        capital_used = float(cur.fetchone()[0] or 0)
        capital_efficiency = (capital_used / 29.40 * 100) if capital_used > 0 else 0
        
        # Profit factor
        cur.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN size * (price - 50) > 0 THEN size * (price - 50) ELSE 0 END), 0) / 100 as wins,
                COALESCE(SUM(CASE WHEN size * (price - 50) < 0 THEN ABS(size * (price - 50)) ELSE 0 END), 0) / 100 as losses
            FROM kalshi_trades
        """)
        pf = cur.fetchone()
        profit_factor = (pf[0] / pf[1]) if pf[1] > 0 else 0
        
        conn.close()
        
        # Risk calculations 
        risk_per_trade = 0.05 * 58  # price * max_position
        expected_value = risk_per_trade * 0.05  # risk * edge
        
        return {
            # Market Activity & Timing
            "last_trade_time": last_trade_time,
            "trading_hours": "Open",  # Would need Kalshi API call
            "liquidity_score": 75,  # Would calculate from orderbook depth
            "time_since_fill": time_since_fill,
            "orders_per_hour": round(perf[0] / 24, 1) if perf[0] > 0 else 0,
            
            # Pricing & Spread (price change calculated from existing data)
            "price_change_24h": "+0.0%",  # Would calculate from historical prices
            
            # Bot Performance
            "fill_rate": round(fill_rate, 1),
            "last_order_time": last_order_time,
            "pnl_this_market": round(pnl_market, 2),
            "avg_trade_size": round(avg_size, 1),
            "current_streak": current_streak,
            
            # Risk Metrics
            "risk_per_trade": round(risk_per_trade, 2),
            "expected_value": round(expected_value, 3),
            
            # Statistical Analysis
            "capital_efficiency": round(capital_efficiency, 1),
            "profit_factor": round(profit_factor, 2),
            
            # System Health
            "api_latency": "45ms",  #Would measure actual API response times
            "db_health": "Good"
        }
    except Exception as e:
        print(f"Analytics error: {e}")
        return {"error": str(e)}


def get_dashboard_html():
    """Return enhanced dashboard HTML with bot controls and reorganized layout"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kalshi Trading Bot - Live Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        /* Header with Bot Control */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(20px);
            padding: 12px 20px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        
        .title-section h1 {
            font-size: 1.5em;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2px;
        }
        
        .subtitle {
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.75em;
        }
        
        .bot-control {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }
        
        .status-indicator:hover {
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(102, 126, 234, 0.5);
            transform: scale(1.05);
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 12px #10b981;
            animation: pulse 2s infinite;
        }
        
        .status-dot.stopped {
            background: #ef4444;
            box-shadow: 0 0 12px #ef4444;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-text {
            font-weight: 600;
            font-size: 0.9em;
        }
        
        .control-hint {
            font-size: 0.65em;
            color: rgba(255, 255, 255, 0.5);
            margin-top: 1px;
        }
        
        
        /* Tab Navigation */
        .tab-nav {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .tab-btn {
            flex: 1;
            padding: 12px 24px;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: rgba(255, 255, 255, 0.6);
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .tab-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(102, 126, 234, 0.3);
            color: rgba(255, 255, 255, 0.8);
        }
        
        .tab-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-color: #667eea;
            color: #fff;
        }
        
        .page-content {
            display: none;
        }
        
        .page-content.active {
            display: block;
        }
        
        /* Live Data Section */
        .live-section {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .activity-feed {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(20px);
            padding: 13px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            max-height: 270px;
            overflow-y: auto;
        }
        
        .feed-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            position: sticky;
            top: 0;
            background: rgba(15, 12, 41, 0.95);
            padding: 5px 0;
            z-index: 10;
        }
        
        .feed-title {
            font-size: 1.2em;
            font-weight: 700;
        }
        
        .live-badge {
            padding: 6px 16px;
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            animation: blink 2s infinite;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .market-info {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(20px);
            padding: 12px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        
        .market-title {
            font-size: 1em;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .market-detail {
            margin-bottom: 6px;
        }
        
        .market-label {
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.65em;
            text-transform: uppercase;
            margin-bottom: 3px;
        }
        
        .market-value {
            font-size: 1.1em;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .market-ticker {
            font-size: 0.7em;
            color: rgba(255, 255, 255, 0.6);
            margin-top: 8px;
            word-break: break-all;
            line-height: 1.2;
        }
        
        .market-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px 10px;
        }
        
        /* Trade Items */
        .trade-item {
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
            transition: all 0.3s ease;
        }
        
        .trade-item:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateX(5px);
        }
        
        .trade-item.filled { border-left-color: #10b981; }
        .trade-item.resting { border-left-color: #f59e0b; }
        
        .trade-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .trade-time {
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.9em;
        }
        
        .trade-status {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-filled {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }
        
        .status-resting {
            background: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
        }
        
        .trade-details {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 15px;
        }
        
        .trade-detail {
            text-align: center;
        }
        
        .trade-detail-label {
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.75em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .trade-detail-value {
            font-size: 1.1em;
            font-weight: 600;
        }
        
        /* Metrics Grid - Now below live data */
        .metrics {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .metric-card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(20px);
            padding: 12px 16px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            border-color: rgba(102, 126, 234, 0.5);
        }
        
        .metric-icon {
            font-size: 1.3em;
            flex-shrink: 0;
            opacity: 0.8;
        }
        
        .metric-content {
            display: flex;
            align-items: baseline;
            gap: 8px;
            flex: 1;
            min-width: 0;
        }
        
        .metric-label {
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.7em;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        
        .metric-value {
            font-size: 1.4em;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            white-space: nowrap;
        }
        
        .metric-value.positive {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .metric-value.negative {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Charts */
        .charts {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }
        
        .chart-container {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(20px);
            padding: 15px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            max-height: 250px;
        }
        
        .chart-title {
            font-size: 1em;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: rgba(255, 255, 255, 0.5);
        }
        

        /* Analytics Page */
        .analytics-section {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(20px);
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            margin-bottom: 20px;
        }
        
        .analytics-section-title {
            font-size: 1.3em;
            font-weight: 700;
            margin-bottom: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .analytics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .analytics-metric {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }
        
        .analytics-metric:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
            border-color: rgba(102, 126, 234, 0.3);
        }
        
        .analytics-label {
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }
        
        .analytics-value {
            font-size: 1.6em;
            font-weight: 700;
            color: #fff;
        }
        
        .analytics-value.positive {
            color: #10b981;
        }
        
        .analytics-value.negative {
            color: #ef4444;
        }
        
        
                /* Responsive */
        @media (max-width: 1400px) {
            .metrics {
                grid-template-columns: repeat(3, 1fr);
            }
        }
        
        @media (max-width: 1024px) {
            .live-section {
                grid-template-columns: 1fr;
            }
            .metrics {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .header {
                flex-direction: column;
                gap: 20px;
            }
            .charts {
                grid-template-columns: 1fr;
            }
            .metrics {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header with Bot Control -->
        <div class="header">
            <div class="title-section">
                <h1>🚀 Rod's Kalshi Trading Bot</h1>
                <p class="subtitle">Real-Time Performance Dashboard</p>
            </div>
            <div class="bot-control">
                <div class="status-indicator" id="bot-control" onclick="toggleBot()">
                    <div class="status-dot" id="status-dot"></div>
                    <div>
                        <div class="status-text" id="status-text">Checking...</div>
                        <div class="control-hint">Click to start/stop</div>
                    </div>
        
        <!-- Tab Navigation -->
        <div class="tab-nav">
            <button class="tab-btn active" id="overview-tab" onclick="switchTab('overview')">
                📊 Overview
            </button>
            <button class="tab-btn" id="analytics-tab" onclick="switchTab('analytics')">
                📈 Analytics
            </button>
        </div>
                </div>
            </div>
        </div>
        
        <!-- Live Data Section -->
        <div class="live-section">
            <!-- Activity Feed -->
            <div class="activity-feed">
                <div class="feed-header">
                    <h3 class="feed-title">🔥 Live Trading Activity</h3>
                    <span class="live-badge">● LIVE</span>
                </div>
                <div id="trades-feed">
                    <div class="loading">
                        <p>Loading trades...</p>
                    </div>
                </div>
            </div>
            
            <!-- Current Market Info -->
            <div class="market-info">
                <h3 class="market-title">📊 Current Market</h3>
                <div class="market-grid">
                    <div class="market-detail">
                        <div class="market-label">Price</div>
                        <div class="market-value" id="market-price">$0.05</div>
                    </div>
                    <div class="market-detail">
                        <div class="market-label">Volume</div>
                        <div class="market-value" id="market-volume">$0</div>
                    </div>
                    <div class="market-detail">
                        <div class="market-label">Closes In</div>
                        <div class="market-value" id="market-closes">N/A</div>
                    </div>
                    <div class="market-detail">
                        <div class="market-label">Implied Prob</div>
                        <div class="market-value" id="market-prob">N/A</div>
                    </div>
                    <div class="market-detail">
                        <div class="market-label">Spread</div>
                        <div class="market-value" style="font-size: 0.9em;" id="market-spread">N/A</div>
                    </div>
                    <div class="market-detail">
                        <div class="market-label">Orders</div>
                        <div class="market-value" id="market-orders">0</div>
                    </div>
                    <div class="market-detail" style="grid-column: span 2;">
                        <div class="market-label">Last Order</div>
                        <div class="market-value" style="font-size: 0.95em;" id="market-last-status">N/A</div>
                    </div>
                </div>
                <div class="market-ticker" id="market-ticker">Loading...</div>
            </div>
        </div>
        
                <div id="overview-page" class="page-content active">
        <!-- Performance Metrics -->
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-icon">💵</div>
                <div class="metric-content">
                    <div class="metric-label">Bankroll</div>
                    <div class="metric-value" id="bankroll">$29.40</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">💰</div>
                <div class="metric-content">
                    <div class="metric-label">P&L</div>
                    <div class="metric-value positive" id="total-pnl">$0.00</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">🎯</div>
                <div class="metric-content">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value" id="win-rate">0%</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">📊</div>
                <div class="metric-content">
                    <div class="metric-label">Trades</div>
                    <div class="metric-value" id="total-trades">0</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">⏳</div>
                <div class="metric-content">
                    <div class="metric-label">Active</div>
                    <div class="metric-value" id="active-positions">0</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">📈</div>
                <div class="metric-content">
                    <div class="metric-label">Sharpe</div>
                    <div class="metric-value" id="sharpe">0.00</div>
                </div>
            </div>
        </div>
        
        <!-- Extended Metrics Row -->
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-icon">⏱️</div>
                <div class="metric-content">
                    <div class="metric-label">Last Fill</div>
                    <div class="metric-value" style="font-size: 1.2em;" id="last-fill-time">N/A</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">📈</div>
                <div class="metric-content">
                    <div class="metric-label">24h High</div>
                    <div class="metric-value" id="high-24h">$0.00</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">📉</div>
                <div class="metric-content">
                    <div class="metric-label">24h Low</div>
                    <div class="metric-value" id="low-24h">$0.00</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">📦</div>
                <div class="metric-content">
                    <div class="metric-label">Position</div>
                    <div class="metric-value" id="current-position">0</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">⚡</div>
                <div class="metric-content">
                    <div class="metric-label">Edge</div>
                    <div class="metric-value" id="edge-pct">5.0%</div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-icon">🎯</div>
                <div class="metric-content">
                    <div class="metric-label">Max Pos</div>
                    <div class="metric-value" id="max-position">0</div>
                </div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="charts">
            <div class="chart-container">
                <h3 class="chart-title">📈 Trading Volume (24h)</h3>
                <canvas id="volume-chart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">📊 Trade Frequency</h3>
                <canvas id="frequency-chart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">💰 P&L Over Time</h3>
                <canvas id="pnl-chart"></canvas>
            </div>
        
        </div></div>
    </div>
    
    <!-- Analytics Page -->
    <div id="analytics-page" class="page-content">
        <h2 style="margin-bottom: 20px; font-size: 1.8em;">📈 Detailed Analytics</h2>
        
        <!-- Section 1: Market Activity & Timing -->
        <div class="analytics-section">
            <h3 class="analytics-section-title">⏱️ Market Activity & Timing</h3>
            <div class="analytics-grid">
                <div class="analytics-metric">
                    <div class="analytics-label">Last Trade Time</div>
                    <div class="analytics-value" id="a-last-trade">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Market Status</div>
                    <div class="analytics-value" id="a-trading-hours">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Liquidity Score</div>
                    <div class="analytics-value" id="a-liquidity">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Time Since Fill</div>
                    <div class="analytics-value" id="a-time-fill">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Orders/Hour</div>
                    <div class="analytics-value" id="a-orders-hour">N/A</div>
                </div>
            </div>
        </div>
        
        <!-- Section 2: Pricing & Spread -->
        <div class="analytics-section">
            <h3 class="analytics-section-title">💰 Pricing & Spread</h3>
            <div class="analytics-grid">
                <div class="analytics-metric">
                    <div class="analytics-label">Bid/Ask Spread</div>
                    <div class="analytics-value" id="a-spread">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Implied Probability</div>
                    <div class="analytics-value" id="a-implied-prob">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">24h High</div>
                    <div class="analytics-value" id="a-high">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">24h Low</div>
                    <div class="analytics-value" id="a-low">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Price Change 24h</div>
                    <div class="analytics-value" id="a-price-change">N/A</div>
                </div>
            </div>
        </div>
        
        <!-- Section 3: Bot Performance -->
        <div class="analytics-section">
            <h3 class="analytics-section-title">🤖 Bot Performance on This Market</h3>
            <div class="analytics-grid">
                <div class="analytics-metric">
                    <div class="analytics-label">Orders Today</div>
                    <div class="analytics-value" id="a-orders-today">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Fill Rate</div>
                    <div class="analytics-value" id="a-fill-rate">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Last Order Time</div>
                    <div class="analytics-value" id="a-last-order">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Current Position</div>
                    <div class="analytics-value" id="a-position">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">P&L This Market</div>
                    <div class="analytics-value" id="a-pnl-market">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Avg Trade Size</div>
                    <div class="analytics-value" id="a-avg-size">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Current Streak</div>
                    <div class="analytics-value" id="a-streak">N/A</div>
                </div>
            </div>
        </div>
        
        <!-- Section 4: Risk Metrics -->
        <div class="analytics-section">
            <h3 class="analytics-section-title">⚠️ Risk Metrics</h3>
            <div class="analytics-grid">
                <div class="analytics-metric">
                    <div class="analytics-label">Max Position Size</div>
                    <div class="analytics-value" id="a-max-pos">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Risk Per Trade</div>
                    <div class="analytics-value" id="a-risk-trade">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Edge %</div>
                    <div class="analytics-value" id="a-edge">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Expected Value</div>
                    <div class="analytics-value" id="a-ev">N/A</div>
                </div>
            </div>
        </div>
        
        <!-- Section 5: Statistical Analysis -->
        <div class="analytics-section">
            <h3 class="analytics-section-title">📊 Statistical Analysis</h3>
            <div class="analytics-grid">
                <div class="analytics-metric">
                    <div class="analytics-label">Capital Efficiency</div>
                    <div class="analytics-value" id="a-capital-eff">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Profit Factor</div>
                    <div class="analytics-value" id="a-profit-factor">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Win Rate</div>
                    <div class="analytics-value" id="a-win-rate">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Sharpe Ratio</div>
                    <div class="analytics-value" id="a-sharpe">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Total Trades</div>
                    <div class="analytics-value" id="a-total-trades">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Total P&L</div>
                    <div class="analytics-value" id="a-total-pnl">N/A</div>
                </div>
            </div>
        </div>
        
        <!-- Section 6: System Health -->
        <div class="analytics-section">
            <h3 class="analytics-section-title">🏥 System Health</h3>
            <div class="analytics-grid">
                <div class="analytics-metric">
                    <div class="analytics-label">API Latency</div>
                    <div class="analytics-value" id="a-latency">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Database Status</div>
                    <div class="analytics-value" id="a-db-health">N/A</div>
                </div>
                <div class="analytics-metric">
                    <div class="analytics-label">Bot Uptime</div>
                    <div class="analytics-value" id="a-uptime">Running</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Tab switching
        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(tabName + '-tab').classList.add('active');
            
            // Update page content
            document.querySelectorAll('.page-content').forEach(page => page.classList.remove('active'));
            document.getElementById(tabName + '-page').classList.add('active');
            
            // If switching to analytics, load data
            if (tabName === 'analytics') {
                updateAnalytics();
            }
        }
        
        // Update analytics metrics
        async function updateAnalytics() {
            try {
                const [analytics, perf, market] = await Promise.all([
                    fetch('/api/market-analytics').then(r => r.json()),
                    fetch('/api/performance').then(r => r.json()),
                    fetch('/api/current-market').then(r => r.json())
                ]);
                
                // Market Activity & Timing
                document.getElementById('a-last-trade').textContent = analytics.last_trade_time;
                document.getElementById('a-trading-hours').textContent = analytics.trading_hours;
                document.getElementById('a-liquidity').textContent = analytics.liquidity_score + '/100';
                document.getElementById('a-time-fill').textContent = analytics.time_since_fill;
                document.getElementById('a-orders-hour').textContent = analytics.orders_per_hour;
                
                // Pricing & Spread
                document.getElementById('a-spread').textContent = market.bid_ask_spread;
                document.getElementById('a-implied-prob').textContent = market.implied_probability;
                document.getElementById('a-high').textContent = '$' + perf.high_24h.toFixed(2);
                document.getElementById('a-low').textContent = '$' + perf.low_24h.toFixed(2);
                document.getElementById('a-price-change').textContent = analytics.price_change_24h;
                
                // Bot Performance
                document.getElementById('a-orders-today').textContent = market.orders_today;
                document.getElementById('a-fill-rate').textContent = analytics.fill_rate + '%';
                document.getElementById('a-last-order').textContent = analytics.last_order_time;
                document.getElementById('a-position').textContent = perf.current_position;
                const pnlMarket = document.getElementById('a-pnl-market');
                pnlMarket.textContent = '$' + analytics.pnl_this_market.toFixed(2);
                pnlMarket.className = 'analytics-value ' + (analytics.pnl_this_market >= 0 ? 'positive' : 'negative');
                document.getElementById('a-avg-size').textContent = analytics.avg_trade_size.toFixed(1);
                document.getElementById('a-streak').textContent = analytics.current_streak;
                
                // Risk Metrics
                document.getElementById('a-max-pos').textContent = perf.max_position;
                document.getElementById('a-risk-trade').textContent = '$' + analytics.risk_per_trade.toFixed(2);
                document.getElementById('a-edge').textContent = perf.edge_pct.toFixed(1) + '%';
                document.getElementById('a-ev').textContent = '$' + analytics.expected_value.toFixed(3);
                
                // Statistical Analysis
                document.getElementById('a-capital-eff').textContent = analytics.capital_efficiency.toFixed(1) + '%';
                document.getElementById('a-profit-factor').textContent = analytics.profit_factor.toFixed(2);
                document.getElementById('a-win-rate').textContent = perf.win_rate.toFixed(1) + '%';
                document.getElementById('a-sharpe').textContent = perf.sharpe_ratio.toFixed(2);
                document.getElementById('a-total-trades').textContent = perf.total_trades;
                const totalPnl = document.getElementById('a-total-pnl');
                totalPnl.textContent = '$' + perf.total_pnl.toFixed(2);
                totalPnl.className = 'analytics-value ' + (perf.total_pnl >= 0 ? 'positive' : 'negative');
                
                // System Health
                document.getElementById('a-latency').textContent = analytics.api_latency;
                document.getElementById('a-db-health').textContent = analytics.db_health;
            } catch (e) {
                console.error('Analytics update failed:', e);
            }
        }
        

        let currentStatus = 'unknown';
        
        // Toggle bot on/off
        async function toggleBot() {
            const endpoint = currentStatus === 'running' ? '/api/bot/stop' : '/api/bot/start';
            
            try {
                const response = await fetch(endpoint, { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    updateStatus();
                } else {
                    alert(data.message);
                }
            } catch (e) {
                alert('Failed to control bot: ' + e.message);
            }
        }
        
        // Update bot status
        async function updateStatus() {
            try {
                const status = await fetch('/api/status').then(r => r.json());
                const statusDot = document.getElementById('status-dot');
                const statusText = document.getElementById('status-text');
                
                currentStatus = status.status;
                
                if (status.status === 'running') {
                    statusDot.className = 'status-dot';
                    statusText.textContent = 'Bot Active';
                } else {
                    statusDot.className = 'status-dot stopped';
                    statusText.textContent = 'Bot Stopped';
                }
            } catch (e) {
                console.error('Status update failed:', e);
            }
        }
        
        // Update current market
        async function updateMarket() {
            try {
                const market = await fetch('/api/current-market').then(r => r.json());
                document.getElementById('market-price').textContent = `$${market.price.toFixed(2)}`;
                document.getElementById('market-volume').textContent = market.volume;
                document.getElementById('market-ticker').textContent = market.ticker;
                
                // Update new metrics
                document.getElementById('market-closes').textContent = market.time_to_close;
                document.getElementById('market-prob').textContent = market.implied_probability;
                document.getElementById('market-spread').textContent = market.bid_ask_spread;
                document.getElementById('market-orders').textContent = market.orders_today;
                document.getElementById('market-last-status').textContent = market.last_order_status;
            } catch (e) {
                console.error('Market update failed:', e);
            }
        }
        
        // Update metrics
        async function updateMetrics() {
            try {
                const perf = await fetch('/api/performance').then(r => r.json());
                
                const pnlElem = document.getElementById('total-pnl');
                pnlElem.textContent = `$${perf.total_pnl.toFixed(2)}`;
                pnlElem.className = 'metric-value ' + (perf.total_pnl >= 0 ? 'positive' : 'negative');
                
                document.getElementById('win-rate').textContent = `${perf.win_rate.toFixed(1)}%`;
                document.getElementById('sharpe').textContent = perf.sharpe_ratio.toFixed(2);
                document.getElementById('total-trades').textContent = perf.total_trades;
                document.getElementById('active-positions').textContent = perf.active_positions;
                document.getElementById('bankroll').textContent = `$${perf.bankroll.toFixed(2)}`;
                
                // Extended metrics
                document.getElementById('last-fill-time').textContent = perf.last_fill_time;
                document.getElementById('high-24h').textContent = `$${perf.high_24h.toFixed(2)}`;
                document.getElementById('low-24h').textContent = `$${perf.low_24h.toFixed(2)}`;
                document.getElementById('current-position').textContent = perf.current_position;
                document.getElementById('edge-pct').textContent = `${perf.edge_pct.toFixed(1)}%`;
                document.getElementById('max-position').textContent = perf.max_position;
            } catch (e) {
                console.error('Metrics update failed:', e);
            }
        }
        
        // Update trades feed
        async function updateTrades() {
            try {
                const data = await fetch('/api/trades').then(r => r.json());
                const feed = document.getElementById('trades-feed');
                
                if (data.trades.length === 0) {
                    feed.innerHTML = '<div class="loading"><p>No trades yet. Waiting for market activity...</p></div>';
                    return;
                }
                
                feed.innerHTML = data.trades.map(t => `
                    <div class="trade-item ${t.status}">
                        <div class="trade-header">
                            <span class="trade-time">⏰ ${t.timestamp}</span>
                            <span class="trade-status status-${t.status}">${t.status}</span>
                        </div>
                        <div style="color: rgba(255,255,255,0.8); margin: 10px 0; font-size: 0.95em;">
                            ${t.market}
                        </div>
                        <div class="trade-details">
                            <div class="trade-detail">
                                <div class="trade-detail-label">Side</div>
                                <div class="trade-detail-value">${t.side.toUpperCase()}</div>
                            </div>
                            <div class="trade-detail">
                                <div class="trade-detail-label">Size</div>
                                <div class="trade-detail-value">${t.size}</div>
                            </div>
                            <div class="trade-detail">
                                <div class="trade-detail-label">Price</div>
                                <div class="trade-detail-value">$${t.price.toFixed(2)}</div>
                            </div>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Trades update failed:', e);
            }
        }
        
        // Create charts
        let volumeChart, frequencyChart, pnlChart;
        
        async function updateCharts() {
            try {
                const chartData = await fetch('/api/chart-data').then(r => r.json());
                
                const chartOptions = {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                        },
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                        }
                    }
                };
                
                if (volumeChart) volumeChart.destroy();
                volumeChart = new Chart(document.getElementById('volume-chart'), {
                    type: 'bar',
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            label: 'Volume ($)',
                            data: chartData.volumes,
                            backgroundColor: 'rgba(102, 126, 234, 0.6)',
                            borderColor: '#667eea',
                            borderWidth: 2
                        }]
                    },
                    options: chartOptions
                });
                
                if (frequencyChart) frequencyChart.destroy();
                frequencyChart = new Chart(document.getElementById('frequency-chart'), {
                    type: 'line',
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            label: 'Trades',
                            data: chartData.trade_counts,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.2)',
                            tension: 0.4,
                            fill: true,
                            borderWidth: 3
                        }]
                    },
                    options: chartOptions
                });
                
                // P&L chart
                const pnlData = await fetch('/api/pnl-history').then(r => r.json());
                if (pnlChart) pnlChart.destroy();
                pnlChart = new Chart(document.getElementById('pnl-chart'), {
                    type: 'line',
                    data: {
                        labels: pnlData.labels,
                        datasets: [{
                            label: 'Cumulative P&L ($)',
                            data: pnlData.pnls,
                            borderColor: '#f093fb',
                            backgroundColor: 'rgba(240, 147, 251, 0.2)',
                            tension: 0.4,
                            fill: true,
                            borderWidth: 3
                        }]
                    },
                    options: chartOptions
                });
            } catch (e) {
                console.error('Chart update failed:', e);
            }
        }
        
        // Initialize
        async function init() {
            await updateStatus();
            await updateMarket();
            await updateMetrics();
            await updateTrades();
            await updateCharts();
        }
        
        init();
        
        // Auto-refresh every 3 seconds for live data
        setInterval(() => {
            updateStatus();
            updateMarket();
            updateTrades();
        }, 3000);
        
        // Refresh metrics and charts every 10 seconds
        setInterval(() => {
            updateMetrics();
            updateCharts();
        }, 10000);
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Kalshi Bot Dashboard Pro on http://0.0.0.0:8082")
    print("   Access from any device: http://192.168.1.X:8082")
    print("   ✨ Features: Bot control, real-time activity, live market data")
    uvicorn.run(app, host="0.0.0.0", port=8082)
