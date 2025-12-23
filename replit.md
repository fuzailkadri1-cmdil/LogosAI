# Logos AI - SMB-First AI Phone System

## Overview
Logos AI is an AI-powered phone system designed for small and medium retail/eCommerce businesses. It automates repetitive inbound calls like order status, pickup readiness, store hours, and FAQs, while intelligently escalating complex issues to human agents.

## Current State (Prototype)
**Status:** Live and demo-ready for pilot customers

### What Works Today
- AI order status lookup via CSV upload
- Store hours and FAQ responses
- Pickup readiness inquiries
- Intelligent human handoff/escalation
- Twilio phone integration
- Real-time analytics dashboard
- Pilot customer management with CSV order upload
- Voicemail recording system

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
- 4 core intents (OrderStatus, StoreHours, FAQs, Escalation)
- Twilio integration
- Analytics dashboard

### Q1 2025 (Phase 2) - Planned
- Shopify integration
- Stripe integration
- Returns & exchanges
- Subscription management

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
- OpenAI API key is managed via Replit integrations

## User Preferences
- Company name: Logos AI
- Focus: SMB retail/eCommerce
- Honest about capabilities vs future features
- Clear "Future Feature" badges on upcoming functionality
