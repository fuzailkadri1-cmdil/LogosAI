# Logos AI - Replit Prompts

## Prompt 1: Add Lead Capture (With After-Hours Handling)

```
I need to add a lead capture flow that behaves differently during business hours vs. after hours. Currently, when the AI doesn't know how to handle something (like a purchase inquiry), it just transfers directly.

DURING BUSINESS HOURS (store is open):
When the AI detects purchase intent or product inquiry (phrases like "do you have", "I'm looking for", "I want to buy", "is X in stock", "can I order"):

1. Capture their name: "Before I transfer you, can I get your name in case we get disconnected?"

2. Confirm what they want: "And you're looking for [what they mentioned] - any specific size/color/details?"

3. Save the lead (fields below)

4. Transfer to merchant's phone: "Great, let me transfer you now."

5. Proceed with existing transfer logic


AFTER HOURS (store is closed):
When the AI detects purchase intent or product inquiry:

1. Acknowledge we're closed: "Thanks for calling! We're currently closed, but I'd love to make sure someone helps you first thing."

2. Capture their name: "Can I get your name?"

3. Capture what they want: "And what are you looking for today?" (or confirm: "So you're looking for [what they mentioned] - any specific details like size or color?")

4. Confirm callback: "Perfect, [name]. Someone from our team will call you back when we open. Is [their phone number from caller ID] the best number to reach you?"
   - If yes: "Great, expect a call from us soon!"
   - If they give different number: Save that number instead

5. Save the lead and END the call (don't transfer - no one will answer)

6. Friendly close: "Thanks for calling [store name]. Talk to you soon!"


LEAD DATA TO SAVE:
- caller_name
- caller_phone (from caller ID, or the number they provide)
- inquiry (what they're looking for, as detailed as possible)
- timestamp
- call_type: "during_hours" or "after_hours"
- status: "new"

DISPLAY:
Show leads in the dashboard - either a new "Leads" section or add to call log with a "lead" tag. After-hours leads should be visually flagged so merchant knows to call back first thing.

NOTES:
- The AI should already know business hours from existing store configuration
- If caller doesn't give name, that's fine - capture what we can
- Don't change how order status, store hours, or pickup readiness calls work
- For during-hours calls, still transfer even if you captured lead info (they want to talk now)
- For after-hours calls, never transfer - just capture and confirm callback
```

---

## Prompt 2: Update Landing Page Pitch

```
I need to adjust the landing page messaging to lead with different value props. Keep the same overall structure and design, but change the hierarchy of benefits.

CURRENT STATE: Leading with revenue recovery ($3-5K/month recovered)

NEW MESSAGING PRIORITY:

1. LEAD WITH - Answer Rate & Availability:
   - "Never miss a call again"
   - "100% answer rate, 24/7"
   - "Every call answered in 2 rings"
   - Position as: your always-on AI receptionist

2. SECOND - Time Savings:
   - "Save 11+ hours per week"
   - "Free your staff to focus on in-store customers"
   - "Automate repetitive calls (order status, store hours, directions)"
   - "75% of calls handled without human intervention"

3. THIRD (keep but don't lead with) - Revenue Recovery:
   - Keep mentions of capturing after-hours opportunities
   - Keep the $3-5K/month stat but move it lower on the page
   - Frame it as an additional benefit, not the main hook

SPECIFIC CHANGES:
- Hero section: Change headline to focus on never missing calls / 24/7 coverage
- Move "11 hours/week saved" and "75% automation" stats higher
- Keep revenue recovery in a lower section, maybe "Plus, capture sales you'd otherwise miss"
- Update any CTAs that mention revenue to be more about coverage/automation

Keep the pricing ($500 pilot, $1000/month) and guarantee (60% automation) the same.
Keep the same overall visual design and layout.
```

---

## Usage Notes

**Priority:** Use Prompt 1 first to get lead capture working before outreach.

**Prompt 2 is optional** - once lead capture works, you can legitimately claim revenue recovery. Only use Prompt 2 if you want to soften claims until you have customer proof.
