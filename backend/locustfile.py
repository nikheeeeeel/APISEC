from locust import HttpUser, task, between

class APISECUser(HttpUser):
    wait_time = between(1, 3)
    jwt_token = None

    def on_start(self):
        # We simulate a typical auth failure or success to test login load
        # In a real environment, we'd provide valid credentials or mock them out
        response = self.client.post("/api/auth/login", data={"username": "testuser", "password": "wrongpassword"})
        if response.status_code == 200:
            self.jwt_token = response.json().get("access_token")

    @task(3)
    def view_schemas(self):
        headers = {"Authorization": f"Bearer {self.jwt_token}"} if self.jwt_token else {}
        # Test an unauthorized view to measure 401 response speed
        self.client.get("/api/schemas/changes", headers=headers)

    @task(1)
    def trigger_ai_analysis(self):
        headers = {"Authorization": f"Bearer {self.jwt_token}"} if self.jwt_token else {}
        self.client.post("/api/analyze", json={"diff": {"endpoint": "/test", "change": "removed parameter"}}, headers=headers)
