"""End-to-end checks of the rules a law firm depends on, through the real API and databases."""
import hashlib
from datetime import date, timedelta

import psycopg
import pytest
from sqlalchemy import text

from .conftest import ADMIN_DSN, TEST_DB, login

API = "/api/v1"
TODAY = date.today()
THEIR_MATTER = 1    # Meera Nair's; lawyer1 is not on it
OWN_MATTER = 2      # lawyer1 is lead counsel


def new_case(client, headers, number, **extra):
    body = {
        "matter_title": f"Test matter {number}",
        "case_number": number,
        "date_cause": str(TODAY - timedelta(days=30)),
        "date_filed": str(TODAY - timedelta(days=10)),
        **extra,
    }
    return client.post(f"{API}/cases/", json=body, headers=headers)


# ---------------------------------------------------------------- access basics

@pytest.mark.parametrize("path", [
    "/cases/", "/lawyers/", "/clients/", "/opposing-parties/", "/evidence/", "/hearings/", "/tasks/",
    "/workspace/summary", "/search/?q=abc", "/analytics/dashboard", "/analytics/firm", "/audit/", "/team/members",
    "/team/directory", "/courts/", "/locations/", "/practice-groups/",
])
def test_every_data_route_needs_a_login(client, path):
    assert client.get(f"{API}{path}").status_code == 401


@pytest.mark.parametrize("path", ["/analytics/dashboard", "/analytics/firm", "/audit/", "/team/members", "/team/join-requests"])
@pytest.mark.parametrize("who", ["lawyer", "staff"])
def test_firm_wide_views_are_admin_only(client, request, path, who):
    assert client.get(f"{API}{path}", headers=request.getfixturevalue(who)).status_code == 403


def test_admin_can_see_firm_views(client, admin):
    for path in ("/analytics/firm", "/audit/", "/team/members", "/team/join-requests"):
        assert client.get(f"{API}{path}", headers=admin).status_code == 200


# ---------------------------------------------------------------- onboarding

def test_join_request_approved_end_to_end(client, admin):
    body = {
        "fname": "Kavya", "lname": "Shetty", "username": "kavya", "email": "kavya@example.com",
        "password": "correct-horse", "bar_id": "KAR/7777/2021", "designation": "Associate", "group_id": 2,
    }
    r = client.post(f"{API}/auth/join-requests", json=body)
    assert r.status_code == 201
    request_id = r.json()["request_id"]

    # Cannot use the system yet, and is told why
    r = client.post(f"{API}/auth/login-json", json={"username": "kavya", "password": "correct-horse"})
    assert r.status_code == 403 and "approval" in r.json()["detail"]
    # No second request for the same person
    assert client.post(f"{API}/auth/join-requests", json=body).status_code == 400

    r = client.post(f"{API}/team/join-requests/{request_id}/approve", json={}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "lawyer" and r.json()["lawyer_id"]
    # Cannot be approved twice
    assert client.post(f"{API}/team/join-requests/{request_id}/approve", json={}, headers=admin).status_code == 409

    headers = login(client, "kavya", "correct-horse")
    me = client.get(f"{API}/auth/me", headers=headers).json()
    profile = client.get(f"{API}/lawyers/{me['lawyer_id']}", headers=headers).json()
    assert profile["bar_id"] == "KAR/7777/2021" and profile["can_view_matters"]


def test_join_request_cannot_ask_for_admin(client):
    r = client.post(f"{API}/auth/join-requests", json={
        "fname": "A", "lname": "B", "username": "sneaky", "email": "sneaky@example.com",
        "password": "correct-horse", "requested_role": "admin",
    })
    assert r.status_code == 422


def test_rejected_request_cannot_log_in(client, admin):
    r = client.post(f"{API}/auth/join-requests", json={
        "fname": "No", "lname": "Thanks", "username": "nothanks", "email": "no@example.com", "password": "correct-horse",
    })
    rid = r.json()["request_id"]
    r = client.post(f"{API}/team/join-requests/{rid}/reject", json={"note": "Not known to the firm"}, headers=admin)
    assert r.json()["status"] == "Rejected"
    r = client.post(f"{API}/auth/login-json", json={"username": "nothanks", "password": "correct-horse"})
    assert r.status_code == 401


def test_admin_created_member_must_change_password(client, admin):
    r = client.post(f"{API}/team/members", headers=admin, json={
        "fname": "Dev", "lname": "Patel", "username": "dev", "email": "dev@example.com", "role": "lawyer", "group_id": 1,
    })
    assert r.status_code == 201, r.text
    temporary = r.json()["temporary_password"]
    headers = login(client, "dev", temporary)
    r = client.get(f"{API}/cases/", headers=headers)
    assert r.status_code == 403 and r.json()["detail"] == "Password change required"
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 200
    r = client.post(f"{API}/auth/change-password", headers=headers, json={"old_password": temporary, "new_password": "a-new-password"})
    assert r.status_code == 200
    assert client.get(f"{API}/cases/", headers=headers).status_code == 200


def test_existing_lawyer_can_be_given_a_login(client, admin):
    r = client.post(f"{API}/team/members", headers=admin, json={
        "fname": "Meera", "lname": "Nair", "username": "meera", "email": "meera@example.com", "role": "lawyer", "lawyer_id": 3,
    })
    assert r.status_code == 201
    assert r.json()["member"]["lawyer_id"] == 3
    # Only one login per lawyer
    r = client.post(f"{API}/team/members", headers=admin, json={
        "fname": "Meera", "lname": "Nair", "username": "meera2", "email": "meera2@example.com", "role": "lawyer", "lawyer_id": 3,
    })
    assert r.status_code == 400


def test_deactivation_ends_open_sessions_and_keeps_history(client, admin):
    r = client.post(f"{API}/team/members", headers=admin, json={
        "fname": "Temp", "lname": "Person", "username": "temp", "email": "temp@example.com", "role": "staff",
    })
    user_id = r.json()["member"]["user_id"]
    temporary = r.json()["temporary_password"]
    headers = login(client, "temp", temporary)
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 200
    client.post(f"{API}/team/members/{user_id}/deactivate", headers=admin)
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401
    r = client.post(f"{API}/auth/login-json", json={"username": "temp", "password": temporary})
    assert r.status_code == 403


def test_firm_keeps_an_admin(client, admin):
    me = client.get(f"{API}/auth/me", headers=admin).json()
    assert client.post(f"{API}/team/members/{me['user_id']}/deactivate", headers=admin).status_code == 400
    r = client.patch(f"{API}/team/members/{me['user_id']}/role", json={"role": "staff"}, headers=admin)
    assert r.status_code == 400


def test_public_registration_endpoint_is_not_open(client):
    r = client.post(f"{API}/auth/register", json={"username": "x12", "email": "x12@example.com", "password": "correct-horse", "role": "admin"})
    assert r.status_code == 401


# ---------------------------------------------------------------- what a lawyer can reach

def test_lawyer_opens_own_matter_only(client, lawyer):
    assert client.get(f"{API}/cases/{OWN_MATTER}", headers=lawyer).status_code == 200
    assert client.get(f"{API}/cases/{THEIR_MATTER}", headers=lawyer).status_code == 403
    for sub in ("timeline", "notes", "lawyers"):
        assert client.get(f"{API}/cases/{THEIR_MATTER}/{sub}", headers=lawyer).status_code == 403
    assert client.get(f"{API}/hearings/?case_id={THEIR_MATTER}", headers=lawyer).status_code == 403


def test_firm_wide_list_redacts_other_lawyers_matters(client, lawyer):
    items = client.get(f"{API}/cases/?size=100", headers=lawyer).json()["items"]
    assert len(items) >= 12
    other = next(c for c in items if c["case_id"] == THEIR_MATTER)
    assert other["can_open"] is False
    assert other["matter_title"] and other["case_number"]
    assert other["court_name"] is None and other["location_name"] is None and other["matter_types"] == []
    own = next(c for c in items if c["case_id"] == OWN_MATTER)
    assert own["can_open"] is True and own["court_name"]


def test_mine_scope_lists_only_own_matters(client, lawyer):
    items = client.get(f"{API}/cases/?scope=mine&size=100", headers=lawyer).json()["items"]
    assert items and all(c["can_open"] for c in items)
    assert THEIR_MATTER not in {c["case_id"] for c in items}


def test_lawyer_cannot_change_someone_elses_matter(client, lawyer):
    assert client.put(f"{API}/cases/{THEIR_MATTER}", json={"matter_title": "Hijacked"}, headers=lawyer).status_code == 403
    assert client.patch(f"{API}/cases/{THEIR_MATTER}/status?new_status=Pending", headers=lawyer).status_code == 403
    assert client.delete(f"{API}/cases/{THEIR_MATTER}", headers=lawyer).status_code == 403
    assert client.post(f"{API}/cases/{THEIR_MATTER}/notes", json={"body": "x"}, headers=lawyer).status_code == 403
    assert client.post(f"{API}/cases/{THEIR_MATTER}/lawyers", json={"lawyer_id": 1, "role": "Associate"}, headers=lawyer).status_code == 403
    r = client.post(f"{API}/hearings/", json={"case_id": THEIR_MATTER, "hearing_date": str(TODAY)}, headers=lawyer)
    assert r.status_code == 403
    r = client.post(f"{API}/tasks/", json={"title": "x", "case_id": THEIR_MATTER}, headers=lawyer)
    assert r.status_code == 403
    r = client.post(f"{API}/evidence/", data={"filed_date": str(TODAY), "case_id": THEIR_MATTER}, headers=lawyer)
    assert r.status_code == 403


def test_lawyer_sees_colleague_profile_without_their_matters(client, lawyer):
    profile = client.get(f"{API}/lawyers/3", headers=lawyer).json()
    assert profile["fname"] == "Meera"
    assert profile["can_view_matters"] is False and profile["matters"] == []
    assert client.get(f"{API}/lawyers/3/cases", headers=lawyer).status_code == 403
    assert client.get(f"{API}/lawyers/3/workload", headers=lawyer).status_code == 403
    assert client.get(f"{API}/cases/?lawyer_id=3", headers=lawyer).status_code == 403
    assert client.get(f"{API}/hearings/?lawyer_id=3", headers=lawyer).status_code == 403
    me = client.get(f"{API}/lawyers/1", headers=lawyer).json()
    assert me["can_view_matters"] and me["matters"]


def test_admin_opens_a_lawyers_matters(client, admin):
    profile = client.get(f"{API}/lawyers/1", headers=admin).json()
    assert profile["can_view_matters"]
    numbers = {m["case_id"] for m in profile["matters"]}
    assert OWN_MATTER in numbers


def test_lawyer_can_only_edit_own_contact_details(client, lawyer):
    assert client.put(f"{API}/lawyers/1", json={"phoneno": "9000000000"}, headers=lawyer).status_code == 200
    assert client.put(f"{API}/lawyers/1", json={"designation": "Managing Partner"}, headers=lawyer).status_code == 403
    assert client.put(f"{API}/lawyers/3", json={"phoneno": "9000000000"}, headers=lawyer).status_code == 403


def test_client_details_are_limited_to_own_matters(client, admin, lawyer):
    own_client = client.get(f"{API}/cases/{OWN_MATTER}", headers=lawyer).json()["clients"][0]["client_id"]
    other_client = client.get(f"{API}/cases/{THEIR_MATTER}", headers=admin).json()["clients"][0]["client_id"]
    assert client.get(f"{API}/clients/{own_client}", headers=lawyer).status_code == 200
    assert client.get(f"{API}/clients/{other_client}", headers=lawyer).status_code == 403
    assert client.put(f"{API}/clients/{other_client}", json={"notes": "x"}, headers=lawyer).status_code == 403
    rows = {c["client_id"]: c for c in client.get(f"{API}/clients/?size=100", headers=lawyer).json()["items"]}
    assert rows[other_client]["can_open"] is False
    assert rows[other_client]["email"] is None and rows[other_client]["notes"] is None
    assert rows[other_client]["fname"]


def test_lawyer_search_never_reveals_other_matters_documents(client, admin, lawyer):
    docs = client.get(f"{API}/evidence/?case_id={THEIR_MATTER}", headers=admin).json()["items"]
    assert docs
    term = docs[0]["description"][:12]
    result = client.get(f"{API}/search/", params={"q": term}, headers=lawyer).json()
    assert all(d["case_id"] != THEIR_MATTER for d in result["documents"])
    result = client.get(f"{API}/search/", params={"q": term}, headers=admin).json()
    assert any(d["case_id"] == THEIR_MATTER for d in result["documents"])


def test_document_list_is_scoped(client, lawyer):
    items = client.get(f"{API}/evidence/?size=100", headers=lawyer).json()["items"]
    own = {c["case_id"] for c in client.get(f"{API}/cases/?scope=mine&size=100", headers=lawyer).json()["items"]}
    assert THEIR_MATTER not in own
    assert items and {i["case_id"] for i in items} <= own
    assert client.get(f"{API}/evidence/?case_id={THEIR_MATTER}", headers=lawyer).json()["items"] == []


def test_task_visibility(client, admin, lawyer, staff):
    task = client.post(f"{API}/tasks/", json={"title": "Private to Meera's matter", "case_id": THEIR_MATTER}, headers=admin).json()
    assert client.put(f"{API}/tasks/{task['task_id']}", json={"status": "Done"}, headers=lawyer).status_code == 404
    titles = [t["title"] for t in client.get(f"{API}/tasks/?size=100", headers=lawyer).json()["items"]]
    assert "Private to Meera's matter" not in titles
    assert any(t["task_id"] == task["task_id"] for t in client.get(f"{API}/tasks/?size=100", headers=staff).json()["items"])


def test_staff_can_do_clerical_work_but_not_control_a_matter(client, staff):
    assert client.get(f"{API}/cases/{THEIR_MATTER}", headers=staff).status_code == 200
    assert client.post(f"{API}/cases/{THEIR_MATTER}/notes", json={"body": "Clerk's note"}, headers=staff).status_code == 201
    assert client.put(f"{API}/cases/{THEIR_MATTER}", json={"matter_title": "Changed"}, headers=staff).status_code == 403
    assert client.delete(f"{API}/cases/{THEIR_MATTER}", headers=staff).status_code == 403
    assert client.post(f"{API}/cases/{THEIR_MATTER}/lawyers", json={"lawyer_id": 1, "role": "Associate"}, headers=staff).status_code == 403
    assert client.delete(f"{API}/lawyers/1", headers=staff).status_code == 403


def test_ai_routes_are_split_by_role(client, lawyer):
    assert client.get(f"{API}/ai/models/status", headers=lawyer).status_code == 403
    assert client.get(f"{API}/ai/hotspots", headers=lawyer).status_code == 403
    r = client.post(f"{API}/ai/classify/matter-type", json={"description": "x"}, headers=lawyer)
    assert r.status_code == 422


# ---------------------------------------------------------------- matters and counsel

def test_lawyer_adds_a_matter_and_becomes_lead(client, lawyer):
    r = new_case(client, lawyer, "OS 1/2026", matter_types=["Civil"], client_ids=[1])
    assert r.status_code == 201, r.text
    body = r.json()
    assert [(a["lawyer_id"], a["role"]) for a in body["assignments"]] == [(1, "Lead Counsel")]
    assert body["permissions"]["assign"] and not body["permissions"]["delete"]
    assert client.get(f"{API}/cases/{body['case_id']}", headers=lawyer).status_code == 200


def test_duplicate_case_number_rejected(client, lawyer):
    assert new_case(client, lawyer, "OS 2/2026").status_code == 201
    assert new_case(client, lawyer, "OS 2/2026").status_code == 400


def test_future_dates_are_a_clean_error(client, lawyer):
    r = new_case(client, lawyer, "OS 3/2026", date_filed=str(TODAY + timedelta(days=5)))
    assert r.status_code == 422


def test_lawyer_cannot_name_someone_else_lead(client, lawyer):
    r = new_case(client, lawyer, "OS 4/2026", assignments=[{"lawyer_id": 3, "role": "Lead Counsel"}])
    assert r.status_code == 403


def test_assigning_an_unassigned_matter(client, admin):
    case = new_case(client, admin, "OS 5/2026").json()
    assert case["assignments"] == []
    listed = client.get(f"{API}/cases/?unassigned=true&size=100", headers=admin).json()["items"]
    assert case["case_id"] in {c["case_id"] for c in listed}

    r = client.post(f"{API}/cases/{case['case_id']}/lawyers", json={"lawyer_id": 2, "role": "Lead Counsel"}, headers=admin)
    assert r.status_code == 201, r.text
    listed = client.get(f"{API}/cases/?unassigned=true&size=100", headers=admin).json()["items"]
    assert case["case_id"] not in {c["case_id"] for c in listed}


def test_replacing_the_lead_ends_the_old_assignment(client, admin):
    case = new_case(client, admin, "OS 6/2026", assignments=[{"lawyer_id": 2, "role": "Lead Counsel"}]).json()
    r = client.post(f"{API}/cases/{case['case_id']}/lawyers", json={"lawyer_id": 4, "role": "Lead Counsel"}, headers=admin)
    assert r.status_code == 201, r.text
    rows = {a["lawyer_id"]: a for a in client.get(f"{API}/cases/{case['case_id']}/lawyers", headers=admin).json()}
    assert rows[2]["end_date"] and rows[4]["end_date"] is None


def test_removing_counsel_keeps_history_and_ends_access(client, admin, lawyer):
    case = new_case(client, admin, "OS 7/2026", assignments=[{"lawyer_id": 1, "role": "Associate"}]).json()
    assert client.get(f"{API}/cases/{case['case_id']}", headers=lawyer).status_code == 200
    assert client.delete(f"{API}/cases/{case['case_id']}/lawyers/1", headers=admin).status_code == 200
    assert client.get(f"{API}/cases/{case['case_id']}", headers=lawyer).status_code == 403
    assert client.get(f"{API}/cases/{case['case_id']}/lawyers", headers=admin).json()[0]["end_date"]


def test_lead_can_assign_associate_on_own_matter_but_associate_cannot(client, admin, lawyer):
    case = new_case(client, admin, "OS 8/2026", assignments=[{"lawyer_id": 1, "role": "Associate"}]).json()
    r = client.post(f"{API}/cases/{case['case_id']}/lawyers", json={"lawyer_id": 2, "role": "Research"}, headers=lawyer)
    assert r.status_code == 403
    r = client.post(f"{API}/cases/{OWN_MATTER}/lawyers", json={"lawyer_id": 2, "role": "Research"}, headers=lawyer)
    assert r.status_code == 201


def test_inactive_lawyer_cannot_be_assigned(client, admin):
    lawyer_row = client.post(f"{API}/lawyers/", json={"fname": "Former", "lname": "Partner"}, headers=admin).json()
    with psycopg.connect(ADMIN_DSN.rsplit("/", 1)[0] + f"/{TEST_DB}", autocommit=True) as conn:
        conn.execute("UPDATE lawyer SET is_active = false WHERE lawyer_id = %s", (lawyer_row["lawyer_id"],))
    r = client.post(f"{API}/cases/{OWN_MATTER}/lawyers", json={"lawyer_id": lawyer_row["lawyer_id"], "role": "Associate"}, headers=admin)
    assert r.status_code == 400


def test_lawyer_with_history_cannot_be_deleted(client, admin):
    assert client.delete(f"{API}/lawyers/1", headers=admin).status_code == 409


def test_client_on_a_matter_cannot_be_deleted(client, admin):
    assert client.delete(f"{API}/clients/1", headers=admin).status_code == 409


def test_case_edit_replaces_parties_and_types(client, admin):
    case = new_case(client, admin, "OS 9/2026", matter_types=["Civil"], client_ids=[1], party_ids=[1]).json()
    r = client.put(f"{API}/cases/{case['case_id']}", json={
        "matter_types": ["Family", "Civil"], "client_ids": [2], "party_ids": [], "matter_description": "Updated",
    }, headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert {m["matter_type"] for m in body["matter_types"]} == {"Family", "Civil"}
    assert [c["client_id"] for c in body["clients"]] == [2]
    assert body["opposing_parties"] == []


# ---------------------------------------------------------------- hearings and history

def test_hearing_lifecycle_and_timeline(client, lawyer):
    case = new_case(client, lawyer, "CC 100/2026").json()
    assert case["status"] == "Filed"
    r = client.post(f"{API}/hearings/", json={
        "case_id": case["case_id"], "hearing_date": str(TODAY + timedelta(days=1)), "purpose": "First hearing", "judge": "J. Rao",
    }, headers=lawyer)
    assert r.status_code == 201, r.text
    hearing = r.json()
    case = client.get(f"{API}/cases/{case['case_id']}", headers=lawyer).json()
    assert case["status"] == "Hearing"
    assert case["next_hearing"] == str(TODAY + timedelta(days=1))

    next_date = TODAY + timedelta(days=30)
    r = client.post(f"{API}/hearings/{hearing['hearing_id']}/result", json={
        "status": "Adjourned", "outcome": "Opposite side sought time", "remarks": "Costs of 500 imposed",
        "attended_by": 1, "next_date": str(next_date), "next_purpose": "Evidence",
    }, headers=lawyer)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "Adjourned"

    rows = client.get(f"{API}/hearings/?case_id={case['case_id']}", headers=lawyer).json()
    assert [(h["status"], h["hearing_date"]) for h in rows] == [
        ("Adjourned", str(TODAY + timedelta(days=1))), ("Scheduled", str(next_date)),
    ]
    assert rows[1]["judge"] == "J. Rao"

    client.post(f"{API}/cases/{case['case_id']}/notes", json={"body": "Spoke to client"}, headers=lawyer)
    events = client.get(f"{API}/cases/{case['case_id']}/timeline", headers=lawyer).json()
    assert events[0]["upcoming"] and "Evidence" in events[0]["title"]
    kinds = {e["kind"] for e in events}
    assert {"hearing", "note", "status", "filed", "counsel"} <= kinds
    assert any("Costs of 500" in (e["detail"] or "") for e in events)


def test_next_date_must_follow_the_hearing(client, lawyer):
    h = client.post(f"{API}/hearings/", json={"case_id": OWN_MATTER, "hearing_date": str(TODAY)}, headers=lawyer).json()
    r = client.post(f"{API}/hearings/{h['hearing_id']}/result", json={"status": "Held", "next_date": str(TODAY)}, headers=lawyer)
    assert r.status_code == 400


def test_status_trigger_records_the_logged_in_user(client, admin):
    case = new_case(client, admin, "CC 101/2026").json()
    client.patch(f"{API}/cases/{case['case_id']}/status?new_status=Pending", headers=admin)
    events = client.get(f"{API}/cases/{case['case_id']}/timeline", headers=admin).json()
    status_events = [e for e in events if e["kind"] == "status"]
    assert status_events and status_events[0]["actor"] == "admin"


def test_disposal_records_outcome_and_cancels_future_hearings(client, admin):
    case = new_case(client, admin, "CC 102/2026").json()
    client.post(f"{API}/hearings/", json={"case_id": case["case_id"], "hearing_date": str(TODAY + timedelta(days=9))}, headers=admin)
    r = client.patch(f"{API}/cases/{case['case_id']}/status?new_status=Disposed&outcome=Settled", headers=admin)
    assert r.status_code == 200
    assert r.json()["outcome"] == "Settled" and r.json()["disposed_on"] == str(TODAY) and r.json()["next_hearing"] is None
    rows = client.get(f"{API}/hearings/?case_id={case['case_id']}", headers=admin).json()
    assert rows[0]["status"] == "Cancelled"
    r = client.post(f"{API}/hearings/", json={"case_id": case["case_id"], "hearing_date": str(TODAY + timedelta(days=1))}, headers=admin)
    assert r.status_code == 409
    r = client.patch(f"{API}/cases/{case['case_id']}/status?new_status=Hearing", headers=admin).json()
    assert r["disposed_on"] is None and r["outcome"] is None


def test_invalid_outcome_rejected(client, admin):
    assert client.patch(f"{API}/cases/{OWN_MATTER}/status?new_status=Disposed&outcome=Maybe", headers=admin).status_code == 400


def test_deadline_needs_a_date(client, lawyer):
    r = client.post(f"{API}/tasks/", json={"title": "Limitation", "kind": "Limitation", "case_id": OWN_MATTER}, headers=lawyer)
    assert r.status_code == 422


def test_task_completion_shows_on_timeline(client, lawyer):
    t = client.post(f"{API}/tasks/", json={"title": "File vakalat", "case_id": OWN_MATTER, "due_date": str(TODAY)}, headers=lawyer).json()
    assert t["assignee_name"]
    done = client.put(f"{API}/tasks/{t['task_id']}", json={"status": "Done"}, headers=lawyer).json()
    assert done["completed_at"]
    events = client.get(f"{API}/cases/{OWN_MATTER}/timeline", headers=lawyer).json()
    assert any("File vakalat" in e["title"] for e in events)


# ---------------------------------------------------------------- documents (MongoDB)

def upload(client, headers, case_id=OWN_MATTER, name="plaint.pdf", data=b"%PDF-1.4 test", content_type="application/pdf", **fields):
    return client.post(
        f"{API}/evidence/",
        data={"filed_date": str(TODAY), "case_id": case_id, "description": "A filing", **fields},
        files={"file": (name, data, content_type)},
        headers=headers,
    )


def test_upload_download_replace_delete(client, lawyer, admin):
    from app.database import get_mongo_db
    data = b"%PDF-1.4 evidence bytes"
    r = upload(client, lawyer, data=data, category="Pleading", name="Plaint – final (v2).pdf")
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["has_file"] and doc["file_size"] == len(data) and doc["category"] == "Pleading"

    stored = get_mongo_db()["evidence_fs.files"].find_one({"metadata.evidence_id": doc["evidence_id"]})
    assert stored["metadata"]["sha256"] == hashlib.sha256(data).hexdigest()

    r = client.get(f"{API}/evidence/{doc['evidence_id']}/download-file", headers=lawyer)
    assert r.status_code == 200 and r.content == data
    assert "filename*=UTF-8''Plaint%20%E2%80%93" in r.headers["content-disposition"]

    r = client.post(f"{API}/evidence/{doc['evidence_id']}/upload-file", files={"file": ("new.pdf", b"newer", "application/pdf")}, headers=lawyer)
    assert r.status_code == 200 and r.json()["file_name"] == "new.pdf"
    assert get_mongo_db()["evidence_fs.files"].count_documents({"metadata.evidence_id": doc["evidence_id"]}) == 1
    assert client.get(f"{API}/evidence/{doc['evidence_id']}/download-file", headers=lawyer).content == b"newer"

    assert client.delete(f"{API}/evidence/{doc['evidence_id']}", headers=lawyer).status_code == 204
    assert get_mongo_db()["evidence_fs.files"].count_documents({"metadata.evidence_id": doc["evidence_id"]}) == 0
    log = client.get(f"{API}/audit/?case_id={OWN_MATTER}&size=100", headers=admin).json()["items"]
    assert {"file_downloaded", "document_deleted"} <= {e["action"] for e in log}


def test_other_lawyers_cannot_download(client, admin, lawyer):
    doc = upload(client, admin, case_id=THEIR_MATTER).json()
    assert client.get(f"{API}/evidence/{doc['evidence_id']}/download-file", headers=lawyer).status_code == 403
    assert client.get(f"{API}/evidence/{doc['evidence_id']}", headers=lawyer).status_code == 403
    assert client.delete(f"{API}/evidence/{doc['evidence_id']}", headers=lawyer).status_code == 403


def test_rejected_files(client, lawyer):
    assert upload(client, lawyer, name="virus.exe", content_type="application/x-msdownload").status_code == 415
    assert upload(client, lawyer, data=b"").status_code == 400


def test_oversize_file_rejected(client, lawyer, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "MAX_FILE_SIZE", 10)
    r = upload(client, lawyer, data=b"x" * 11)
    assert r.status_code == 413
    # Nothing half-created
    assert not any(d["description"] == "too big" for d in client.get(f"{API}/evidence/?size=100", headers=lawyer).json()["items"])


def test_document_without_file_and_date_rules(client, lawyer):
    r = client.post(f"{API}/evidence/", data={"filed_date": str(TODAY), "case_id": OWN_MATTER, "description": "Physical file"}, headers=lawyer)
    assert r.status_code == 201 and r.json()["has_file"] is False
    r = client.post(f"{API}/evidence/", data={"filed_date": str(TODAY + timedelta(days=1)), "case_id": OWN_MATTER}, headers=lawyer)
    assert r.status_code == 400


def test_deleting_a_matter_removes_its_stored_files(client, admin):
    from app.database import get_mongo_db
    case = new_case(client, admin, "OS 20/2026").json()
    doc = upload(client, admin, case_id=case["case_id"]).json()
    assert client.delete(f"{API}/cases/{case['case_id']}", headers=admin).status_code == 204
    assert get_mongo_db()["evidence_fs.files"].count_documents({"metadata.evidence_id": doc["evidence_id"]}) == 0


# ---------------------------------------------------------------- conflict check

def test_conflict_when_client_is_an_opponent_elsewhere(client, admin):
    party = client.get(f"{API}/opposing-parties/?size=1", headers=admin).json()["items"][0]
    name = f"  {party['fname'].upper()}   {party['lname'].lower()} "
    hits = client.post(f"{API}/conflicts/check", json={"clients": [{"name": name}]}, headers=admin).json()["conflicts"]
    assert hits and hits[0]["kind"] == "client_is_adverse" and hits[0]["matters"]


def test_conflict_when_opponent_is_a_client(client, admin):
    who = client.get(f"{API}/clients/?size=100", headers=admin).json()["items"]
    who = next(c for c in who if c["total_cases"] > 0)
    hits = client.post(f"{API}/conflicts/check", json={"parties": [{"name": f"{who['fname']} {who['lname']}"}]}, headers=admin).json()["conflicts"]
    assert hits and hits[0]["kind"] == "opponent_is_client"


def test_no_conflict_for_a_new_name(client, admin):
    r = client.post(f"{API}/conflicts/check", json={"clients": [{"name": "Nobody Atall"}], "parties": [{"name": "Someone Else"}]}, headers=admin)
    assert r.json()["conflicts"] == []


# ---------------------------------------------------------------- audit log

def test_audit_log_cannot_be_altered_even_with_sql(client, admin):
    from app.database import engine
    client.post(f"{API}/cases/{OWN_MATTER}/notes", json={"body": "Audited"}, headers=admin)
    for statement in ("UPDATE audit_log SET username = 'x'", "DELETE FROM audit_log"):
        with engine.connect() as conn, pytest.raises(Exception, match="append-only"):
            conn.execute(text(statement))


def test_audit_records_who_did_it(client, admin, lawyer):
    client.post(f"{API}/cases/{OWN_MATTER}/notes", json={"body": "By lawyer"}, headers=lawyer)
    rows = client.get(f"{API}/audit/?case_id={OWN_MATTER}&action=note_added", headers=admin).json()["items"]
    assert rows[0]["username"] == "lawyer1"


# ---------------------------------------------------------------- dashboards

def test_workspace_differs_by_role(client, admin, lawyer):
    mine = client.get(f"{API}/workspace/summary", headers=lawyer).json()
    firm = client.get(f"{API}/workspace/summary", headers=admin).json()
    assert mine["counts"]["open_matters"] < firm["counts"]["open_matters"]
    assert "pending_join_requests" not in mine and "pending_join_requests" in firm
    assert {h["case_id"] for h in mine["hearings"]} <= {
        c["case_id"] for c in client.get(f"{API}/cases/?scope=mine&size=100", headers=lawyer).json()["items"]
    }
    assert mine["my_tasks"] and all(t["assignee_name"] for t in mine["my_tasks"])


def test_firm_analytics(client, admin):
    data = client.get(f"{API}/analytics/firm", headers=admin).json()
    assert data["headline"]["active_matters"] > 0
    assert sum(b["count"] for b in data["age_of_open_matters"]) == data["headline"]["active_matters"]
    assert {o["outcome"] for o in data["outcomes"]} >= {"Won", "Settled"}
    assert data["time_to_disposal"] and data["lawyers"] and data["courts"]
    assert any(c["adjourned"] > 0 for c in data["courts"])
    assert len(data["flow"]) == 12


def test_first_admin_setup_status(client):
    assert client.get(f"{API}/auth/setup-status").json() == {"needs_first_admin": False}
