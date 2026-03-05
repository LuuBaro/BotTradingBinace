# 🔑 Binance API Key Regeneration Guide

## ❌ Problem
```
Status: 400
Response: {"code":-1022,"msg":"Signature for this request is not valid."}
```

This error means one of:
1. ✗ API key is invalid, revoked, or doesn't exist
2. ✗ API secret is wrong or was truncated
3. ✗ API key doesn't have permissions enabled
4. ✗ Using mainnet key instead of testnet

---

## ✅ Solution: Regenerate API Key

### Step 1: Go to Binance Testnet
```
https://testnet.binancefuture.com
```
(NOT https://www.binance.com - that's mainnet)

### Step 2: Account Settings
```
1. Click on your account icon (top-right)
2. Select "Account" or "API Management"
3. Look for "API keys" section
```

### Step 3: Delete Old Key (Optional)
```
1. Find existing API keys
2. Click "Delete" on any old/broken keys
3. Wait a moment for deletion
```

### Step 4: Create New API Key
```
1. Click "Create API"
2. Choose restrictions (recommend "IP Whitelist"):
   ☑ Testnet API key
   ☑ Restricted IP Access (optional - leave blank if using local)
   
3. Restrictions to enable:
   ☑ Futures API (must be enabled)
   ☑ Trading (for orders)
   ☑ Reading (for account info)
   ☑ Reading Account Trade Data
   ☑ My Trades (for history)
   
4. Copy the complete strings (**IMPORTANT: Copy completely!**)
   - API Key: fMMi318r4zyioqhLNlwY...
   - Secret Key: bnHaj62vMPMZ4gRh...
```

### Step 5: Update .env File
```env
# Windows Explorer
# 1. Open d:\BotTradingBinace\.env in Notepad
# 2. Find these lines:
BINANCE_API_KEY='YOUR_NEW_KEY_HERE'
BINANCE_API_SECRET='YOUR_NEW_SECRET_HERE'

# 3. Replace with new values (keep the quotes!)
# 4. Save file
```

### Step 6: Verify Changes
```bash
# Run verification script
.venv\Scripts\python.exe debug_signature.py

# If still getting 400, API key may not be valid
```

---

## ⚠️ Common Mistakes

| Mistake | Fix |
|---------|-----|
| Copied only part of key | Make sure you copy the **entire** string |
| Used mainnet key on testnet | Generate testnet key at testnet.binancefuture.com |
| Didn't enable Futures API | Must enable "Futures API" permission |
| Key not activated | Check email confirmation (might need to activate) |
| Used wrong account | Testnet keys only work on testnet.binance future.com |

---

## 🔍 How to Verify After Update

```bash
# Test 1: Check configuration
.venv\Scripts\python.exe debug_signature.py

# Test 2: Test connection
.venv\Scripts\python.exe test_binance_api_key.py

# If Status 200 on get account info → ✅ SUCCESS!
```

---

## 📱 If Issues Persist

1. **Check Binance Status**: https://twitter.com/binanceapi
2. **API Key might be locked** - Try again after 24 hours
3. **Use different key name** - Sometimes key conflicts cause issues
4. **Contact Binance Support** - testnet.binance.com/support

---

## ✅ Success Signs

```bash
✅ Test 3: Get account info (with signature)
   Status: 200
   ✓ SUCCESS! Account data retrieved
   Keys in response: [...account info...]
```

If you see Status 200, the API key is valid and working!
