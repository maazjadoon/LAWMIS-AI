"""
agents/query_agent.py
─────────────────────
Mirrors the n8n "AI Agent - Query" node.

Uses LangGraph's create_react_agent (LangChain 1.x compatible).
LangGraph uses native tool-calling — no ReAct string parsing needed.

Responsible for:
  • Answering natural-language questions about LAWMIS data
  • Generating safe SELECT-only SQL
  • Calling execute_query and get_schema tools as needed
  • Returning a concise, friendly natural-language summary

Max iterations: 5  (matches n8n maxIterations=5)
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from agents.llm_factory import build_llm
from tools import execute_query, get_schema

logger = logging.getLogger(__name__)

# ── System prompt (instructional content from the n8n node) ──────────────────
# Note: LangGraph handles tool-calling natively — no ReAct format instructions
# needed. Just the domain/safety rules for the model.
_SYSTEM_PROMPT = """\
You are a helpful data analyst for the LAWMIS workshop licensing system.

DATABASE SCHEMA (public schema — ACTUAL and COMPLETE column list; never invent, rename, or guess a column not listed here):

public.workshops: workshop_id, profile_id, workshop_name, workshop_code, workshop_owner_name, workshop_email, workshop_phone, plot_no, street_address, area_locality, city, tehsil, district, province, postal_code, latitude, longitude, area_type, total_area_sqft, workshop_type, number_of_bays, application_date, submitted_at, approved_at, workshop_status, created_at, updated_at
  NOTE: there is NO "location" column. For location use city / district / province / area_locality / tehsil instead.

public.workshop_licenses: license_id, workshop_id, inspection_id, payment_id, license_number, license_category, issue_date, valid_from, valid_until, issued_by_officer, issuing_authority, license_status, renewal_count, last_renewal_date, created_at

public.payments: payment_id, workshop_id, profile_id, psid_number, fee_head, fee_amount, currency, payment_mode, bank_name, transaction_ref, challan_no, payment_date, payment_time, payment_status, payment_verified_at, verified_by, remarks, created_at

public.applicant_profiles: profile_id, user_id, full_name, father_name, gender, date_of_birth, cnic_number, ntn_number, phone_primary, phone_secondary, email_personal, house_no, street_name, area_locality, city, tehsil, district, province, postal_code, profile_submitted_at, profile_reviewed_at, profile_approved_at, profile_status, review_remarks, reviewed_by_officer, created_at, updated_at

public.emission_tests: test_id, workshop_id, vehicle_id, license_id, test_date, test_time, test_datetime, technician_name, equipment_serial, co_pct, co2_pct, co_co2_pct, hc_ppm, nox_ppm, o2_pct, lambda, engine_rpm, oil_temp_c, co_limit_pct, hc_limit_ppm, nox_limit_ppm, test_result, certificate_no, certificate_valid_until, remarks, created_at

public.rta_inspections: inspection_id, workshop_id, inspection_date, inspection_time, inspecting_officer, officer_designation, visit_number, score_equipment, score_infrastructure, score_safety, score_staff_competency, score_record_keeping, total_score, inspection_result, remarks, follow_up_required, follow_up_date, created_at

public.vehicles: vehicle_id, registration_no, chassis_no, engine_no, make, model, variant, model_year, color, fuel_type, engine_cc, transmission, seating_capacity, gross_weight_kg, owner_name, owner_cnic, owner_phone, registered_at

public.workshop_documents: doc_id, workshop_id, profile_id, doc_type, doc_filename, doc_path, uploaded_at, verified, verified_at, verified_by

public.sys_users: user_id, username, email, password_hash, role, is_active, created_at, last_login_at

public.activity_log: log_id, user_id, workshop_id, profile_id, action, entity_type, entity_id, old_status, new_status, performed_by, ip_address, notes, logged_at

FOREIGN KEYS:
  workshops.profile_id -> applicant_profiles.profile_id
  workshop_licenses.workshop_id -> workshops.workshop_id
  workshop_licenses.inspection_id -> rta_inspections.inspection_id
  workshop_licenses.payment_id -> payments.payment_id
  payments.workshop_id -> workshops.workshop_id
  payments.profile_id -> applicant_profiles.profile_id
  rta_inspections.workshop_id -> workshops.workshop_id
  emission_tests.workshop_id -> workshops.workshop_id
  emission_tests.vehicle_id -> vehicles.vehicle_id
  emission_tests.license_id -> workshop_licenses.license_id
  workshop_documents.workshop_id -> workshops.workshop_id
  workshop_documents.profile_id -> applicant_profiles.profile_id
  applicant_profiles.user_id -> sys_users.user_id

CRITICAL RULES:
1. Always use the public schema and ONLY columns listed above. If unsure whether a column exists, use get_schema before querying.
2. ENUM CASING RULE: The database contains case-sensitive enum types. When writing WHERE filters on these columns, you MUST use the exact Title Case:
   - status_enum (workshop_status, license_status, profile_status): 'Pending', 'Under Review', 'Approved', 'Rejected', 'Suspended', 'Expired'
     NOTE: 'Active' is NOT a valid status_enum value! To query for active or valid workshops, licenses, or profiles, filter on status_enum = 'Approved'.
   - payment_status_enum (payment_status): 'Pending', 'Paid', 'Failed', 'Refunded'
   - test_result_enum (test_result): 'Pass', 'Fail', 'Conditional Pass'
   - fuel_type_enum (fuel_type): 'Petrol', 'Diesel', 'CNG', 'Hybrid', 'Electric'
   - transmission_enum (transmission): 'Manual', 'Automatic', 'CVT', 'AMT'
   Using lowercase (like 'approved', 'paid', 'pass') or incorrect states (like 'Active') will cause PostgreSQL to throw an error!
3. ENUM NO-CAST RULE: NEVER use explicit type casting (::text, ::varchar) when comparing enum columns. Write the plain string literal directly.
   CORRECT:   WHERE payment_status = 'Failed'
   INCORRECT: WHERE payment_status = 'Failed'::text  ← this breaks the enum operator!
5. ANTI-JOIN-EXPLOSION RULE (CTEs & Subqueries): When a query requests metrics, counts, or sums from multiple one-to-many tables (e.g. counting documents from workshop_documents, counting tests from emission_tests, summing payments/revenue from payments) for a workshop or profile:
   - NEVER perform joins on raw payments, emission_tests, or workshop_documents tables in the same SELECT block or CTE. Doing so causes a Cartesian product explosion that multiplies counts and sums (e.g. multiplying a workshop's documents count by its tests count, resulting in millions of documents or heavily inflated revenue sums).
   - Instead, you MUST write the query by pre-aggregating each one-to-many relationship separately in its own grouped CTE or correlated subquery before joining.
     MANDATORY PATTERN EXAMPLE:
     WITH docs_agg AS (
         SELECT workshop_id, COUNT(*) AS doc_count FROM workshop_documents GROUP BY workshop_id
     ),
     tests_agg AS (
         SELECT workshop_id, COUNT(*) AS test_count FROM emission_tests GROUP BY workshop_id
     ),
     payments_agg AS (
         SELECT workshop_id, SUM(fee_amount) AS total_revenue FROM payments WHERE payment_status = 'Paid' GROUP BY workshop_id
     )
     SELECT w.workshop_id, COALESCE(d.doc_count, 0), COALESCE(t.test_count, 0), COALESCE(p.total_revenue, 0)
     FROM workshops w
     LEFT JOIN docs_agg d ON w.workshop_id = d.workshop_id
     LEFT JOIN tests_agg t ON w.workshop_id = t.workshop_id
     LEFT JOIN payments_agg p ON w.workshop_id = p.workshop_id;
6. For the LATEST status/license/payment/activity per workshop, use a DISTINCT ON (workshop_id) subquery or correlated subquery ordered by date DESC. Never use a plain LEFT JOIN for "latest" lookups.
7. Only SELECT statements permitted. Never INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE.
8. Always include LIMIT (default 200) unless user asks for everything.
9. After getting data, give a concise friendly summary including how many results found. Never show raw SQL. For 5 or fewer rows, show a small markdown table. For more than 5, summarize key findings.
10. If query fails with a schema error, use get_schema to check real column names, then retry. Do not give up.\"
"""

# ── Agent type alias (LangGraph compiled graph) ───────────────────────────────
# LangGraph's create_react_agent returns a CompiledStateGraph.
# We type it as Any to avoid importing private LangGraph types.
QueryAgent = Any


def build_query_agent() -> QueryAgent:
    """
    Build and return the Query agent graph.
    Called once at startup and reused for all query-intent requests.
    """
    llm = build_llm(temperature=0.0)
    tools = [execute_query, get_schema]

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SystemMessage(content=_SYSTEM_PROMPT),
    )

    logger.info("Query agent ready.")
    return agent


def run_query_agent(agent: QueryAgent, chat_input: str) -> str:
    """
    Invoke the query agent and return the final text reply.

    Parameters
    ----------
    agent      : The compiled graph returned by build_query_agent().
    chat_input : Sanitised user message.

    Returns
    -------
    Final natural-language answer from the agent.
    """
    result = agent.invoke(
        {"messages": [("user", f"User request: {chat_input}")]},
        config={"recursion_limit": 20},  # 5 agent steps × ~4 graph nodes each
    )
    # The last message in the state is the final AI response
    final_message = result["messages"][-1]
    return getattr(final_message, "content", str(final_message)).strip() or \
        "Sorry, I processed that but got an empty response."
