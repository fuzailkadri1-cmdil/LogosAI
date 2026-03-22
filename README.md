# Logos AI — SMB AI Phone Receptionist

Logos AI is a 24/7 AI voice receptionist for local retail stores. It answers every inbound call, handles common requests automatically, and captures sales leads when staff are unavailable — so no customer call goes unanswered.

---

## What It Does

| Caller says... | What happens |
|---|---|
| "What are your store hours?" | AI answers immediately from configured hours |
| "Can I check my order status?" | AI looks up the order number in the database |
| "I'm looking for a sport watch in black" | AI captures name + inquiry + callback number as a lead |
| "I need a refund" | AI transfers to staff (during hours) or captures callback (after hours) |
| "Can I speak to someone?" | AI transfers or captures callback, depending on time of day |

Leads are logged in real time and visible in the dashboard. Store owners call back captured leads to close the sale.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Database | PostgreSQL via SQLAlchemy |
| AI | OpenAI GPT-4o-mini (via Replit AI Integrations) |
| Telephony | Twilio (inbound calls, TTS via Amazon Polly Neural) |
| Frontend | Bootstrap 5, Chart.js |
| Auth | Replit Auth (OAuth) |

---

## Project Structure

```
logos-ai/
├── main.py              # Entry point — starts Flask dev server
├── app.py               # All Flask routes (dashboard, webhooks, leads, pilots)
├── models.py            # SQLAlchemy models (Company, CallLog, Lead, etc.)
├── ai_voice_agent.py    # Core AI conversation engine
├── call_engine.py       # Legacy DTMF call router + call logging utilities
├── business_hours.py    # Store hours parsing and open/closed detection
├── providers.py         # Telephony abstraction (Twilio, Cisco, SIP)
├── ssml_helper.py       # TTS formatting utilities and text sanitisation
├── latency_logger.py    # Pipeline latency measurement (STT → LLM → TTS)
├── orders_db.py         # Mock order database for demo/testing
└── templates/
    ├── dashboard.html   # Main analytics dashboard
    ├── leads.html       # Captured leads management
    ├── pilots.html      # Pilot customer + CSV order upload
    ├── settings.html    # Company configuration (greeting, hours, escalation)
    ├── index.html       # Public landing page
    ├── roadmap.html     # Product roadmap
    ├── pricing.html     # Pricing page
    └── investor_dashboard.html
```

---

## Environment Variables

Set these in your Replit Secrets panel (or `.env` locally):

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SESSION_SECRET` | Yes | Flask session signing secret (any random string) |
| `TWILIO_ACCOUNT_SID` | Yes | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Yes | Your Twilio Auth Token |
| `AI_INTEGRATIONS_OPENAI_BASE_URL` | Yes | Provided automatically by Replit AI Integrations |
| `AI_INTEGRATIONS_OPENAI_API_KEY` | Yes | Provided automatically by Replit AI Integrations |
| `SSML_ENABLED` | No | Set to `true` to enable SSML voice formatting (disabled by default — see note below) |

> **Note on SSML:** SSML is currently disabled because Twilio's Python SDK HTML-escapes XML tags inside `<Say>`, causing tags to be read aloud. The `Polly.Joanna-Neural` voice handles natural pacing without SSML.

---

## Local Setup

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd logos-ai
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the variables listed above into your environment. On Replit, use the Secrets panel. Locally, create a `.env` file and load it with `python-dotenv`.

### 3. Set up the database

The application creates all tables automatically on first run via SQLAlchemy's `db.create_all()`. Just make sure `DATABASE_URL` is set to a valid PostgreSQL connection string.

```
postgresql://user:password@localhost:5432/logosai
```

### 4. Run the server

```bash
python main.py
```

The server starts on **http://localhost:5000**.

---

## Twilio Setup

### Configure your Twilio number webhook

1. Log in to [console.twilio.com](https://console.twilio.com)
2. Go to **Phone Numbers → Manage → Active Numbers**
3. Click your number
4. Under **Voice & Fax → A CALL COMES IN**, set:
   - **Webhook:** `https://your-domain.com/voice/webhook`
   - **Method:** `HTTP POST`
5. Save

### Point the number to a pilot store

1. Log in to Logos AI
2. Go to **Pilot Customers** → add a pilot store
3. Enter the Twilio number assigned to that store
4. The webhook will automatically match incoming calls to the right store

---

## Key Flows

### Inbound call flow

```
Call arrives at Twilio number
    ↓
POST /voice/webhook
    ↓  Looks up company by phone number
    ↓  Plays greeting
POST /voice/ai_conversation  (each turn)
    ↓  Detects intent (OpenAI GPT-4o-mini)
    ↓  Handles intent:
       ├─ order_status      → look up order, speak result
       ├─ store_hours       → speak configured hours
       ├─ purchase_inquiry  → capture lead (name + inquiry + phone)
       ├─ refund/complaint  → escalate or offer callback
       └─ speak_to_human   → transfer or capture callback
```

### Lead capture flow

```
Caller: "I'm looking for a sport watch in black"
AI detects: purchase_inquiry
    ↓
AI asks for name
    ↓
If caller already gave details → skip to callback confirmation
If not → ask for details
    ↓
AI confirms callback number (last 4 digits of caller's number)
    ↓
Lead saved to database
Store owner sees lead in Leads dashboard
Store owner calls back to close the sale
```

### Intent priority order

The AI evaluates each caller turn in this priority order:

1. Explicit human request → escalate immediately
2. Human-required keywords (refund, return, complaint) → escalate or callback
3. Order context ("my order", "tracking") → order_status
4. Pickup phrases → pickup_readiness
5. Store hours phrases → store_hours
6. Purchase intent ("I'm looking for") → purchase_inquiry
7. Default → general_inquiry

---

## Dashboard Features

- **Live call stats** — total calls, AI resolution rate, leads captured, escalations
- **ROI calculator** — estimates monthly revenue recovered from answered calls
- **Listen Mode** — real-time call transcript viewer
- **Leads dashboard** — all captured leads with status tracking (new / contacted / closed)
- **Call history** — full conversation transcripts for every call
- **Pilot management** — manage pilot stores and upload order CSVs

---

## Roadmap

### Now (Phase 1)
- Order status lookup via CSV upload
- Store hours responses
- Purchase inquiry lead capture
- Human escalation + callback flow
- Twilio integration
- Analytics dashboard + leads dashboard

### Q1 2025 (Phase 2)
- FAQ responses (custom Q&A per store)
- Shopify integration (live order lookup)
- Stripe integration

### Q2–Q4 2025 (Phase 3)
- Healthcare vertical
- Multi-language support (French for Montreal market)
- Salesforce / Zendesk integrations
- OpenAI Realtime API for lower latency and more natural voice

---

## Voice Quality Note

The current voice uses **Amazon Polly Joanna Neural** (`Polly.Joanna-Neural`), which is significantly more natural than standard Polly voices. For production deployments requiring Boardy-level voice quality, the next step is migrating to the **OpenAI Realtime API**, which handles STT + LLM + TTS in a single streaming WebSocket connection and reduces response latency from ~1.5s to ~300ms.

---

## Target Customers

Local retail stores in Montreal and Toronto:
- Boutique clothing, electronics, furniture, specialty food, gift shops
- 20–40 inbound calls per day
- Losing $30,000–$40,000/year to missed after-hours calls

---

## License

Proprietary — Logos AI. All rights reserved.




