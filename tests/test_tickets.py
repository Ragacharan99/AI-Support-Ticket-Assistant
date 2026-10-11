"""Core ticket creation and retrieval API tests."""


def test_create_ticket_ignores_client_category_and_urgency(client):
    response = client.post(
        "/tickets",
        json={
            "subject": "Cannot sign in",
            "body": "The password reset link expires immediately.",
            "category": "billing",
            "urgency": "critical",
        },
    )

    assert response.status_code == 201
    ticket = response.json()
    assert ticket["status"] == "new"
    assert ticket["category"] is None
    assert ticket["urgency"] is None


def test_get_ticket(client):
    created = client.post("/tickets", json={"subject": "Question", "body": "How does export work?"})

    response = client.get(f"/tickets/{created.json()['id']}")

    assert response.status_code == 200
    assert response.json()["subject"] == "Question"


def test_get_missing_ticket_returns_404(client):
    assert client.get("/tickets/99999").status_code == 404
