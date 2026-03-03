# Detailed Solution: Bot Lifecycle, Session Management & Deep AI

## 🔴 PART 1: TOKEN 24H LOGOUT ISSUE - Critical Session Management

### Problem Analysis

```
Timeline:
┌─────────────────────────────────────────────────────────────┐
│                          24 Hours                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  00:00  User Login         12:00  Trading              24:00 │
│  ├─Token Created              ├─Position: +5000$      │      │
│  ├─JWT Exp: 24:00            ├─PnL: +2$              Token   │
│  │ Bot starts                │ (Position OPEN)        EXPIRES │
│  │                           │                        ↓       │
│  │                           │            Session Dies!      │
│  │                           │                        ↓       │
│  │                           │        Bot Status: ???         │
│  │                           │                                │
│  └──────────────────────────────────────────────────────────┘
│
└─ DANGER ZONE: What happens to position at 24:00?
```

### Current Problem (Without Session Management)

❌ **Scenario 1: Bot continues (DANGER)**
- Position stays open after logout
- User can't close it (no token)
- Market moves → loss
- User loses money silently

❌ **Scenario 2: Bot stops immediately (DANGER)**
- Position force-closed at market price
- Might close at bad price
- Slippage loss
- Profit becomes loss

### ✅ **RECOMMENDED SOLUTION: Graceful Session Management**

```
Token Expires at 24:00
        ↓
Worker checks: is User's session still valid?
        ↓
   ┌────┴────┐
   │          │
   YES       NO (Expired)
   │          │
   │      ├─ Check "auto_close_on_logout" flag
   │      │
   │      ├─ YES: Close all positions gracefully (limit orders)
   │      │
   │      └─ NO: Keep positions open, bot pauses
   │             → Alert user immediately
   │             → Keep persistent session flag
   │
   │
   Refresh token
   (if user re-login within grace period)
```

### Implementation: Session State Management

**Database Schema:**

```python
# Add to User model:
class User(Base):
    # Existing fields...
    bot_enabled: bool
    
    # NEW: Session Management
    last_session_token: str | None  # Last valid JWT
    last_session_refresh_at: datetime | None  # When token was last refreshed
    session_expiry_at: datetime | None  # When current session ends
    
    # Logout Handling
    auto_close_on_logout: bool = True  # Safety flag
    grace_period_minutes: int = 15  # Time to recover after logout
    graceful_exit_at: datetime | None  # When graceful exit started

# NEW TABLE for Session Tracking:
class SessionLog(Base):
    __tablename__ = "session_logs"
    
    id: int = pk
    user_id: str = fk("users.id")
    session_token: str  # JWT token used
    login_at: datetime
    logout_at: datetime | None
    expired_at: datetime
    status: str  # ACTIVE, EXPIRED, CLOSED, GRACE_PERIOD
    positions_at_logout: int  # How many open positions
    action_taken: str  # CLOSED_ALL, KEPT_OPEN, PAUSED
    notes: str | None
```

---

## 🎯 PART 2: Session Management Architecture

### Layer 1: Session Validation in Worker

File: `apps/worker/main.py`

```python
async def _check_user_session_valid(self, session: AsyncSession, user: User) -> bool:
    """
    Check if user's session is still valid
    Returns: True if session valid, False if expired
    """
    if not user.session_expiry_at:
        # No session tracking yet
        return True
    
    now = datetime.utcnow()
    
    # Session expired?
    if now > user.session_expiry_at:
        logger.warning(f"❌ Session expired for user {user.username}")
        
        # Handle graceful exit
        await self._handle_session_expiry(session, user)
        return False
    
    # Grace period handling
    grace_end = user.session_expiry_at + timedelta(
        minutes=user.grace_period_minutes
    )
    if now > grace_end:
        # Grace period ended, force action
        logger.error(f"⚠️ Grace period ended for {user.username}, force closing")
        await self._force_close_all_positions(session, user, reason="Session expired")
        return False
    
    # Session valid
    return True

async def _handle_session_expiry(self, session: AsyncSession, user: User):
    """Handle user session expiry - graceful shutdown"""
    
    if user.auto_close_on_logout:
        # Graceful close: Use limit orders to avoid slippage
        await self._graceful_close_positions(session, user)
    else:
        # Keep positions, just pause bot
        user.bot_enabled = False
        user.graceful_exit_at = datetime.utcnow()
        
        # Alert user immediately
        await self._alert_user_session_expired(
            session, user,
            message="Your session expired. Bot trading paused. Login to resume or close positions."
        )
        
        logger.info(f"Bot paused for {user.username} (session expired, positions kept)")

async def _graceful_close_positions(self, session: AsyncSession, user: User):
    """Close all positions using limit orders (avoid market order slippage)"""
    
    positions = await session.execute(
        select(Position).where(
            Position.user_id == user.id,
            Position.status == "OPEN"
        )
    )
    open_positions = positions.scalars().all()
    
    logger.info(f"Gracefully closing {len(open_positions)} positions for {user.username}")
    
    for pos in open_positions:
        try:
            # Get current price
            snapshot = await exchange.fetch_mark_price(pos.symbol)
            current_price = snapshot.close
            
            # Create limit close order slightly better than market
            if pos.side == "LONG":
                # Selling long: limit order slightly above market
                close_price = current_price * 1.001  # 0.1% above market
            else:
                # Covering short: limit order slightly below market
                close_price = current_price * 0.999  # 0.1% below market
            
            # Execute close with limit order
            order = await execution_engine.place_order(
                symbol=pos.symbol,
                side="SELL" if pos.side == "LONG" else "BUY",
                order_type="LIMIT",
                quantity=pos.qty,
                price=close_price,
                reduce_only=True,
                time_in_force="GTC"  # Good Till Cancel
            )
            
            pos.status = "CLOSING"
            pos.close_reason = "Session expired - graceful close"
            
            # Log action
            log = SessionLog(
                user_id=user.id,
                session_token=user.last_session_token,
                expired_at=user.session_expiry_at,
                status="EXPIRED",
                positions_at_logout=len(open_positions),
                action_taken="CLOSED_ALL",
                notes=f"Graceful close: limit order at {close_price}"
            )
            session.add(log)
            
        except Exception as e:
            logger.error(f"Failed to close position {pos.id}: {str(e)}")
            # Fallback to market order
            await self._force_close_position(session, pos)
    
    await session.commit()

async def _alert_user_session_expired(self, session: AsyncSession, user: User, message: str):
    """Alert user through all channels"""
    # Send system notification
    notification = SystemNotification(
        target_user_id=user.id,
        title="⚠️ Session Expired",
        message=message,
        level="warning"
    )
    session.add(notification)
    
    # Send Telegram if available
    if user.telegram_id:
        try:
            await send_telegram_message(
                user.telegram_id,
                f"⚠️ **Session Expired**\n\n{message}"
            )
        except:
            pass
    
    await session.commit()
```

### Layer 2: Token Refresh Mechanism

File: `apps/api/auth.py`

```python
async def refresh_session(
    current_token: str,
    user: User,
    session: AsyncSession
) -> Token:
    """
    Refresh JWT token when near expiry
    Extends session by 24 hours
    """
    
    # Verify current token still valid
    payload = jwt_handler.decode_token(current_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token invalid")
    
    # Create new token
    new_token = jwt_handler.create_access_token(user)
    
    # Update user session tracking
    user.last_session_token = new_token.access_token
    user.last_session_refresh_at = datetime.utcnow()
    user.session_expiry_at = datetime.utcnow() + timedelta(hours=24)
    user.graceful_exit_at = None  # Clear grace period
    user.bot_enabled = True  # Re-enable bot if it was paused
    
    # Log session refresh
    log = SessionLog(
        user_id=user.id,
        session_token=new_token.access_token,
        login_at=datetime.utcnow(),
        expired_at=user.session_expiry_at,
        status="ACTIVE"
    )
    session.add(log)
    await session.commit()
    
    logger.info(f"Session refreshed for {user.username}, expires at {user.session_expiry_at}")
    return new_token
```

### Layer 3: Dashboard API Endpoints

File: `apps/api/phase4_routes.py`

```python
@router.get("/session/status")
async def get_session_status(
    credentials = Depends(security)
):
    """Get current session status with timeline"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    now = datetime.utcnow()
    time_remaining = user.session_expiry_at - now if user.session_expiry_at else None
    
    # Get open positions
    async with AsyncSessionFactory() as session:
        positions = await session.execute(
            select(Position).where(
                Position.user_id == user.id,
                Position.status == "OPEN"
            )
        )
        open_count = len(positions.scalars().all())
    
    return {
        "user_id": user.id,
        "username": user.username,
        "logged_in_at": user.last_session_refresh_at.isoformat() if user.last_session_refresh_at else None,
        "session_expires_at": user.session_expiry_at.isoformat() if user.session_expiry_at else None,
        "time_remaining_minutes": int(time_remaining.total_seconds() / 60) if time_remaining else None,
        "time_remaining_hours": round(time_remaining.total_seconds() / 3600, 1) if time_remaining else None,
        "open_positions": open_count,
        "auto_close_on_logout": user.auto_close_on_logout,
        "grace_period_minutes": user.grace_period_minutes,
        "bot_enabled": user.bot_enabled,
        "status": (
            "✅ Active" if now < user.session_expiry_at else
            "⏳ Grace Period" if now < user.session_expiry_at + timedelta(minutes=user.grace_period_minutes) else
            "❌ Expired"
        ),
        "urgent_action_needed": (
            open_count > 0 and 
            time_remaining and 
            time_remaining.total_seconds() < 3600  # Less than 1 hour
        )
    }

@router.post("/session/refresh")
async def extend_session(
    credentials = Depends(security)
):
    """Extend session for another 24 hours"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        from apps.api.auth import refresh_session
        
        db_user = await session.get(User, user.id)
        new_token = await refresh_session(
            current_token=credentials.credentials,
            user=db_user,
            session=session
        )
    
    return {
        "message": "Session extended for 24 hours",
        "access_token": new_token.access_token,
        "expires_at": new_token.expires_in,
        "session_expires_at": db_user.session_expiry_at.isoformat()
    }

@router.post("/session/logout")
async def user_logout(
    close_positions: bool = True,
    credentials = Depends(security)
):
    """User initiated logout"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        db_user = await session.get(User, user.id)
        
        if close_positions:
            # Gracefully close all positions
            positions = await session.execute(
                select(Position).where(
                    Position.user_id == user.id,
                    Position.status == "OPEN"
                )
            )
            for pos in positions.scalars():
                pos.status = "CLOSING_REQUESTED"
                pos.close_reason = "User logout - requested close"
            
            logger.info(f"User {user.username} logged out with position close request")
        
        # Mark session as ended
        db_user.session_expiry_at = datetime.utcnow()
        db_user.bot_enabled = False
        
        # Log logout
        log = SessionLog(
            user_id=user.id,
            session_token=credentials.credentials,
            logout_at=datetime.utcnow(),
            expired_at=datetime.utcnow(),
            status="CLOSED",
            action_taken="CLOSED_ALL" if close_positions else "BOT_PAUSED"
        )
        session.add(log)
        await session.commit()
    
    return {
        "message": "Logged out successfully",
        "positions_closed": close_positions
    }

@router.get("/session/logs")
async def get_session_logs(
    limit: int = 20,
    credentials = Depends(security)
):
    """Get session history"""
    user = await jwt_handler.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        logs = await session.execute(
            select(SessionLog)
            .where(SessionLog.user_id == user.id)
            .order_by(desc(SessionLog.expired_at))
            .limit(limit)
        )
        
        return [
            {
                "id": log.id,
                "login_at": log.login_at.isoformat() if log.login_at else None,
                "logout_at": log.logout_at.isoformat() if log.logout_at else None,
                "expired_at": log.expired_at.isoformat(),
                "status": log.status,
                "positions_at_logout": log.positions_at_logout,
                "action_taken": log.action_taken,
                "notes": log.notes
            }
            for log in logs.scalars().all()
        ]
```

### Layer 4: Frontend Warning System

```typescript
// React component: SessionWarning.tsx

const SessionWarning = () => {
  const [sessionStatus, setSessionStatus] = useState<SessionStatus | null>(null)
  const [showWarning, setShowWarning] = useState(false)

  useEffect(() => {
    // Check every 1 minute
    const interval = setInterval(async () => {
      const status = await api.get('/session/status')
      setSessionStatus(status)

      // Show warning if less than 1 hour remaining
      if (status.time_remaining_hours < 1 && status.open_positions > 0) {
        setShowWarning(true)
      }
    }, 60000)

    return () => clearInterval(interval)
  }, [])

  if (!showWarning || !sessionStatus) return null

  return (
    <div className="bg-orange-100 border-l-4 border-orange-500 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-bold">⚠️ Session Expiring Soon</h3>
          <p>
            {sessionStatus.time_remaining_hours} hours remaining
            {sessionStatus.open_positions > 0 && (
              <span className="text-red-600">
                • {sessionStatus.open_positions} open positions
              </span>
            )}
          </p>
          {sessionStatus.auto_close_on_logout ? (
            <p className="text-sm text-gray-600">
              ✅ Positions will auto-close gracefully on logout
            </p>
          ) : (
            <p className="text-sm text-red-600">
              ❌ Positions will remain open - you must login to close them!
            </p>
          )}
        </div>
        
        <button 
          onClick={async () => {
            await api.post('/session/refresh')
            setShowWarning(false)
          }}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          Extend Session (24h)
        </button>
      </div>
    </div>
  )
}
```

---

## 🤖 PART 3: Deep AI Trading - Strategy Profiler

### Layer 1: Strategy Analysis Engine

File: `packages/shared/strategy_profiler.py` (NEW)

```python
"""
Strategy Profiler - Analyzes trader's style and adapts AI decisions
Extracts: trading style, risk tolerance, timeframe preference, psychology
"""

import json
import re
from typing import Dict, Any, List, Optional
from enum import Enum

class TradingStyle(Enum):
    """Trader psychological style"""
    SCALPER = "scalper"  # Fast, many small trades
    SWING_TRADER = "swing"  # Days to weeks
    POSITION_TRADER = "position"  # Weeks to months
    TREND_FOLLOWER = "trend"  # Follow momentum
    MEAN_REVERTER = "mean_revert"  # Trade ranges
    MOMENTUM_RIDER = "momentum"  # Chase moves
    NEWS_TRADER = "news"  # React to events
    UNKNOWN = "unknown"

class RiskProfile(Enum):
    """User's risk tolerance"""
    ULTRA_CONSERVATIVE = "ultra_conservative"  # SL 2%, small positions
    CONSERVATIVE = "conservative"  # SL 5%, moderate size
    BALANCED = "balanced"  # SL 10%, normal size
    AGGRESSIVE = "aggressive"  # SL 15%, larger size
    ULTRA_AGGRESSIVE = "ultra_aggressive"  # SL 20%, all-in

class StrategyProfiler:
    """Analyzes trader context and creates intelligent profile"""
    
    def __init__(self):
        self.keywords_scalper = [
            "5 phút", "15 phút", "nhanh", "lướt", "scalp",
            "tick", "second", "mở đóng", "quick", "fast"
        ]
        self.keywords_swing = [
            "1 giờ", "4 giờ", "1 ngày", "ngày", "tuần",
            "hold", "keep", "swing", "day trade"
        ]
        self.keywords_position = [
            "tuần", "tháng", "dài hạn", "long term",
            "position", "fundamental", "đầu tư"
        ]
        self.keywords_trend = [
            "xu hướng", "trend", "moving average", "ema",
            "đi theo", "follow", "uptrend", "downtrend"
        ]
        self.keywords_mean_revert = [
            "quay lại", "revert", "range", "support", "resistance",
            "bounce", "pullback", "oversold", "overbought"
        ]
    
    def analyze_trader_context(self, prompt: str) -> Dict[str, Any]:
        """
        Deeply analyze trader's natural language description
        Extract: style, risk tolerance, psychology, preferences
        """
        
        prompt_lower = prompt.lower()
        
        # 1. Detect trading style
        style = self._detect_trading_style(prompt_lower)
        
        # 2. Extract risk profile
        risk_profile = self._extract_risk_profile(prompt_lower)
        
        # 3. Analyze psychological traits
        psychology = self._analyze_psychology(prompt)
        
        # 4. Extract numerical parameters
        parameters = self._extract_parameters(prompt)
        
        # 5. Preferred timeframes
        timeframes = self._extract_timeframes(prompt_lower)
        
        # 6. Confidence boost factors
        confidence_boosts = self._identify_confidence_boosts(style, parameters)
        
        profile = {
            "trading_style": style.value,
            "risk_profile": risk_profile.value,
            "psychology": psychology,
            "base_parameters": parameters,
            "preferred_timeframes": timeframes,
            "confidence_boosts": confidence_boosts,
            "decision_weights": self._calculate_decision_weights(style, risk_profile),
            "regime_preferences": self._get_regime_preferences(style),
            "raw_analysis": {
                "style_detection": style.value,
                "risk_level": risk_profile.value,
                "keywords_found": self._extract_keywords(prompt_lower)
            }
        }
        
        return profile
    
    def _detect_trading_style(self, prompt_lower: str) -> TradingStyle:
        """Detect trader's primary style"""
        
        # Count keyword matches
        scores = {
            TradingStyle.SCALPER: self._count_matches(prompt_lower, self.keywords_scalper),
            TradingStyle.SWING_TRADER: self._count_matches(prompt_lower, self.keywords_swing),
            TradingStyle.POSITION_TRADER: self._count_matches(prompt_lower, self.keywords_position),
            TradingStyle.TREND_FOLLOWER: self._count_matches(prompt_lower, self.keywords_trend),
            TradingStyle.MEAN_REVERTER: self._count_matches(prompt_lower, self.keywords_mean_revert),
        }
        
        # Find highest score
        best_style = max(scores, key=scores.get)
        
        # If low confidence, consider multiple styles
        if scores[best_style] < 2:
            return TradingStyle.UNKNOWN
        
        return best_style
    
    def _extract_risk_profile(self, prompt_lower: str) -> RiskProfile:
        """Determine risk tolerance from context"""
        
        # Extract stop loss percentage
        sl_matches = re.findall(r'(cắt lỗ|stop loss|sl|stoploss).*?(\d+(?:\.\d+)?)\s*(%|percent)', prompt_lower)
        if sl_matches:
            sl_pct = float(sl_matches[0][1])
            if sl_pct <= 2:
                return RiskProfile.ULTRA_CONSERVATIVE
            elif sl_pct <= 5:
                return RiskProfile.CONSERVATIVE
            elif sl_pct <= 10:
                return RiskProfile.BALANCED
            elif sl_pct <= 15:
                return RiskProfile.AGGRESSIVE
            else:
                return RiskProfile.ULTRA_AGGRESSIVE
        
        # Infer from style
        style = self._detect_trading_style(prompt_lower)
        if style == TradingStyle.SCALPER:
            return RiskProfile.CONSERVATIVE  # Scalpers use tight stops
        elif style == TradingStyle.POSITION_TRADER:
            return RiskProfile.BALANCED  # Longer holds = wider stops
        
        return RiskProfile.BALANCED
    
    def _analyze_psychology(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze trader's psychological traits:
        - Patience level
        - FOMO tendency
        - Loss aversion
        - Discipline
        """
        
        prompt_lower = prompt.lower()
        
        return {
            "patience": (
                "high" if any(w in prompt for w in ["đợi", "chờ", "nhẫn nại", "wait"]) else
                "medium" if any(w in prompt for w in ["vào ngay", "nhanh"]) else
                "low"
            ),
            "fomo_risk": (
                "high" if any(w in prompt for w in ["miss", "missed", "sợ mất", "fomo"]) else
                "low"
            ),
            "discipline": (
                "high" if any(w in prompt for w in ["luôn", "always", "nghiêm ngặt", "strict"]) else
                "medium"
            ),
            "loss_aversion": (
                "high" if any(w in prompt for w in ["cắt lỗ", "stop loss", "risk control"]) else
                "low"
            ),
            "trend_following": (
                "strong" if any(w in prompt for w in ["trend", "xu hướng", "follow"]) else
                "weak"
            )
        }
    
    def _extract_parameters(self, prompt: str) -> Dict[str, Any]:
        """Extract numerical parameters from text"""
        
        params = {}
        
        # Profit target
        profit_matches = re.findall(r'(lời|profit|target).*?(\d+(?:\.\d+)?)\s*(\$|đô|percent|%)', prompt, re.IGNORECASE)
        if profit_matches:
            params['profit_target'] = float(profit_matches[0][1])
        
        # Capital
        capital_matches = re.findall(r'(vốn|capital|account).*?(\d+(?:\.\d+)?)\s*(\$|đô)', prompt, re.IGNORECASE)
        if capital_matches:
            params['capital'] = float(capital_matches[0][1])
        
        # Leverage
        lev_matches = re.findall(r'(đòn bẩy|leverage).*?(\d+(?:\.\d+)?)\s*x', prompt, re.IGNORECASE)
        if lev_matches:
            params['leverage'] = float(lev_matches[0][1])
        
        # Win rate target
        wr_matches = re.findall(r'(thắng|win|rate).*?(\d+(?:\.\d+)?)\s*(%|percent)', prompt, re.IGNORECASE)
        if wr_matches:
            params['min_win_rate'] = float(wr_matches[0][1])
        
        # Max concurrent positions
        pos_matches = re.findall(r'(vị\s*thế|position|lệnh).*?(\d+)\s*(cùng lúc|at once|concurrent)', prompt, re.IGNORECASE)
        if pos_matches:
            params['max_positions'] = int(pos_matches[0][1])
        
        return params
    
    def _extract_timeframes(self, prompt_lower: str) -> List[str]:
        """Extract preferred timeframes"""
        
        tf_map = {
            '1m': ['1 phút', '1m', '1min'],
            '5m': ['5 phút', '5m', '5min'],
            '15m': ['15 phút', '15m', '15min'],
            '1h': ['1 giờ', '1h', '1hour'],
            '4h': ['4 giờ', '4h', '4hour'],
            '1d': ['1 ngày', '1d', 'daily'],
        }
        
        timeframes = []
        for tf, keywords in tf_map.items():
            if any(kw in prompt_lower for kw in keywords):
                timeframes.append(tf)
        
        return timeframes or ['15m', '1h']  # Default
    
    def _calculate_decision_weights(self, style: TradingStyle, risk: RiskProfile) -> Dict[str, float]:
        """
        Calculate AI decision weights based on profile
        Values 0.0-2.0 where 1.0 = neutral
        """
        
        weights = {
            "trend_entry": 1.0,
            "mean_revert_entry": 1.0,
            "momentum_entry": 1.0,
            "position_size": 1.0,
            "stop_loss_width": 1.0,
            "take_profit_ratio": 1.0,
            "holding_time": 1.0,
        }
        
        # Style-based adjustments
        if style == TradingStyle.TREND_FOLLOWER:
            weights["trend_entry"] = 1.8
            weights["mean_revert_entry"] = 0.3
        elif style == TradingStyle.MEAN_REVERTER:
            weights["mean_revert_entry"] = 1.8
            weights["trend_entry"] = 0.4
        elif style == TradingStyle.SCALPER:
            weights["holding_time"] = 0.2
            weights["position_size"] = 0.5
        elif style == TradingStyle.SWING_TRADER:
            weights["holding_time"] = 2.0
            weights["position_size"] = 1.5
        
        # Risk-based adjustments
        if risk == RiskProfile.ULTRA_CONSERVATIVE:
            weights["position_size"] = 0.3
            weights["stop_loss_width"] = 0.5
        elif risk == RiskProfile.AGGRESSIVE:
            weights["position_size"] = 1.5
            weights["stop_loss_width"] = 1.3
        
        return weights
    
    def _identify_confidence_boosts(self, style: TradingStyle, params: Dict) -> List[str]:
        """Identify factors that should boost AI confidence"""
        
        boosts = []
        
        if style == TradingStyle.SCALPER:
            boosts.extend([
                "short_holding_time",  # Quick wins expected
                "multiple_signals",  # Need confluence
                "high_volatility",  # Opportunity
            ])
        elif style == TradingStyle.POSITION_TRADER:
            boosts.extend([
                "fundamental_support",  # Long thesis
                "long_timeframe_trend",  # 4h+ trends
                "daily_close",  # End of day confirmation
            ])
        
        if params.get('min_win_rate', 0) > 70:
            boosts.append("high_win_rate_target")  # Wants quality over quantity
        
        return boosts
    
    def _get_regime_preferences(self, style: TradingStyle) -> Dict[str, float]:
        """Get market regime preference multipliers (0-2 range)"""
        
        preferences = {
            "strong_uptrend": 1.0,
            "weak_uptrend": 1.0,
            "consolidation": 1.0,
            "weak_downtrend": 1.0,
            "strong_downtrend": 1.0,
        }
        
        if style == TradingStyle.TREND_FOLLOWER:
            preferences["strong_uptrend"] = 1.8
            preferences["strong_downtrend"] = 1.8
            preferences["consolidation"] = 0.3
        elif style == TradingStyle.MEAN_REVERTER:
            preferences["consolidation"] = 1.8
            preferences["strong_uptrend"] = 0.3
            preferences["strong_downtrend"] = 0.3
        
        return preferences
    
    def _count_matches(self, text: str, keywords: List[str]) -> int:
        """Count how many keywords match in text"""
        return sum(1 for kw in keywords if kw in text)
    
    def _extract_keywords(self, prompt_lower: str) -> List[str]:
        """Extract all recognized keywords from prompt"""
        found = []
        all_keywords = (
            self.keywords_scalper + self.keywords_swing + 
            self.keywords_position + self.keywords_trend + 
            self.keywords_mean_revert
        )
        for kw in all_keywords:
            if kw in prompt_lower:
                found.append(kw)
        return found


# Usage in AIOrchestrator:
async def make_decision_with_profiler(
    self,
    market_snapshot,
    prompt_pack,
    current_positions,
    trader_context: Optional[str] = None
):
    """Make decision adapted to trader's profile"""
    
    profiler = StrategyProfiler()
    
    # 1. Get trader profile
    if trader_context:
        trader_profile = profiler.analyze_trader_context(trader_context)
    else:
        trader_profile = {
            "trading_style": "unknown",
            "decision_weights": {k: 1.0 for k in ["trend_entry", "mean_revert_entry", ...]},
            "confidence_boosts": []
        }
    
    # 2. Make base decision via LLM
    decision = await self.llm.generate(prompt)
    decision_data = json.loads(decision)
    
    # 3. Adjust decision based on profile
    decision_data = self._apply_profile_adjustments(
        decision_data,
        trader_profile,
        market_snapshot
    )
    
    # 4. Return profiler-adapted decision
    return decision_data

def _apply_profile_adjustments(self, decision, profile, snapshot) -> dict:
    """Apply trader profile adjustments to decision"""
    
    if decision.get("decision_type") != "ENTRY":
        return decision
    
    weights = profile["decision_weights"]
    
    # Adjust position size based on risk profile
    if "position_size" in decision:
        decision["position_size"] *= weights["position_size"]
    
    # Adjust stop loss width
    if "stop_loss_pips" in decision:
        decision["stop_loss_pips"] *= weights["stop_loss_width"]
    
    # Boost confidence if favorable conditions
    if all(boost in profile["confidence_boosts"] for boost in ["multiple_signals"]):
        decision["confidence"] = min(0.95, decision.get("confidence", 0.5) * 1.2)
    
    return decision
```

---

## 📊 PART 4: Quota Tracking System with User Alerts

File: `packages/shared/quota_manager.py` (NEW)

```python
"""
API Quota Management - Track & Alert per user
Prevents 429 errors with proactive quota monitoring
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from enum import Enum
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from packages.shared.models import UserCredential, SystemNotification

class QuotaStatus(Enum):
    HEALTHY = "healthy"  # 0-70%
    WARNING = "warning"  # 70-85%
    CRITICAL = "critical"  # 85-95%
    EXCEEDED = "exceeded"  # 100%+

class QuotaManager:
    """
    Manage API quotas per user per provider
    Automatic alerts, fallback model switching
    """
    
    # Default monthly quotas per provider (can be overridden)
    DEFAULT_QUOTAS = {
        "openai": 50000,  # 50k calls/month
        "anthropic": 30000,  # 30k calls/month
        "gemini": 60000,  # 60k calls/month
        "groq": 100000,  # Unlimited for free tier
        "external_agent": 40000,  # Custom limit
    }
    
    ALERT_THRESHOLDS = {
        "70%": "warning",
        "85%": "critical",
        "95%": "emergency",
    }
    
    @staticmethod
    async def record_api_call(
        session: AsyncSession,
        user_id: str,
        provider: str,
        tokens_used: int = 1,
        success: bool = True,
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Record API call for quota tracking
        Returns: quota status with warnings if needed
        """
        
        cred = await session.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        )
        credential = cred.scalar_one_or_none()
        
        if not credential:
            return {"error": "No credentials"}
        
        # Check if quota should reset (monthly)
        if not credential.quota_reset_date or datetime.utcnow() > credential.quota_reset_date:
            # Reset for new month
            first_of_next_month = (datetime.utcnow().replace(day=1) + timedelta(days=32)).replace(day=1)
            credential.quota_reset_date = first_of_next_month
            credential.monthly_api_calls = 0
        
        # Record the call
        if success:
            credential.monthly_api_calls += 1
        
        await session.commit()
        
        # Calculate quota status
        limit = credential.monthly_quota_limit or QuotaManager.DEFAULT_QUOTAS.get(provider, 50000)
        used = credential.monthly_api_calls
        percentage = (used / limit * 100) if limit else 0
        
        status = {
            "provider": provider,
            "api_calls_used": used,
            "quota_limit": limit,
            "remaining": limit - used,
            "percentage_used": round(percentage, 1),
            "month": credential.quota_reset_date.strftime("%Y-%m") if credential.quota_reset_date else "unknown",
            "quota_status": QuotaManager._get_quota_status(percentage).value,
            "days_remaining_in_month": (credential.quota_reset_date - datetime.utcnow()).days if credential.quota_reset_date else 0,
        }
        
        # Check if alert needed
        if percentage >= 95:
            await QuotaManager._send_alert(
                session, user_id, provider,
                level="EMERGENCY",
                message=f"🚨 QUOTA EXCEEDED for {provider}! Used {percentage:.0f}% ({used}/{limit})"
            )
        elif percentage >= 85:
            await QuotaManager._send_alert(
                session, user_id, provider,
                level="CRITICAL",
                message=f"⚠️ CRITICAL: {provider} quota {percentage:.0f}% used ({used}/{limit})"
            )
        elif percentage >= 70:
            await QuotaManager._send_alert(
                session, user_id, provider,
                level="WARNING",
                message=f"⚡ Warning: {provider} quota {percentage:.0f}% used"
            )
        
        return status
    
    @staticmethod
    async def get_quota_status(
        session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Get complete quota status for all user's API keys"""
        
        cred = await session.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        )
        credential = cred.scalar_one_or_none()
        
        if not credential:
            return {"error": "Credentials not found"}
        
        providers = ["openai", "anthropic", "gemini", "groq"]
        if credential.external_agent_enabled:
            providers.append("external_agent")
        
        statuses = {}
        overall_critical = False
        
        for provider in providers:
            limit = QuotaManager.DEFAULT_QUOTAS.get(provider, 50000)
            used = credential.monthly_api_calls  # Shared counter for now
            percentage = (used / limit * 100) if limit else 0
            
            status = QuotaManager._get_quota_status(percentage)
            if status == QuotaStatus.CRITICAL or status == QuotaStatus.EXCEEDED:
                overall_critical = True
            
            statuses[provider] = {
                "api_calls_used": used,
                "quota_limit": limit,
                "percentage_used": round(percentage, 1),
                "status": status.value,
                "icon": QuotaManager._get_status_icon(status)
            }
        
        return {
            "user_id": user_id,
            "quota_month": credential.quota_reset_date.strftime("%Y-%m") if credential.quota_reset_date else "unknown",
            "overall_status": "🚨 CRITICAL" if overall_critical else "✅ HEALTHY",
            "provider_quotas": statuses,
            "action_needed": overall_critical
        }
    
    @staticmethod
    async def set_provider_quota(
        session: AsyncSession,
        user_id: str,
        provider: str,
        monthly_limit: int
    ):
        """Set custom monthly quota limit for specific provider"""
        
        from packages.shared.models import User
        
        # Store as JSON on user preferences
        user = await session.get(User, user_id)
        if not user:
            return
        
        # For simplicity, store in monthly_quota_limit for now
        # In production, use JSON field for per-provider limits
        cred = await session.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        )
        credential = cred.scalar_one_or_none()
        
        if credential:
            credential.monthly_quota_limit = monthly_limit
            await session.commit()
    
    @staticmethod
    async def _send_alert(
        session: AsyncSession,
        user_id: str,
        provider: str,
        level: str,
        message: str
    ):
        """Send quota alert to user through all channels"""
        
        # Show in dashboard
        notification = SystemNotification(
            target_user_id=user_id,
            title=f"{level}: {provider.upper()} API Quota",
            message=message,
            level="critical" if level in ["CRITICAL", "EMERGENCY"] else "warning"
        )
        session.add(notification)
        await session.commit()
        
        # In production, also send:
        # - Telegram message
        # - Email alert
        # - Webhook notification
    
    @staticmethod
    def _get_quota_status(percentage: float) -> QuotaStatus:
        """Determine quota status from usage percentage"""
        if percentage >= 100:
            return QuotaStatus.EXCEEDED
        elif percentage >= 85:
            return QuotaStatus.CRITICAL
        elif percentage >= 70:
            return QuotaStatus.WARNING
        else:
            return QuotaStatus.HEALTHY
    
    @staticmethod
    def _get_status_icon(status: QuotaStatus) -> str:
        """Get emoji icon for status"""
        return {
            QuotaStatus.HEALTHY: "✅",
            QuotaStatus.WARNING: "⚡",
            QuotaStatus.CRITICAL: "🔴",
            QuotaStatus.EXCEEDED: "🚨"
        }.get(status, "❓")
    
    @staticmethod
    async def suggest_model_fallback(
        session: AsyncSession,
        user_id: str,
        current_provider: str
    ) -> Optional[str]:
        """
        Suggest fallback model if current provider quota exhausted
        Returns: provider name to use instead, or None
        """
        
        status = await QuotaManager.get_quota_status(session, user_id)
        
        # If current provider critical, suggest alternatives
        if status["provider_quotas"].get(current_provider, {}).get("status") in ["critical", "exceeded"]:
            # Fallback priority: Groq → Anthropic → OpenAI → Gemini → Mock
            fallback_order = ["groq", "anthropic", "openai", "gemini", "mock"]
            
            for provider in fallback_order:
                if provider == "mock":
                    return "mock"
                
                prov_status = status["provider_quotas"].get(provider)
                if prov_status and prov_status["status"] != "exceeded":
                    return provider
        
        return None
```

### API Endpoints for Quota Management

File: `apps/api/phase4_routes.py` (add these endpoints)

```python
@router.get("/quota/dashboard")
async def quota_dashboard(
    user_id: str | None = None,
    credentials = Depends(security)
):
    """Get quota dashboard with usage charts"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    target_id = _get_target_user_id(requester, user_id)
    
    from packages.shared.quota_manager import QuotaManager
    async with AsyncSessionFactory() as session:
        status = await QuotaManager.get_quota_status(session, target_id)
    
    return {
        "user_id": target_id,
        "quota_info": status,
        "warning": status.get("action_needed")
    }


@router.post("/quota/alert-configure")
async def configure_quota_alerts(
    warning_threshold: int = 70,  # percentage
    critical_threshold: int = 85,
    alert_methods: List[str] = ["dashboard", "telegram"],  # notification methods
    credentials = Depends(security)
):
    """Configure quota alert thresholds and methods"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Store preferences in user profile
    async with AsyncSessionFactory() as session:
        from packages.shared.models import User
        user = await session.get(User, requester.id)
        # TODO: Add alert preferences to User model
        await session.commit()
    
    return {
        "message": "Quota alerts configured",
        "warning_threshold": f"{warning_threshold}%",
        "critical_threshold": f"{critical_threshold}%",
        "alert_methods": alert_methods
    }


@router.get("/quota/alerts")
async def get_quota_alerts(
    limit: int = 10,
    credentials = Depends(security)
):
    """Get recent quota alerts for user"""
    requester = await jwt_handler.verify_token(credentials.credentials)
    if not requester:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with AsyncSessionFactory() as session:
        alerts = await session.execute(
            select(SystemNotification)
            .where(
                SystemNotification.target_user_id == requester.id,
                SystemNotification.title.contains("QUOTA")
            )
            .order_by(desc(SystemNotification.created_at))
            .limit(limit)
        )
        
        return [
            {
                "id": a.id,
                "title": a.title,
                "message": a.message,
                "level": a.level,
                "timestamp": a.created_at.isoformat(),
                "read": a.is_read
            }
            for a in alerts.scalars().all()
        ]
```

---

## 📋 PART 5: Learning Agent Auto-Apply System

File: `packages/shared/learning_agent.py` (modify existing)

```python
# Add to existing LearningAgent class:

async def auto_apply_safe_recommendations(
    self,
    session: AsyncSession,
    user_id: str,
    min_confidence: float = 0.75
) -> Dict[str, Any]:
    """
    AUTO-APPLY recommendations that meet safety criteria
    Only modifies parameters that improve risk management
    
    Safe changes:
    ✅ Widen stop loss if losing too much
    ✅ Reduce position size if overleveraged
    ✅ Avoid bad regimes if win rate < 40%
    
    UNSAFE changes (require manual approval):
    ❌ Increase leverage
    ❌ Remove risk limits
    ❌ Change core strategy
    """
    
    # Get latest trade analysis
    report = self.analyze()
    
    if not report or not report.suggested_adaptations:
        return {"message": "No recommendations to apply", "applied": []}
    
    recommendations = report.suggested_adaptations
    applied_changes = []
    rejected_changes = []
    
    for rec in recommendations:
        # Check safety criteria
        is_safe = await self._is_safe_recommendation(rec, user_id)
        is_confident = rec.confidence >= min_confidence
        
        if is_safe and is_confident:
            # Apply immediately
            success = await self._apply_recommendation(session, user_id, rec)
            if success:
                applied_changes.append({
                    "recommendation": rec.action,
                    "parameter": rec.variable,
                    "change": rec.delta,
                    "reason": rec.rationale,
                    "applied_at": datetime.utcnow().isoformat()
                })
        else:
            # Require manual approval
            rejected_changes.append({
                "recommendation": rec.action,
                "reason": (
                    "Low confidence" if not is_confident else
                    "Safety concerns" if not is_safe else
                    "Unknown"
                ),
                "confidence": rec.confidence,
                "requires_approval": True
            })
    
    await session.commit()
    
    return {
        "applied": applied_changes,
        "rejected": rejected_changes,
        "total_applied": len(applied_changes),
        "total_rejected": len(rejected_changes)
    }

async def _is_safe_recommendation(self, recommendation, user_id: str) -> bool:
    """Check if recommendation is safe to auto-apply"""
    
    # CATEGORIZE recommendations
    safe_actions = [
        "WIDEN_STOP_LOSS",  # Safer, not greedy
        "REDUCE_POSITION_SIZE",  # Reduces risk
        "INCREASE_MIN_WIN_RATE_THRESHOLD",  # Can't hurt
        "AVOID_REGIME_DOWNTREND",  # Reduces risky trades
        "REDUCE_LEVERAGE",  # Always safer
    ]
    
    unsafe_actions = [
        "INCREASE_LEVERAGE",  # DANGER
        "REMOVE_RISK_LIMIT",  # DANGER
        "DISABLE_STOP_LOSS",  # DANGER
        "CHANGE_STRATEGY",  # DANGER
    ]
    
    action = recommendation.action
    
    if action in unsafe_actions:
        return False
    
    if action not in safe_actions:
        return False
    
    # Additional safety checks
    if action == "WIDEN_STOP_LOSS":
        # Only widen if not already too wide (e.g., >5%)
        if recommendation.delta > 5:
            return False
    
    if action == "REDUCE_POSITION_SIZE":
        # Can always reduce safely
        return True
    
    return True

async def _apply_recommendation(
    self,
    session: AsyncSession,
    user_id: str,
    recommendation
) -> bool:
    """Actually apply the recommendation to user's config"""
    
    try:
        from packages.shared.models import BotConfig
        
        # Get active config
        config = await session.execute(
            select(BotConfig)
            .where(BotConfig.user_id == user_id, BotConfig.is_active == True)
            .order_by(desc(BotConfig.id))
            .limit(1)
        )
        bot_config = config.scalar_one_or_none()
        
        if not bot_config:
            return False
        
        risk_config = bot_config.risk_json or {}
        
        # Apply changes
        if recommendation.action == "WIDEN_STOP_LOSS":
            current_sl = risk_config.get("default_stop_loss_pct", 1.0)
            new_sl = min(current_sl + recommendation.delta, 5.0)  # Cap at 5%
            risk_config["default_stop_loss_pct"] = new_sl
        
        elif recommendation.action == "REDUCE_POSITION_SIZE":
            current_pos = risk_config.get("max_position_pct", 10.0)
            new_pos = max(current_pos * (1.0 - recommendation.delta / 100), 1.0)
            risk_config["max_position_pct"] = new_pos
        
        elif recommendation.action == "REDUCE_LEVERAGE":
            current_lev = risk_config.get("max_leverage", 10.0)
            new_lev = max(current_lev - recommendation.delta, 1.0)
            risk_config["max_leverage"] = new_lev
        
        elif recommendation.action == "INCREASE_MIN_WIN_RATE_THRESHOLD":
            current_wr = risk_config.get("min_win_rate", 50.0)
            new_wr = min(current_wr + recommendation.delta, 90.0)
            risk_config["min_win_rate"] = new_wr
        
        # Save updated config
        bot_config.risk_json = risk_config
        bot_config.version += 1
        
        # Log the change
        audit_log = AuditLog(
            user_id=user_id,
            action="LEARNING_AGENT_AUTO_APPLY",
            details={
                "recommendation": recommendation.action,
                "parameter": recommendation.variable,
                "old_value": risk_config.get(recommendation.variable),
                "new_value": recommendation.delta,
                "confidence": recommendation.confidence,
                "reason": recommendation.rationale
            }
        )
        session.add(audit_log)
        
        await session.commit()
        
        logger.info(f"✅ Applied recommendation: {recommendation.action} for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to apply recommendation: {str(e)}")
        return False
```

---

## 🔌 PART 6: Why External AI Agents Not Yet Integrated - Detailed Analysis

File: `EXTERNAL_AI_INTEGRATION_ANALYSIS.md` (NEW)

```markdown
# Why External AI Agents Model Not Yet Integrated - Technical Analysis

## Current State (3/3/2026)

### ✅ Infrastructure Ready
- LLMAdapter abstract base class exists
- Factory pattern implemented in `get_llm_adapter()`
- Support for 5+ providers (OpenAI, Claude, Gemini, Groq, Local)
- Fallback to Mock LLM built-in
- Error handling for quota exceeded (429)

### ❌ Blocking Issues for External Integration

#### 1. **No VPS Endpoint Specification**
**Problem:** Don't know your exact API format
- Expected input format? JSON? Binary?
- Expected output format? 
- Which LLM model are you using? (requires specific parsing)
- Authentication method? (API key? Auth header? Custom?)
- Rate limits on your VPS?

**What's Needed:**
```
Example VPS specification:
{
  "endpoint": "http://your-vps:5000/api/generate",
  "method": "POST",
  "request_body": {
    "prompt": "string",
    "model": "string",
    "temperature": float,
    "max_tokens": int
  },
  "response_body": {
    "text": "string (JSON decision)",
    "confidence": float,
    "metadata": {}
  },
  "auth": "Bearer {api_key}",
  "error_codes": {
    "429": "quota exceeded",
    "503": "service unavailable"
  }
}
```

**Action Items:**
- [ ] Provide VPS API documentation
- [ ] Test API with curl command
- [ ] Verify response format with real example
- [ ] Document rate limits

---

#### 2. **No Fallback Chain Design**
**Problem:** What if your VPS is down?
- Should fall back to OpenAI? Groq? Both?
- Which one is cheapest?
- Which has best reliability?
- How long to wait before giving up?

**Current Fallback Plan (Placeholder):**
```
Your VPS → OpenAI → Groq → Mock
50ms timeout per level
```

**What's Needed:**
```markdown
## Your Fallback Preferences:

1. **Primary**: Your VPS AI Agents
   - Timeout: __ ms
   - Retry times: __
   - Cost: $__ per 1000 calls

2. **Secondary**: OpenAI (backup)
   - Cost: $__ per 1000 calls
   - Max calls/month budget: __

3. **Tertiary**: Groq LLaMA (free)
   - Cost: Free
   - Quality: 60% of GPT-4

4. **Last Resort**: Mock (no-think)
   - Cost: Free
   - Quality: 30% (random responses)
```

**Action Items:**
- [ ] Document fallback order preference
- [ ] Set timeouts per provider
- [ ] Document cost constraints
- [ ] Set up budget alerts

---

#### 3. **No Model Output Standardization**
**Problem:** Your model might output different JSON format than system expects

**System expects:**
```json
{
  "decision_type": "ENTRY",
  "confidence": 0.75,
  "rationale": "Price broke above EMA20 with volume",
  "market_regime": "trend",
  "order_spec": {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 10.0,
    "entry_price": 2500.0,
    "stop_loss_price": 2450.0,
    "take_profit_price": 2550.0,
    "leverage": 5.0
  },
  "checklist_results": [...],
  "risk_assessment": {...}
}
```

**Your model might output:** 
```json
{
  "action": "LONG",
  "score": 0.8,
  "reason": "bullish",
  "size": 1.5,
  "entry": 2500,
  "stop": 2450,
  "profit": 2550
}
```

**What's Needed:**
- Sample output from your model
- JSON schema documentation
- Field mapping rules
- Handle mismatches gracefully

**Action Items:**
- [ ] Provide sample outputs (5-10 examples)
- [ ] Document schema
- [ ] Create mapping layer in adapter

---

#### 4. **No Quota/Billing Structure**
**Problem:** Need to monitor usage without surprise 429 errors

**What's Needed:**
```yaml
Your VPS Quota Model:
  - Monthly cap: __ calls
  - Cost: $__ per month / per call
  - Warning threshold: 70%
  - Critical threshold: 85%
  - Email alerts: __
  - Billing contact: __
  - Payment method: __
```

**Action Items:**
- [ ] Define quota limits
- [ ] Set up billing alerts
- [ ] Provide API to check quota status
- [ ] Document cost calculations

---

#### 5. **No Failover/Health Check Testing**
**Problem:** Don't know how your VPS behaves under stress

**What's Needed:**
```
Load test results:
  - Latency (p50, p95, p99): __ ms
  - Throughput: __ req/sec
  - Error rate: __
  - Memory usage: __
  - CPU usage: __
  - Typical uptime: __
  - SLA: __
  
Health check endpoint:
  - URL: /health or /status
  - Expected response: {status: "okay"}
```

**Action Items:**
- [ ] Provide load test results
- [ ] Document health check endpoint
- [ ] Set up monitoring alerts
- [ ] Define SLA commitments

---

#### 6. **No Decision Quality Benchmarking**
**Problem:** Is the model better than OpenAI?

**What's Needed:**
```
Comparison vs OpenAI GPT-4:
  - Win rate: __ vs 55%
  - Avg profit per trade: $__ vs $2.50
  - Drawdown: __% vs 15%
  - Execution speed: __ ms vs 1000ms
  - Cost: $__ vs $0.03/call
```

**Action Items:**
- [ ] Run backtests against GPT-4
- [ ] Document performance metrics
- [ ] Identify where model excels
- [ ] Identify where model struggles

---

## Integration Roadmap (Once Issues Resolved)

### Week 1: Specification & Testing
- Receive VPS API documentation
- Create test adapter with sample calls
- Verify output format and parsing
- Test fallback chain

### Week 2: Adapter Development
- Create `ExternalAIAgentAdapter` class
- Implement quota tracking
- Add health checks
- Add error handling

### Week 3: Integration & Testing
- Integrate into `get_llm_adapter()` factory
- Run parallel tests (VPS vs OpenAI)
- Measure latency impact
- Test fallback scenarios

### Week 4: Monitoring & Deployment
- Set up quota alerts
- Configure logging
- Deploy to staging
- Production rollout

## Summary

**Integration is blocked on:**
1. ❌ VPS API specification (you need to provide)
2. ❌ Fallback strategy (you need to decide)
3. ❌ Output format mapping (you need samples)
4. ❌ Quota/billing terms (you need to define)
5. ❌ Performance benchmarks (you need to run)

**Once you provide these, integration takes 1-2 days.**

**Do you have:**
- [ ] VPS documentation?
- [ ] API examples?
- [ ] Sample decisions?
- [ ] Quota info?
- [ ] Performance metrics?
```

---

## Summary Table: What's Ready vs What's Needed

| Task | Status | Blocker | Action |
|------|--------|---------|--------|
| Strategy Profiler | ✅ Designed | None | Implement code |
| Session Management | ✅ Designed | None | Implement code |
| Quota Tracking | ✅ Designed | None | Implement code |
| External AI Adapter | ⚠️ Designed | VPS Spec | You provide |
| Learning Agent AutoApply | ✅ Designed | None | Implement code |

---

**Next Steps:**
1. Decide: Implement Session Management (4h) first
2. Implement: Strategy Profiler (3h) 
3. Implement: Quota Tracking (3h)
4. Provide: VPS AI Agents documentation
5. Then: Integrate External AI (3h)

Total for items 1-3: 10 hours
