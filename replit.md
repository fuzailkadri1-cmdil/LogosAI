# Call Center Automation Platform

## Overview
This is a multi-tenant SaaS platform designed to automate call centers using AI-powered voice assistants. It integrates with various telephony providers (Twilio, Cisco Webex, SIP/VoIP), offers intelligent call routing with intent detection, and provides comprehensive analytics. The platform aims to revolutionize call center operations by significantly increasing automation rates, reducing per-call costs, and shortening setup times compared to traditional solutions. Key capabilities include live AI conversations, multi-turn order lookup, intelligent escalation, and detailed performance metrics. The business vision is to capture a significant share of the North American call center automation market by offering an accessible, performant, and cost-effective solution for businesses of all sizes, with a particular focus on fast-growing sectors like healthcare, retail/eCommerce, and IT/Telecom.

## User Preferences
None specified yet.

## System Architecture
The platform is built on Python 3.11 using Flask and Flask-SQLAlchemy, with SQLite as the database (migratable to PostgreSQL). It features a multi-tenant architecture managing companies, users, integrations, call logs, and voicemails.

**UI/UX Decisions:**
- The frontend utilizes Bootstrap 5, Chart.js, and Vanilla JavaScript.
- Design incorporates a professional enterprise blue color scheme (`#1e40af`, `#1e3a8a`, `#10b981`) across all templates.
- Features a redesigned landing page with industry-specific sections, conversational UI demos, and an interactive Conversation Preview/Tester.
- Includes an ROI Calculator tool and Industry Templates for quick setup.
- Navigation is enhanced for quick access to all features.

**Technical Implementations & Feature Specifications:**
- **Pluggable Telephony Provider Abstraction:** Supports Twilio, Cisco Webex, and generic SIP/VoIP providers, allowing dynamic webhook routing to the correct company based on phone number.
- **AI-powered Call Flow Engine:** Employs intent detection (OrderStatus, StoreHours, ConnectAgent, Voicemail) for both DTMF and speech input.
- **AI Voice Agent:** Utilizes OpenAI GPT-4o-mini for natural language understanding and human-like responses. It supports multi-turn conversations, maintains conversation state (initial, waiting_for_order_number, offering_more_help, goodbye), and handles flexible order number matching. Optimized for speed with: shorter system prompts, reduced max_tokens (80), cached responses for common intents (store hours, goodbye, escalation), and limited conversation history to reduce API latency.
- **Intelligent Escalation:** AI automatically escalates to human agents for sensitive topics, low confidence scores (<0.5), or explicit requests.
- **Order Database Integration:** Includes a mock order database (`orders_db.py`) with 9 demo-ready orders using single-digit numbers (1-9) for optimal Twilio speech recognition. All orders feature full delivery addresses for realistic investor demos.
- **Speech Recognition Number Normalization:** Advanced `normalize_spoken_numbers()` function converts Twilio speech transcriptions ("one", "two", "three") to digits ("1", "2", "3"). Features two-tier pattern matching to prevent false positives (e.g., "I have 2 questions" won't extract "2"). Handles spoken numbers, comma-separated digits, and requires explicit order context ("order 1", "number is 1", "it's 1") for single-digit extractions.
- **Exact-Match Order Lookup:** `lookup_order()` uses exact matching for single-digit orders to prevent false positives (e.g., "111" won't match order "1"). Flexible substring matching is reserved for multi-digit orders (3+ characters).
- **Analytics Dashboard:** Real-time metrics and Chart.js visualizations display AI performance (average confidence, conversation turns, escalation rate, AI resolution rate) and overall call center performance.
- **Voicemail System:** Supports recording, storage, and transcription per company.
- **Onboarding Wizard:** A Bootstrap-styled interface guides setup of telephony providers.
- **Call Simulation Endpoint:** Allows testing without requiring live phone calls.
- **Investor-Ready Tools:** Includes a professional pricing page, a comprehensive demo script, a Twilio setup guide, and an investor dashboard with market metrics and competitive analysis.
- **Legal Documentation:** Professional Terms of Service (`/terms`) and Privacy Policy (`/privacy`) pages covering AI disclaimers, call recording consent, GDPR/CCPA compliance, data retention policies, and security measures. Footer links on all pages.

**System Design Choices:**
- **Robust Error Handling:** All webhooks return valid TwiML even on failures to prevent call drops.
- **Conversation Tracking:** Full dialogue history, confidence scores, and turn counts are stored in the database.
- **Dynamic Configuration:** Company-specific settings (greeting message, menu options, business hours, escalation numbers) are configurable per tenant.
- **Authentication:** Uses Werkzeug password hashing and Flask sessions for secure user access.

## External Dependencies
- **Telephony Services:** Twilio (SDK integrated), Cisco Webex, generic SIP/VoIP providers.
- **AI/NLP:** OpenAI GPT-4o-mini.
- **Frontend Libraries:** Bootstrap 5, Chart.js.