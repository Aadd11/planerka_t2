from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import app
from auth import verify_password
from config import Settings
from constants import UserRole
from models import VerificationToken
from routes_auth import hash_verification_token

from conftest import create_entry, create_period, create_user


def _client() -> TestClient:
    return TestClient(app)


def _json_login(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth_headers(client: TestClient, email: str, password: str = "password123") -> dict[str, str]:
    return {"Authorization": f"Bearer {_json_login(client, email, password)}"}


def _seed_verification_token(db_session, user_id: int, raw_token: str = "verify-token") -> str:
    token = VerificationToken(
        user_id=user_id,
        token=hash_verification_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        consumed=False,
    )
    db_session.add(token)
    db_session.commit()
    return raw_token


def test_health_endpoint_exposes_runtime_headers():
    with _client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"


def test_auth_register_login_verify_and_me_flow(db_session):
    with _client() as client:
        register_response = client.post(
            "/auth/register",
            json={
                "full_name": "Ivan Ivanov",
                "email": "ivan@example.com",
                "password": "password123",
                "alliance": "Retail East",
                "employeeCategory": "adult",
            },
        )
        assert register_response.status_code == 201, register_response.text
        registered = register_response.json()
        assert registered["role"] == "employee"
        assert registered["isVerified"] is False

        duplicate_response = client.post(
            "/auth/register",
            json={
                "full_name": "Ivan Ivanov",
                "email": "ivan@example.com",
                "password": "password123",
                "alliance": "Retail East",
                "employeeCategory": "adult",
            },
        )
        assert duplicate_response.status_code == 400

        user = create_user(
            db_session,
            email="verified@example.com",
            full_name="Verified User",
            alliance="Retail East",
            verified=False,
        )
        raw_token = _seed_verification_token(db_session, user.id, "known-token")

        invalid_verify = client.post("/auth/verify", json={"token": "bad-token"})
        assert invalid_verify.status_code == 400

        verify_response = client.post("/auth/verify", json={"token": raw_token})
        assert verify_response.status_code == 200, verify_response.text
        assert verify_response.json()["isVerified"] is True

        login_response = client.post(
            "/auth/login",
            data={"username": "verified@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200, login_response.text
        access_token = login_response.json()["access_token"]

        me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me_response.status_code == 200, me_response.text
        assert me_response.json()["email"] == "verified@example.com"

    created = db_session.query(VerificationToken).filter(VerificationToken.user_id == registered["id"]).first()
    assert created is not None
    assert len(created.token) == 64
    assert verify_password("password123", db_session.get(type(user), user.id).password_hash)


def test_auth_login_rejects_invalid_credentials(db_session):
    create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )

    with _client() as client:
        response = client.post("/auth/login", json={"email": "employee@example.com", "password": "wrongpass"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Некорректный email или пароль"


def test_periods_endpoints_cover_current_create_close_stats_submissions_history(db_session):
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    employee1 = create_user(
        db_session,
        email="employee1@example.com",
        full_name="Employee One",
        alliance="Retail East",
    )
    employee2 = create_user(
        db_session,
        email="employee2@example.com",
        full_name="Employee Two",
        alliance="Retail East",
    )

    with _client() as client:
        manager_headers = _auth_headers(client, manager.email)

        create_response = client.post(
            "/periods",
            json={
                "name": "May 2026",
                "periodStart": "2026-05-04",
                "periodEnd": "2026-05-10",
                "deadline": "2026-04-30T18:00:00Z",
            },
            headers=manager_headers,
        )
        assert create_response.status_code == 201, create_response.text
        period = create_response.json()
        assert period["alliance"] == "Retail East"
        assert period["holidays"]["2026-05-09"] == "День Победы"

        current_response = client.get("/periods/current", headers=_auth_headers(client, employee1.email))
        assert current_response.status_code == 200
        assert current_response.json()["id"] == period["id"]

        draft_schedule = {
            "employeeComment": "Ready for review",
            "days": {
                "2026-05-04": {"dayType": "work", "segments": [{"start": "09:00", "end": "17:00"}]},
                "2026-05-05": {"dayType": "day_off", "segments": []},
                "2026-05-06": {"dayType": "day_off", "segments": []},
            },
        }
        save_response = client.put("/schedules/me", json=draft_schedule, headers=_auth_headers(client, employee1.email))
        assert save_response.status_code == 200, save_response.text

        submit_response = client.post("/schedules/me/submit", headers=_auth_headers(client, employee1.email))
        assert submit_response.status_code == 200, submit_response.text
        assert submit_response.json()["submission"]["status"] == "submitted"

        stats_response = client.get("/periods/current/stats", headers=manager_headers)
        assert stats_response.status_code == 200
        assert stats_response.json() == {"totalEmployees": 2, "submittedCount": 1, "pendingCount": 1}

        submissions_response = client.get("/periods/current/submissions", headers=manager_headers)
        assert submissions_response.status_code == 200
        body = submissions_response.json()
        assert len(body["submitted"]) == 1
        assert body["submitted"][0]["email"] == employee1.email
        assert len(body["pending"]) == 1
        assert body["pending"][0]["email"] == employee2.email

        history_response = client.get("/periods/history", headers=manager_headers)
        assert history_response.status_code == 200
        assert history_response.json()[0]["id"] == period["id"]

        close_response = client.post(f"/periods/{period['id']}/close", headers=manager_headers)
        assert close_response.status_code == 200
        assert close_response.json()["isOpen"] is False


def test_periods_current_returns_null_without_group_period(db_session):
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )

    with _client() as client:
        response = client.get("/periods/current", headers=_auth_headers(client, employee.email))

    assert response.status_code == 200
    assert response.json() is None


def test_schedule_endpoints_cover_read_update_validate_submit_and_manager_view(db_session):
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )
    outsider = create_user(
        db_session,
        email="outsider@example.com",
        full_name="Outsider",
        alliance="Retail West",
    )
    period = create_period(db_session)
    create_period(db_session, alliance="Retail West")

    with _client() as client:
        employee_headers = _auth_headers(client, employee.email)
        manager_headers = _auth_headers(client, manager.email)

        my_schedule = client.get("/schedules/me", headers=employee_headers)
        assert my_schedule.status_code == 200, my_schedule.text
        assert my_schedule.json()["submission"]["status"] == "draft"

        invalid_validate = client.post(
            "/schedules/validate",
            json={
                "periodId": period.id,
                "days": {
                    "2026-05-04": {
                        "dayType": "work",
                        "segments": [
                            {"start": "09:00", "end": "12:00"},
                            {"start": "11:00", "end": "13:00"},
                        ],
                    }
                },
            },
            headers=employee_headers,
        )
        assert invalid_validate.status_code == 200
        issue_codes = {issue["code"] for issue in invalid_validate.json()["issues"]}
        assert "SEGMENTS_OVERLAP" in issue_codes

        update_response = client.put(
            "/schedules/me",
            json={
                "employeeComment": "Can work mornings",
                "days": {
                    "2026-05-01": {"dayType": "day_off", "segments": []},
                    "2026-05-02": {"dayType": "day_off", "segments": []},
                    "2026-05-03": {"dayType": "day_off", "segments": []},
                    "2026-05-04": {"dayType": "work", "segments": [{"start": "09:00", "end": "13:00"}]},
                    "2026-05-05": {"dayType": "day_off", "segments": []},
                    "2026-05-06": {"dayType": "day_off", "segments": []},
                    "2026-05-11": {"dayType": "day_off", "segments": []},
                    "2026-05-12": {"dayType": "day_off", "segments": []},
                },
            },
            headers=employee_headers,
        )
        assert update_response.status_code == 200, update_response.text
        assert update_response.json()["entries"]["2026-05-04"]["dayType"] == "work"

        submit_response = client.post("/schedules/me/submit", headers=employee_headers)
        assert submit_response.status_code == 200, submit_response.text
        assert submit_response.json()["submission"]["status"] == "submitted"

        manager_view = client.get(f"/schedules/by-user/{employee.id}", headers=manager_headers)
        assert manager_view.status_code == 200, manager_view.text
        assert manager_view.json()["user"]["email"] == employee.email

        forbidden = client.get(f"/schedules/by-user/{outsider.id}", headers=manager_headers)
        assert forbidden.status_code == 403


def test_schedule_submit_blocks_invalid_schedule(db_session):
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )
    create_period(db_session)

    with _client() as client:
        employee_headers = _auth_headers(client, employee.email)
        client.put(
            "/schedules/me",
            json={"days": {"2026-05-04": {"dayType": "work", "segments": []}}},
            headers=employee_headers,
        )
        response = client.post("/schedules/me/submit", headers=employee_headers)

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "График не отправлен: есть ошибки валидации."


def test_manager_endpoints_cover_matrix_comments_and_coverage(db_session):
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )
    period = create_period(db_session)
    create_entry(
        db_session,
        user_id=employee.id,
        period_id=period.id,
        day="2026-05-04",
        status="work",
        meta={"dayType": "work", "segments": [{"start": "09:00", "end": "11:00"}]},
    )

    with _client() as client:
        manager_headers = _auth_headers(client, manager.email)

        matrix_response = client.get("/manager/schedules", headers=manager_headers)
        assert matrix_response.status_code == 200, matrix_response.text
        assert matrix_response.json()["items"][0]["user"]["email"] == employee.email

        day_comment_response = client.post(
            "/manager/comments",
            json={"userId": employee.id, "periodId": period.id, "date": "2026-05-04", "comment": "Cover lunch peak"},
            headers=manager_headers,
        )
        assert day_comment_response.status_code == 201, day_comment_response.text
        assert day_comment_response.json()["dayComments"]["2026-05-04"] == "Cover lunch peak"

        schedule_comment_response = client.post(
            "/manager/comments",
            json={"userId": employee.id, "periodId": period.id, "comment": "Looks good overall"},
            headers=manager_headers,
        )
        assert schedule_comment_response.status_code == 201, schedule_comment_response.text
        assert schedule_comment_response.json()["scheduleComment"] == "Looks good overall"

        comments_response = client.get(
            f"/manager/comments?user_id={employee.id}&period_id={period.id}",
            headers=manager_headers,
        )
        assert comments_response.status_code == 200
        assert comments_response.json()["scheduleComment"] == "Looks good overall"

        coverage_response = client.get(
            f"/manager/coverage?day=2026-05-04&period_id={period.id}",
            headers=manager_headers,
        )
        assert coverage_response.status_code == 200, coverage_response.text
        buckets = {item["hour"]: item for item in coverage_response.json()["buckets"]}
        assert buckets["09:00"]["count"] == 1
        assert employee.full_name in buckets["10:00"]["users"]


def test_admin_endpoints_cover_list_verify_role_alliance_and_delete(db_session):
    admin = create_user(
        db_session,
        email="admin@example.com",
        full_name="Admin",
        alliance="Retail East",
        role=UserRole.ADMIN.value,
    )
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    pending_user = create_user(
        db_session,
        email="pending@example.com",
        full_name="Pending User",
        alliance="Retail East",
        verified=False,
    )

    with _client() as client:
        admin_headers = _auth_headers(client, admin.email)
        manager_headers = _auth_headers(client, manager.email)

        list_response = client.get("/admin/users?verified=false", headers=admin_headers)
        assert list_response.status_code == 200, list_response.text
        assert [item["email"] for item in list_response.json()] == [pending_user.email]

        manager_list_response = client.get("/admin/users", headers=manager_headers)
        assert manager_list_response.status_code == 200
        assert all(item["alliance"] == "Retail East" for item in manager_list_response.json())

        verify_response = client.put(f"/admin/users/{pending_user.id}/verify", headers=admin_headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["isVerified"] is True

        role_response = client.put(
            f"/admin/users/{pending_user.id}/role",
            json={"role": "manager"},
            headers=admin_headers,
        )
        assert role_response.status_code == 200
        assert role_response.json()["role"] == "manager"

        alliance_response = client.put(
            f"/admin/users/{pending_user.id}/alliance",
            json={"alliance": "Retail West"},
            headers=admin_headers,
        )
        assert alliance_response.status_code == 200
        assert alliance_response.json()["alliance"] == "Retail West"

        delete_response = client.delete(f"/admin/users/{pending_user.id}", headers=admin_headers)
        assert delete_response.status_code == 204

        not_found_response = client.put(f"/admin/users/{pending_user.id}/verify", headers=admin_headers)
        assert not_found_response.status_code == 404


def test_export_schedule_endpoint_returns_xlsx(db_session):
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )
    period = create_period(db_session)
    create_entry(
        db_session,
        user_id=employee.id,
        period_id=period.id,
        day="2026-05-02",
        status="work",
        meta={"dayType": "work", "segments": [{"start": "09:00", "end": "18:00"}]},
    )

    with _client() as client:
        response = client.get(f"/export/schedule?period_id={period.id}", headers=_auth_headers(client, manager.email))

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert response.content.startswith(b"PK")


def test_template_endpoints_cover_list_create_and_delete(db_session):
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )

    with _client() as client:
        headers = _auth_headers(client, employee.email)

        empty_response = client.get("/templates", headers=headers)
        assert empty_response.status_code == 200
        assert empty_response.json() == []

        create_response = client.post(
            "/templates",
            json={
                "name": "2/2 Day Shift",
                "workDays": 2,
                "restDays": 2,
                "shiftStart": "09:00",
                "shiftEnd": "18:00",
                "hasBreak": True,
                "breakStart": "13:00",
                "breakEnd": "14:00",
            },
            headers=headers,
        )
        assert create_response.status_code == 201, create_response.text
        template_id = create_response.json()["id"]

        list_response = client.get("/templates", headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()[0]["id"] == template_id

        delete_response = client.delete(f"/templates/{template_id}", headers=headers)
        assert delete_response.status_code == 204

        missing_response = client.delete(f"/templates/{template_id}", headers=headers)
        assert missing_response.status_code == 404


def test_settings_require_strong_jwt_secret_in_production():
    settings = Settings(
        DATABASE_URL="sqlite:////tmp/t2_security_test.db",
        JWT_SECRET_KEY="CHANGE_ME_SECRET",
        APP_ENV="production",
        CORS_ORIGINS="http://localhost:8000",
    )
    try:
        settings.validate_security()
        raise AssertionError("Expected validate_security to reject weak secret")
    except ValueError:
        pass
