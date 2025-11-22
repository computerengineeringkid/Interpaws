import requests
import time
import datetime

BASE_URL = "http://localhost:8000"

def run():
    timestamp = int(time.time())
    email = f"test_repro_{timestamp}@example.com"
    password = "password123"
    name = "Repro User"

    print(f"1. Registering {email}...")
    resp = requests.post(f"{BASE_URL}/clients", json={
        "name": name,
        "email": email,
        "password": password
    })
    if resp.status_code != 200:
        print(f"Registration failed: {resp.status_code} {resp.text}")
        # Try login anyway, maybe it exists
    else:
        print("Registration success.")

    print("2. Logging in...")
    resp = requests.post(f"{BASE_URL}/token", data={
        "username": email,
        "password": password
    })
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}")
        return
    
    token = resp.json()["access_token"]
    print(f"Login success. Token: {token[:10]}...")

    print("3. Booking appointment...")
    # Tomorrow 10am
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    start_time = f"{tomorrow}T10:00:00"
    end_time = f"{tomorrow}T11:00:00"

    payload = {
        "start_time": start_time,
        "end_time": end_time,
        "pet_id": 32,
        "staff_id": 2
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Note: using /bookings (no trailing slash) as per my fix
    resp = requests.post(f"{BASE_URL}/bookings", json=payload, headers=headers)
    
    print(f"Booking Response: {resp.status_code}")
    print(f"Body: {resp.text}")

    if resp.status_code == 307:
        print("ERROR: Still getting 307 Redirect!")
    elif resp.status_code == 401:
        print("ERROR: Getting 401 Unauthorized!")
    elif resp.status_code == 200:
        print("SUCCESS: Booking created.")

if __name__ == "__main__":
    run()
