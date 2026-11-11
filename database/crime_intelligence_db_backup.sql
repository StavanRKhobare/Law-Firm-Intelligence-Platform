--
-- PostgreSQL database dump
--

\restrict vS0abBNJrs8OBPkkD7jFTOa9zgsxrDiN5vyfWxQ24teebwvvhk5U4R2V0tS2S8K

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

-- Started on 2026-01-15 08:21:47

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 267 (class 1255 OID 16654)
-- Name: assign_officer_to_case(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.assign_officer_to_case(p_case_id integer, p_officer_id integer) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_officer_name TEXT;
    v_officer_rank VARCHAR;
    v_fir_no VARCHAR;
    v_current_status VARCHAR;
BEGIN
    -- Validate officer exists
    IF NOT EXISTS (SELECT 1 FROM OFFICER WHERE Officer_ID = p_officer_id) THEN
        RAISE EXCEPTION 'Officer ID % does not exist', p_officer_id;
    END IF;
    
    -- Validate case exists
    IF NOT EXISTS (SELECT 1 FROM CRIME_CASE WHERE Crime_Case_ID = p_case_id) THEN
        RAISE EXCEPTION 'Case ID % does not exist', p_case_id;
    END IF;
    
    -- Get officer details
    SELECT CONCAT(Fname, ' ', Lname), Rank INTO v_officer_name, v_officer_rank
    FROM OFFICER WHERE Officer_ID = p_officer_id;
    
    -- Get case details
    SELECT FIR_No, Status INTO v_fir_no, v_current_status
    FROM CRIME_CASE WHERE Crime_Case_ID = p_case_id;
    
    -- Assign officer
    UPDATE CRIME_CASE
    SET Officer_ID = p_officer_id
    WHERE Crime_Case_ID = p_case_id;
    
    -- Return success message
    RETURN format('SUCCESS: %s (%s) assigned to case %s (Status: %s)', 
                  v_officer_name, v_officer_rank, v_fir_no, v_current_status);
END;
$$;


ALTER FUNCTION public.assign_officer_to_case(p_case_id integer, p_officer_id integer) OWNER TO postgres;

--
-- TOC entry 5221 (class 0 OID 0)
-- Dependencies: 267
-- Name: FUNCTION assign_officer_to_case(p_case_id integer, p_officer_id integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.assign_officer_to_case(p_case_id integer, p_officer_id integer) IS 'Assigns an officer to a case with validation';


--
-- TOC entry 269 (class 1255 OID 16656)
-- Name: close_case(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.close_case(p_case_id integer, p_officer_id integer DEFAULT NULL::integer) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_fir_no VARCHAR;
    v_current_status VARCHAR;
    v_evidence_count INTEGER;
BEGIN
    -- Get case details
    SELECT FIR_No, Status INTO v_fir_no, v_current_status
    FROM CRIME_CASE WHERE Crime_Case_ID = p_case_id;
    
    -- Validate case exists
    IF v_fir_no IS NULL THEN
        RAISE EXCEPTION 'Case ID % does not exist', p_case_id;
    END IF;
    
    -- Check if already closed
    IF v_current_status = 'Closed' THEN
        RETURN format('Case %s is already closed', v_fir_no);
    END IF;
    
    -- Check if evidence exists
    SELECT COUNT(*) INTO v_evidence_count
    FROM EVIDENCE WHERE Crime_Case_ID = p_case_id;
    
    IF v_evidence_count = 0 THEN
        RAISE NOTICE 'Warning: Closing case % without any evidence', v_fir_no;
    END IF;
    
    -- Close the case
    UPDATE CRIME_CASE
    SET Status = 'Closed'
    WHERE Crime_Case_ID = p_case_id;
    
    -- Return success message
    RETURN format('SUCCESS: Case %s closed (Previous status: %s, Evidence count: %s)', 
                  v_fir_no, v_current_status, v_evidence_count);
END;
$$;


ALTER FUNCTION public.close_case(p_case_id integer, p_officer_id integer) OWNER TO postgres;

--
-- TOC entry 5222 (class 0 OID 0)
-- Dependencies: 269
-- Name: FUNCTION close_case(p_case_id integer, p_officer_id integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.close_case(p_case_id integer, p_officer_id integer) IS 'Closes a case with validation checks';


--
-- TOC entry 268 (class 1255 OID 16655)
-- Name: generate_department_report(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.generate_department_report(dept_id_param integer) RETURNS TABLE(officer_name text, officer_rank character varying, phone_no character varying, total_cases bigint, open_cases bigint, under_investigation bigint, closed_cases bigint, evidence_collected bigint, case_closure_rate numeric)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CONCAT(o.Fname, ' ', o.Lname),
        o.Rank,
        o.PhoneNo,
        COUNT(DISTINCT cc.Crime_Case_ID),
        COUNT(DISTINCT CASE WHEN cc.Status = 'Open' THEN cc.Crime_Case_ID END),
        COUNT(DISTINCT CASE WHEN cc.Status = 'Under Investigation' THEN cc.Crime_Case_ID END),
        COUNT(DISTINCT CASE WHEN cc.Status = 'Closed' THEN cc.Crime_Case_ID END),
        COUNT(DISTINCT e.Evidence_ID),
        ROUND(
            100.0 * COUNT(DISTINCT CASE WHEN cc.Status = 'Closed' THEN cc.Crime_Case_ID END) / 
            NULLIF(COUNT(DISTINCT cc.Crime_Case_ID), 0),
            2
        )
    FROM OFFICER o
    LEFT JOIN CRIME_CASE cc ON o.Officer_ID = cc.Officer_ID
    LEFT JOIN EVIDENCE e ON o.Officer_ID = e.Officer_ID
    WHERE o.Dept_ID = dept_id_param
    GROUP BY o.Officer_ID, o.Fname, o.Lname, o.Rank, o.PhoneNo
    ORDER BY COUNT(DISTINCT cc.Crime_Case_ID) DESC;
END;
$$;


ALTER FUNCTION public.generate_department_report(dept_id_param integer) OWNER TO postgres;

--
-- TOC entry 5223 (class 0 OID 0)
-- Dependencies: 268
-- Name: FUNCTION generate_department_report(dept_id_param integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.generate_department_report(dept_id_param integer) IS 'Generates performance report for a department';


--
-- TOC entry 266 (class 1255 OID 16653)
-- Name: get_complete_case_details(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_complete_case_details(case_id integer) RETURNS TABLE(fir_no character varying, crime_title character varying, crime_description text, case_status character varying, occurrence_date date, report_date date, officer_name text, officer_rank character varying, department text, location_info text, suspects text, victims text, crime_types text, ipc_sections text, evidence_count bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cc.FIR_No,
        cc.Crime_title,
        cc.Crime_description,
        cc.Status,
        cc.Date_occ,
        cc.Date_rep,
        CONCAT(o.Fname, ' ', o.Lname)::TEXT,
        o.Rank,
        d.Dept_Name::TEXT,
        CONCAT(l.Landmark, ', ', pa.City, ', ', pa.State)::TEXT,
        (SELECT STRING_AGG(CONCAT(s.Fname, ' ', s.Lname), ', ')
         FROM IS_SUSPECT iss
         JOIN SUSPECT s ON iss.Suspect_ID = s.Suspect_ID
         WHERE iss.Crime_Case_ID = case_id),
        (SELECT STRING_AGG(CONCAT(v.Fname, ' ', v.Lname), ', ')
         FROM IS_VICTIM iv
         JOIN VICTIM v ON iv.Victim_ID = v.Victim_ID
         WHERE iv.Crime_Case_ID = case_id),
        (SELECT STRING_AGG(ct.Crime_type, ', ')
         FROM CRIME_TYPE ct
         WHERE ct.Crime_Case_ID = case_id),
        (SELECT STRING_AGG(ips.IPC_Section, ', ')
         FROM IPC_SECTION ips
         WHERE ips.Crime_Case_ID = case_id),
        (SELECT COUNT(*) FROM EVIDENCE WHERE Crime_Case_ID = case_id)
    FROM CRIME_CASE cc
    LEFT JOIN OFFICER o ON cc.Officer_ID = o.Officer_ID
    LEFT JOIN DEPARTMENT d ON o.Dept_ID = d.Dept_ID
    LEFT JOIN LOCATION l ON cc.Location_ID = l.Location_ID
    LEFT JOIN PINCODE_AREA pa ON l.Pincode = pa.Pincode
    WHERE cc.Crime_Case_ID = case_id;
END;
$$;


ALTER FUNCTION public.get_complete_case_details(case_id integer) OWNER TO postgres;

--
-- TOC entry 5224 (class 0 OID 0)
-- Dependencies: 266
-- Name: FUNCTION get_complete_case_details(case_id integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.get_complete_case_details(case_id integer) IS 'Retrieves all details for a specific case';


--
-- TOC entry 270 (class 1255 OID 16657)
-- Name: get_suspect_history(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_suspect_history(p_suspect_id integer) RETURNS TABLE(case_id integer, fir_no character varying, crime_title character varying, crime_date date, case_status character varying, crime_types text, investigating_officer text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cc.Crime_Case_ID,
        cc.FIR_No,
        cc.Crime_title,
        cc.Date_occ,
        cc.Status,
        (SELECT STRING_AGG(ct.Crime_type, ', ')
         FROM CRIME_TYPE ct
         WHERE ct.Crime_Case_ID = cc.Crime_Case_ID),
        CONCAT(o.Fname, ' ', o.Lname)
    FROM CRIME_CASE cc
    JOIN IS_SUSPECT iss ON cc.Crime_Case_ID = iss.Crime_Case_ID
    LEFT JOIN OFFICER o ON cc.Officer_ID = o.Officer_ID
    WHERE iss.Suspect_ID = p_suspect_id
    ORDER BY cc.Date_occ DESC;
END;
$$;


ALTER FUNCTION public.get_suspect_history(p_suspect_id integer) OWNER TO postgres;

--
-- TOC entry 5225 (class 0 OID 0)
-- Dependencies: 270
-- Name: FUNCTION get_suspect_history(p_suspect_id integer); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.get_suspect_history(p_suspect_id integer) IS 'Retrieves complete criminal history for a suspect';


--
-- TOC entry 251 (class 1255 OID 16647)
-- Name: log_case_status_change(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.log_case_status_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Only log if status actually changed
    IF OLD.Status IS DISTINCT FROM NEW.Status THEN
        INSERT INTO CASE_STATUS_AUDIT (Crime_Case_ID, Old_Status, New_Status)
        VALUES (NEW.Crime_Case_ID, OLD.Status, NEW.Status);
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.log_case_status_change() OWNER TO postgres;

--
-- TOC entry 5226 (class 0 OID 0)
-- Dependencies: 251
-- Name: FUNCTION log_case_status_change(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.log_case_status_change() IS 'Logs all case status changes for audit purposes';


--
-- TOC entry 265 (class 1255 OID 16658)
-- Name: search_cases(date, date, character varying, character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.search_cases(p_start_date date DEFAULT NULL::date, p_end_date date DEFAULT NULL::date, p_city character varying DEFAULT NULL::character varying, p_status character varying DEFAULT NULL::character varying) RETURNS TABLE(case_id integer, fir_no character varying, crime_title character varying, occurrence_date date, case_status character varying, location text, officer_name text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cc.Crime_Case_ID,
        cc.FIR_No,
        cc.Crime_title,
        cc.Date_occ,
        cc.Status,
        CONCAT(l.Landmark, ', ', pa.City),
        CONCAT(o.Fname, ' ', o.Lname)
    FROM CRIME_CASE cc
    LEFT JOIN LOCATION l ON cc.Location_ID = l.Location_ID
    LEFT JOIN PINCODE_AREA pa ON l.Pincode = pa.Pincode
    LEFT JOIN OFFICER o ON cc.Officer_ID = o.Officer_ID
    WHERE 
        (p_start_date IS NULL OR cc.Date_occ >= p_start_date)
        AND (p_end_date IS NULL OR cc.Date_occ <= p_end_date)
        AND (p_city IS NULL OR pa.City ILIKE '%' || p_city || '%')
        AND (p_status IS NULL OR cc.Status = p_status)
    ORDER BY cc.Date_occ DESC;
END;
$$;


ALTER FUNCTION public.search_cases(p_start_date date, p_end_date date, p_city character varying, p_status character varying) OWNER TO postgres;

--
-- TOC entry 5227 (class 0 OID 0)
-- Dependencies: 265
-- Name: FUNCTION search_cases(p_start_date date, p_end_date date, p_city character varying, p_status character varying); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.search_cases(p_start_date date, p_end_date date, p_city character varying, p_status character varying) IS 'Searches cases with flexible filters';


--
-- TOC entry 249 (class 1255 OID 16632)
-- Name: update_case_status_on_evidence(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_case_status_on_evidence() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- If new evidence is added and case is 'Open', change to 'Under Investigation'
    UPDATE CRIME_CASE
    SET Status = 'Under Investigation'
    WHERE Crime_Case_ID = NEW.Crime_Case_ID 
      AND Status = 'Open';
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_case_status_on_evidence() OWNER TO postgres;

--
-- TOC entry 5228 (class 0 OID 0)
-- Dependencies: 249
-- Name: FUNCTION update_case_status_on_evidence(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.update_case_status_on_evidence() IS 'Automatically updates case status when evidence is collected';


--
-- TOC entry 253 (class 1255 OID 16651)
-- Name: update_suspect_criminal_record(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_suspect_criminal_record() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- If suspect is involved in more than one case, mark as having criminal record
    IF (SELECT COUNT(*) FROM IS_SUSPECT WHERE Suspect_ID = NEW.Suspect_ID) > 1 THEN
        UPDATE SUSPECT
        SET HasCriminalRec = TRUE
        WHERE Suspect_ID = NEW.Suspect_ID;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_suspect_criminal_record() OWNER TO postgres;

--
-- TOC entry 5229 (class 0 OID 0)
-- Dependencies: 253
-- Name: FUNCTION update_suspect_criminal_record(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.update_suspect_criminal_record() IS 'Automatically marks suspects involved in multiple cases';


--
-- TOC entry 250 (class 1255 OID 16634)
-- Name: validate_crime_case_dates(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.validate_crime_case_dates() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Ensure Date_rep is not before Date_occ
    IF NEW.Date_rep < NEW.Date_occ THEN
        RAISE EXCEPTION 'Date reported (%) cannot be before date of occurrence (%)', 
            NEW.Date_rep, NEW.Date_occ;
    END IF;
    
    -- Ensure Date_occ is not in future
    IF NEW.Date_occ > CURRENT_DATE THEN
        RAISE EXCEPTION 'Date of occurrence (%) cannot be in the future', NEW.Date_occ;
    END IF;
    
    -- Ensure Date_rep is not in future
    IF NEW.Date_rep > CURRENT_DATE THEN
        RAISE EXCEPTION 'Date reported (%) cannot be in the future', NEW.Date_rep;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.validate_crime_case_dates() OWNER TO postgres;

--
-- TOC entry 5230 (class 0 OID 0)
-- Dependencies: 250
-- Name: FUNCTION validate_crime_case_dates(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.validate_crime_case_dates() IS 'Validates date logic for crime cases';


--
-- TOC entry 252 (class 1255 OID 16649)
-- Name: validate_evidence_date(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.validate_evidence_date() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_case_date DATE;
BEGIN
    -- Get the case occurrence date
    SELECT Date_occ INTO v_case_date
    FROM CRIME_CASE
    WHERE Crime_Case_ID = NEW.Crime_Case_ID;
    
    -- Evidence cannot be collected before crime occurred
    IF NEW.Collection_date < v_case_date THEN
        RAISE EXCEPTION 'Evidence collection date (%) cannot be before crime occurrence date (%)', 
            NEW.Collection_date, v_case_date;
    END IF;
    
    -- Evidence cannot be collected in future
    IF NEW.Collection_date > CURRENT_DATE THEN
        RAISE EXCEPTION 'Evidence collection date (%) cannot be in the future', 
            NEW.Collection_date;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.validate_evidence_date() OWNER TO postgres;

--
-- TOC entry 5231 (class 0 OID 0)
-- Dependencies: 252
-- Name: FUNCTION validate_evidence_date(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.validate_evidence_date() IS 'Ensures evidence collection dates are logical';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 231 (class 1259 OID 16468)
-- Name: crime_case; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crime_case (
    crime_case_id integer NOT NULL,
    crime_title character varying(200) NOT NULL,
    crime_description text,
    fir_no character varying(50) NOT NULL,
    date_occ date NOT NULL,
    date_rep date NOT NULL,
    status character varying(50) DEFAULT 'Open'::character varying,
    officer_id integer,
    location_id integer,
    CONSTRAINT crime_case_check CHECK ((date_rep >= date_occ)),
    CONSTRAINT crime_case_status_check CHECK (((status)::text = ANY ((ARRAY['Open'::character varying, 'Under Investigation'::character varying, 'Closed'::character varying, 'Pending'::character varying])::text[])))
);


ALTER TABLE public.crime_case OWNER TO postgres;

--
-- TOC entry 5232 (class 0 OID 0)
-- Dependencies: 231
-- Name: TABLE crime_case; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.crime_case IS 'Main crime case records with FIR information';


--
-- TOC entry 220 (class 1259 OID 16391)
-- Name: department; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.department (
    dept_id integer NOT NULL,
    dept_name character varying(100) NOT NULL,
    description text,
    email character varying(100),
    contactno character varying(15)
);


ALTER TABLE public.department OWNER TO postgres;

--
-- TOC entry 5233 (class 0 OID 0)
-- Dependencies: 220
-- Name: TABLE department; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.department IS 'Stores police department information';


--
-- TOC entry 223 (class 1259 OID 16413)
-- Name: location; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.location (
    location_id integer NOT NULL,
    landmark character varying(200),
    streetno character varying(50),
    pincode character varying(10)
);


ALTER TABLE public.location OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16426)
-- Name: officer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.officer (
    officer_id integer NOT NULL,
    fname character varying(50) NOT NULL,
    lname character varying(50) NOT NULL,
    rank character varying(50),
    phoneno character varying(15),
    dept_id integer
);


ALTER TABLE public.officer OWNER TO postgres;

--
-- TOC entry 5234 (class 0 OID 0)
-- Dependencies: 225
-- Name: TABLE officer; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.officer IS 'Stores officer details and department assignments';


--
-- TOC entry 221 (class 1259 OID 16403)
-- Name: pincode_area; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pincode_area (
    pincode character varying(10) NOT NULL,
    city character varying(100) NOT NULL,
    district character varying(100) NOT NULL,
    state character varying(100) NOT NULL
);


ALTER TABLE public.pincode_area OWNER TO postgres;

--
-- TOC entry 5235 (class 0 OID 0)
-- Dependencies: 221
-- Name: TABLE pincode_area; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.pincode_area IS 'Normalized location data (3NF)';


--
-- TOC entry 240 (class 1259 OID 16607)
-- Name: active_cases_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.active_cases_view AS
 SELECT cc.crime_case_id,
    cc.fir_no,
    cc.crime_title,
    cc.status,
    cc.date_occ,
    cc.date_rep,
    concat(o.fname, ' ', o.lname) AS investigating_officer,
    o.rank,
    d.dept_name,
    l.landmark,
    pa.city,
    pa.district,
    (CURRENT_DATE - cc.date_occ) AS days_open
   FROM ((((public.crime_case cc
     LEFT JOIN public.officer o ON ((cc.officer_id = o.officer_id)))
     LEFT JOIN public.department d ON ((o.dept_id = d.dept_id)))
     LEFT JOIN public.location l ON ((cc.location_id = l.location_id)))
     LEFT JOIN public.pincode_area pa ON (((l.pincode)::text = (pa.pincode)::text)))
  WHERE ((cc.status)::text = ANY ((ARRAY['Open'::character varying, 'Under Investigation'::character varying])::text[]));


ALTER VIEW public.active_cases_view OWNER TO postgres;

--
-- TOC entry 5236 (class 0 OID 0)
-- Dependencies: 240
-- Name: VIEW active_cases_view; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.active_cases_view IS 'Shows all active cases with officer and location details';


--
-- TOC entry 246 (class 1259 OID 16637)
-- Name: case_status_audit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.case_status_audit (
    audit_id integer NOT NULL,
    crime_case_id integer NOT NULL,
    old_status character varying(50),
    new_status character varying(50),
    changed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    changed_by character varying(100) DEFAULT CURRENT_USER
);


ALTER TABLE public.case_status_audit OWNER TO postgres;

--
-- TOC entry 5237 (class 0 OID 0)
-- Dependencies: 246
-- Name: TABLE case_status_audit; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.case_status_audit IS 'Audit trail for case status changes';


--
-- TOC entry 245 (class 1259 OID 16636)
-- Name: case_status_audit_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.case_status_audit_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.case_status_audit_audit_id_seq OWNER TO postgres;

--
-- TOC entry 5238 (class 0 OID 0)
-- Dependencies: 245
-- Name: case_status_audit_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.case_status_audit_audit_id_seq OWNED BY public.case_status_audit.audit_id;


--
-- TOC entry 230 (class 1259 OID 16467)
-- Name: crime_case_crime_case_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.crime_case_crime_case_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.crime_case_crime_case_id_seq OWNER TO postgres;

--
-- TOC entry 5239 (class 0 OID 0)
-- Dependencies: 230
-- Name: crime_case_crime_case_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.crime_case_crime_case_id_seq OWNED BY public.crime_case.crime_case_id;


--
-- TOC entry 238 (class 1259 OID 16577)
-- Name: crime_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crime_type (
    crime_case_id integer NOT NULL,
    crime_type character varying(100) NOT NULL
);


ALTER TABLE public.crime_type OWNER TO postgres;

--
-- TOC entry 244 (class 1259 OID 16627)
-- Name: crime_hotspot_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.crime_hotspot_view AS
 SELECT l.location_id,
    l.landmark,
    l.streetno,
    pa.city,
    pa.district,
    pa.state,
    pa.pincode,
    count(cc.crime_case_id) AS total_crimes,
    string_agg(DISTINCT (ct.crime_type)::text, ', '::text) AS crime_types,
    count(
        CASE
            WHEN ((cc.status)::text = 'Open'::text) THEN 1
            ELSE NULL::integer
        END) AS open_cases,
    count(
        CASE
            WHEN ((cc.status)::text = 'Closed'::text) THEN 1
            ELSE NULL::integer
        END) AS closed_cases,
    max(cc.date_occ) AS last_crime_date
   FROM (((public.location l
     JOIN public.pincode_area pa ON (((l.pincode)::text = (pa.pincode)::text)))
     LEFT JOIN public.crime_case cc ON ((l.location_id = cc.location_id)))
     LEFT JOIN public.crime_type ct ON ((cc.crime_case_id = ct.crime_case_id)))
  GROUP BY l.location_id, l.landmark, l.streetno, pa.city, pa.district, pa.state, pa.pincode
 HAVING (count(cc.crime_case_id) > 0);


ALTER VIEW public.crime_hotspot_view OWNER TO postgres;

--
-- TOC entry 5240 (class 0 OID 0)
-- Dependencies: 244
-- Name: VIEW crime_hotspot_view; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.crime_hotspot_view IS 'Crime hotspot analysis by location';


--
-- TOC entry 219 (class 1259 OID 16390)
-- Name: department_dept_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.department_dept_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.department_dept_id_seq OWNER TO postgres;

--
-- TOC entry 5241 (class 0 OID 0)
-- Dependencies: 219
-- Name: department_dept_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.department_dept_id_seq OWNED BY public.department.dept_id;


--
-- TOC entry 233 (class 1259 OID 16497)
-- Name: evidence; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.evidence (
    evidence_id integer NOT NULL,
    description text,
    collection_date date NOT NULL,
    mongo_id character varying(100),
    status character varying(50) DEFAULT 'Collected'::character varying,
    officer_id integer,
    crime_case_id integer,
    CONSTRAINT evidence_status_check CHECK (((status)::text = ANY ((ARRAY['Collected'::character varying, 'Analyzed'::character varying, 'In Storage'::character varying, 'Presented in Court'::character varying])::text[])))
);


ALTER TABLE public.evidence OWNER TO postgres;

--
-- TOC entry 5242 (class 0 OID 0)
-- Dependencies: 233
-- Name: TABLE evidence; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.evidence IS 'Evidence tracking with MongoDB reference';


--
-- TOC entry 232 (class 1259 OID 16496)
-- Name: evidence_evidence_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.evidence_evidence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.evidence_evidence_id_seq OWNER TO postgres;

--
-- TOC entry 5243 (class 0 OID 0)
-- Dependencies: 232
-- Name: evidence_evidence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.evidence_evidence_id_seq OWNED BY public.evidence.evidence_id;


--
-- TOC entry 239 (class 1259 OID 16589)
-- Name: ipc_section; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ipc_section (
    crime_case_id integer NOT NULL,
    ipc_section character varying(50) NOT NULL
);


ALTER TABLE public.ipc_section OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 16536)
-- Name: is_suspect; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.is_suspect (
    crime_case_id integer NOT NULL,
    suspect_id integer NOT NULL
);


ALTER TABLE public.is_suspect OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 16519)
-- Name: is_victim; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.is_victim (
    crime_case_id integer NOT NULL,
    victim_id integer NOT NULL
);


ALTER TABLE public.is_victim OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16412)
-- Name: location_location_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.location_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.location_location_id_seq OWNER TO postgres;

--
-- TOC entry 5244 (class 0 OID 0)
-- Dependencies: 222
-- Name: location_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.location_location_id_seq OWNED BY public.location.location_id;


--
-- TOC entry 241 (class 1259 OID 16612)
-- Name: monthly_crime_stats; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.monthly_crime_stats AS
 SELECT to_char((date_occ)::timestamp with time zone, 'YYYY-MM'::text) AS month,
    count(*) AS total_cases,
    count(DISTINCT location_id) AS unique_locations,
    count(DISTINCT officer_id) AS officers_involved,
    sum(
        CASE
            WHEN ((status)::text = 'Closed'::text) THEN 1
            ELSE 0
        END) AS closed_cases,
    sum(
        CASE
            WHEN ((status)::text = 'Open'::text) THEN 1
            ELSE 0
        END) AS open_cases,
    sum(
        CASE
            WHEN ((status)::text = 'Under Investigation'::text) THEN 1
            ELSE 0
        END) AS under_investigation,
    round(((100.0 * (sum(
        CASE
            WHEN ((status)::text = 'Closed'::text) THEN 1
            ELSE 0
        END))::numeric) / (count(*))::numeric), 2) AS closure_rate_percent
   FROM public.crime_case cc
  GROUP BY (to_char((date_occ)::timestamp with time zone, 'YYYY-MM'::text));


ALTER VIEW public.monthly_crime_stats OWNER TO postgres;

--
-- TOC entry 5245 (class 0 OID 0)
-- Dependencies: 241
-- Name: VIEW monthly_crime_stats; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.monthly_crime_stats IS 'Monthly aggregated crime statistics';


--
-- TOC entry 224 (class 1259 OID 16425)
-- Name: officer_officer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.officer_officer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.officer_officer_id_seq OWNER TO postgres;

--
-- TOC entry 5246 (class 0 OID 0)
-- Dependencies: 224
-- Name: officer_officer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.officer_officer_id_seq OWNED BY public.officer.officer_id;


--
-- TOC entry 243 (class 1259 OID 16622)
-- Name: officer_performance_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.officer_performance_view AS
 SELECT o.officer_id,
    concat(o.fname, ' ', o.lname) AS officer_name,
    o.rank,
    d.dept_name,
    count(DISTINCT cc.crime_case_id) AS total_cases,
    sum(
        CASE
            WHEN ((cc.status)::text = 'Open'::text) THEN 1
            ELSE 0
        END) AS open_cases,
    sum(
        CASE
            WHEN ((cc.status)::text = 'Under Investigation'::text) THEN 1
            ELSE 0
        END) AS under_investigation,
    sum(
        CASE
            WHEN ((cc.status)::text = 'Closed'::text) THEN 1
            ELSE 0
        END) AS closed_cases,
    count(DISTINCT e.evidence_id) AS evidence_collected,
    round(((100.0 * (sum(
        CASE
            WHEN ((cc.status)::text = 'Closed'::text) THEN 1
            ELSE 0
        END))::numeric) / (NULLIF(count(cc.crime_case_id), 0))::numeric), 2) AS case_closure_rate
   FROM (((public.officer o
     LEFT JOIN public.department d ON ((o.dept_id = d.dept_id)))
     LEFT JOIN public.crime_case cc ON ((o.officer_id = cc.officer_id)))
     LEFT JOIN public.evidence e ON ((o.officer_id = e.officer_id)))
  GROUP BY o.officer_id, o.fname, o.lname, o.rank, d.dept_name;


ALTER VIEW public.officer_performance_view OWNER TO postgres;

--
-- TOC entry 5247 (class 0 OID 0)
-- Dependencies: 243
-- Name: VIEW officer_performance_view; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.officer_performance_view IS 'Officer performance metrics and statistics';


--
-- TOC entry 227 (class 1259 OID 16441)
-- Name: suspect; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suspect (
    suspect_id integer NOT NULL,
    fname character varying(50) NOT NULL,
    lname character varying(50) NOT NULL,
    email character varying(100),
    address text,
    sex character(1),
    hascriminalrec boolean DEFAULT false,
    CONSTRAINT suspect_sex_check CHECK ((sex = ANY (ARRAY['M'::bpchar, 'F'::bpchar, 'O'::bpchar])))
);


ALTER TABLE public.suspect OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 16565)
-- Name: suspect_phone_no; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suspect_phone_no (
    suspect_id integer NOT NULL,
    phoneno character varying(15) NOT NULL
);


ALTER TABLE public.suspect_phone_no OWNER TO postgres;

--
-- TOC entry 242 (class 1259 OID 16617)
-- Name: suspect_profile_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.suspect_profile_view AS
 SELECT s.suspect_id,
    concat(s.fname, ' ', s.lname) AS suspect_name,
    s.email,
    s.address,
    s.sex,
    s.hascriminalrec,
    count(DISTINCT iss.crime_case_id) AS total_cases_involved,
    string_agg(DISTINCT (cc.fir_no)::text, ', '::text ORDER BY (cc.fir_no)::text) AS fir_list,
    string_agg(DISTINCT (ct.crime_type)::text, ', '::text) AS crime_types_involved,
    min(cc.date_occ) AS first_case_date,
    max(cc.date_occ) AS latest_case_date
   FROM (((public.suspect s
     LEFT JOIN public.is_suspect iss ON ((s.suspect_id = iss.suspect_id)))
     LEFT JOIN public.crime_case cc ON ((iss.crime_case_id = cc.crime_case_id)))
     LEFT JOIN public.crime_type ct ON ((cc.crime_case_id = ct.crime_case_id)))
  GROUP BY s.suspect_id, s.fname, s.lname, s.email, s.address, s.sex, s.hascriminalrec;


ALTER VIEW public.suspect_profile_view OWNER TO postgres;

--
-- TOC entry 5248 (class 0 OID 0)
-- Dependencies: 242
-- Name: VIEW suspect_profile_view; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.suspect_profile_view IS 'Comprehensive suspect profiles with case history';


--
-- TOC entry 226 (class 1259 OID 16440)
-- Name: suspect_suspect_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.suspect_suspect_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.suspect_suspect_id_seq OWNER TO postgres;

--
-- TOC entry 5249 (class 0 OID 0)
-- Dependencies: 226
-- Name: suspect_suspect_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.suspect_suspect_id_seq OWNED BY public.suspect.suspect_id;


--
-- TOC entry 248 (class 1259 OID 16676)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(100) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(100),
    role character varying(20),
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 247 (class 1259 OID 16675)
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_user_id_seq OWNER TO postgres;

--
-- TOC entry 5250 (class 0 OID 0)
-- Dependencies: 247
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- TOC entry 229 (class 1259 OID 16455)
-- Name: victim; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.victim (
    victim_id integer NOT NULL,
    fname character varying(50) NOT NULL,
    lname character varying(50) NOT NULL,
    email character varying(100),
    address text,
    sex character(1),
    injury_details text,
    CONSTRAINT victim_sex_check CHECK ((sex = ANY (ARRAY['M'::bpchar, 'F'::bpchar, 'O'::bpchar])))
);


ALTER TABLE public.victim OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 16553)
-- Name: victim_phone_no; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.victim_phone_no (
    victim_id integer NOT NULL,
    phoneno character varying(15) NOT NULL
);


ALTER TABLE public.victim_phone_no OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 16454)
-- Name: victim_victim_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.victim_victim_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.victim_victim_id_seq OWNER TO postgres;

--
-- TOC entry 5251 (class 0 OID 0)
-- Dependencies: 228
-- Name: victim_victim_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.victim_victim_id_seq OWNED BY public.victim.victim_id;


--
-- TOC entry 4965 (class 2604 OID 16640)
-- Name: case_status_audit audit_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.case_status_audit ALTER COLUMN audit_id SET DEFAULT nextval('public.case_status_audit_audit_id_seq'::regclass);


--
-- TOC entry 4961 (class 2604 OID 16471)
-- Name: crime_case crime_case_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_case ALTER COLUMN crime_case_id SET DEFAULT nextval('public.crime_case_crime_case_id_seq'::regclass);


--
-- TOC entry 4955 (class 2604 OID 16394)
-- Name: department dept_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.department ALTER COLUMN dept_id SET DEFAULT nextval('public.department_dept_id_seq'::regclass);


--
-- TOC entry 4963 (class 2604 OID 16500)
-- Name: evidence evidence_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence ALTER COLUMN evidence_id SET DEFAULT nextval('public.evidence_evidence_id_seq'::regclass);


--
-- TOC entry 4956 (class 2604 OID 16416)
-- Name: location location_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location ALTER COLUMN location_id SET DEFAULT nextval('public.location_location_id_seq'::regclass);


--
-- TOC entry 4957 (class 2604 OID 16429)
-- Name: officer officer_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.officer ALTER COLUMN officer_id SET DEFAULT nextval('public.officer_officer_id_seq'::regclass);


--
-- TOC entry 4958 (class 2604 OID 16444)
-- Name: suspect suspect_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suspect ALTER COLUMN suspect_id SET DEFAULT nextval('public.suspect_suspect_id_seq'::regclass);


--
-- TOC entry 4968 (class 2604 OID 16679)
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- TOC entry 4960 (class 2604 OID 16458)
-- Name: victim victim_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.victim ALTER COLUMN victim_id SET DEFAULT nextval('public.victim_victim_id_seq'::regclass);


--
-- TOC entry 5213 (class 0 OID 16637)
-- Dependencies: 246
-- Data for Name: case_status_audit; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.case_status_audit (audit_id, crime_case_id, old_status, new_status, changed_at, changed_by) FROM stdin;
1	4	Open	Under Investigation	2025-12-28 22:05:54.075028	postgres
\.


--
-- TOC entry 5203 (class 0 OID 16468)
-- Dependencies: 231
-- Data for Name: crime_case; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crime_case (crime_case_id, crime_title, crime_description, fir_no, date_occ, date_rep, status, officer_id, location_id) FROM stdin;
1	Robbery at MG Road Store	Armed robbery at jewelry store with multiple suspects	FIR/2024/001	2024-01-15	2024-01-15	Under Investigation	1	1
2	Cyber Fraud Case	Online banking fraud through phishing emails	FIR/2024/002	2024-02-10	2024-02-11	Open	4	5
3	Hit and Run Accident	Vehicle collision with pedestrian, driver fled scene	FIR/2024/003	2024-03-05	2024-03-05	Under Investigation	7	3
5	Assault Case	Physical assault in public area near bus stand	FIR/2024/005	2024-04-01	2024-04-01	Closed	1	2
4	Burglary in Koramangala	House break-in during daytime, valuables stolen	FIR/2024/004	2024-03-20	2024-03-21	Under Investigation	2	4
7	Test Crime from API	Testing the new API	FIR/2024/TEST001	2024-12-29	2024-12-29	Open	\N	\N
8	Test Crime from API	Testing the new API	FIR/2024/TEST015	2024-12-29	2024-12-29	Open	\N	\N
\.


--
-- TOC entry 5210 (class 0 OID 16577)
-- Dependencies: 238
-- Data for Name: crime_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crime_type (crime_case_id, crime_type) FROM stdin;
1	Theft
1	Armed Robbery
2	Cyber Crime
2	Fraud
3	Traffic Violation
3	Negligent Driving
4	Burglary
4	Trespassing
5	Assault
7	Test
8	Test
\.


--
-- TOC entry 5192 (class 0 OID 16391)
-- Dependencies: 220
-- Data for Name: department; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.department (dept_id, dept_name, description, email, contactno) FROM stdin;
1	Criminal Investigation	Handles major crime investigations	cid@police.gov.in	080-22942500
2	Cyber Crime	Investigates cybercrimes and digital fraud	cyber@police.gov.in	080-22942600
3	Traffic Police	Manages traffic violations and accidents	traffic@police.gov.in	080-22942700
4	Forensic	Provides forensic analysis and lab services	forensic@police.gov.in	080-22942800
\.


--
-- TOC entry 5205 (class 0 OID 16497)
-- Dependencies: 233
-- Data for Name: evidence; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.evidence (evidence_id, description, collection_date, mongo_id, status, officer_id, crime_case_id) FROM stdin;
1	CCTV Footage from jewelry store	2024-01-16	mongo_obj_001	Analyzed	1	1
2	Weapon recovered from scene	2024-01-16	mongo_obj_002	In Storage	1	1
3	Email logs and IP addresses	2024-02-12	mongo_obj_003	Analyzed	4	2
4	Vehicle dashcam footage	2024-03-06	mongo_obj_004	Analyzed	7	3
5	Fingerprints from window frame	2024-03-22	mongo_obj_005	Analyzed	6	4
6	Witness testimony recording	2024-04-02	mongo_obj_006	Presented in Court	1	5
7	Fingerprint evidence	2025-12-28	\N	Collected	1	4
\.


--
-- TOC entry 5211 (class 0 OID 16589)
-- Dependencies: 239
-- Data for Name: ipc_section; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ipc_section (crime_case_id, ipc_section) FROM stdin;
1	IPC 392
1	IPC 397
2	IPC 420
2	IT Act 66C
3	IPC 279
3	IPC 304A
4	IPC 454
4	IPC 380
5	IPC 323
7	IPC 999
8	IPC 999
\.


--
-- TOC entry 5207 (class 0 OID 16536)
-- Dependencies: 235
-- Data for Name: is_suspect; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.is_suspect (crime_case_id, suspect_id) FROM stdin;
1	1
1	2
2	3
3	4
4	1
5	2
\.


--
-- TOC entry 5206 (class 0 OID 16519)
-- Dependencies: 234
-- Data for Name: is_victim; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.is_victim (crime_case_id, victim_id) FROM stdin;
1	1
2	2
3	3
4	4
5	1
\.


--
-- TOC entry 5195 (class 0 OID 16413)
-- Dependencies: 223
-- Data for Name: location; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.location (location_id, landmark, streetno, pincode) FROM stdin;
1	MG Road Metro Station	15/A	560001
2	Indiranagar Bus Stand	23/B	560025
3	JP Nagar 4th Phase	45/C	560017
4	Koramangala 5th Block	12/D	560059
5	Whitefield Main Road	78/E	560003
6	Jayanagar Shopping Complex	34/F	560004
7	Electronic City Phase 1	56/G	560002
\.


--
-- TOC entry 5197 (class 0 OID 16426)
-- Dependencies: 225
-- Data for Name: officer; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.officer (officer_id, fname, lname, rank, phoneno, dept_id) FROM stdin;
1	Rajesh	Kumar	Inspector	9876543210	1
2	Priya	Sharma	Sub-Inspector	9876543211	1
3	Amit	Verma	Constable	9876543212	1
4	Sneha	Reddy	Inspector	9876543213	2
5	Vikram	Singh	Sub-Inspector	9876543214	2
6	Anita	Desai	Forensic Expert	9876543215	4
7	Ravi	Menon	Traffic Inspector	9876543216	3
8	Test	Officer	Sub-Inspector	9999999999	1
\.


--
-- TOC entry 5193 (class 0 OID 16403)
-- Dependencies: 221
-- Data for Name: pincode_area; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.pincode_area (pincode, city, district, state) FROM stdin;
560001	Bangalore	Bangalore Urban	Karnataka
560002	Bangalore	Bangalore Urban	Karnataka
560003	Bangalore	Bangalore Urban	Karnataka
560004	Bangalore	Bangalore Urban	Karnataka
560017	Bangalore	Bangalore Urban	Karnataka
560025	Bangalore	Bangalore Urban	Karnataka
560059	Bangalore	Bangalore Urban	Karnataka
\.


--
-- TOC entry 5199 (class 0 OID 16441)
-- Dependencies: 227
-- Data for Name: suspect; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.suspect (suspect_id, fname, lname, email, address, sex, hascriminalrec) FROM stdin;
1	Ramesh	Patel	ramesh.p@email.com	12/A MG Road, Bangalore	M	t
2	Sanjay	Gupta	\N	45/B Whitefield, Bangalore	M	f
3	Lakshmi	Iyer	lakshmi.i@email.com	23/C Jayanagar, Bangalore	F	f
4	Deepak	Rao	deepak.r@email.com	78/D Electronic City, Bangalore	M	t
\.


--
-- TOC entry 5209 (class 0 OID 16565)
-- Dependencies: 237
-- Data for Name: suspect_phone_no; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.suspect_phone_no (suspect_id, phoneno) FROM stdin;
1	9987654321
2	9987654322
2	9987654323
3	9987654324
4	9987654325
\.


--
-- TOC entry 5215 (class 0 OID 16676)
-- Dependencies: 248
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (user_id, username, email, hashed_password, full_name, role, is_active, created_at, updated_at) FROM stdin;
1	admin	admin@crime.com	$2b$12$I/K6QiQ3oV2Z1RF4rdTBOOjY2JLHpA9YTcG8hyCAbn5G55bSz8mSO	System Administrator	admin	t	2025-12-31 01:58:18.617716	2025-12-31 01:58:18.617722
2	officer1	officer1@crime.com	$2b$12$d8LWbfwRJ0v9/VKg4HmIP.0QTpJE34BYWZrD4l04k4cBjgN1WU3b.	John Officer	officer	t	2025-12-31 02:08:18.642201	2025-12-31 02:08:18.642207
\.


--
-- TOC entry 5201 (class 0 OID 16455)
-- Dependencies: 229
-- Data for Name: victim; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.victim (victim_id, fname, lname, email, address, sex, injury_details) FROM stdin;
1	Anjali	Nair	anjali.n@email.com	34/E Indiranagar, Bangalore	F	Minor bruises on arm
2	Karthik	Reddy	karthik.r@email.com	56/F Koramangala, Bangalore	M	Head injury, required stitches
3	Meera	Singh	meera.s@email.com	12/G JP Nagar, Bangalore	F	No physical injuries
4	Suresh	Kumar	\N	89/H Whitefield, Bangalore	M	Fracture in left hand
\.


--
-- TOC entry 5208 (class 0 OID 16553)
-- Dependencies: 236
-- Data for Name: victim_phone_no; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.victim_phone_no (victim_id, phoneno) FROM stdin;
1	9123456780
1	9123456781
2	9123456782
3	9123456783
4	9123456784
4	9123456785
\.


--
-- TOC entry 5252 (class 0 OID 0)
-- Dependencies: 245
-- Name: case_status_audit_audit_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.case_status_audit_audit_id_seq', 1, true);


--
-- TOC entry 5253 (class 0 OID 0)
-- Dependencies: 230
-- Name: crime_case_crime_case_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crime_case_crime_case_id_seq', 8, true);


--
-- TOC entry 5254 (class 0 OID 0)
-- Dependencies: 219
-- Name: department_dept_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.department_dept_id_seq', 4, true);


--
-- TOC entry 5255 (class 0 OID 0)
-- Dependencies: 232
-- Name: evidence_evidence_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.evidence_evidence_id_seq', 7, true);


--
-- TOC entry 5256 (class 0 OID 0)
-- Dependencies: 222
-- Name: location_location_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.location_location_id_seq', 7, true);


--
-- TOC entry 5257 (class 0 OID 0)
-- Dependencies: 224
-- Name: officer_officer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.officer_officer_id_seq', 8, true);


--
-- TOC entry 5258 (class 0 OID 0)
-- Dependencies: 226
-- Name: suspect_suspect_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.suspect_suspect_id_seq', 4, true);


--
-- TOC entry 5259 (class 0 OID 0)
-- Dependencies: 247
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_user_id_seq', 2, true);


--
-- TOC entry 5260 (class 0 OID 0)
-- Dependencies: 228
-- Name: victim_victim_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.victim_victim_id_seq', 4, true);


--
-- TOC entry 5013 (class 2606 OID 16646)
-- Name: case_status_audit case_status_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.case_status_audit
    ADD CONSTRAINT case_status_audit_pkey PRIMARY KEY (audit_id);


--
-- TOC entry 4991 (class 2606 OID 16485)
-- Name: crime_case crime_case_fir_no_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_case
    ADD CONSTRAINT crime_case_fir_no_key UNIQUE (fir_no);


--
-- TOC entry 4993 (class 2606 OID 16483)
-- Name: crime_case crime_case_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_case
    ADD CONSTRAINT crime_case_pkey PRIMARY KEY (crime_case_id);


--
-- TOC entry 5009 (class 2606 OID 16583)
-- Name: crime_type crime_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_type
    ADD CONSTRAINT crime_type_pkey PRIMARY KEY (crime_case_id, crime_type);


--
-- TOC entry 4975 (class 2606 OID 16402)
-- Name: department department_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.department
    ADD CONSTRAINT department_email_key UNIQUE (email);


--
-- TOC entry 4977 (class 2606 OID 16400)
-- Name: department department_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.department
    ADD CONSTRAINT department_pkey PRIMARY KEY (dept_id);


--
-- TOC entry 4998 (class 2606 OID 16508)
-- Name: evidence evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_pkey PRIMARY KEY (evidence_id);


--
-- TOC entry 5011 (class 2606 OID 16595)
-- Name: ipc_section ipc_section_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ipc_section
    ADD CONSTRAINT ipc_section_pkey PRIMARY KEY (crime_case_id, ipc_section);


--
-- TOC entry 5003 (class 2606 OID 16542)
-- Name: is_suspect is_suspect_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.is_suspect
    ADD CONSTRAINT is_suspect_pkey PRIMARY KEY (crime_case_id, suspect_id);


--
-- TOC entry 5001 (class 2606 OID 16525)
-- Name: is_victim is_victim_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.is_victim
    ADD CONSTRAINT is_victim_pkey PRIMARY KEY (crime_case_id, victim_id);


--
-- TOC entry 4982 (class 2606 OID 16419)
-- Name: location location_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_pkey PRIMARY KEY (location_id);


--
-- TOC entry 4985 (class 2606 OID 16434)
-- Name: officer officer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.officer
    ADD CONSTRAINT officer_pkey PRIMARY KEY (officer_id);


--
-- TOC entry 4979 (class 2606 OID 16411)
-- Name: pincode_area pincode_area_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pincode_area
    ADD CONSTRAINT pincode_area_pkey PRIMARY KEY (pincode);


--
-- TOC entry 5007 (class 2606 OID 16571)
-- Name: suspect_phone_no suspect_phone_no_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suspect_phone_no
    ADD CONSTRAINT suspect_phone_no_pkey PRIMARY KEY (suspect_id, phoneno);


--
-- TOC entry 4987 (class 2606 OID 16453)
-- Name: suspect suspect_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suspect
    ADD CONSTRAINT suspect_pkey PRIMARY KEY (suspect_id);


--
-- TOC entry 5019 (class 2606 OID 16687)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- TOC entry 5005 (class 2606 OID 16559)
-- Name: victim_phone_no victim_phone_no_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.victim_phone_no
    ADD CONSTRAINT victim_phone_no_pkey PRIMARY KEY (victim_id, phoneno);


--
-- TOC entry 4989 (class 2606 OID 16466)
-- Name: victim victim_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.victim
    ADD CONSTRAINT victim_pkey PRIMARY KEY (victim_id);


--
-- TOC entry 4994 (class 1259 OID 16602)
-- Name: idx_crime_case_date_occ; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crime_case_date_occ ON public.crime_case USING btree (date_occ);


--
-- TOC entry 4995 (class 1259 OID 16603)
-- Name: idx_crime_case_officer; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crime_case_officer ON public.crime_case USING btree (officer_id);


--
-- TOC entry 4996 (class 1259 OID 16601)
-- Name: idx_crime_case_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crime_case_status ON public.crime_case USING btree (status);


--
-- TOC entry 5014 (class 1259 OID 16691)
-- Name: idx_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_email ON public.users USING btree (email);


--
-- TOC entry 4999 (class 1259 OID 16604)
-- Name: idx_evidence_case; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_evidence_case ON public.evidence USING btree (crime_case_id);


--
-- TOC entry 4980 (class 1259 OID 16606)
-- Name: idx_location_pincode; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_location_pincode ON public.location USING btree (pincode);


--
-- TOC entry 4983 (class 1259 OID 16605)
-- Name: idx_officer_dept; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_officer_dept ON public.officer USING btree (dept_id);


--
-- TOC entry 5015 (class 1259 OID 16690)
-- Name: idx_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_username ON public.users USING btree (username);


--
-- TOC entry 5016 (class 1259 OID 16688)
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- TOC entry 5017 (class 1259 OID 16689)
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- TOC entry 5034 (class 2620 OID 16672)
-- Name: crime_case case_status_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER case_status_audit AFTER UPDATE ON public.crime_case FOR EACH ROW EXECUTE FUNCTION public.log_case_status_change();


--
-- TOC entry 5036 (class 2620 OID 16670)
-- Name: evidence evidence_triggers_investigation; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER evidence_triggers_investigation AFTER INSERT ON public.evidence FOR EACH ROW EXECUTE FUNCTION public.update_case_status_on_evidence();


--
-- TOC entry 5038 (class 2620 OID 16674)
-- Name: is_suspect mark_repeat_offender; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER mark_repeat_offender AFTER INSERT ON public.is_suspect FOR EACH ROW EXECUTE FUNCTION public.update_suspect_criminal_record();


--
-- TOC entry 5035 (class 2620 OID 16671)
-- Name: crime_case validate_case_dates; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER validate_case_dates BEFORE INSERT OR UPDATE ON public.crime_case FOR EACH ROW EXECUTE FUNCTION public.validate_crime_case_dates();


--
-- TOC entry 5037 (class 2620 OID 16673)
-- Name: evidence validate_evidence_collection_date; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER validate_evidence_collection_date BEFORE INSERT OR UPDATE ON public.evidence FOR EACH ROW EXECUTE FUNCTION public.validate_evidence_date();


--
-- TOC entry 5022 (class 2606 OID 16491)
-- Name: crime_case crime_case_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_case
    ADD CONSTRAINT crime_case_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(location_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5023 (class 2606 OID 16486)
-- Name: crime_case crime_case_officer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_case
    ADD CONSTRAINT crime_case_officer_id_fkey FOREIGN KEY (officer_id) REFERENCES public.officer(officer_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5032 (class 2606 OID 16584)
-- Name: crime_type crime_type_crime_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_type
    ADD CONSTRAINT crime_type_crime_case_id_fkey FOREIGN KEY (crime_case_id) REFERENCES public.crime_case(crime_case_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5024 (class 2606 OID 16514)
-- Name: evidence evidence_crime_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_crime_case_id_fkey FOREIGN KEY (crime_case_id) REFERENCES public.crime_case(crime_case_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5025 (class 2606 OID 16509)
-- Name: evidence evidence_officer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_officer_id_fkey FOREIGN KEY (officer_id) REFERENCES public.officer(officer_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5033 (class 2606 OID 16596)
-- Name: ipc_section ipc_section_crime_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ipc_section
    ADD CONSTRAINT ipc_section_crime_case_id_fkey FOREIGN KEY (crime_case_id) REFERENCES public.crime_case(crime_case_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5028 (class 2606 OID 16543)
-- Name: is_suspect is_suspect_crime_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.is_suspect
    ADD CONSTRAINT is_suspect_crime_case_id_fkey FOREIGN KEY (crime_case_id) REFERENCES public.crime_case(crime_case_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5029 (class 2606 OID 16548)
-- Name: is_suspect is_suspect_suspect_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.is_suspect
    ADD CONSTRAINT is_suspect_suspect_id_fkey FOREIGN KEY (suspect_id) REFERENCES public.suspect(suspect_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5026 (class 2606 OID 16526)
-- Name: is_victim is_victim_crime_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.is_victim
    ADD CONSTRAINT is_victim_crime_case_id_fkey FOREIGN KEY (crime_case_id) REFERENCES public.crime_case(crime_case_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5027 (class 2606 OID 16531)
-- Name: is_victim is_victim_victim_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.is_victim
    ADD CONSTRAINT is_victim_victim_id_fkey FOREIGN KEY (victim_id) REFERENCES public.victim(victim_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5020 (class 2606 OID 16420)
-- Name: location location_pincode_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_pincode_fkey FOREIGN KEY (pincode) REFERENCES public.pincode_area(pincode) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5021 (class 2606 OID 16435)
-- Name: officer officer_dept_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.officer
    ADD CONSTRAINT officer_dept_id_fkey FOREIGN KEY (dept_id) REFERENCES public.department(dept_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5031 (class 2606 OID 16572)
-- Name: suspect_phone_no suspect_phone_no_suspect_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suspect_phone_no
    ADD CONSTRAINT suspect_phone_no_suspect_id_fkey FOREIGN KEY (suspect_id) REFERENCES public.suspect(suspect_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5030 (class 2606 OID 16560)
-- Name: victim_phone_no victim_phone_no_victim_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.victim_phone_no
    ADD CONSTRAINT victim_phone_no_victim_id_fkey FOREIGN KEY (victim_id) REFERENCES public.victim(victim_id) ON UPDATE CASCADE ON DELETE CASCADE;


-- Completed on 2026-01-15 08:21:47

--
-- PostgreSQL database dump complete
--

\unrestrict vS0abBNJrs8OBPkkD7jFTOa9zgsxrDiN5vyfWxQ24teebwvvhk5U4R2V0tS2S8K

