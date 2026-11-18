import datetime as dt

from app.models import TripRequest

PW = "password1"


def register(client, name, email, gender="female", phone="0300 1111111"):
    r = client.post(
        "/auth/register",
        json={"full_name": name, "email": email, "password": PW, "gender": gender, "phone": phone},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def future(hours=24):
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=hours)).isoformat()


def add_car(client, h, seats=4):
    r = client.post(
        "/vehicles",
        json={"make": "Honda", "model": "City", "color": "White", "plate_number": "kpl-1234", "total_seats": seats},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["vehicle_id"]


def post_trip(client, h, vehicle_id, origin="Clifton", campus="IBA City Campus", gender="any", seats=3, hours=24):
    r = client.post(
        "/trips",
        json={
            "origin_area": origin, "destination_area": campus, "departure_time": future(hours),
            "seats": seats, "cost_per_person": 250, "gender_filter": gender,
            "ride_type": "own_car", "vehicle_id": vehicle_id,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()["trip_id"]


# ---------- authentication ----------
def test_register_ok_and_hash_not_returned(client):
    r = client.post("/auth/register", json={"full_name": "Uroos Fatima", "email": "Uroos.31094@khi.iba.edu.pk",
                                            "password": PW, "gender": "female"})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "uroos.31094@khi.iba.edu.pk"
    assert "password" not in str(body).lower().replace("password_hash", "")
    assert "token" in body


def test_register_rejects_non_iba_email(client):
    r = client.post("/auth/register", json={"full_name": "X", "email": "x@gmail.com", "password": PW, "gender": "male"})
    assert r.status_code == 422


def test_register_rejects_weak_password_and_bad_gender(client):
    base = {"full_name": "X", "email": "x@khi.iba.edu.pk"}
    assert client.post("/auth/register", json={**base, "password": "short1", "gender": "male"}).status_code == 422
    assert client.post("/auth/register", json={**base, "password": "nonumberhere", "gender": "male"}).status_code == 422
    assert client.post("/auth/register", json={**base, "password": PW, "gender": "other"}).status_code == 422


def test_register_duplicate_email(client):
    register(client, "A", "a@khi.iba.edu.pk")
    r = client.post("/auth/register", json={"full_name": "A2", "email": "a@khi.iba.edu.pk", "password": PW, "gender": "female"})
    assert r.status_code == 409


def test_login_and_me(client):
    register(client, "A", "a@khi.iba.edu.pk")
    assert client.post("/auth/login", json={"email": "a@khi.iba.edu.pk", "password": "wrong123"}).status_code == 401
    r = client.post("/auth/login", json={"email": "a@khi.iba.edu.pk", "password": PW})
    assert r.status_code == 200
    me = client.get("/me", headers={"Authorization": f"Bearer {r.json()['token']}"})
    assert me.status_code == 200 and me.json()["full_name"] == "A"
    assert client.get("/me").status_code == 401


def test_change_password_and_locked_fields(client):
    h = register(client, "A", "a@khi.iba.edu.pk")
    assert client.post("/auth/change-password", json={"current_password": "bad", "new_password": "newpass12"}, headers=h).status_code == 400
    assert client.post("/auth/change-password", json={"current_password": PW, "new_password": PW}, headers=h).status_code == 422
    assert client.post("/auth/change-password", json={"current_password": PW, "new_password": "newpass12"}, headers=h).status_code == 200
    assert client.post("/auth/login", json={"email": "a@khi.iba.edu.pk", "password": "newpass12"}).status_code == 200
    r = client.put("/me", json={"full_name": "New Name", "phone": "0322 5555555", "gender": "male", "email": "z@z.com"}, headers=h)
    assert r.json()["full_name"] == "New Name" and r.json()["gender"] == "female" and r.json()["email"] == "a@khi.iba.edu.pk"


# ---------- vehicles ----------
def test_vehicle_crud_and_delete_rule(client):
    h = register(client, "Uroos", "u@khi.iba.edu.pk")
    vid = add_car(client, h)
    assert len(client.get("/vehicles", headers=h).json()) == 1
    assert client.put(f"/vehicles/{vid}", json={"make": "Honda", "model": "Civic", "color": "Black", "plate_number": "abc-1", "total_seats": 4}, headers=h).json()["model"] == "Civic"
    post_trip(client, h, vid)
    r = client.delete(f"/vehicles/{vid}", headers=h)
    assert r.status_code == 409   # used by an upcoming trip
    other = register(client, "Other", "o@khi.iba.edu.pk")
    assert client.delete(f"/vehicles/{vid}", headers=other).status_code == 404   # not their car


def test_vehicle_delete_when_free(client):
    h = register(client, "U", "u@khi.iba.edu.pk")
    vid = add_car(client, h)
    assert client.delete(f"/vehicles/{vid}", headers=h).status_code == 200
    assert client.get("/vehicles", headers=h).json() == []


# ---------- trips ----------
def test_post_trip_rules(client):
    h = register(client, "U", "u@khi.iba.edu.pk", "female")
    vid = add_car(client, h, seats=2)
    base = {"origin_area": "Clifton", "destination_area": "IBA City Campus", "departure_time": future(),
            "seats": 2, "cost_per_person": 100, "gender_filter": "any", "ride_type": "own_car", "vehicle_id": vid}
    assert client.post("/trips", json={**base, "gender_filter": "male"}, headers=h).status_code == 422   # male-only locked for a woman
    assert client.post("/trips", json={**base, "seats": 3}, headers=h).status_code == 422                # more than vehicle seats
    assert client.post("/trips", json={**base, "departure_time": future(-2)}, headers=h).status_code == 422
    assert client.post("/trips", json={**base, "destination_area": "Saddar"}, headers=h).status_code == 422   # no campus involved
    assert client.post("/trips", json={**base, "vehicle_id": None}, headers=h).status_code == 422
    r = client.post("/trips", json={**base, "ride_type": "indrive_group", "vehicle_id": None, "destination_area": "IBA Main Campus"}, headers=h)
    assert r.status_code == 201 and r.json()["ride_type"] == "indrive_group" and r.json()["vehicle"] is None


def test_browse_filters_by_pickup_and_campus(client):
    m = register(client, "Mgr", "m@khi.iba.edu.pk", "female")
    v = add_car(client, m)
    post_trip(client, m, v, origin="Clifton Block 5", campus="IBA City Campus")
    post_trip(client, m, v, origin="Nazimabad", campus="IBA Main Campus")
    rider = register(client, "Rider", "r@khi.iba.edu.pk", "female")
    allt = client.get("/trips", headers=rider).json()
    assert len(allt) == 2
    assert [t["origin_area"] for t in client.get("/trips?origin=clifton", headers=rider).json()] == ["Clifton Block 5"]
    assert [t["destination_area"] for t in client.get("/trips?campus=IBA Main Campus", headers=rider).json()] == ["IBA Main Campus"]
    assert client.get("/trips?origin=clifton&campus=IBA Main Campus", headers=rider).json() == []
    assert client.get("/trips", headers=m).json() == []   # managers don't see their own trips in Home


def test_gender_restricted_trips_hidden(client):
    m = register(client, "Mgr", "m@khi.iba.edu.pk", "female")
    v = add_car(client, m)
    post_trip(client, m, v, gender="female")
    male = register(client, "Male", "ml@khi.iba.edu.pk", "male")
    female = register(client, "Fem", "f@khi.iba.edu.pk", "female")
    assert client.get("/trips", headers=male).json() == []
    assert len(client.get("/trips", headers=female).json()) == 1


def test_edit_and_cancel_trip(client):
    m = register(client, "Mgr", "m@khi.iba.edu.pk")
    v = add_car(client, m)
    tid = post_trip(client, m, v)
    body = {"origin_area": "DHA", "destination_area": "IBA Main Campus", "departure_time": future(30), "seats": 2,
            "cost_per_person": 300, "gender_filter": "any", "ride_type": "own_car", "vehicle_id": v}
    r = client.put(f"/trips/{tid}", json=body, headers=m)
    assert r.status_code == 200 and r.json()["origin_area"] == "DHA" and r.json()["available_seats"] == 2
    other = register(client, "Other", "o@khi.iba.edu.pk")
    assert client.put(f"/trips/{tid}", json=body, headers=other).status_code == 403
    assert client.post(f"/trips/{tid}/cancel", headers=other).status_code == 403
    assert client.post(f"/trips/{tid}/cancel", headers=m).status_code == 200
    assert client.post(f"/trips/{tid}/cancel", headers=m).status_code == 409
    assert client.get("/trips", headers=other).json() == []


# ---------- requests ----------
def setup_trip(client, gender="any", seats=3):
    m = register(client, "Manager", "m@khi.iba.edu.pk", "female", "0311 7654321")
    v = add_car(client, m)
    return m, post_trip(client, m, v, gender=gender, seats=seats)


def test_request_accept_flow_and_phone_visibility(client):
    m, tid = setup_trip(client)
    r = register(client, "Rider", "r@khi.iba.edu.pk", "female", "0300 9999999")
    sent = client.post(f"/trips/{tid}/requests", json={"message": "Ready at the stop"}, headers=r)
    assert sent.status_code == 201 and sent.json()["status"] == "pending" and sent.json()["expires_at"]
    rid = sent.json()["request_id"]
    mine = client.get("/requests/sent", headers=r).json()[0]
    assert mine["manager_phone"] is None                       # hidden until accepted
    inc = client.get("/requests/received", headers=m).json()
    assert len(inc) == 1 and inc[0]["rider"]["phone"] is None
    assert client.post(f"/requests/{rid}/accept", headers=r).status_code == 403   # rider cannot accept
    assert client.post(f"/requests/{rid}/accept", headers=m).status_code == 200
    assert client.get("/requests/sent", headers=r).json()[0]["manager_phone"] == "0311 7654321"
    assert client.get(f"/trips/{tid}", headers=r).json()["available_seats"] == 2
    assert client.post(f"/requests/{rid}/accept", headers=m).status_code == 409   # already answered


def test_one_active_request_at_a_time(client):
    m = register(client, "Manager", "m@khi.iba.edu.pk")
    v = add_car(client, m)
    t1, t2 = post_trip(client, m, v, origin="Clifton"), post_trip(client, m, v, origin="DHA")
    r = register(client, "Rider", "r@khi.iba.edu.pk")
    first = client.post(f"/trips/{t1}/requests", json={}, headers=r)
    assert first.status_code == 201
    assert client.post(f"/trips/{t2}/requests", json={}, headers=r).status_code == 409
    listing = {t["trip_id"]: t for t in client.get("/trips", headers=r).json()}
    assert listing[t1]["locked"] is False and listing[t2]["locked"] is True
    assert client.post(f"/requests/{first.json()['request_id']}/cancel", headers=r).status_code == 200
    assert client.post(f"/trips/{t2}/requests", json={}, headers=r).status_code == 201   # free again


def test_decline_frees_rider_and_allows_new_request(client):
    m = register(client, "Manager", "m@khi.iba.edu.pk")
    v = add_car(client, m)
    t1, t2 = post_trip(client, m, v, origin="Clifton"), post_trip(client, m, v, origin="DHA")
    r = register(client, "Rider", "r@khi.iba.edu.pk")
    rid = client.post(f"/trips/{t1}/requests", json={}, headers=r).json()["request_id"]
    assert client.post(f"/requests/{rid}/decline", headers=m).status_code == 200
    assert client.post(f"/trips/{t2}/requests", json={}, headers=r).status_code == 201
    # asking the same trip again after a decline reuses the row instead of breaking UNIQUE(trip, requester)
    rid2 = client.post(f"/requests/{client.get('/requests/sent', headers=r).json()[0]['request_id']}/cancel", headers=r)
    assert rid2.status_code == 200
    again = client.post(f"/trips/{t1}/requests", json={}, headers=r)
    assert again.status_code == 201 and again.json()["request_id"] == rid


def test_request_expires_after_timer(client, db_session):
    m, tid = setup_trip(client)
    r = register(client, "Rider", "r@khi.iba.edu.pk")
    rid = client.post(f"/trips/{tid}/requests", json={}, headers=r).json()["request_id"]
    row = db_session.get(TripRequest, rid)
    row.expires_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)   # pretend 10 minutes passed
    db_session.commit()
    assert client.post(f"/requests/{rid}/accept", headers=m).status_code == 409
    assert client.get("/requests/sent", headers=r).json()[0]["status"] == "expired"
    assert client.get("/requests/received", headers=m).json() == []   # no longer pending
    t2 = client.get(f"/trips/{tid}", headers=r).json()
    assert t2["available_seats"] == 3                               # seat was never taken
    assert client.post(f"/trips/{tid}/requests", json={}, headers=r).status_code == 201   # rider is free again


def test_cannot_request_own_trip_or_wrong_gender_or_full_trip(client):
    m, tid = setup_trip(client, gender="female", seats=1)
    assert client.post(f"/trips/{tid}/requests", json={}, headers=m).status_code == 409
    male = register(client, "Male", "ml@khi.iba.edu.pk", "male")
    assert client.post(f"/trips/{tid}/requests", json={}, headers=male).status_code == 403
    f1 = register(client, "F1", "f1@khi.iba.edu.pk", "female")
    f2 = register(client, "F2", "f2@khi.iba.edu.pk", "female")
    rid = client.post(f"/trips/{tid}/requests", json={}, headers=f1).json()["request_id"]
    client.post(f"/requests/{rid}/accept", headers=m)
    assert client.post(f"/trips/{tid}/requests", json={}, headers=f2).status_code == 409   # no seats left
    assert client.get("/trips", headers=f2).json() == []                                    # full trips are not listed


def test_leave_trip_releases_seat_and_cancel_trip_cancels_requests(client):
    m, tid = setup_trip(client)
    r = register(client, "Rider", "r@khi.iba.edu.pk")
    rid = client.post(f"/trips/{tid}/requests", json={}, headers=r).json()["request_id"]
    client.post(f"/requests/{rid}/accept", headers=m)
    assert client.post(f"/requests/{rid}/leave", headers=r).status_code == 200
    assert client.get(f"/trips/{tid}", headers=m).json()["available_seats"] == 3
    rid2 = client.post(f"/trips/{tid}/requests", json={}, headers=r).json()["request_id"]
    client.post(f"/trips/{tid}/cancel", headers=m)
    assert client.get("/requests/sent", headers=r).json()[0]["status"] == "cancelled"


def test_my_trips_lists_managing_and_joined(client):
    m, tid = setup_trip(client)
    r = register(client, "Rider", "r@khi.iba.edu.pk")
    client.post(f"/trips/{tid}/requests", json={}, headers=r)
    mm = client.get("/trips/mine", headers=m).json()
    assert len(mm["managing"]) == 1 and mm["managing"][0]["pending_requests"] == 1
    rr = client.get("/trips/mine", headers=r).json()
    assert len(rr["joined"]) == 1 and rr["joined"][0]["my_request"]["status"] == "pending"
