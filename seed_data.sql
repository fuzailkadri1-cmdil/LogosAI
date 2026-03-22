-- =============================================================================
-- Logos AI — Seed Data
-- PostgreSQL INSERT statements for demo / development use.
--
-- Covers: companies, users, integrations, pilot_customers,
--         call_logs (15), leads (10), voicemails (5)
--
-- All IDs start at 100 to avoid collisions with rows already created by
-- the application. Sequence values are reset at the end of the file.
-- Run in psql:  \i seed_data.sql
-- =============================================================================

-- Turn off deferred constraint checks so we can insert in any order
SET session_replication_role = replica;

-- =============================================================================
-- COMPANIES
-- =============================================================================

INSERT INTO companies (id, name, phone_number, created_at, is_active,
    greeting_message, menu_options, business_hours, escalation_number)
VALUES
(100,
 'La Bella Trattoria',
 '+15143210001',
 '2026-01-08 10:00:00',
 true,
 'Ciao! Thanks for calling La Bella Trattoria. How can I help you today?',
 '{"1": "Reservations", "2": "Hours & Location", "3": "Speak to Staff"}',
 '{"tuesday-friday": "11am-10pm", "saturday-sunday": "10am-11pm", "monday": "closed"}',
 '+15143219999'),

(101,
 'ProFix Plumbing',
 '+14165550182',
 '2026-01-15 09:00:00',
 true,
 'Thanks for calling ProFix Plumbing! We''re available 24/7 for emergencies. How can I help?',
 '{"1": "Get a Quote", "2": "Emergency Service", "3": "Hours & Location", "4": "Speak to a Plumber"}',
 '{"monday-friday": "7am-6pm", "saturday": "8am-4pm", "sunday": "emergency only"}',
 '+14165550199');

-- =============================================================================
-- USERS
-- =============================================================================
-- Passwords (Werkzeug scrypt hashes):
--   marco@labellat.ca   → Trattoria2024!
--   sarah@profixplumbing.ca → ProFix2024!
--   james@profixplumbing.ca → Plumber99!

INSERT INTO users (id, email, first_name, last_name, profile_image_url,
    company_id, is_admin, role, created_at, updated_at, is_active, password_hash)
VALUES
('d9284a0c-06f5-4cf7-8a41-b878c48c3fe3',
 'marco@labellat.ca',
 'Marco',
 'Rossi',
 NULL,
 100,
 true,
 'admin',
 '2026-01-08 10:05:00',
 '2026-01-08 10:05:00',
 true,
 'scrypt:32768:8:1$fPJY8873ltGadmNv$7b70abb90d8e802f16d225f11d38ffb5fc2fffc9c7a2382ff5970940ce5fbc371f47573c9be41ba5250a4ceb2c7d5a9634cf052468979962f2075b92c5ec3906'),

('2f304558-3681-44bf-bc1d-808c3ae045c6',
 'sarah@profixplumbing.ca',
 'Sarah',
 'Kowalski',
 NULL,
 101,
 true,
 'admin',
 '2026-01-15 09:10:00',
 '2026-01-15 09:10:00',
 true,
 'scrypt:32768:8:1$wGTWSFaUxM4Ws5LV$634e407a934e0fef8f868ed505a00ed4390ddfa5e617e978545e4e4570aced5044d4e6f8abc1c74f1a62cb23a81e2faca8293d83c73eb1478e140404baa47535'),

('b668118e-5afe-451f-8f44-766333f0ef4f',
 'james@profixplumbing.ca',
 'James',
 'Tremblay',
 NULL,
 101,
 false,
 'user',
 '2026-01-16 08:00:00',
 '2026-01-16 08:00:00',
 true,
 'scrypt:32768:8:1$kqZYMf7Q4gkJNdav$2b3f0b17e010fdfd73afb660578357e027742a5af0fad26b94426c4bc6ccf846bcff089e680a81434aca88d9e1cb370c6935ad2554162469cf9b9d73ceb5bf76');

-- =============================================================================
-- INTEGRATIONS
-- =============================================================================

INSERT INTO integrations (id, company_id, provider_type, provider_name,
    config, is_active, created_at, last_tested, test_status)
VALUES
(100,
 100,
 'twilio',
 'Twilio Voice',
 '{"account_sid": "ACdemo00000000000000000000trattoria", "auth_token": "demo_token_trattoria", "phone_number": "+15143210001"}',
 true,
 '2026-01-08 10:30:00',
 '2026-03-20 08:00:00',
 'success'),

(101,
 101,
 'openai',
 'OpenAI GPT-4o-mini',
 '{"model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 300}',
 true,
 '2026-01-15 09:45:00',
 '2026-03-20 07:55:00',
 'success');

-- =============================================================================
-- PILOT CUSTOMERS
-- =============================================================================

INSERT INTO pilot_customers (id, company_id, name, industry, contact_email,
    contact_phone, twilio_number, start_date, end_date, status, notes, created_at)
VALUES
(100,
 100,
 'La Bella Trattoria',
 'Restaurant',
 'marco@labellat.ca',
 '+15143210001',
 '+15143210001',
 '2026-01-08 00:00:00',
 NULL,
 'active',
 'Italian restaurant in Montreal Plateau. ~25 calls/day. Peak times Fri-Sun evenings. Owners speak French and Italian — AI greets in English per their request.',
 '2026-01-08 10:00:00'),

(101,
 101,
 'ProFix Plumbing',
 'Home Services',
 'sarah@profixplumbing.ca',
 '+14165550182',
 '+14165550182',
 '2026-01-15 00:00:00',
 NULL,
 'active',
 'Residential & light commercial plumbing in Toronto East. Emergency line active 24/7. ~18 calls/day. High lead value — average job $650 CAD.',
 '2026-01-15 09:00:00');

-- =============================================================================
-- CALL LOGS  (15 calls spread across both companies, last 30 days)
-- =============================================================================

INSERT INTO call_logs (id, company_id, caller_phone, call_sid, intent, outcome,
    duration_seconds, transcript, provider_type, created_at, completed_at,
    handled_by_ai, ai_conversation, ai_confidence, conversation_turns,
    escalation_reason, pilot_id)
VALUES

-- ── La Bella Trattoria calls ──────────────────────────────────────────────────

(100, 100, '+15141112233', 'CA1000000000000000000000000000001',
 'store_hours', 'resolved', 28,
 'Caller asked what time the restaurant opens on Saturday. AI answered correctly (10am). Call resolved.',
 'twilio', '2026-02-20 11:14:00', '2026-02-20 11:14:28', true,
 '[{"role":"assistant","content":"Ciao! Thanks for calling La Bella Trattoria. How can I help you today?"},{"role":"user","content":"Hi yeah what time do you open on Saturday?"},{"role":"assistant","content":"We open at 10 in the morning on Saturdays and stay open until 11pm. Is there anything else I can help with?"},{"role":"user","content":"No that''s perfect thanks."},{"role":"assistant","content":"Great! Hope to see you Saturday. Ciao!"}]',
 0.97, 4, NULL, 100),

(101, 100, '+15149887766', 'CA1000000000000000000000000000002',
 'purchase_inquiry', 'resolved', 67,
 'Caller looking for a private dining room for a birthday party of 12. AI captured lead: name Sophie Lavoie, callback +15149887766. After-hours call.',
 'twilio', '2026-02-21 22:31:00', '2026-02-21 22:32:07', true,
 '[{"role":"assistant","content":"Ciao! Thanks for calling La Bella Trattoria. How can I help you today?"},{"role":"user","content":"Hi, I''m looking to book a private space for a birthday dinner, about 12 people."},{"role":"assistant","content":"How lovely! We do have a private dining area perfect for groups. Can I get your name?"},{"role":"user","content":"It''s Sophie, Sophie Lavoie."},{"role":"assistant","content":"Great Sophie! And what''s the best callback number for our team?"},{"role":"user","content":"Same number I''m calling from, 514-988-7766."},{"role":"assistant","content":"Perfect. Someone from La Bella Trattoria will give you a call back first thing when we open tomorrow. Ciao!"}]',
 0.94, 6, NULL, 100),

(102, 100, '+15143334455', 'CA1000000000000000000000000000003',
 'complaint', 'escalated', 42,
 'Caller complained that a reservation was lost last Saturday — party of 6 had no table when they arrived. AI escalated to staff.',
 'twilio', '2026-02-24 19:45:00', '2026-02-24 19:45:42', true,
 '[{"role":"assistant","content":"Ciao! Thanks for calling La Bella Trattoria. How can I help you today?"},{"role":"user","content":"Yes I''m calling because we had a reservation last Saturday and when we showed up you had no record of it. There were six of us and we had to leave."},{"role":"assistant","content":"I''m really sorry to hear that — that sounds very frustrating. Let me connect you with a team member right away who can look into this for you."}]',
 0.91, 3, 'reservation complaint', 100),

(103, 100, '+15146667788', 'CA1000000000000000000000000000004',
 'store_hours', 'resolved', 22,
 'Caller asked if restaurant is open on Mondays. AI correctly said closed Mondays.',
 'twilio', '2026-02-25 13:00:00', '2026-02-25 13:00:22', true,
 '[{"role":"assistant","content":"Ciao! Thanks for calling La Bella Trattoria. How can I help you today?"},{"role":"user","content":"Are you guys open on Mondays?"},{"role":"assistant","content":"We''re actually closed on Mondays. We''re open Tuesday through Friday from 11am to 10pm, and weekends from 10am to 11pm. Would another day work for you?"},{"role":"user","content":"Okay, I''ll come Thursday then. Thanks!"},{"role":"assistant","content":"Perfect, see you Thursday! Ciao!"}]',
 0.98, 4, NULL, 100),

(104, 100, '+15147778899', 'CA1000000000000000000000000000005',
 'purchase_inquiry', 'resolved', 89,
 'Caller wants catering for a corporate lunch, 30 people. AI captured lead: name Daniel Fontaine, callback +15147778899. During business hours — lead flagged for staff follow-up.',
 'twilio', '2026-02-26 14:22:00', '2026-02-26 14:23:29', true,
 '[{"role":"assistant","content":"Ciao! Thanks for calling La Bella Trattoria. How can I help you today?"},{"role":"user","content":"Hi, I''m looking into catering options for a corporate lunch event we''re planning, about 30 people."},{"role":"assistant","content":"Wonderful! We do offer catering. Can I grab your name so our catering coordinator can follow up?"},{"role":"user","content":"Sure, it''s Daniel Fontaine."},{"role":"assistant","content":"Great Daniel! And what''s a good number to reach you?"},{"role":"user","content":"514-777-8899"},{"role":"assistant","content":"Perfect. Our team will give you a call shortly to discuss the details. Is there anything else I can help with?"},{"role":"user","content":"No, that''s everything."},{"role":"assistant","content":"Wonderful, speak soon! Ciao!"}]',
 0.93, 8, NULL, 100),

(105, 100, '+15148889900', 'CA1000000000000000000000000000006',
 'human_requested', 'escalated', 18,
 'Caller immediately asked to speak with a person. AI transferred during business hours.',
 'twilio', '2026-03-01 12:05:00', '2026-03-01 12:05:18', true,
 '[{"role":"assistant","content":"Ciao! Thanks for calling La Bella Trattoria. How can I help you today?"},{"role":"user","content":"Can I speak to someone please?"},{"role":"assistant","content":"Of course! Let me connect you with a team member right now. One moment please."}]',
 0.99, 2, 'human requested', 100),

(106, 100, '+15141234567', 'CA1000000000000000000000000000007',
 'purchase_inquiry', 'resolved', 74,
 'Caller asking about gluten-free and vegan menu options for a dinner party. AI captured lead: name Emma Gagnon, callback +15141234567. After-hours.',
 'twilio', '2026-03-04 21:15:00', '2026-03-04 21:16:14', true,
 '[{"role":"assistant","content":"Ciao! Thanks for calling La Bella Trattoria. How can I help you today?"},{"role":"user","content":"Hi, I''m planning a dinner for some friends and a few of them have dietary restrictions — gluten-free and vegan. Do you accommodate that?"},{"role":"assistant","content":"We do have gluten-free pasta options and a few vegan dishes on our menu. Our team would love to walk you through the options and help plan something special. Can I get your name?"},{"role":"user","content":"Emma, Emma Gagnon."},{"role":"assistant","content":"And the best number to reach you, Emma?"},{"role":"user","content":"514-123-4567."},{"role":"assistant","content":"Perfect. Someone from La Bella Trattoria will call you back first thing when we open. Ciao!"}]',
 0.92, 6, NULL, 100),

-- ── ProFix Plumbing calls ─────────────────────────────────────────────────────

(107, 101, '+14161112222', 'CA1000000000000000000000000000008',
 'purchase_inquiry', 'resolved', 95,
 'Caller needs a hot water tank replaced. AI captured lead: name Kevin Martel, callback +14161112222. After-hours call.',
 'twilio', '2026-02-19 20:45:00', '2026-02-19 20:46:35', true,
 '[{"role":"assistant","content":"Thanks for calling ProFix Plumbing! We''re available 24/7 for emergencies. How can I help?"},{"role":"user","content":"Hey, my hot water tank is on its last legs. I need someone to come take a look and probably replace it."},{"role":"assistant","content":"Absolutely, we can help with that. Hot water tank replacements are one of our specialties. Can I get your name?"},{"role":"user","content":"Kevin Martel."},{"role":"assistant","content":"And the best number to reach you, Kevin?"},{"role":"user","content":"416-111-2222."},{"role":"assistant","content":"Got it. One of our plumbers will give you a call back first thing when we open tomorrow. Is there anything else I can help with?"},{"role":"user","content":"Nope, that''s it. Thanks."},{"role":"assistant","content":"No problem Kevin, speak soon!"}]',
 0.95, 8, NULL, 101),

(108, 101, '+14163334444', 'CA1000000000000000000000000000009',
 'purchase_inquiry', 'resolved', 81,
 'Caller reporting a slow drain in the master bathroom and kitchen sink. AI captured lead: name Linda Osei, callback +14163334444. During hours.',
 'twilio', '2026-02-22 10:30:00', '2026-02-22 10:31:51', true,
 '[{"role":"assistant","content":"Thanks for calling ProFix Plumbing! How can I help you today?"},{"role":"user","content":"Hi, I''ve got a really slow drain in my master bathroom and also in the kitchen sink. It''s been going on for about two weeks."},{"role":"assistant","content":"That sounds like a clog that needs clearing — definitely something we can take care of. Can I get your name?"},{"role":"user","content":"Linda Osei."},{"role":"assistant","content":"Great Linda. And the best number for our team to call you back?"},{"role":"user","content":"416-333-4444."},{"role":"assistant","content":"Perfect. One of our plumbers will be in touch shortly to schedule a visit. Is there anything else?"},{"role":"user","content":"No that''s it, thank you."}]',
 0.96, 6, NULL, 101),

(109, 101, '+14165556666', 'CA1000000000000000000000000000010',
 'complaint', 'escalated', 54,
 'Caller upset that a plumber arrived 3 hours late for a scheduled appointment last week with no call ahead. AI escalated to senior staff.',
 'twilio', '2026-02-23 09:15:00', '2026-02-23 09:15:54', true,
 '[{"role":"assistant","content":"Thanks for calling ProFix Plumbing! How can I help you today?"},{"role":"user","content":"Yeah, I''m calling because one of your guys showed up three hours late last Tuesday for an appointment I booked and nobody called ahead to warn me. I had to take the whole day off work."},{"role":"assistant","content":"I''m really sorry that happened — that''s not the experience we want you to have at all. Let me connect you with a senior team member right away who can make this right."}]',
 0.90, 3, 'service delay complaint', 101),

(110, 101, '+14167778888', 'CA1000000000000000000000000000011',
 'store_hours', 'resolved', 31,
 'Caller asked if ProFix does weekend appointments. AI explained Saturday hours and Sunday emergency-only policy.',
 'twilio', '2026-02-27 16:50:00', '2026-02-27 16:50:31', true,
 '[{"role":"assistant","content":"Thanks for calling ProFix Plumbing! How can I help?"},{"role":"user","content":"Do you guys work on weekends?"},{"role":"assistant","content":"We do! We''re available Saturday 8am to 4pm for regular service calls. Sundays are emergency-only. Would you like to schedule a Saturday appointment?"},{"role":"user","content":"Yeah Saturday would work great."},{"role":"assistant","content":"Excellent — our team will be happy to book that in. Let me get you connected. One moment!"}]',
 0.97, 4, NULL, 101),

(111, 101, '+14169990011', 'CA1000000000000000000000000000012',
 'purchase_inquiry', 'resolved', 112,
 'Caller needs a bathroom renovation quote — full fixture replacement, new tile, new vanity. AI captured lead: name Amanda Chen, callback +14169990011. After-hours.',
 'twilio', '2026-03-02 21:08:00', '2026-03-02 21:09:52', true,
 '[{"role":"assistant","content":"Thanks for calling ProFix Plumbing! How can I help you today?"},{"role":"user","content":"Hi, I''m renovating my main bathroom and I need someone to come give me a quote. I''m thinking new toilet, new vanity, new shower fixtures, and I might want to move a drain."},{"role":"assistant","content":"That sounds like a full bathroom reno — definitely something our team handles. Let me make sure someone gets back to you to set up an estimate. Can I get your name?"},{"role":"user","content":"Amanda Chen."},{"role":"assistant","content":"And a good number to reach you?"},{"role":"user","content":"416-999-0011."},{"role":"assistant","content":"Perfect Amanda. One of our senior plumbers will call you back first thing when we open. These renovation quotes usually take about 45 minutes on-site. Is there anything else?"},{"role":"user","content":"No that covers it, thanks a lot."},{"role":"assistant","content":"Talk soon!"}]',
 0.93, 8, NULL, 101),

(112, 101, '+14162223333', 'CA1000000000000000000000000000013',
 'purchase_inquiry', 'resolved', 68,
 'Caller has a pipe burst in the basement — treated as emergency. AI captured lead: name Robert Singh, callback +14162223333. After-hours emergency.',
 'twilio', '2026-03-05 02:14:00', '2026-03-05 02:15:08', true,
 '[{"role":"assistant","content":"Thanks for calling ProFix Plumbing! We''re available 24/7 for emergencies. How can I help?"},{"role":"user","content":"Yes hi, I''ve got water coming out of a pipe in my basement right now. It''s bad."},{"role":"assistant","content":"Okay, that''s definitely an emergency — let''s get someone out to you. Can I get your name?"},{"role":"user","content":"Robert Singh."},{"role":"assistant","content":"And your callback number Robert?"},{"role":"user","content":"416-222-3333."},{"role":"assistant","content":"Got it. I''m flagging this as an emergency and someone will call you back within minutes. In the meantime, if you can, locate your main water shutoff valve and turn it off to stop the flow. Is that possible?"},{"role":"user","content":"Yes I''ll do that now."},{"role":"assistant","content":"Perfect. Help is on the way Robert."}]',
 0.94, 8, 'emergency pipe burst', 101),

(113, 101, '+14164445555', 'CA1000000000000000000000000000014',
 'human_requested', 'escalated', 14,
 'Caller asked to speak to a plumber directly. AI transferred immediately during business hours.',
 'twilio', '2026-03-10 11:30:00', '2026-03-10 11:30:14', true,
 '[{"role":"assistant","content":"Thanks for calling ProFix Plumbing! How can I help?"},{"role":"user","content":"I just need to speak to one of your plumbers directly, please."},{"role":"assistant","content":"Absolutely, let me connect you right now. One moment!"}]',
 0.99, 2, 'human requested', 101),

(114, 101, '+14166667777', 'CA1000000000000000000000000000015',
 'purchase_inquiry', 'resolved', 88,
 'Caller wants quote for backwater valve installation (recent basement flood). AI captured lead: name Patricia Nguyen, callback +14166667777. After-hours.',
 'twilio', '2026-03-15 23:04:00', '2026-03-15 23:05:28', true,
 '[{"role":"assistant","content":"Thanks for calling ProFix Plumbing! How can I help?"},{"role":"user","content":"Hi, we had a bit of a flood situation in our basement during the last big rain and our neighbour said we should get a backwater valve installed. I''d like to get a quote for that."},{"role":"assistant","content":"That''s a really smart move — a backwater valve is great protection. We install those regularly. Can I get your name so our team can follow up?"},{"role":"user","content":"Patricia Nguyen."},{"role":"assistant","content":"And a good number for you, Patricia?"},{"role":"user","content":"416-666-7777."},{"role":"assistant","content":"Perfect. One of our plumbers will call you back first thing in the morning. These installations typically take half a day and may be partially covered by your home insurance — our team can walk you through that too. Is there anything else?"},{"role":"user","content":"No, that''s great. Thank you!"},{"role":"assistant","content":"Our pleasure, Patricia. Talk soon!"}]',
 0.95, 8, NULL, 101);

-- =============================================================================
-- VOICEMAILS  (5 — linked to call logs above where applicable)
-- =============================================================================

INSERT INTO voicemails (id, company_id, call_log_id, caller_phone,
    recording_url, transcription, duration_seconds, is_listened, created_at)
VALUES

(100, 100, NULL, '+15142223333',
 'https://api.twilio.com/2010-04-01/Accounts/ACdemo/Recordings/RE_demo_vm100.mp3',
 'Hi, this is Antoine Bergeron calling. I was hoping to make a reservation for next Friday night, table for four around 7:30. Please call me back at 514-222-3333. Thanks.',
 19, false,
 '2026-02-28 20:45:00'),

(101, 100, NULL, '+15144445555',
 'https://api.twilio.com/2010-04-01/Accounts/ACdemo/Recordings/RE_demo_vm101.mp3',
 'Hello, I''d like to order a gift card for my mother''s birthday. Could someone call me back? My number is 514-444-5555. Thank you.',
 14, true,
 '2026-03-03 14:12:00'),

(102, 101, 112, '+14162223333',
 'https://api.twilio.com/2010-04-01/Accounts/ACdemo/Recordings/RE_demo_vm102.mp3',
 'This is Robert Singh. I called earlier about a burst pipe — I''ve shut off the main water but I still really need someone tonight. Please call me back as soon as possible, it''s 416-222-3333.',
 22, true,
 '2026-03-05 02:18:00'),

(103, 101, NULL, '+14168889900',
 'https://api.twilio.com/2010-04-01/Accounts/ACdemo/Recordings/RE_demo_vm103.mp3',
 'Hey, my name is Thomas Wright and I''m looking for a quote on installing a new sump pump. My basement flooded twice last year. Call me at 416-888-9900 whenever you get a chance.',
 18, false,
 '2026-03-08 09:30:00'),

(104, 101, NULL, '+14161230000',
 'https://api.twilio.com/2010-04-01/Accounts/ACdemo/Recordings/RE_demo_vm104.mp3',
 'Hi, this is Grace Park. I had an appointment booked for this morning between 9 and 11 and no one has shown up yet. It''s now 11:15. Can someone please let me know what''s going on? My number is 416-123-0000.',
 26, true,
 '2026-03-12 11:18:00');

-- =============================================================================
-- LEADS  (10 — all referencing valid pilot_ids and call_log_ids)
-- =============================================================================

INSERT INTO leads (id, company_id, pilot_id, caller_name, caller_phone,
    inquiry, call_type, status, call_log_id, created_at, notes)
VALUES

-- La Bella Trattoria leads (pilot_id=100)
(100, 100, 100,
 'Sophie Lavoie', '+15149887766',
 'Private dining space for a birthday dinner, approximately 12 guests.',
 'after_hours', 'contacted', 101,
 '2026-02-21 22:32:07',
 'Called back 2026-02-22 AM. Quoted private room for Saturdays. Awaiting confirmation.'),

(101, 100, 100,
 'Daniel Fontaine', '+15147778899',
 'Corporate catering for a lunch event, approximately 30 people.',
 'during_hours', 'new', 104,
 '2026-02-26 14:23:29',
 NULL),

(102, 100, 100,
 'Emma Gagnon', '+15141234567',
 'Dinner for a group with gluten-free and vegan dietary restrictions.',
 'after_hours', 'new', 106,
 '2026-03-04 21:16:14',
 NULL),

(103, 100, 100,
 'Antoine Bergeron', '+15142223333',
 'Reservation for Friday night, table for 4 at 7:30pm.',
 'after_hours', 'contacted', NULL,
 '2026-02-28 20:45:00',
 'Left voicemail. Called back next morning. Reservation booked.'),

(104, 100, 100,
 'Chloé Mercier', '+15146661234',
 'Inquiry about wine pairing dinner events and upcoming special menus.',
 'after_hours', 'new', NULL,
 '2026-03-07 21:55:00',
 NULL),

-- ProFix Plumbing leads (pilot_id=101)
(105, 101, 101,
 'Kevin Martel', '+14161112222',
 'Hot water tank on its last legs — needs inspection and likely replacement.',
 'after_hours', 'closed', 107,
 '2026-02-19 20:46:35',
 'Booked for 2026-02-21. Job completed. New 50-gallon tank installed. $1,240 CAD.'),

(106, 101, 101,
 'Linda Osei', '+14163334444',
 'Slow drains in master bathroom and kitchen sink, ongoing for two weeks.',
 'during_hours', 'closed', 108,
 '2026-02-22 10:31:51',
 'Dispatched same day. Cleared blockage. $185 CAD.'),

(107, 101, 101,
 'Amanda Chen', '+14169990011',
 'Full bathroom renovation quote: new toilet, vanity, shower fixtures, possible drain relocation.',
 'after_hours', 'contacted', 111,
 '2026-03-02 21:09:52',
 'Called back 2026-03-03. Estimate visit booked for 2026-03-08. Quote: $4,200–$5,800 CAD.'),

(108, 101, 101,
 'Robert Singh', '+14162223333',
 'Emergency — burst pipe in basement, water flowing, needs immediate help.',
 'after_hours', 'closed', 112,
 '2026-03-05 02:15:08',
 'Emergency dispatch. On-site within 40 mins. Pipe repaired. $890 CAD.'),

(109, 101, 101,
 'Patricia Nguyen', '+14166667777',
 'Backwater valve installation quote after recent basement flooding.',
 'after_hours', 'new', 114,
 '2026-03-15 23:05:28',
 NULL);

-- =============================================================================
-- RESET SEQUENCES  (so the next auto-generated ID doesn''t collide)
-- =============================================================================

SELECT setval('companies_id_seq',       (SELECT MAX(id) FROM companies));
SELECT setval('integrations_id_seq',    (SELECT MAX(id) FROM integrations));
SELECT setval('pilot_customers_id_seq', (SELECT MAX(id) FROM pilot_customers));
SELECT setval('call_logs_id_seq',       (SELECT MAX(id) FROM call_logs));
SELECT setval('voicemails_id_seq',      (SELECT MAX(id) FROM voicemails));
SELECT setval('leads_id_seq',           (SELECT MAX(id) FROM leads));

-- Restore normal constraint checking
SET session_replication_role = DEFAULT;

-- Quick verification counts
SELECT 'companies'       AS "table", COUNT(*) AS rows FROM companies
UNION ALL
SELECT 'users',          COUNT(*) FROM users
UNION ALL
SELECT 'integrations',   COUNT(*) FROM integrations
UNION ALL
SELECT 'pilot_customers',COUNT(*) FROM pilot_customers
UNION ALL
SELECT 'call_logs',      COUNT(*) FROM call_logs
UNION ALL
SELECT 'leads',          COUNT(*) FROM leads
UNION ALL
SELECT 'voicemails',     COUNT(*) FROM voicemails
ORDER BY 1;
