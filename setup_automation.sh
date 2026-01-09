#!/bin/bash
# Setup automated trading schedule for Kalshi bot
# This script configures cron jobs for continuous operation

set -e

BOT_DIR="/Users/rod/Antigravity/kalshi_bot"

echo "🤖 Setting up Kalshi Bot Automation"
echo "===================================="
echo ""

# Check if running on Aragorn
if [ "$(hostname)" != "Aragorn.local" ] && [ "$(hostname)" != "Aragorn" ]; then
    echo "⚠️  Warning: Expected to run on Aragorn, current host: $(hostname)"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Backup existing crontab
echo "📋 Backing up existing crontab..."
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || echo "No existing crontab"

# Create new cron entries
CRON_ENTRIES="
# Kalshi Trading Bot - Automated Schedule
# Added: $(date '+%Y-%m-%d %H:%M:%S')

# Daily market scan and bot restart (9 AM Eastern)
0 9 * * * cd $BOT_DIR && ./daily_scan.sh >> $BOT_DIR/logs/daily_scan.log 2>&1 && pkill -f bot_v3.py; sleep 3; nohup python3 -u $BOT_DIR/bot_v3.py > $BOT_DIR/logs/trading_\$(date +\\%Y\\%m\\%d).log 2>&1 &

# Auto-restart if bot halted during peak hours (hourly check 6 PM - 11 PM Eastern)
0 18-23 * * * pgrep -f bot_v3.py > /dev/null || (cd $BOT_DIR && nohup python3 -u $BOT_DIR/bot_v3.py >> $BOT_DIR/logs/trading_\$(date +\\%Y\\%m\\%d).log 2>&1 &)

# Optional: Auto-stop after midnight (cleanup for next day)
0 0 * * * pkill -f bot_v3.py
"

# Create logs directory
mkdir -p "$BOT_DIR/logs"

# Ask for confirmation
echo ""
echo "The following cron jobs will be added:"
echo "----------------------------------------"
echo "$CRON_ENTRIES"
echo "----------------------------------------"
echo ""
echo "Summary:"
echo "  • 9:00 AM  - Daily market scan + bot restart with fresh target"
echo "  • 6-11 PM  - Hourly check: restart bot if halted during peak hours"
echo "  • 12:00 AM - Stop bot for daily reset"
echo ""
read -p "Install these cron jobs? (y/n) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Installation cancelled"
    exit 1
fi

# Install cron jobs
echo ""
echo "📦 Installing cron jobs..."

# Get existing crontab (excluding old Kalshi entries)
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -v "Kalshi Trading Bot" | grep -v "daily_scan.sh" | grep -v "bot_v3.py" || true)

# Combine and install
{
    echo "$EXISTING_CRON"
    echo "$CRON_ENTRIES"
} | crontab -

echo "✅ Cron jobs installed!"
echo ""

# Verify installation
echo "📋 Current crontab:"
echo "----------------------------------------"
crontab -l | grep -A 20 "Kalshi Trading Bot" || echo "Error: Could not verify installation"
echo "----------------------------------------"
echo ""

# Test daily_scan.sh is executable
if [ ! -x "$BOT_DIR/daily_scan.sh" ]; then
    echo "⚠️  Making daily_scan.sh executable..."
    chmod +x "$BOT_DIR/daily_scan.sh"
fi

# Test gameday_prep.sh is executable
if [ ! -x "$BOT_DIR/gameday_prep.sh" ]; then
    echo "⚠️  Making gameday_prep.sh executable..."
    chmod +x "$BOT_DIR/gameday_prep.sh"
fi

echo ""
echo "===================================="
echo "✅ Setup Complete!"
echo "===================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Start bot now (optional):"
echo "   cd $BOT_DIR"
echo "   nohup python3 -u bot_v3.py > logs/trading_\$(date +%Y%m%d).log 2>&1 &"
echo ""
echo "2. Monitor bot status:"
echo "   tail -f $BOT_DIR/logs/trading_\$(date +%Y%m%d).log"
echo ""
echo "3. Check if bot is running:"
echo "   ps aux | grep bot_v3"
echo ""
echo "4. View cron schedule:"
echo "   crontab -l"
echo ""
echo "5. Remove automation (if needed):"
echo "   crontab -e  # then delete the Kalshi entries"
echo ""
echo "The bot will now:"
echo "  • Scan for best markets daily at 9 AM"
echo "  • Auto-restart if it halts during 6-11 PM"
echo "  • Stop at midnight for daily reset"
echo ""
