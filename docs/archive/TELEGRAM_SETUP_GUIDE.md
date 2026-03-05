# 📱 Telegram Bot Setup & Usage Guide

**Status**: ✅ Complete with Interactive Help & Pro Tips  
**Last Updated**: March 5, 2026  
**Bot Version**: Phase 3+ Enhanced

---

## Table of Contents

1. [🚀 Quick Start](#quick-start)
2. [⚙️ Configuration](#configuration)
3. [📚 Command Reference](#command-reference)
4. [💡 Tips & Best Practices](#tips--best-practices)  
5. [🔄 Common Workflows](#common-workflows)
6. [🆘 Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Step 1: Get Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Choose a name (e.g., "My Trading Bot")
4. Choose a unique username (e.g., "MyTrading_bot")
5. Copy the **API Token** provided

### Step 2: Get Your Chat ID

**Method A: Using Bot**
1. Start a conversation with your bot (click username from BotFather)
2. Send any message
3. Check bot logs: Look for `chat_id` in output
4. Or visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`

**Method B: Using @userinfobot**
1. Search for **@userinfobot** on Telegram
2. Start chat with it - it will show your User ID
3. Use this as your chat ID

### Step 3: Configure Environment

Edit `.env` file with Telegram settings:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=<paste_your_token_here>          # From BotFather
TELEGRAM_ADMIN_IDS=<your_chat_id>,<other_admin_ids>  # Comma-separated
TELEGRAM_TRADER_IDS=<trader_ids>                      # Comma-separated
```

**Example:**
```bash
TELEGRAM_BOT_TOKEN=5831245678:ABEfXyZ_1234567890abc
TELEGRAM_ADMIN_IDS=123456789,987654321
TELEGRAM_TRADER_IDS=111111111,222222222
```

### Step 4: Start the Bot

**Terminal 1: Start Bot Worker**
```bash
(.venv) $ python -m apps.telegram.main
# Output: telegram_worker_running
```

**Terminal 2: Start Backend API** (if not already running)
```bash
(.venv) $ python -m apps.api.main
# API available at http://localhost:8000
```

**Terminal 3: Start Backend Worker** (if not already running)
```bash
(.venv) $ python -m apps.worker.main_phase2
# Worker: executing phase 2 trading loop
```

### Step 5: Test the Bot

Send `/help` to your bot on Telegram - you should see:
- Interactive menu with command categories
- Your assigned role
- Available actions based on your permissions

✅ **You're ready to go!**

---

## ⚙️ Configuration

### Role-Based Access Control (RBAC)

Your role determines what commands you can run:

| Feature | Admin | Trader | Viewer |
|---------|:-----:|:------:|:------:|
| View Health/Time | ✅ | ✅ | ✅ |
| View Market Data | ✅ | ✅ | ✅ |
| View Trading State | ✅ | ✅ | ✅ |
| Pause/Resume Trading | ✅ | ✅ | ❌ |
| Close Positions | ✅ | ✅ | ❌ |
| Emergency Close All | ✅ | ✅ | ❌ |
| Force Reconciliation | ✅ | ❌ | ❌ |
| View Audit Logs | ✅ | ❌ | ❌ |

**How to Change Roles:**
1. Contact your admin to adjust your role
2. Admin updates `.env` and restarts bot
3. Changes take effect immediately

### Configuration Environment

The bot automatically detects your trading environment:

```bash
# Check your environment
/settings
# Shows: TESTNET ✅ or MAINNET 🔴
```

⚠️ **Important:**
- **TESTNET** ✅: Practice mode, no real money
- **MAINNET** 🔴: Real money trading - be careful!

---

## 📚 Command Reference

### 🏥 Health & Time Commands

#### `/time` - System Time & Uptime
```
Usage: /time
Response: Current UTC time, environment, last bot tick
Purpose: Verify bot is running and synchronized
Tip: Run daily to check system is responsive
```

#### `/latency` - Network Performance
```
Usage: /latency
Response: WebSocket P95, REST P95, clock skew, network status
Purpose: Monitor connection quality
Tip: High latency (>200ms) = slower order execution
```

#### `/health` - System Status
```
Usage: /health
Response: Status of WebSocket, REST, Database, Circuit Breaker, Worker
Purpose: Troubleshoot when bot isn't responding
Tip: Check this first if something seems wrong! 🔧
```

---

### 💰 Market Data Commands

#### `/price SYMBOL` - Current Price
```
Usage: /price BTCUSDT
Examples:
  /price ETHUSDT
  /price BNBUSDT
Response: Current price, 24h change %, last update time
Purpose: Quick market check
Tip: Check before making trading decisions
```

#### `/spread SYMBOL` - Bid/Ask Spread
```
Usage: /spread BTCUSDT
Examples:
  /spread ETHUSDT
  /spread BNBUSDT
Response: Current bid, ask, spread %, network time
Purpose: Gauge market liquidity
Tip: Tight spread = good execution, wide = slippage risk
```

#### `/kline SYMBOL INTERVAL COUNT` - Candlestick Data
```
Usage: /kline BTCUSDT 1m 60
Parameters:
  - SYMBOL: Trading pair (BTCUSDT, ETHUSDT, etc.)
  - INTERVAL: 1m, 5m, 15m, 1h, 4h, 1d
  - COUNT: Number of candles (1-500)

Examples:
  /kline BTCUSDT 1m 60      → Last 60 minutes
  /kline ETHUSDT 5m 24      → Last 2 hours (5-min)
  /kline BNBUSDT 1h 72      → Last 3 days (1-hour)

Response: OHLCV data for last N candles
Purpose: Technical analysis
Tip: Use for trend confirmation before trading
```

---

### 📊 Trading State Commands

#### `/status` - Bot Trading Status
```
Usage: /status
Response: Environment, active position count, open order count
Purpose: Quick overview
Tip: Check this before pausing/resuming
```

#### `/positions` - Open Positions
```
Usage: /positions
Response: All open positions with:
  - Symbol (e.g., BTCUSDT)
  - Quantity held
  - Entry price
  - Unrealized P&L
Purpose: See all current exposure
Tip: Always check this before closing trades!
```

#### `/orders` - Open Orders
```
Usage: /orders
Response: All pending orders with:
  - Symbol
  - Side (BUY/SELL)
  - Quantity
  - Price
  - Status
Purpose: See unfilled orders
Tip: Cancel old orders if they're not needed
```

#### `/recon` - Reconciliation Status
```
Usage: /recon
Response: Last synchronization time, mismatch count, sync status
Purpose: Verify database matches Binance
Tip: Should show "All systems in sync" ✅
```

#### `/decision` - Latest AI Decision
```
Usage: /decision
Response: Latest decision with:
  - Symbol (e.g., BTCUSDT)
  - Action (BUY/SELL/HOLD)
  - Confidence (0.0-1.0)
  - Regime (uptrend/downtrend/neutral)
  - Trace ID for deep dive
Purpose: Understand what AI decided
Tip: Review decision before critical actions
```

#### `/trace TRACE_ID` - Decision Deep Dive
```
Usage: /trace abc123def456
Response: Full decision logic, parameters, calculations
Purpose: Understand why AI made that decision
Tip: Use when results are unexpected
```

---

### ⚙️ Control Commands (Traders + Admins)

#### `/pause` - Stop Trading
```
Usage: /pause
Response: "⏸️ Trading paused"
Effect: No new orders will be placed
Wait Time: Usually takes 1-2 seconds
Recovery: Use /resume to continue
Tip: Pause before market news/events
```

#### `/resume` - Resume Trading
```
Usage: /resume
Response: "▶️ Trading resumed"
Effect: Bot will start placing orders again
Wait Time: Ready immediately
Caution: Check /decision first!
Tip: Wait 5 seconds after /pause before resuming
```

#### `/close_position SYMBOL` - Close One Position
```
Usage: /close_position BTCUSDT
Examples:
  /close_position ETHUSDT
  /close_position LTCUSDT

Response: Confirmation prompt (2-step)
Step 1: Send command → receives buttons
Step 2: Tap ✅ Confirm button to execute
Effect: Position closes at market price

⚠️ Confirmation Required: Yes
Tip: Check current price first with /price before closing!
```

#### `/close_all` - Emergency Close All
```
Usage: /close_all
Response: Confirmation prompt (2-step)
Step 1: Send command → receives buttons
Step 2: Tap ✅ Confirm button to execute
Effect: ALL open positions close immediately at market price

⚠️⚠️ WARNING: Irreversible! Use only in emergencies
Tip: Check /positions first to see what will close
```

---

### 🔐 Admin-Only Commands

#### `/sync_now` - Force Reconciliation
```
Usage: /sync_now
Response: "🔄 Sync initiated - reconciling..."
Timing: Takes 10-30 seconds
Effect: Forces immediate sync with Binance
Purpose: Resolve mismatches after market events
Tip: Run after system restarts or unusual gaps
```

---

### 🆕 Utility Commands (All Roles)

#### `/help` - Interactive Command Guide
```
Usage: /help
Response: Interactive menu with command categories
Features:
  - Tap category buttons to see details
  - Each button shows examples & tips
  - Tap "← Back" to return to main menu
Purpose: Discover and learn commands
Tip: Use this when you forget how to use something
```

#### `/tips` - Pro Tips & Best Practices
```
Usage: /tips
Response: 50+ trading tips organized by category
Categories:
  🏥 Health Checks
  📊 Market Monitoring
  🚨 Before Critical Actions
  ⚙️ Control Operations
  📈 Positioning
  🔐 Admin Operations
  ⏰ Timing
Purpose: Learn best practices
Tip: Review these regularly to improve trading!
```

#### `/guide` - Usage Examples & Workflows
```
Usage: /guide
Response: Common workflows with step-by-step examples
Workflows:
  - Morning Check (5 mins)
  - Market Open Workflow
  - Emergency Response
  - Decision Analysis
  - Market Analysis
Purpose: See how commands work together
Tip: Copy-paste commands from here
```

#### `/settings` - Configuration Check
```
Usage: /settings
Response: Current configuration summary
Shows:
  - Environment (TESTNET/MAINNET)
  - Your role (ADMIN/TRADER/VIEWER)
  - Risk settings
  - Notification status
Purpose: Verify settings
Tip: Contact admin if settings need changing
```

---

## 💡 Tips & Best Practices

### 🏥 Health & Monitoring Tips

✅ **Good Practices:**
- Run `/health` every morning before trading
- Monitor `/latency` during peak hours (9-11 AM, 4-6 PM)
- Check `/time` weekly to verify timezone is correct
- Review `/recon` after system restarts

⚠️ **Warning Signs:**
- `/latency` > 200ms = slow execution
- `/health` shows ❌ for any component
- `/time` shows clock skew > 100ms
- `/recon` shows mismatches > 0

### 📊 Market Monitoring Tips

✅ **Before Any Trade:**
1. Check `/price` to see current mood
2. Check `/spread` to estimate slippage
3. Check `/kline` for trend confirmation
4. Review `/decision` for AI insight

💡 **Pro Tips:**
- Check `/spread BTCUSDT` first - if huge, market is panicking
- Use `/kline BTCUSDT 5m 12` for short-term trends (1 hour)
- Use `/kline BTCUSDT 1h 24` for medium-term (24 hours)
- Compare latest `/decision` with previous decisions

### ⚙️ Control Operation Tips

✅ **Pause/Resume:**
- Always `/pause` before important meetings
- Wait 5 seconds after `/pause` before `/resume`
- Check `/decision` before resuming
- Never resume during high volatility without checking

✅ **Closing Positions:**
- ALWAYS check `/positions` first
- Review `/price SYMBOL` before closing (avoid market orders at bad prices)
- Close positions one at a time (use `/close_position` individually)
- Use `/close_all` ONLY in true emergencies

⚠️ **Never:**
- Close positions during news announcements
- Resume trading without checking `/decision`
- Ignore confirmation dialogs - read them carefully
- Close positions if circuit breaker is open (check `/health`)

### 🚀 Advanced Workflow Tips

**Decision Analysis Workflow:**
```
1. /decision          → See latest AI decision
2. /trace <id>        → Understand the logic
3. /positions         → Check if it was executed
4. /kline BTCUSDT 1m  → Verify with technical analysis
5. /price BTCUSDT     → Check current market conditions
```

**Emergency Response:**
```
1. /pause                    → Stop immediately
2. /positions                → Assess damage
3. /price BTC ETHUSDT ...    → Check market conditions
4. /close_position BTCUSDT   → Close highest risk first
5. /recon                    → Verify all closed
6. Contact admin             → Report incident
```

**System Health Check:**
```
/health        → Component status
/latency       → Network quality
/time          → System synchronization
/recon         → Database sync status
/status        → Overall trading status
```

---

## 🔄 Common Workflows

### 📅 Daily Trading Routine (10 mins)

**Start of Day (Pre-market):**
```
1️⃣  /health     → "All systems green?" ✅
2️⃣  /status     → "Any overnight positions?" 📊
3️⃣  /latency    → "Network OK?" 📡
4️⃣  /time       → "Clocks synchronized?" ⏰
5️⃣  /resume     → "Ready to trade" ▶️
```

**Market Open (During first hour):**
```
1️⃣  /decision   → "What did AI decide?" 🤖
2️⃣  /positions  → "How many trades opened?" 📍
3️⃣  /price BTCUSDT / /price ETHUSDT → "Market mood?" 💰
4️⃣  /recon      → "Database in sync?" ♻️
```

**Mid-Day Check (Every 2 hours):**
```
1️⃣  /status     → "Still running OK?" 📊
2️⃣  /decision   → "Recent decisions good?" 🤖
3️⃣  /latency    → "Network still OK?" 📡
```

**End of Day (Before market close):**
```
1️⃣  /positions  → "Final positions" 📍
2️⃣  /trace <id> → "Review last few decisions" 🔍
3️⃣  /pause      → "Stop trading" ⏸️
```

### 🆘 Emergency Response (When Things Go Wrong)

**Scenario: Unusual Position Opening**
```
1️⃣  /pause              → Freeze trading immediately
2️⃣  /positions          → See what opened
3️⃣  /decision           → Check what AI decided
4️⃣  /trace <trace_id>   → Understand the decision logic
5️⃣  /close_position ... → Close if not needed
6️⃣  /resume             → Resume after verification
```

**Scenario: Latency Issues**
```
1️⃣  /health     → Check status
2️⃣  /latency    → Verify latency
3️⃣  /pause      → Pause if latency > 500ms
4️⃣  /recon      → Check for mismatches
5️⃣  Contact admin if persists
```

**Scenario: System Not Responding**
```
1️⃣  /health     → Check which component failed
2️⃣  /time       → Is system alive?
3️⃣  /recon      → Is database working?
4️⃣  Contact admin → Restart if needed
```

**Scenario: Position Stuck (Can't Close)**
```
1️⃣  /positions       → Verify it still exists
2️⃣  /orders          → Check for pending close order
3️⃣  /price SYMBOL    → Check if market is moving
4️⃣  /recon           → Check database sync
5️⃣  Contact admin    → Manual intervention needed
```

### 🔍 Decision Review Workflow

**Understanding a Decision:**
```
1️⃣  /decision         → See latest decision
2️⃣  /trace <trace_id> → Review decision parameters
3️⃣  /kline BTCUSDT 1m → Verify with chart
4️⃣  /latency          → Check if network caused it
5️⃣  /recon            → Verify execution
```

**Reviewing Multiple Decisions:**
```
1️⃣  /decision         → Latest
2️⃣  Note trace_id
3️⃣  /trace trace_id   → Deep dive
4️⃣  /positions        → See result
5️⃣  Repeat above for 3-4 recent decisions
```

---

## 🆘 Troubleshooting

### Bot Not Responding

**Check 1: Is bot running?**
```powershell
# Windows: Check if process is running
tasklist | findstr python

# If no python running, start bot:
python -m apps.telegram.main
```

**Check 2: Is token valid?**
```bash
# Test token directly
https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# If error, regenerate token:
# Send /newbot to @BotFather
```

**Check 3: Are you registered?**
```bash
# Check .env for your chat ID:
grep TELEGRAM_ADMIN_IDS .env
grep TELEGRAM_TRADER_IDS .env

# If not listed, contact admin to add you
```

**Check 4: Check logs**
```bash
# View bot logs (if running in terminal):
# Look for "telegram_bot_running" message

# Or check log file:
tail -f logs/telegram.log
```

### Permission Denied Errors

**Message:** "❌ You don't have permission for this command"

**Solutions:**
1. **Get your Chat ID**
   - Use `/settings` command
   - Or visit @userinfobot

2. **Contact Admin**
   - Send your chat ID
   - Ask for ADMIN or TRADER role

3. **Admin adds you**
   - Edit `.env` file
   - Add your chat ID to TELEGRAM_ADMIN_IDS or TELEGRAM_TRADER_IDS
   - Restart bot

### Commands Not Working

**Check 1: Correct syntax?**
```
✅ Correct:   /price BTCUSDT
❌ Wrong:     /price BTC USDT  (space)
❌ Wrong:     /price btcusdt   (lowercase)

✅ Correct:   /kline BTCUSDT 1m 60
❌ Wrong:     /kline BTCUSDT 1m  (missing count)
```

**Check 2: Have permission?**
```
/help → Check your role
- ADMIN: All commands
- TRADER: View + Control
- VIEWER: View only
```

**Check 3: Database working?**
```
/health  → Check DB status
/recon   → Check sync status
```

### High Latency Issues

**Normal latency:**
- WebSocket P95: 50-100ms ✅
- REST P95: 100-200ms ✅
- Clock skew: < 50ms ✅

**High latency (>200ms):**
```
1. Check /latency
2. /pause trading
3. Check internet connection
4. Restart bot if persists
5. Contact admin
```

### Positions Won't Close

**Diagnostic Workflow:**
```
1. /positions       → Verify position exists
2. /orders          → Check if close order placed
3. /price SYMBOL    → Check if market is moving
4. /recon           → Check database sync
5. Contact admin    → May need manual close
```

**Common Reasons:**
- Market halted (check exchange status)
- Insufficient balance
- Position size too large
- Exchange in maintenance mode

---

## 📞 Support & Contact

**For Questions:**
- Check `/help`, `/tips`, `/guide` first
- Read this document
- Contact your bot admin

**For Emergencies:**
1. Use `/pause` to stop trading
2. Use `/close_all` if critical
3. Contact admin immediately

**For Bugs/Issues:**
- Take a screenshot of error message
- Note timestamp from `/time`
- Report to bot admin

---

## 🎓 Learning Path

**Day 1: Basics**
- [ ] `/start` - Get welcome message
- [ ] `/help` - Learn available commands
- [ ] `/settings` - Check your configuration
- [ ] `/status` - See current state

**Day 2: Monitoring**
- [ ] `/health` - Monitor system
- [ ] `/latency` - Check network
- [ ] `/positions` - See trades
- [ ] `/price BTCUSDT` - Check single pair

**Day 3: Trading**
- [ ] `/decision` - See AI decisions
- [ ] `/trace <id>` - Understand decisions
- [ ] `/pause` / `/resume` - Control trading
- [ ] `/close_position` - Close specific trade

**Day 4: Advanced**
- [ ] `/kline` - Technical analysis
- [ ] `/guide` - Learn workflows
- [ ] `/tips` - Pro tips
- [ ] `/recon` - System health

**Day 5: Expert**
- [ ] `/sync_now` - Admin operations (if enabled)
- [ ] Regular decision review
- [ ] Incident response procedures
- [ ] Daily monitoring routine

---

## 🎉 You're All Set!

Your Telegram bot is configured and ready! 

**Quick Commands to Remember:**
```
🚀 To start:       /help
💡 For tips:       /tips
📖 For examples:   /guide
⚡ For quick check: /status
🆘 Emergency:      /pause then /close_all
```

**Happy Trading! 📈**

---

## 📋 Checklist

Before going live, verify:

- [ ] Bot token is valid (test with `/time`)
- [ ] You are registered (test with `/help`)  
- [ ] Environment is correct (test with `/settings`)
- [ ] Database is connected (test with `/status`)
- [ ] Network latency is acceptable (check `/latency`)
- [ ] You can see positions (test with `/positions`)
- [ ] You understand `/pause` and `/close_all` (emergency buttons)
- [ ] Admin is available for support (contact verified)

✅ All checked? You're ready to trade!

---

**Bot Status: 🟢 ONLINE & READY**  
**Last Health Check**: Use `/health` to verify  
**Documentation Version**: 2.0 (March 5, 2026)
