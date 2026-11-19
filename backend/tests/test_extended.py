"""Extended automated tests: negative, boundary, security and regression cases.
Each test name is listed against its test case ID in the 'FareShare Test Cases' sheet.
Run from the backend folder:   python -m pytest -v"""
import datetime as dt

import pytest
from jose import jwt

from app.models import Trip, TripRequest, User
from test_api import PW, add_car, future, post_trip, register, setup_trip

M = "m@khi.iba.edu.pk"


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def trip_body(vehicle_id=None, **over):
    body = {"origin_area": "Clifton", "destination_area": "IBA City Campus", "departure_time": future(24),
            "seats": 3, "cost_per_person": 250, "gender_filter": "any", "ride_type": "own_car",
            "vehicle_id": vehicle_id}
    body.update(over)
    return body


def rider_with_request(client, tid, email="r@khi.iba.edu.pk", gender="female", phone="0300 9999999"):
    r = register(client, "Rider", email, gender, phone)
    rid = client.post(f"/trips/{tid}/requests", json={}, headers=r).json()["request_id"]
    return r, rid


def accepted_rider(client, m, tid, email="r@khi.iba.edu.pk", **kw):
    r, rid = rider_with_request(client, tid, email, **kw)
    assert client.post(f"/requests/{rid}/accept", headers=m).status_code == 200
    return r, rid


def user_id(client, h):
    return client.get("/me", headers=h).json()["user_id"]


# ======================= AUTHENTICATION =======================
@pytest.mark.parametrize("missing", ["full_name", "email", "password", "gender"])
def test_register_missing_required_field(client, missing):
    body = {"full_name": "A", "email": "a@khi.iba.edu.pk", "password": PW, "gender": "male"}
    body.pop(missing)
    assert client.post("/auth/register", json=body).status_code == 422


def test_register_blank_name_rejected(client):
    r = client.post("/auth/register", json={"full_name": "   ", "email": "a@khi.iba.edu.pk", "password": PW, "gender": "male"})
    assert r.status_code == 422


def test_register_email_is_trimmed_and_lowercased(client):
    r = client.post("/auth/register", json={"full_name": "A", "email": "  Ab.C@KHI.IBA.EDU.PK ", "password": PW, "gender": "male"})
    assert r.status_code == 201 and r.json()["user"]["email"] == "ab.c@khi.iba.edu.pk"


@pytest.mark.parametrize("email", ["a@khi.iba.edu.pk.com", "a@iba.edu.pk", "a@evil-khi.iba.edu.pk",
                                   "a@gmail.com", "plainstring", "a@", "@khi.iba.edu.pk x"])
def test_register_lookalike_and_malformed_emails_rejected(client, email):
    r = client.post("/auth/register", json={"full_name": "A", "email": email, "password": PW, "gender": "male"})
    assert r.status_code == 422


@pytest.mark.parametrize("pw,ok", [("abcdefg1", True), ("abcdef1", False), ("abcdefgh", False), ("12345678", True), ("", False)])
def test_register_password_boundaries(client, pw, ok):
    r = client.post("/auth/register", json={"full_name": "A", "email": "a@khi.iba.edu.pk", "password": pw, "gender": "male"})
    assert (r.status_code == 201) is ok


@pytest.mark.parametrize("gender,code", [("Female", 201), ("MALE", 201), ("other", 422), ("", 422)])
def test_register_gender_values(client, gender, code):
    r = client.post("/auth/register", json={"full_name": "A", "email": "a@khi.iba.edu.pk", "password": PW, "gender": gender})
    assert r.status_code == code


def test_register_phone_is_optional(client):
    r = client.post("/auth/register", json={"full_name": "A", "email": "a@khi.iba.edu.pk", "password": PW, "gender": "male"})
    assert r.status_code == 201 and r.json()["user"]["phone"] is None


def test_register_duplicate_email_ignores_case(client):
    register(client, "A", "dup@khi.iba.edu.pk")
    r = client.post("/auth/register", json={"full_name": "B", "email": "DUP@khi.iba.edu.pk", "password": PW, "gender": "male"})
    assert r.status_code == 409


def test_login_wrong_password_and_unknown_email_give_same_message(client):
    register(client, "A", "a@khi.iba.edu.pk")
    wrong = client.post("/auth/login", json={"email": "a@khi.iba.edu.pk", "password": "nope12345"})
    unknown = client.post("/auth/login", json={"email": "zzz@khi.iba.edu.pk", "password": PW})
    assert wrong.status_code == unknown.status_code == 401 and wrong.json() == unknown.json()


def test_login_email_is_case_insensitive_and_hash_never_returned(client):
    register(client, "A", "a@khi.iba.edu.pk")
    r = client.post("/auth/login", json={"email": " A@KHI.IBA.EDU.PK", "password": PW})
    assert r.status_code == 200 and "password_hash" not in r.text and "token" in r.json()


def test_protected_endpoints_need_a_token(client):
    for method, url in [("get", "/me"), ("put", "/me"), ("get", "/vehicles"), ("post", "/vehicles"), ("get", "/trips"),
                        ("post", "/trips"), ("get", "/trips/mine"), ("get", "/trips/1"), ("post", "/trips/1/cancel"),
                        ("post", "/trips/1/confirm"), ("post", "/trips/1/complete"), ("get", "/trips/1/riders"),
                        ("post", "/trips/1/requests"), ("get", "/requests/sent"), ("get", "/requests/received"),
                        ("post", "/requests/1/accept"), ("post", "/requests/1/decline"), ("post", "/requests/1/cancel"),
                        ("post", "/requests/1/leave"), ("post", "/requests/1/confirm-travel"),
                        ("post", "/auth/change-password")]:
        assert getattr(client, method)(url).status_code == 401, (method, url)


def test_garbage_tampered_and_expired_tokens_rejected(client):
    h = register(client, "A", "a@khi.iba.edu.pk")
    assert client.get("/me", headers=bearer("not-a-token")).status_code == 401
    good = h["Authorization"].split()[1]
    assert client.get("/me", headers=bearer(good[:-3] + "abc")).status_code == 401
    expired = jwt.encode({"sub": "1", "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)}, "test-secret", algorithm="HS256")
    assert client.get("/me", headers=bearer(expired)).status_code == 401
    wrong_key = jwt.encode({"sub": "1", "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)}, "other-secret", algorithm="HS256")
    assert client.get("/me", headers=bearer(wrong_key)).status_code == 401


def test_token_of_a_user_that_no_longer_exists_rejected(client):
    ghost = jwt.encode({"sub": "9999", "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)}, "test-secret", algorithm="HS256")
    assert client.get("/me", headers=bearer(ghost)).status_code == 401


def test_sql_injection_text_in_login_is_just_a_failed_login(client):
    r = client.post("/auth/login", json={"email": "' OR 1=1 --@khi.iba.edu.pk", "password": "x' OR '1'='1"})
    assert r.status_code == 401


# ======================= PROFILE =======================
def test_profile_update_name_and_phone_and_clear_phone(client):
    h = register(client, "Old", "a@khi.iba.edu.pk", phone="0300 1")
    r = client.put("/me", json={"full_name": "  New Name ", "phone": "0322 2"}, headers=h)
    assert r.json()["full_name"] == "New Name" and r.json()["phone"] == "0322 2"
    assert client.put("/me", json={"phone": "  "}, headers=h).json()["phone"] is None


def test_profile_empty_name_rejected(client):
    h = register(client, "Old", "a@khi.iba.edu.pk")
    assert client.put("/me", json={"full_name": "  "}, headers=h).status_code == 422


def test_profile_email_and_gender_cannot_be_changed(client):
    h = register(client, "Old", "a@khi.iba.edu.pk", "female")
    r = client.put("/me", json={"email": "x@khi.iba.edu.pk", "gender": "male", "completed_trips_count": 99}, headers=h)
    assert r.status_code == 200 and r.json()["email"] == "a@khi.iba.edu.pk"
    assert r.json()["gender"] == "female" and r.json()["completed_trips_count"] == 0


def test_change_password_rules(client):
    h = register(client, "A", "a@khi.iba.edu.pk")
    assert client.post("/auth/change-password", json={"current_password": "wrong1234", "new_password": "newpass99"}, headers=h).status_code == 400
    assert client.post("/auth/change-password", json={"current_password": PW, "new_password": PW}, headers=h).status_code == 422
    assert client.post("/auth/change-password", json={"current_password": PW, "new_password": "short1"}, headers=h).status_code == 422
    assert client.post("/auth/change-password", json={"current_password": PW, "new_password": "nodigitshere"}, headers=h).status_code == 422
    assert client.post("/auth/change-password", json={"current_password": PW, "new_password": "newpass99"}, headers=h).status_code == 200
    assert client.post("/auth/login", json={"email": "a@khi.iba.edu.pk", "password": PW}).status_code == 401
    assert client.post("/auth/login", json={"email": "a@khi.iba.edu.pk", "password": "newpass99"}).status_code == 200


# ======================= VEHICLES =======================
def vehicle_body(**over):
    b = {"make": "Honda", "model": "City", "color": "White", "plate_number": " kpl-1234 ", "total_seats": 3}
    b.update(over)
    return b


@pytest.mark.parametrize("seats,code", [(0, 422), (1, 201), (4, 201), (5, 422), (-1, 422)])
def test_vehicle_seat_boundaries(client, seats, code):
    h = register(client, "A", "a@khi.iba.edu.pk")
    assert client.post("/vehicles", json=vehicle_body(total_seats=seats), headers=h).status_code == code


@pytest.mark.parametrize("field", ["make", "model", "color", "plate_number"])
def test_vehicle_blank_fields_rejected(client, field):
    h = register(client, "A", "a@khi.iba.edu.pk")
    assert client.post("/vehicles", json=vehicle_body(**{field: "  "}), headers=h).status_code == 422


def test_vehicle_plate_is_trimmed_and_uppercased(client):
    h = register(client, "A", "a@khi.iba.edu.pk")
    assert client.post("/vehicles", json=vehicle_body(), headers=h).json()["plate_number"] == "KPL-1234"


def test_vehicles_are_private_to_their_owner(client):
    a = register(client, "A", "a@khi.iba.edu.pk")
    b = register(client, "B", "b@khi.iba.edu.pk")
    vid = client.post("/vehicles", json=vehicle_body(), headers=a).json()["vehicle_id"]
    assert client.get("/vehicles", headers=b).json() == []
    assert client.put(f"/vehicles/{vid}", json=vehicle_body(), headers=b).status_code == 404
    assert client.delete(f"/vehicles/{vid}", headers=b).status_code == 404
    assert client.put("/vehicles/9999", json=vehicle_body(), headers=a).status_code == 404


def test_vehicle_edit_saves_changes(client):
    a = register(client, "A", "a@khi.iba.edu.pk")
    vid = client.post("/vehicles", json=vehicle_body(), headers=a).json()["vehicle_id"]
    r = client.put(f"/vehicles/{vid}", json=vehicle_body(color="Black", total_seats=2), headers=a)
    assert r.status_code == 200 and r.json()["color"] == "Black" and r.json()["total_seats"] == 2


def test_vehicle_with_cancelled_trip_history_cannot_be_deleted(client):
    m, tid = setup_trip(client)
    vid = client.get("/vehicles", headers=m).json()[0]["vehicle_id"]
    client.post(f"/trips/{tid}/cancel", headers=m)
    r = client.delete(f"/vehicles/{vid}", headers=m)
    assert r.status_code == 409 and "history" in r.json()["detail"]


# ======================= POST TRIP =======================
@pytest.mark.parametrize("seats,code", [(0, 422), (1, 201), (3, 201), (4, 201), (5, 422)])
def test_post_trip_seat_boundaries(client, seats, code):
    h = register(client, "A", "a@khi.iba.edu.pk")
    v = add_car(client, h, seats=4)
    assert client.post("/trips", json=trip_body(v, seats=seats), headers=h).status_code == code


def test_post_trip_seats_cannot_exceed_vehicle_seats(client):
    h = register(client, "A", "a@khi.iba.edu.pk")
    v = add_car(client, h, seats=2)
    assert client.post("/trips", json=trip_body(v, seats=3), headers=h).status_code == 422


def test_post_trip_cost_rules(client):
    h = register(client, "A", "a@khi.iba.edu.pk")
    v = add_car(client, h)
    assert client.post("/trips", json=trip_body(v, cost_per_person=-1), headers=h).status_code == 422
    free = client.post("/trips", json=trip_body(v, cost_per_person=0), headers=h)
    assert free.status_code == 201 and free.json()["cost_per_person"] == 0


def test_post_trip_departure_must_be_in_the_future(client):
    h = register(client, "A", "a@khi.iba.edu.pk")
    v = add_car(client, h)
    past = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)).isoformat()
    assert client.post("/trips", json=trip_body(v, departure_time=past), headers=h).status_code == 422
    soon = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)).isoformat()
    assert client.post("/trips", json=trip_body(v, departure_time=soon), headers=h).status_code == 201


def test_post_trip_campus_rules(client):
    h = register(client, "A", "a@khi.iba.edu.pk")
    v = add_car(client, h)
    assert client.post("/trips", json=trip_body(v, origin_area="DHA", destination_area="Clifton"), headers=h).status_code == 422
    assert client.post("/trips", json=trip_body(v, destination_area="IBA"), headers=h).status_code == 422      # not an exact campus name
    assert client.post("/trips", json=trip_body(v, origin_area=" ", destination_area="IBA City Campus"), headers=h).status_code == 422
    ok = client.post("/trips", json=trip_body(v, origin_area="IBA Main Campus", destination_area="Gulshan"), headers=h)
    assert ok.status_code == 201                                                                                # campus can be the origin


def test_post_trip_gender_filter_rules(client):
    f = register(client, "F", "f@khi.iba.edu.pk", "female")
    vf = add_car(client, f)
    m = register(client, "M", "m2@khi.iba.edu.pk", "male")
    vm = add_car(client, m)
    assert client.post("/trips", json=trip_body(vf, gender_filter="female"), headers=f).status_code == 201
    assert client.post("/trips", json=trip_body(vf, gender_filter="male"), headers=f).status_code == 422
    assert client.post("/trips", json=trip_body(vm, gender_filter="female"), headers=m).status_code == 422
    assert client.post("/trips", json=trip_body(vm, gender_filter="male"), headers=m).status_code == 201
    assert client.post("/trips", json=trip_body(vm, gender_filter="everyone"), headers=m).status_code == 422


def test_post_trip_ride_type_rules(client):
    a = register(client, "A", "a@khi.iba.edu.pk")
    b = register(client, "B", "b@khi.iba.edu.pk")
    vb = add_car(client, b)
    assert client.post("/trips", json=trip_body(None), headers=a).status_code == 422                       # own car needs a vehicle
    assert client.post("/trips", json=trip_body(vb), headers=a).status_code == 404                         # someone else's car
    assert client.post("/trips", json=trip_body(None, ride_type="taxi"), headers=a).status_code == 422
    ind = client.post("/trips", json=trip_body(None, ride_type="indrive_group"), headers=a)
    assert ind.status_code == 201 and ind.json()["ride_type"] == "indrive_group" and ind.json()["vehicle"] is None


def test_posted_trip_exposes_no_private_data(client):
    h = register(client, "A", "a@khi.iba.edu.pk", phone="0300 1")
    v = add_car(client, h)
    t = client.post("/trips", json=trip_body(v), headers=h).json()
    assert t["status"] == "open" and t["manager"].keys() == {"user_id", "full_name", "gender", "completed_trips_count"}
    assert "0300 1" not in str(t) and "a@khi.iba.edu.pk" not in str(t)


# ======================= BROWSE / SEARCH =======================
def set_trip(db_session, tid, **fields):
    t = db_session.get(Trip, tid)
    for k, v in fields.items():
        setattr(t, k, v)
    db_session.commit()


def test_browse_hides_own_full_past_and_non_open_trips(client, db_session):
    m = register(client, "M", M)
    v = add_car(client, m)
    open_id = post_trip(client, m, v, origin="Open")
    full_id = post_trip(client, m, v, origin="Full")
    past_id = post_trip(client, m, v, origin="Past")
    conf_id = post_trip(client, m, v, origin="Conf")
    canc_id = post_trip(client, m, v, origin="Canc")
    set_trip(db_session, full_id, available_seats=0)
    set_trip(db_session, past_id, departure_time=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1))
    set_trip(db_session, conf_id, status="confirmed")
    set_trip(db_session, canc_id, status="cancelled")
    other = register(client, "O", "o@khi.iba.edu.pk")
    ids = [t["trip_id"] for t in client.get("/trips", headers=other).json()]
    assert ids == [open_id]
    assert client.get("/trips", headers=m).json() == []        # the manager does not see their own trips in Browse


def test_browse_origin_filter_partial_and_case_insensitive(client):
    m = register(client, "M", M)
    v = add_car(client, m)
    post_trip(client, m, v, origin="Clifton Block 5")
    post_trip(client, m, v, origin="Gulshan-e-Iqbal")
    o = register(client, "O", "o@khi.iba.edu.pk")
    assert len(client.get("/trips", params={"origin": "clif"}, headers=o).json()) == 1
    assert len(client.get("/trips", params={"origin": "GULSHAN"}, headers=o).json()) == 1
    assert client.get("/trips", params={"origin": "Nowhere"}, headers=o).json() == []
    assert len(client.get("/trips", params={"origin": "   "}, headers=o).json()) == 2


def test_browse_campus_filter_is_exact(client):
    m = register(client, "M", M)
    v = add_car(client, m)
    post_trip(client, m, v, campus="IBA City Campus")
    post_trip(client, m, v, campus="IBA Main Campus")
    o = register(client, "O", "o@khi.iba.edu.pk")
    r = client.get("/trips", params={"campus": "IBA Main Campus"}, headers=o).json()
    assert len(r) == 1 and r[0]["destination_area"] == "IBA Main Campus"


def test_browse_date_and_gender_filters_and_bad_date(client):
    f = register(client, "F", "f@khi.iba.edu.pk", "female")
    v = add_car(client, f)
    post_trip(client, f, v, gender="female", hours=24)
    post_trip(client, f, v, gender="any", hours=72)
    o = register(client, "O", "o@khi.iba.edu.pk", "female")
    day = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=72)).date().isoformat()
    assert len(client.get("/trips", params={"date": day}, headers=o).json()) == 1
    assert len(client.get("/trips", params={"gender": "female"}, headers=o).json()) == 1
    assert len(client.get("/trips", params={"gender": "any"}, headers=o).json()) == 1
    assert client.get("/trips", params={"date": "31-12-2026"}, headers=o).status_code == 422


def test_browse_is_sorted_by_departure_time(client):
    m = register(client, "M", M)
    v = add_car(client, m)
    late = post_trip(client, m, v, hours=48)
    early = post_trip(client, m, v, hours=2)
    mid = post_trip(client, m, v, hours=10)
    o = register(client, "O", "o@khi.iba.edu.pk")
    assert [t["trip_id"] for t in client.get("/trips", headers=o).json()] == [early, mid, late]


def test_browse_special_characters_in_search_do_not_break(client):
    m, _ = setup_trip(client)
    o = register(client, "O", "o@khi.iba.edu.pk")
    for text in ["'; DROP TABLE trips;--", "%", "_", "<script>alert(1)</script>", "Ünïcode ✓"]:
        assert client.get("/trips", params={"origin": text}, headers=o).status_code == 200
    assert client.get("/trips", headers=o).status_code == 200


def test_browse_men_cannot_see_women_only_trips_and_vice_versa(client):
    f = register(client, "F", "f@khi.iba.edu.pk", "female")
    v = add_car(client, f)
    post_trip(client, f, v, gender="female")
    male = register(client, "Ma", "ma@khi.iba.edu.pk", "male")
    female = register(client, "Fe", "fe@khi.iba.edu.pk", "female")
    assert client.get("/trips", headers=male).json() == []
    assert len(client.get("/trips", headers=female).json()) == 1


# ======================= TRIP DETAILS =======================
def test_trip_details_content_and_404(client):
    m, tid = setup_trip(client)
    o = register(client, "O", "o@khi.iba.edu.pk")
    d = client.get(f"/trips/{tid}", headers=o).json()
    assert d["ride_type"] == "own_car" and d["vehicle"]["plate_number"] == "KPL-1234" and d["my_request"] is None
    assert d["manager"]["full_name"] == "Manager" and "phone" not in d["manager"]
    assert client.get("/trips/99999", headers=o).status_code == 404


def test_trip_details_show_my_request_after_requesting(client):
    m, tid = setup_trip(client)
    r, rid = rider_with_request(client, tid)
    assert client.get(f"/trips/{tid}", headers=r).json()["my_request"]["status"] == "pending"


# ======================= EDIT / CANCEL TRIP =======================
def test_edit_trip_permissions_and_state_rules(client):
    m, tid = setup_trip(client)
    vid = client.get("/vehicles", headers=m).json()[0]["vehicle_id"]
    o = register(client, "O", "o@khi.iba.edu.pk")
    assert client.put(f"/trips/{tid}", json=trip_body(vid), headers=o).status_code == 403
    client.post(f"/trips/{tid}/cancel", headers=m)
    assert client.put(f"/trips/{tid}", json=trip_body(vid), headers=m).status_code == 409


def test_edit_trip_validation_is_reused(client):
    m, tid = setup_trip(client)
    vid = client.get("/vehicles", headers=m).json()[0]["vehicle_id"]
    assert client.put(f"/trips/{tid}", json=trip_body(vid, seats=9), headers=m).status_code == 422
    assert client.put(f"/trips/{tid}", json=trip_body(vid, cost_per_person=-5), headers=m).status_code == 422


def test_edit_trip_seats_account_for_accepted_riders(client):
    m, tid = setup_trip(client, seats=3)
    vid = client.get("/vehicles", headers=m).json()[0]["vehicle_id"]
    accepted_rider(client, m, tid, "r1@khi.iba.edu.pk")
    accepted_rider(client, m, tid, "r2@khi.iba.edu.pk")
    assert client.put(f"/trips/{tid}", json=trip_body(vid, seats=1), headers=m).status_code == 409
    ok = client.put(f"/trips/{tid}", json=trip_body(vid, seats=4), headers=m)
    assert ok.status_code == 200 and ok.json()["available_seats"] == 2          # 4 seats - 2 already accepted


def test_edit_trip_vehicle_locked_once_a_rider_is_accepted(client):
    m, tid = setup_trip(client)
    vid2 = client.post("/vehicles", json=vehicle_body(plate_number="ABC-1"), headers=m).json()["vehicle_id"]
    accepted_rider(client, m, tid)
    assert client.put(f"/trips/{tid}", json=trip_body(vid2), headers=m).status_code == 409
    assert client.put(f"/trips/{tid}", json=trip_body(None, ride_type="indrive_group"), headers=m).status_code == 409


def test_edit_trip_changes_are_saved(client):
    m, tid = setup_trip(client)
    vid = client.get("/vehicles", headers=m).json()[0]["vehicle_id"]
    r = client.put(f"/trips/{tid}", json=trip_body(vid, origin_area="DHA", cost_per_person=400), headers=m).json()
    assert r["origin_area"] == "DHA" and r["cost_per_person"] == 400
    assert client.get(f"/trips/{tid}", headers=m).json()["origin_area"] == "DHA"


def test_cancel_trip_rules(client):
    m, tid = setup_trip(client)
    o = register(client, "O", "o@khi.iba.edu.pk")
    assert client.post(f"/trips/{tid}/cancel", headers=o).status_code == 403
    assert client.post(f"/trips/{tid}/cancel", headers=m).status_code == 200
    assert client.post(f"/trips/{tid}/cancel", headers=m).status_code == 409     # already cancelled
    assert client.post("/trips/99999/cancel", headers=m).status_code == 404


def test_cancelling_a_trip_frees_pending_and_accepted_riders(client):
    m, tid = setup_trip(client)
    r1, _ = accepted_rider(client, m, tid, "r1@khi.iba.edu.pk")
    r2, _ = rider_with_request(client, tid, "r2@khi.iba.edu.pk")
    client.post(f"/trips/{tid}/cancel", headers=m)
    for r in (r1, r2):
        assert client.get("/requests/sent", headers=r).json()[0]["status"] == "cancelled"
    m2 = register(client, "M2", "m3@khi.iba.edu.pk")
    t2 = post_trip(client, m2, add_car(client, m2))
    assert client.post(f"/trips/{t2}/requests", json={}, headers=r1).status_code == 201    # no longer busy


# ======================= SEND REQUEST =======================
def test_request_message_length_limit(client):
    m, tid = setup_trip(client)
    r = register(client, "R", "r@khi.iba.edu.pk")
    assert client.post(f"/trips/{tid}/requests", json={"message": "x" * 301}, headers=r).status_code == 422
    ok = client.post(f"/trips/{tid}/requests", json={"message": "x" * 300}, headers=r)
    assert ok.status_code == 201


def test_request_with_blank_message_stores_none(client):
    m, tid = setup_trip(client)
    r = register(client, "R", "r@khi.iba.edu.pk")
    assert client.post(f"/trips/{tid}/requests", json={"message": "   "}, headers=r).json()["message"] is None


def test_request_to_unavailable_trips_is_blocked(client, db_session):
    m, tid = setup_trip(client)
    r = register(client, "R", "r@khi.iba.edu.pk")
    assert client.post("/trips/99999/requests", json={}, headers=r).status_code == 404
    set_trip(db_session, tid, status="cancelled")
    assert client.post(f"/trips/{tid}/requests", json={}, headers=r).status_code == 409
    set_trip(db_session, tid, status="confirmed")
    assert client.post(f"/trips/{tid}/requests", json={}, headers=r).status_code == 409
    set_trip(db_session, tid, status="open", departure_time=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1))
    assert client.post(f"/trips/{tid}/requests", json={}, headers=r).status_code == 409


def test_request_timer_is_ten_minutes(client):
    m, tid = setup_trip(client)
    r = register(client, "R", "r@khi.iba.edu.pk")
    q = client.post(f"/trips/{tid}/requests", json={}, headers=r).json()
    a, b = dt.datetime.fromisoformat(q["requested_at"]), dt.datetime.fromisoformat(q["expires_at"])
    assert dt.timedelta(minutes=9, seconds=55) < b - a < dt.timedelta(minutes=10, seconds=5)


def test_rider_with_accepted_request_is_also_busy(client):
    m = register(client, "M", M)
    v = add_car(client, m)
    t1, t2 = post_trip(client, m, v, origin="A"), post_trip(client, m, v, origin="B")
    r, _ = accepted_rider(client, m, t1)
    assert client.post(f"/trips/{t2}/requests", json={}, headers=r).status_code == 409


def test_cancelled_request_row_is_reused_for_the_same_trip(client):
    m, tid = setup_trip(client)
    r, rid = rider_with_request(client, tid)
    client.post(f"/requests/{rid}/cancel", headers=r)
    again = client.post(f"/trips/{tid}/requests", json={"message": "second try"}, headers=r)
    assert again.status_code == 201 and again.json()["request_id"] == rid and again.json()["status"] == "pending"


# ======================= RESPOND (MANAGER) =======================
def test_only_the_manager_can_accept_or_decline(client):
    m, tid = setup_trip(client)
    r, rid = rider_with_request(client, tid)
    o = register(client, "O", "o@khi.iba.edu.pk")
    for who in (r, o):
        assert client.post(f"/requests/{rid}/accept", headers=who).status_code == 403
        assert client.post(f"/requests/{rid}/decline", headers=who).status_code == 403
    assert client.post("/requests/99999/accept", headers=m).status_code == 404


def test_answered_requests_cannot_be_answered_again(client):
    m, tid = setup_trip(client)
    r, rid = rider_with_request(client, tid)
    assert client.post(f"/requests/{rid}/decline", headers=m).status_code == 200
    assert client.post(f"/requests/{rid}/decline", headers=m).status_code == 409
    assert client.post(f"/requests/{rid}/accept", headers=m).status_code == 409


def test_second_pending_request_cannot_be_accepted_when_seats_run_out(client):
    m, tid = setup_trip(client, seats=1)
    _, r1 = rider_with_request(client, tid, "r1@khi.iba.edu.pk")
    _, r2 = rider_with_request(client, tid, "r2@khi.iba.edu.pk")
    assert client.post(f"/requests/{r1}/accept", headers=m).status_code == 200
    assert client.post(f"/requests/{r2}/accept", headers=m).status_code == 409
    assert client.get(f"/trips/{tid}", headers=m).json()["available_seats"] == 0


def test_received_requests_status_filter_and_phone_rules(client):
    m, tid = setup_trip(client)
    r1, rid1 = accepted_rider(client, m, tid, "r1@khi.iba.edu.pk", phone="0300 5")
    r2, rid2 = rider_with_request(client, tid, "r2@khi.iba.edu.pk", phone="0300 6")
    pending = client.get("/requests/received", headers=m).json()
    assert [x["request_id"] for x in pending] == [rid2] and pending[0]["rider"]["phone"] is None
    accepted = client.get("/requests/received", params={"status": "accepted"}, headers=m).json()
    assert accepted[0]["rider"]["phone"] == "0300 5"
    assert client.get("/requests/received", headers=r1).json() == []           # a rider has nothing to manage


def test_manager_phone_hidden_from_pending_and_declined_riders(client):
    m, tid = setup_trip(client)
    r, rid = rider_with_request(client, tid)
    assert client.get("/requests/sent", headers=r).json()[0]["manager_phone"] is None
    client.post(f"/requests/{rid}/decline", headers=m)
    assert client.get("/requests/sent", headers=r).json()[0]["manager_phone"] is None


# ======================= REQUEST LIFECYCLE =======================
def test_cancel_request_rules(client):
    m, tid = setup_trip(client)
    r, rid = rider_with_request(client, tid)
    o = register(client, "O", "o@khi.iba.edu.pk")
    assert client.post(f"/requests/{rid}/cancel", headers=o).status_code == 403
    assert client.post(f"/requests/{rid}/cancel", headers=m).status_code == 403
    client.post(f"/requests/{rid}/accept", headers=m)
    assert client.post(f"/requests/{rid}/cancel", headers=r).status_code == 409    # accepted: must use Leave


def test_leave_trip_rules(client):
    m, tid = setup_trip(client)
    r, rid = rider_with_request(client, tid)
    assert client.post(f"/requests/{rid}/leave", headers=r).status_code == 409     # still pending
    client.post(f"/requests/{rid}/accept", headers=m)
    o = register(client, "O", "o@khi.iba.edu.pk")
    assert client.post(f"/requests/{rid}/leave", headers=o).status_code == 403
    assert client.post(f"/requests/{rid}/leave", headers=r).status_code == 200
    assert client.post(f"/requests/{rid}/leave", headers=r).status_code == 409     # already left


def test_leaving_a_confirmed_trip_releases_the_seat(client):
    m, tid = setup_trip(client)
    r, rid = accepted_rider(client, m, tid)
    client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=m)
    assert client.post(f"/requests/{rid}/leave", headers=r).status_code == 200
    assert client.get(f"/trips/{tid}", headers=m).json()["available_seats"] == 3


def test_sent_requests_are_newest_first(client):
    m = register(client, "M", M)
    v = add_car(client, m)
    t1, t2 = post_trip(client, m, v, origin="A"), post_trip(client, m, v, origin="B")
    r, rid1 = rider_with_request(client, t1)
    client.post(f"/requests/{rid1}/cancel", headers=r)
    rid2 = client.post(f"/trips/{t2}/requests", json={}, headers=r).json()["request_id"]
    assert [x["request_id"] for x in client.get("/requests/sent", headers=r).json()] == [rid2, rid1]


def test_expired_request_cannot_be_cancelled_or_declined(client, db_session):
    m, tid = setup_trip(client)
    r, rid = rider_with_request(client, tid)
    db_session.get(TripRequest, rid).expires_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)
    db_session.commit()
    assert client.post(f"/requests/{rid}/cancel", headers=r).status_code == 409
    assert client.post(f"/requests/{rid}/decline", headers=m).status_code == 409


# ======================= CONFIRM PICKUP =======================
def test_confirm_pickup_rules(client):
    m, tid = setup_trip(client)
    r, rid = accepted_rider(client, m, tid)
    assert client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=r).status_code == 403
    assert client.post(f"/trips/{tid}/confirm", json={"pickup_point": "   "}, headers=m).status_code == 422
    ok = client.post(f"/trips/{tid}/confirm", json={"pickup_point": "  Gate 2  "}, headers=m)
    assert ok.status_code == 200 and ok.json()["status"] == "confirmed" and ok.json()["pickup_point"] == "Gate 2"
    assert client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 3"}, headers=m).status_code == 409
    assert client.post("/trips/99999/confirm", json={"pickup_point": "x"}, headers=m).status_code == 404


def test_confirming_declines_waiting_requests_and_closes_the_trip(client):
    m, tid = setup_trip(client)
    accepted_rider(client, m, tid, "r1@khi.iba.edu.pk")
    waiting, wid = rider_with_request(client, tid, "r2@khi.iba.edu.pk")
    client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=m)
    assert client.get("/requests/sent", headers=waiting).json()[0]["status"] == "declined"
    assert client.get("/trips", headers=waiting).json() == []                      # no longer in Browse
    late = register(client, "L", "l@khi.iba.edu.pk")
    assert client.post(f"/trips/{tid}/requests", json={}, headers=late).status_code == 409


def test_accepted_rider_sees_the_pickup_point(client):
    m, tid = setup_trip(client)
    r, _ = accepted_rider(client, m, tid)
    client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=m)
    assert client.get(f"/trips/{tid}", headers=r).json()["pickup_point"] == "Gate 2"


def test_confirmed_trip_can_still_be_cancelled_by_the_manager(client):
    m, tid = setup_trip(client)
    r, _ = accepted_rider(client, m, tid)
    client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=m)
    assert client.post(f"/trips/{tid}/cancel", headers=m).status_code == 200
    assert client.get("/requests/sent", headers=r).json()[0]["status"] == "cancelled"


def test_riders_list_is_manager_only_and_shows_phones(client):
    m, tid = setup_trip(client)
    r, _ = accepted_rider(client, m, tid, phone="0300 5")
    assert client.get(f"/trips/{tid}/riders", headers=r).status_code == 403
    rows = client.get(f"/trips/{tid}/riders", headers=m).json()
    assert len(rows) == 1 and rows[0]["rider"]["phone"] == "0300 5" and rows[0]["manager_marked"] is False


# ======================= COMPLETE TRIP =======================
def test_complete_rules(client):
    m, tid = setup_trip(client)
    r, _ = accepted_rider(client, m, tid)
    uid = user_id(client, r)
    assert client.post(f"/trips/{tid}/complete", json={"rider_ids": [uid]}, headers=m).status_code == 409   # not confirmed yet
    client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=m)
    assert client.post(f"/trips/{tid}/complete", json={"rider_ids": [uid]}, headers=r).status_code == 403
    assert client.post(f"/trips/{tid}/complete", json={"rider_ids": [999]}, headers=m).status_code == 422   # not a rider
    assert client.post(f"/trips/{tid}/complete", json={"rider_ids": [uid]}, headers=m).status_code == 200
    assert client.post(f"/trips/{tid}/complete", json={"rider_ids": [uid]}, headers=m).status_code == 409   # twice


def test_complete_with_nobody_ticked_still_counts_for_the_manager(client):
    m, tid = setup_trip(client)
    r, rid = accepted_rider(client, m, tid)
    client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=m)
    assert client.post(f"/trips/{tid}/complete", json={"rider_ids": []}, headers=m).status_code == 200
    assert client.get("/me", headers=m).json()["completed_trips_count"] == 1
    assert client.get("/requests/sent", headers=r).json()[0]["needs_confirmation"] is False
    assert client.post(f"/requests/{rid}/confirm-travel", json={"travelled": True}, headers=r).status_code == 409


def test_rider_confirmation_rules_and_counts(client):
    m, tid = setup_trip(client)
    r, rid = accepted_rider(client, m, tid)
    o = register(client, "O", "o@khi.iba.edu.pk")
    assert client.post(f"/requests/{rid}/confirm-travel", json={"travelled": True}, headers=r).status_code == 409   # too early
    client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=m)
    client.post(f"/trips/{tid}/complete", json={"rider_ids": [user_id(client, r)]}, headers=m)
    assert client.get("/requests/sent", headers=r).json()[0]["needs_confirmation"] is True
    assert client.post(f"/requests/{rid}/confirm-travel", json={"travelled": True}, headers=o).status_code == 403
    assert client.post(f"/requests/{rid}/confirm-travel", json={"travelled": "maybe"}, headers=r).status_code == 422
    assert client.post(f"/requests/{rid}/confirm-travel", json={"travelled": True}, headers=r).status_code == 200
    assert client.post(f"/requests/{rid}/confirm-travel", json={"travelled": False}, headers=r).status_code == 409   # once only
    assert client.get("/me", headers=r).json()["completed_trips_count"] == 1
    assert client.get("/me", headers=m).json()["completed_trips_count"] == 1
    assert client.get("/requests/sent", headers=r).json()[0]["needs_confirmation"] is False


def test_two_riders_one_ticked_one_not(client):
    m, tid = setup_trip(client)
    r1, id1 = accepted_rider(client, m, tid, "r1@khi.iba.edu.pk")
    r2, id2 = accepted_rider(client, m, tid, "r2@khi.iba.edu.pk")
    client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=m)
    client.post(f"/trips/{tid}/complete", json={"rider_ids": [user_id(client, r1)]}, headers=m)
    assert client.post(f"/requests/{id2}/confirm-travel", json={"travelled": True}, headers=r2).status_code == 409
    assert client.post(f"/requests/{id1}/confirm-travel", json={"travelled": True}, headers=r1).status_code == 200
    assert client.get("/me", headers=r2).json()["completed_trips_count"] == 0


def test_completed_trip_cannot_be_cancelled_or_edited(client):
    m, tid = setup_trip(client)
    vid = client.get("/vehicles", headers=m).json()[0]["vehicle_id"]
    accepted_rider(client, m, tid)
    client.post(f"/trips/{tid}/confirm", json={"pickup_point": "Gate 2"}, headers=m)
    client.post(f"/trips/{tid}/complete", json={"rider_ids": []}, headers=m)
    assert client.post(f"/trips/{tid}/cancel", headers=m).status_code == 409
    assert client.put(f"/trips/{tid}", json=trip_body(vid), headers=m).status_code == 409


# ======================= MY TRIPS =======================
def test_my_trips_counts_and_joined_filtering(client):
    m, tid = setup_trip(client)
    accepted_rider(client, m, tid, "r1@khi.iba.edu.pk")
    declined, did = rider_with_request(client, tid, "r2@khi.iba.edu.pk")
    client.post(f"/requests/{did}/decline", headers=m)
    pend, _ = rider_with_request(client, tid, "r3@khi.iba.edu.pk")
    mine = client.get("/trips/mine", headers=m).json()
    assert mine["managing"][0]["accepted_riders"] == 1 and mine["managing"][0]["pending_requests"] == 1
    assert client.get("/trips/mine", headers=declined).json()["joined"] == []        # declined is not "joined"
    assert len(client.get("/trips/mine", headers=pend).json()["joined"]) == 1        # pending is


def test_my_trips_empty_for_new_user(client):
    h = register(client, "New", "n@khi.iba.edu.pk")
    assert client.get("/trips/mine", headers=h).json() == {"managing": [], "joined": []}


# ======================= SECURITY / PRIVACY / REGRESSION =======================
def test_no_response_ever_contains_a_password_hash(client):
    m, tid = setup_trip(client)
    r, rid = accepted_rider(client, m, tid)
    texts = [client.get(u, headers=h).text for h in (m, r) for u in
             ("/me", "/trips/mine", f"/trips/{tid}", "/requests/sent", "/requests/received", "/vehicles")]
    assert not any("password" in t.lower() for t in texts)


def test_riders_cannot_see_each_others_phone_numbers(client):
    m, tid = setup_trip(client, seats=3)
    r1, _ = accepted_rider(client, m, tid, "r1@khi.iba.edu.pk", phone="0300 5")
    r2, _ = accepted_rider(client, m, tid, "r2@khi.iba.edu.pk", phone="0300 6")
    assert "0300 5" not in client.get(f"/trips/{tid}", headers=r2).text
    assert "0300 5" not in client.get("/requests/sent", headers=r2).text
    assert client.get(f"/trips/{tid}/riders", headers=r2).status_code == 403


def test_regression_decline_then_rerequest_same_trip_no_unique_violation(client):
    m, tid = setup_trip(client)
    r, rid = rider_with_request(client, tid)
    client.post(f"/requests/{rid}/decline", headers=m)
    again = client.post(f"/trips/{tid}/requests", json={}, headers=r)
    assert again.status_code == 201 and again.json()["status"] == "pending"


def test_regression_seat_count_never_goes_negative_or_above_total(client):
    m, tid = setup_trip(client, seats=2)
    r1, id1 = accepted_rider(client, m, tid, "r1@khi.iba.edu.pk")
    r2, id2 = accepted_rider(client, m, tid, "r2@khi.iba.edu.pk")
    assert client.get(f"/trips/{tid}", headers=m).json()["available_seats"] == 0
    client.post(f"/requests/{id1}/leave", headers=r1)
    client.post(f"/requests/{id2}/leave", headers=r2)
    assert client.get(f"/trips/{tid}", headers=m).json()["available_seats"] == 2


def test_health_and_root_endpoints(client):
    assert client.get("/").json() == {"message": "Hello from FareShare"}
    assert client.get("/health").json() == {"status": "ok"}
    h = client.get("/health/db")
    assert h.status_code == 200 and h.json()["database"] == "connected"


def test_unknown_route_returns_404_and_wrong_method_405(client):
    assert client.get("/nope").status_code == 404
    assert client.delete("/trips").status_code == 405
