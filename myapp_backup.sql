--
-- PostgreSQL database dump
--

\restrict JBTlda0wq49idNwJCGuKV3CoUVBobpICne7FLzpTTxeo54UsHasIXgzdl760efK

-- Dumped from database version 16.12 (0113957)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: _system; Type: SCHEMA; Schema: -; Owner: neondb_owner
--

CREATE SCHEMA _system;


ALTER SCHEMA _system OWNER TO neondb_owner;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: replit_database_migrations_v1; Type: TABLE; Schema: _system; Owner: neondb_owner
--

CREATE TABLE _system.replit_database_migrations_v1 (
    id bigint NOT NULL,
    build_id text NOT NULL,
    deployment_id text NOT NULL,
    statement_count bigint NOT NULL,
    applied_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE _system.replit_database_migrations_v1 OWNER TO neondb_owner;

--
-- Name: replit_database_migrations_v1_id_seq; Type: SEQUENCE; Schema: _system; Owner: neondb_owner
--

CREATE SEQUENCE _system.replit_database_migrations_v1_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE _system.replit_database_migrations_v1_id_seq OWNER TO neondb_owner;

--
-- Name: replit_database_migrations_v1_id_seq; Type: SEQUENCE OWNED BY; Schema: _system; Owner: neondb_owner
--

ALTER SEQUENCE _system.replit_database_migrations_v1_id_seq OWNED BY _system.replit_database_migrations_v1.id;


--
-- Name: call_logs; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.call_logs (
    id integer NOT NULL,
    company_id integer NOT NULL,
    caller_phone character varying(20) NOT NULL,
    call_sid character varying(100),
    intent character varying(50),
    outcome character varying(50),
    duration_seconds integer,
    transcript text,
    provider_type character varying(50),
    created_at timestamp without time zone,
    completed_at timestamp without time zone,
    handled_by_ai boolean,
    ai_conversation text,
    ai_confidence double precision,
    conversation_turns integer,
    escalation_reason character varying(100),
    pilot_id integer
);


ALTER TABLE public.call_logs OWNER TO neondb_owner;

--
-- Name: call_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.call_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.call_logs_id_seq OWNER TO neondb_owner;

--
-- Name: call_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.call_logs_id_seq OWNED BY public.call_logs.id;


--
-- Name: companies; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.companies (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    phone_number character varying(20),
    created_at timestamp without time zone,
    is_active boolean,
    greeting_message text,
    menu_options text,
    business_hours text,
    escalation_number character varying(20)
);


ALTER TABLE public.companies OWNER TO neondb_owner;

--
-- Name: companies_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.companies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.companies_id_seq OWNER TO neondb_owner;

--
-- Name: companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.companies_id_seq OWNED BY public.companies.id;


--
-- Name: integrations; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.integrations (
    id integer NOT NULL,
    company_id integer NOT NULL,
    provider_type character varying(50) NOT NULL,
    provider_name character varying(100) NOT NULL,
    config text NOT NULL,
    is_active boolean,
    created_at timestamp without time zone,
    last_tested timestamp without time zone,
    test_status character varying(20)
);


ALTER TABLE public.integrations OWNER TO neondb_owner;

--
-- Name: integrations_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.integrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.integrations_id_seq OWNER TO neondb_owner;

--
-- Name: integrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.integrations_id_seq OWNED BY public.integrations.id;


--
-- Name: leads; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.leads (
    id integer NOT NULL,
    pilot_id integer NOT NULL,
    caller_name character varying(200),
    caller_phone character varying(20) NOT NULL,
    inquiry text,
    call_type character varying(20),
    status character varying(20),
    call_log_id integer,
    created_at timestamp without time zone,
    notes text,
    company_id integer
);


ALTER TABLE public.leads OWNER TO neondb_owner;

--
-- Name: leads_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.leads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.leads_id_seq OWNER TO neondb_owner;

--
-- Name: leads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.leads_id_seq OWNED BY public.leads.id;


--
-- Name: oauth; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.oauth (
    id integer NOT NULL,
    user_id character varying,
    browser_session_key character varying NOT NULL,
    provider character varying(50) NOT NULL,
    token json
);


ALTER TABLE public.oauth OWNER TO neondb_owner;

--
-- Name: oauth_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.oauth_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.oauth_id_seq OWNER TO neondb_owner;

--
-- Name: oauth_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.oauth_id_seq OWNED BY public.oauth.id;


--
-- Name: pilot_customers; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.pilot_customers (
    id integer NOT NULL,
    company_id integer NOT NULL,
    name character varying(200) NOT NULL,
    industry character varying(100),
    contact_email character varying(200),
    contact_phone character varying(20),
    twilio_number character varying(20),
    start_date timestamp without time zone,
    end_date timestamp without time zone,
    status character varying(20),
    notes text,
    created_at timestamp without time zone
);


ALTER TABLE public.pilot_customers OWNER TO neondb_owner;

--
-- Name: pilot_customers_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.pilot_customers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pilot_customers_id_seq OWNER TO neondb_owner;

--
-- Name: pilot_customers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.pilot_customers_id_seq OWNED BY public.pilot_customers.id;


--
-- Name: pilot_orders; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.pilot_orders (
    id integer NOT NULL,
    pilot_id integer NOT NULL,
    order_id character varying(100) NOT NULL,
    customer_name character varying(200),
    status character varying(50),
    tracking_number character varying(100),
    estimated_delivery character varying(100),
    delivery_address text,
    order_total character varying(50),
    created_at timestamp without time zone
);


ALTER TABLE public.pilot_orders OWNER TO neondb_owner;

--
-- Name: pilot_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.pilot_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pilot_orders_id_seq OWNER TO neondb_owner;

--
-- Name: pilot_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.pilot_orders_id_seq OWNED BY public.pilot_orders.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.users (
    id character varying NOT NULL,
    email character varying(120),
    first_name character varying(100),
    last_name character varying(100),
    profile_image_url character varying(500),
    company_id integer,
    is_admin boolean,
    role character varying(20),
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_active boolean
);


ALTER TABLE public.users OWNER TO neondb_owner;

--
-- Name: voicemails; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.voicemails (
    id integer NOT NULL,
    company_id integer NOT NULL,
    call_log_id integer,
    caller_phone character varying(20) NOT NULL,
    recording_url character varying(500),
    transcription text,
    duration_seconds integer,
    is_listened boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.voicemails OWNER TO neondb_owner;

--
-- Name: voicemails_id_seq; Type: SEQUENCE; Schema: public; Owner: neondb_owner
--

CREATE SEQUENCE public.voicemails_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.voicemails_id_seq OWNER TO neondb_owner;

--
-- Name: voicemails_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: neondb_owner
--

ALTER SEQUENCE public.voicemails_id_seq OWNED BY public.voicemails.id;


--
-- Name: replit_database_migrations_v1 id; Type: DEFAULT; Schema: _system; Owner: neondb_owner
--

ALTER TABLE ONLY _system.replit_database_migrations_v1 ALTER COLUMN id SET DEFAULT nextval('_system.replit_database_migrations_v1_id_seq'::regclass);


--
-- Name: call_logs id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.call_logs ALTER COLUMN id SET DEFAULT nextval('public.call_logs_id_seq'::regclass);


--
-- Name: companies id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.companies ALTER COLUMN id SET DEFAULT nextval('public.companies_id_seq'::regclass);


--
-- Name: integrations id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.integrations ALTER COLUMN id SET DEFAULT nextval('public.integrations_id_seq'::regclass);


--
-- Name: leads id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.leads ALTER COLUMN id SET DEFAULT nextval('public.leads_id_seq'::regclass);


--
-- Name: oauth id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.oauth ALTER COLUMN id SET DEFAULT nextval('public.oauth_id_seq'::regclass);


--
-- Name: pilot_customers id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pilot_customers ALTER COLUMN id SET DEFAULT nextval('public.pilot_customers_id_seq'::regclass);


--
-- Name: pilot_orders id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pilot_orders ALTER COLUMN id SET DEFAULT nextval('public.pilot_orders_id_seq'::regclass);


--
-- Name: voicemails id; Type: DEFAULT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.voicemails ALTER COLUMN id SET DEFAULT nextval('public.voicemails_id_seq'::regclass);


--
-- Data for Name: replit_database_migrations_v1; Type: TABLE DATA; Schema: _system; Owner: neondb_owner
--

COPY _system.replit_database_migrations_v1 (id, build_id, deployment_id, statement_count, applied_at) FROM stdin;
1	35e62078-45c0-44dd-bf61-3744ed217f43	2ec29bae-1990-4130-82fc-ca3bf451cfbb	21	2026-01-29 00:00:31.073069+00
\.


--
-- Data for Name: call_logs; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.call_logs (id, company_id, caller_phone, call_sid, intent, outcome, duration_seconds, transcript, provider_type, created_at, completed_at, handled_by_ai, ai_conversation, ai_confidence, conversation_turns, escalation_reason, pilot_id) FROM stdin;
\.


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.companies (id, name, phone_number, created_at, is_active, greeting_message, menu_options, business_hours, escalation_number) FROM stdin;
\.


--
-- Data for Name: integrations; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.integrations (id, company_id, provider_type, provider_name, config, is_active, created_at, last_tested, test_status) FROM stdin;
\.


--
-- Data for Name: leads; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.leads (id, pilot_id, caller_name, caller_phone, inquiry, call_type, status, call_log_id, created_at, notes, company_id) FROM stdin;
\.


--
-- Data for Name: oauth; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.oauth (id, user_id, browser_session_key, provider, token) FROM stdin;
\.


--
-- Data for Name: pilot_customers; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.pilot_customers (id, company_id, name, industry, contact_email, contact_phone, twilio_number, start_date, end_date, status, notes, created_at) FROM stdin;
\.


--
-- Data for Name: pilot_orders; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.pilot_orders (id, pilot_id, order_id, customer_name, status, tracking_number, estimated_delivery, delivery_address, order_total, created_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.users (id, email, first_name, last_name, profile_image_url, company_id, is_admin, role, created_at, updated_at, is_active) FROM stdin;
\.


--
-- Data for Name: voicemails; Type: TABLE DATA; Schema: public; Owner: neondb_owner
--

COPY public.voicemails (id, company_id, call_log_id, caller_phone, recording_url, transcription, duration_seconds, is_listened, created_at) FROM stdin;
\.


--
-- Name: replit_database_migrations_v1_id_seq; Type: SEQUENCE SET; Schema: _system; Owner: neondb_owner
--

SELECT pg_catalog.setval('_system.replit_database_migrations_v1_id_seq', 1, true);


--
-- Name: call_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.call_logs_id_seq', 1, false);


--
-- Name: companies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.companies_id_seq', 1, false);


--
-- Name: integrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.integrations_id_seq', 1, false);


--
-- Name: leads_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.leads_id_seq', 1, false);


--
-- Name: oauth_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.oauth_id_seq', 1, false);


--
-- Name: pilot_customers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.pilot_customers_id_seq', 1, false);


--
-- Name: pilot_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.pilot_orders_id_seq', 1, false);


--
-- Name: voicemails_id_seq; Type: SEQUENCE SET; Schema: public; Owner: neondb_owner
--

SELECT pg_catalog.setval('public.voicemails_id_seq', 1, false);


--
-- Name: replit_database_migrations_v1 replit_database_migrations_v1_pkey; Type: CONSTRAINT; Schema: _system; Owner: neondb_owner
--

ALTER TABLE ONLY _system.replit_database_migrations_v1
    ADD CONSTRAINT replit_database_migrations_v1_pkey PRIMARY KEY (id);


--
-- Name: call_logs call_logs_call_sid_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.call_logs
    ADD CONSTRAINT call_logs_call_sid_key UNIQUE (call_sid);


--
-- Name: call_logs call_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.call_logs
    ADD CONSTRAINT call_logs_pkey PRIMARY KEY (id);


--
-- Name: companies companies_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_phone_number_key UNIQUE (phone_number);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: integrations integrations_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_pkey PRIMARY KEY (id);


--
-- Name: leads leads_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_pkey PRIMARY KEY (id);


--
-- Name: oauth oauth_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.oauth
    ADD CONSTRAINT oauth_pkey PRIMARY KEY (id);


--
-- Name: pilot_customers pilot_customers_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pilot_customers
    ADD CONSTRAINT pilot_customers_pkey PRIMARY KEY (id);


--
-- Name: pilot_orders pilot_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pilot_orders
    ADD CONSTRAINT pilot_orders_pkey PRIMARY KEY (id);


--
-- Name: oauth uq_user_browser_session_provider; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.oauth
    ADD CONSTRAINT uq_user_browser_session_provider UNIQUE (user_id, browser_session_key, provider);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: voicemails voicemails_pkey; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.voicemails
    ADD CONSTRAINT voicemails_pkey PRIMARY KEY (id);


--
-- Name: idx_replit_database_migrations_v1_build_id; Type: INDEX; Schema: _system; Owner: neondb_owner
--

CREATE UNIQUE INDEX idx_replit_database_migrations_v1_build_id ON _system.replit_database_migrations_v1 USING btree (build_id);


--
-- Name: call_logs call_logs_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.call_logs
    ADD CONSTRAINT call_logs_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: call_logs call_logs_pilot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.call_logs
    ADD CONSTRAINT call_logs_pilot_id_fkey FOREIGN KEY (pilot_id) REFERENCES public.pilot_customers(id);


--
-- Name: integrations integrations_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: leads leads_call_log_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_call_log_id_fkey FOREIGN KEY (call_log_id) REFERENCES public.call_logs(id);


--
-- Name: leads leads_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: leads leads_pilot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_pilot_id_fkey FOREIGN KEY (pilot_id) REFERENCES public.pilot_customers(id);


--
-- Name: oauth oauth_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.oauth
    ADD CONSTRAINT oauth_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: pilot_customers pilot_customers_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pilot_customers
    ADD CONSTRAINT pilot_customers_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: pilot_orders pilot_orders_pilot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pilot_orders
    ADD CONSTRAINT pilot_orders_pilot_id_fkey FOREIGN KEY (pilot_id) REFERENCES public.pilot_customers(id);


--
-- Name: users users_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: voicemails voicemails_call_log_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.voicemails
    ADD CONSTRAINT voicemails_call_log_id_fkey FOREIGN KEY (call_log_id) REFERENCES public.call_logs(id);


--
-- Name: voicemails voicemails_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.voicemails
    ADD CONSTRAINT voicemails_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION;


--
-- PostgreSQL database dump complete
--

\unrestrict JBTlda0wq49idNwJCGuKV3CoUVBobpICne7FLzpTTxeo54UsHasIXgzdl760efK

