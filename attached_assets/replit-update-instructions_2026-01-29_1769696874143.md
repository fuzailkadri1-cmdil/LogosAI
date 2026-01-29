# Replit Update Instructions
**Date:** 2026-01-29
**Update:** Context-Aware Intent Detection System

---

## What This Update Does

Fixes the issue where phrases like "I'm looking for my order status" were incorrectly triggering sales lead capture instead of being handled as order status inquiries.

**Before:** AI triggered on first few words ("I'm looking for" → sales lead)
**After:** AI analyzes full sentence context (has "my order" → order status)

---

## Files to Update in Replit

### 1. ai_voice_agent.py (MAIN UPDATE)

**Location:** Root directory of your Replit project

**Action:** Replace the ENTIRE file content with the code from:
`ai_voice_agent_2026-01-29.py`

**Key Changes:**
- New `ORDER_CONTEXT_WORDS` list (lines ~75-95)
- Updated `PURCHASE_INTENT_PHRASES` list (lines ~98-140)
- New `_has_order_context()` function
- New `_is_purchase_intent()` function
- Updated `_analyze_intent()` function with priority order

---

## Step-by-Step Update Process

### Step 1: Backup Current File
In Replit terminal:
```bash
cp ai_voice_agent.py ai_voice_agent_backup.py
```

### Step 2: Replace File Content
1. Open `ai_voice_agent.py` in Replit editor
2. Select all (Cmd+A or Ctrl+A)
3. Delete all content
4. Copy entire content from `ai_voice_agent_2026-01-29.py`
5. Paste into Replit editor
6. Save (Cmd+S or Ctrl+S)

### Step 3: Restart the Application
In Replit:
1. Click "Stop" button
2. Click "Run" button
3. Wait for server to start

### Step 4: Test the Changes
Use the Conversation Preview feature or make test calls:

**Test 1: Order Status (should NOT trigger lead capture)**
- Say: "I'm looking for my order status"
- Expected: AI asks for order number

**Test 2: Sales Inquiry (should trigger lead capture)**
- Say: "I'm looking for a red jacket"
- Expected: AI starts lead capture flow

**Test 3: Mixed Context (should route to order status)**
- Say: "Do you have info on my delivery"
- Expected: AI asks for order number (NOT lead capture)

---

## Rollback Instructions

If something goes wrong:

```bash
# In Replit terminal
cp ai_voice_agent_backup.py ai_voice_agent.py
```

Then restart the application.

---

## What Changed - Summary

### New ORDER_CONTEXT_WORDS (check these FIRST)
```
my order, my package, my delivery, my tracking, my shipment
the order, the package, the delivery
order status, order number, tracking number, delivery status
where is my, when will my, check on my, status of my
placed an order, made an order, i ordered
confirmation number, order id
```

### Updated PURCHASE_INTENT_PHRASES (check ONLY if no order context)
```
do you have, do you carry, do you sell
looking for a, looking for an, looking for some
looking to order, looking to buy, looking to get
i want to buy, i want to order
can i order, can i buy
in stock, available
how much is, price of, cost of
place an order
```

### New Priority Order in _analyze_intent()
1. Explicit human request → speak_to_human
2. Human-required keywords → refund/return/complaint
3. **ORDER CONTEXT → order_status** (NEW - before purchase)
4. Pickup readiness → pickup_readiness
5. Store hours → store_hours
6. Purchase intent → purchase_inquiry (only if no order context)
7. Default → general_inquiry

---

## Verification Checklist

After updating, verify these scenarios work correctly:

- [ ] "I'm looking for my order status" → Asks for order number
- [ ] "Do you have my tracking info" → Asks for order number
- [ ] "I placed an order last week" → Asks for order number
- [ ] "I'm looking for a red jacket" → Starts lead capture
- [ ] "Do you have Nike shoes" → Starts lead capture
- [ ] "I'm looking to order a gift" → Starts lead capture
- [ ] "What time do you close" → Gives store hours
- [ ] "I want a refund" → Escalates to human/callback
- [ ] "Let me speak to someone" → Escalates to human/callback

---

## Support

If you encounter issues:
1. Check Replit logs for errors
2. Verify the file was saved correctly
3. Restart the application
4. Test with conversation preview first
5. Rollback if needed using backup

---

## Files in This Update Package

1. `ai_voice_agent_2026-01-29.py` - Complete updated code file
2. `intent-detection-spec_2026-01-29.md` - Technical specification
3. `replit-update-instructions_2026-01-29.md` - This file
4. `Claude_2026-01-29.md` - Updated Claude.md documentation
5. `logos-ai-prd_2026-01-29.md` - Updated PRD with technical spec
