#!/bin/bash
# Simple cron installer for Kalshi bot
cd "$(dirname "$0")"

echo "📦 Installing Kalshi Bot Automation..."
echo ""

# Create logs directory
mkdir -p logs

# Backup existing crontab if it exists
crontab -l > crontab_backup.txt 2>/dev/null && echo "✅ Backed up existing crontab to crontab_backup.txt" || echo "ℹ️  No existing crontab to backup"

# Install from file
cat kalshi_crontab.txt | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron jobs installed successfully!"
    echo ""
    echo "Scheduled tasks:"
    echo "  • 9:00 AM  - Daily market scan + bot restart"
    echo "  • 6-11 PM  - Hourly auto-restart if halted"
    echo "  • 12:00 AM - Stop bot for daily reset"
    echo ""
    echo "View crontab: crontab -l"
    echo "Remove crontab: crontab -r"
else
    echo "❌ Failed to install cron jobs"
    exit 1
fi
