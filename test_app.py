import unittest
import json
import os
import db
from app import app

class MTHGateTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        db.init_db()

    def test_01_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_02_verify_pin_fresh_device(self):
        users = db.load_users()
        if not users:
            db.add_user("เจ้าหน้าที่ทดสอบ", "เจ้าหน้าที่", "123456")
            users = db.load_users()

        test_user = users[0]
        test_pin = test_user["pin"]

        # Test fresh device entry with matching PIN
        res = self.client.post('/api/verify_pin', json={
            "pin": test_pin,
            "bound_token": None
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["name"], test_user["name"])

    def test_03_verify_pin_bound_device_mismatch(self):
        users = db.load_users()
        user1 = users[0]
        # Use a PIN that is guaranteed not to match user1's PIN
        wrong_pin = "999999" if user1["pin"] != "999999" else "888888"

        # Bound to User 1 token, but typing wrong/another staff PIN -> Should reject!
        res = self.client.post('/api/verify_pin', json={
            "pin": wrong_pin,
            "bound_token": user1["token"]
        })
        self.assertNotEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("ไม่ถูกต้องสำหรับผู้ใช้งานเครื่องนี้", data["message"])

    def test_04_admin_login_fail(self):
        res = self.client.post('/api/admin/login', json={"password": "wrongpassword"})
        self.assertEqual(res.status_code, 401)

    def test_05_admin_login_success(self):
        res = self.client.post('/api/admin/login', json={"password": "admin1234"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

if __name__ == '__main__':
    unittest.main()
