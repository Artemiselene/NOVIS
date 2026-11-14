def test_health(client):
    assert client.get("/api/extension/health").status_code == 200

def test_environments(client):
    r = client.get("/api/extension/environments")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_body_systems_and_grey_without_source(client):
    r = client.get("/api/extension/body-systems/heart/status?astronaut_id=1")
    assert r.status_code == 200
    assert r.json()["status"] == "grey"
    assert r.json()["measurements"] == []

def test_unknown_body_system(client):
    assert client.get("/api/extension/body-systems/not-real/status?astronaut_id=1").status_code == 404

def test_routine_completion(client):
    created = client.post("/api/extension/routines", json={
        "astronaut_id":1,"kind":"wellbeing","title":"Daily check-in"
    })
    assert created.status_code == 201
    rid = created.json()["id"]
    done = client.post(f"/api/extension/routines/{rid}/complete", json={"notes":"completed"})
    assert done.status_code == 200 and done.json()["ok"] is True

def test_challenge_points_reward_participation(client):
    challenges = client.get("/api/extension/challenges").json()
    assert challenges
    r = client.post(f"/api/extension/challenges/{challenges[0]['id']}/complete/1")
    assert r.status_code == 200
    assert "Participation" in r.json()["reason"]

def test_education_metrics(client):
    keys = {x["metric_key"] for x in client.get("/api/extension/education").json()}
    assert {"heart_rate","hrv","eda","respiration","eeg","sleep","fatigue","cognitive","mood","workload","psi"} <= keys
