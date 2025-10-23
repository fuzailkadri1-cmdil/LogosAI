# Call Center Automation Platform

## Overview
Multi-tenant SaaS platform for automating call centers with AI-powered voice assistants. Built with Flask, this platform provides pluggable telephony provider integrations (Twilio, Cisco Webex, SIP/VoIP), intelligent call routing with intent detection, and comprehensive analytics dashboards.

## Project Status
**Current State:** MVP Complete - Fully functional multi-tenant call center automation platform

## Recent Changes (October 23, 2025)
**AI Voice Agent Implementation (October 23, 2025):**
  - **Live AI Conversations:** Customers can now call and speak naturally with AI instead of pressing buttons
  - **Natural Language Understanding:** OpenAI GPT-4o-mini processes speech and generates human-like responses
  - **Intelligent Escalation:** AI automatically escalates to human agents for sensitive topics (refunds, billing, complaints), low confidence (<0.5), or explicit requests
  - **Conversation Tracking:** Full dialogue history stored in database with confidence scores and turn counts
  - **Enhanced Dashboard Metrics:** New AI performance cards showing average confidence (%), conversation turns, escalation rate (%), and AI resolution rate (%)
  - **Database Schema Updates:** Added 4 new fields to CallLog: ai_conversation, ai_confidence, conversation_turns, escalation_reason
  - **Twilio Speech Integration:** Webhooks now use Twilio's speech recognition for natural voice input

## Previous Updates (October 23, 2025)
- Initial project setup with Flask and SQLAlchemy
- Implemented multi-tenant architecture with Companies, Users, Integrations, CallLogs, and Voicemails tables
- Created pluggable telephony provider abstraction layer supporting Twilio, Cisco, and SIP providers
- Built AI-powered call flow engine with intent detection (OrderStatus, StoreHours, ConnectAgent, Voicemail)
- Implemented dynamic webhook routing for multi-tenant call handling
- Created complete onboarding wizard with provider setup interface
- Built admin dashboard with real-time analytics using Chart.js
- Added voicemail recording and company configuration features
- Implemented call simulation endpoint for testing without real calls
- **Enhanced UI/UX inspired by FlipCX:**
  - Redesigned landing page with industry-specific sections (eCommerce, Transportation, Healthcare)
  - Added conversational UI demos showing AI interactions
  - Implemented Listen Mode analytics for call pattern analysis and intent recommendations
  - Created ROI Calculator tool for cost savings projections
  - Built interactive Conversation Preview/Tester for real-time AI testing
  - Added Industry Templates for quick setup (eCommerce, Healthcare, Transportation)
  - Enhanced navigation with quick access to all features
- **Bug Fixes & Stability Improvements:**
  - Added delete integration functionality with confirmation dialog and proper authorization
  - Implemented fallback error handling for missing greetings to prevent call disconnections
  - Set default company settings (greeting, menu options, business hours) during registration
  - Fixed voice webhook crash by removing invalid provider_type parameter from log_call()
- **RedRoute-Inspired Enterprise Redesign (October 23, 2025):**
  - **Design System Update:** Replaced purple gradients with professional enterprise blue (#1e40af, #1e3a8a, #10b981) across all templates
  - **Market Data (USA + Canada):** Updated to accurate North America figures - TAM $25B, SAM $3.8B, SOM $190M, 3.05M jobs
  - **Industry Segmentation:** Added BFSI 21.7%, IT/Telecom 24.7%, Healthcare (fastest growth), Retail/eCommerce 53%
  - **Proven Metrics:** 50% automation rate (vs legacy 10%), $1.25→$0.25/call (80% cost reduction), $420K avg savings
  - **Competitive Positioning:** Added "Why We're Different" section - 1 day vs 12 months setup, $0 vs $1M+ upfront, SaaS vs consultants
  - **Pricing Model:** 30-day free trial, $0 upfront, performance-based pricing consistently messaged
  - **ROI Calculator:** Enhanced with RedRoute 20-seat example (840K calls/year, 50% automation, $420K savings)
  - **Demo Script:** Updated with Series A pitch positioning and accurate market statistics

## Key Features
1. **Multi-Tenant Architecture**: Complete company and user management system
2. **Onboarding Wizard**: Bootstrap-styled interface for telephony provider setup
3. **Pluggable Providers**: Abstraction layer supporting Twilio, Cisco Webex, and SIP/VoIP
4. **AI Call Flow**: Intent detection supporting both DTMF and speech input
5. **Dynamic Routing**: Webhook routing directing calls to correct company based on phone number
6. **Analytics Dashboard**: Real-time metrics with Chart.js visualizations
7. **Voicemail System**: Recording, storage, and transcription support per company
8. **Call Simulation**: Testing endpoint for integration validation
9. **Investor-Ready Tools**: 
   - Professional pricing page with 3-tier SaaS model
   - Complete demo script for 5-10 minute investor pitches
   - Step-by-step Twilio setup guide for live phone demos
   - Investor dashboard with market metrics, competitive analysis, and unit economics

## Project Structure
```
.
├── app.py                 # Main Flask application with all routes
├── models.py              # Database models (Company, User, Integration, CallLog, Voicemail)
├── providers.py           # Telephony provider abstraction layer
├── call_engine.py         # AI-powered call flow engine with intent detection
├── templates/             # HTML templates with Bootstrap 5
│   ├── base.html         # Base template with navigation
│   ├── index.html        # Landing page
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   ├── onboarding.html   # Provider setup wizard
│   ├── dashboard.html    # Admin dashboard with analytics
│   ├── settings.html     # Company configuration
│   ├── calls.html        # Call logs list
│   ├── call_detail.html  # Individual call details
│   └── voicemails.html   # Voicemail management
├── static/               # CSS and JavaScript files
├── callcenter.db         # SQLite database (auto-created)
└── replit.md             # This file
```

## Technology Stack
- **Backend**: Python 3.11, Flask, Flask-SQLAlchemy
- **Database**: SQLite
- **Telephony**: Twilio SDK (with abstraction for other providers)
- **Frontend**: Bootstrap 5, Chart.js, Vanilla JavaScript
- **Authentication**: Werkzeug password hashing, Flask sessions

## Database Schema
- **companies**: Company information, phone numbers, greetings, menu options, business hours
- **users**: User accounts with company association and role-based access
- **integrations**: Telephony provider configurations per company
- **call_logs**: Complete call history with intent, outcome, duration, transcripts
- **voicemails**: Recorded messages with transcription support

## Demo Account
- **Email**: demo@example.com
- **Password**: demo123
- **Company**: Demo Company
- **Phone**: +15555550100

## API Endpoints

### Public Routes
- `GET /` - Landing page
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /register` - Registration page
- `POST /register` - Create new account
- `GET /pricing` - SaaS pricing page (Starter/Professional/Enterprise)

### Protected Routes (require login)
- `GET /dashboard` - Main dashboard with analytics
- `GET /onboarding` - Provider setup wizard
- `POST /onboarding/provider` - Save provider integration
- `GET /settings` - Company configuration
- `POST /settings` - Update company settings
- `GET /calls` - Call logs list
- `GET /calls/<id>` - Call detail view
- `GET /voicemails` - Voicemail list
- `POST /voicemails/<id>/listen` - Mark voicemail as listened
- `GET /api/stats` - Analytics data (JSON)
- `POST /test_integration/<id>` - Test provider integration
- `GET /demo-script` - Investor pitch guide with talking points
- `GET /twilio-setup` - Complete Twilio configuration guide
- `GET /investor-dashboard` - Market metrics and business analytics

### Webhook Routes (for telephony providers)
- `POST /voice/webhook` - Initial call handler
- `POST /voice/handle_input` - Process DTMF/speech input
- `POST /voice/voicemail` - Voicemail recording handler

### Testing Routes
- `GET /simulate_call` - Simulate a call for testing (params: intent, caller)

## Configuration

### Environment Variables
- `SESSION_SECRET` - Flask session secret key (configured in Replit Secrets)
- `TWILIO_ACCOUNT_SID` - (Optional) Default Twilio Account SID
- `TWILIO_AUTH_TOKEN` - (Optional) Default Twilio Auth Token

### Company Settings (per tenant)
- Greeting message
- Menu options (up to 5 DTMF choices)
- Business hours (weekday/weekend)
- Escalation phone number for agent transfers

## Call Flow Logic

1. **Incoming Call** → `/voice/webhook`
   - Identify company by phone number
   - Load company configuration
   - Play greeting with menu options
   - Listen for DTMF or speech input

2. **Input Processing** → `/voice/handle_input`
   - Determine intent from user input
   - Route to appropriate handler:
     - OrderStatus: Look up order in database
     - StoreHours: Provide business hours
     - ConnectAgent: Transfer to escalation number
     - Voicemail: Start recording

3. **Intent Handlers**
   - Use keyword matching and DTMF mapping
   - Support context (e.g., order numbers)
   - Log all interactions to database

4. **Call Completion**
   - Update call log with outcome
   - Save voicemail if recorded
   - Generate analytics data

## Testing the Platform

### Without Real Phone Calls
```
# Simulate a call
http://localhost:5000/simulate_call?intent=OrderStatus&caller=+15551234567

# Or use the Conversation Preview tester in the dashboard
```

### With Twilio Integration
1. Follow the step-by-step guide at `/twilio-setup`
2. Set up Twilio account (free $15 trial credit)
3. Configure integration in Onboarding wizard
4. Point Twilio webhook to: `https://your-repl-url.repl.co/voice/webhook`
5. Call your Twilio number to test live

## Investor Demo Preparation

### Quick Start (5 minutes)
1. Visit `/pricing` to show your business model
2. Review `/demo-script` for pitch talking points
3. Open `/investor-dashboard` to display market metrics
4. Use `/roi-calculator` to demonstrate customer savings
5. Test AI with `/conversation-preview` during presentations

### Live Phone Demo (Optional)
- Follow `/twilio-setup` guide to get a real demo number
- $15 free Twilio credit = ~100 demo calls
- Investors can call and interact with your AI live

## Future Enhancements
- Real-time call monitoring dashboard with WebSocket updates
- Advanced AI using OpenAI for natural language understanding
- Zendesk/Salesforce integration for automatic ticket creation
- Cloud storage integration (S3/Google Cloud) for call recordings
- Role-based access control with company admin and agent roles
- REST API for third-party integrations
- Mobile app support
- SMS capabilities for call notifications

## User Preferences
None specified yet.

## Notes
- Server runs on port 5000 (required for Replit)
- Uses SQLite for simplicity (can migrate to PostgreSQL for production)
- Demo data automatically created on first run
- All providers use abstraction layer for easy extension
- Bootstrap 5 and Chart.js loaded from CDN
