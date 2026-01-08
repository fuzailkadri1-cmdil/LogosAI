# Logos AI - SMB-First AI Phone System

## Overview
Logos AI is an AI-powered phone system designed for small and medium retail/eCommerce businesses. It automates repetitive inbound calls like order status and store hours, while intelligently escalating complex issues to human agents.

## Current State (Prototype)
**Status:** Live and demo-ready for pilot customers

### What Works Today (2 AI Intents)
- AI order status lookup via CSV upload
- Store hours responses
- Intelligent human handoff/escalation
- Twilio phone integration
- Real-time analytics dashboard with Listen Mode
- Pilot customer management with CSV order upload
- Voicemail recording system
- **SSML voice optimization** for natural-sounding TTS (Tier 1)
- **Latency logging** to measure STT→LLM→TTS performance

### Coming Q1 2025
- FAQ responses (custom Q&A)
- Shopify integration (live order lookup)
- Stripe integration
- Returns & exchanges automation

### Target Customers
- SMB retail and eCommerce businesses
- 10-500 employees
- Looking to reduce call volume on repetitive queries

## Architecture

### Tech Stack
- **Backend:** Python Flask
- **Database:** PostgreSQL (via SQLAlchemy)
- **AI:** OpenAI GPT-4o-mini
- **Telephony:** Twilio
- **Frontend:** Bootstrap 5, Chart.js

### Key Files
- `app.py` - Main Flask application with all routes
- `models.py` - SQLAlchemy database models
- `ai_voice_agent.py` - OpenAI-powered voice AI agent
- `call_engine.py` - Call flow logic and intent routing
- `providers.py` - Telephony provider abstraction
- `ssml_helper.py` - SSML voice optimization (breaks, prosody, emphasis)
- `latency_logger.py` - Voice pipeline latency measurement

### Templates
- `templates/index.html` - Landing page (investor-focused)
- `templates/dashboard.html` - Main user dashboard
- `templates/pilots.html` - Pilot customer management
- `templates/roadmap.html` - Product roadmap
- `templates/investor_dashboard.html` - Investor metrics
- `templates/pricing.html` - Pricing page
- `templates/settings.html` - Company settings

## Roadmap

### Current (Phase 1) - Available Now
- Retail/eCommerce focus
- CSV order data upload
- 2 AI intents (OrderStatus, StoreHours) + Human Handoff + Voicemail
- Twilio integration
- Analytics dashboard with Listen Mode

### Q1 2025 (Phase 2) - Planned
- FAQ responses (custom Q&A)
- Shopify integration
- Stripe integration
- Returns & exchanges

### Q2-Q4 2025 (Phase 3) - Future
- Healthcare vertical
- Transportation vertical
- Salesforce/Zendesk integrations
- Multi-language support
- Advanced AI training

## Running the Application

The Flask server runs on port 5000:
```bash
python main.py
```

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - Flask session secret
- `SSML_ENABLED` - Enable/disable SSML voice optimization (default: true)
- OpenAI API key is managed via Replit integrations

## Voice Quality (Tier 1 SSML)
The voice AI uses SSML (Speech Synthesis Markup Language) for more natural-sounding responses:
- Natural pauses at punctuation (400ms after sentences, 200ms after commas)
- Emphasis on key words (order, delivered, help, sorry)
- Prosody adjustments for warmth (95% rate, -2% pitch)
- Uses Polly.Joanna voice (more natural than alice)

To disable SSML for rollback: Set `SSML_ENABLED=false` in environment variables

## User Preferences
- Company name: Logos AI
- Focus: SMB retail/eCommerce
- Honest about capabilities vs future features
- Clear "Future Feature" badges on upcoming functionality
