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
        db.execute_sql("DELETE FROM user_devices WHERE device_id LIKE %s OR device_id LIKE %s", ("test_%", "dev_%"))

    def test_01_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_02_verify_pin_unbound_device_rejected(self):
        users = db.load_users()
        if not users:
            db.add_user("เจ้าหน้าที่ทดสอบ", "เจ้าหน้าที่", "123456")
            users = db.load_users()

        test_user = users[0]
        test_pin = test_user["pin"]

        # PIN entry without QR Code / bound_token should be rejected
        res = self.client.post('/api/verify_pin', json={
            "pin": test_pin,
            "bound_token": None
        })
        self.assertNotEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("ยังไม่ได้ผูกสิทธิ์", data["message"])

    def test_03_verify_pin_bound_device_success(self):
        users = db.load_users()
        test_user = users[0]

        # PIN entry with valid bound_token and device_id should succeed
        res = self.client.post('/api/verify_pin', json={
            "pin": test_user["pin"],
            "bound_token": test_user["token"],
            "device_id": "test_device_1",
            "device_name": "Test Device"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["name"], test_user["name"])

    def test_04_verify_pin_bound_device_mismatch(self):
        users = db.load_users()
        user1 = users[0]
        wrong_pin = "999999" if user1["pin"] != "999999" else "888888"

        # Bound to User 1 token, but typing wrong PIN -> Should reject!
        res = self.client.post('/api/verify_pin', json={
            "pin": wrong_pin,
            "bound_token": user1["token"],
            "device_id": "test_device_1",
            "device_name": "Test Device"
        })
        self.assertNotEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_05_admin_login_fail(self):
        res = self.client.post('/api/admin/login', json={"password": "wrongpassword"})
        self.assertEqual(res.status_code, 401)

    def test_06_admin_login_success(self):
        res = self.client.post('/api/admin/login', json={"password": "admin1234"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

    def test_07_device_registration_limit_and_revoke(self):
        users = db.load_users()
        user1 = users[0]

        # Login admin session
        self.client.post('/api/admin/login', json={"password": "admin1234"})

        # Reset max_devices to 1 for user1
        self.client.post(f'/api/admin/users/{user1["id"]}/devices/max', json={"max_devices": 1})

        # Revoke existing devices for user1 to clean up state
        existing_devs = db.load_user_devices(user1["id"])
        for dev in existing_devs:
            db.revoke_user_device(user1["id"], dev["device_id"])

        # Device A: Open gate with device_id="dev_A" -> Should succeed
        res1 = self.client.post('/api/open', json={
            "token": user1["token"],
            "device_id": "dev_A",
            "device_name": "Phone A"
        })
        self.assertEqual(res1.status_code, 200)

        # Device B: Open gate with device_id="dev_B" on max_devices=1 -> Should be blocked!
        res2 = self.client.post('/api/open', json={
            "token": user1["token"],
            "device_id": "dev_B",
            "device_name": "Phone B"
        })
        self.assertEqual(res2.status_code, 403)
        data2 = res2.get_json()
        self.assertFalse(data2["success"])
        self.assertTrue("อุปกรณ์" in data2["message"] or "จำกัด" in data2["message"])

        # Admin increases max_devices to 2
        res_max = self.client.post(f'/api/admin/users/{user1["id"]}/devices/max', json={"max_devices": 2})
        self.assertEqual(res_max.status_code, 200)

        # Device B tries again -> Should now succeed!
        res3 = self.client.post('/api/open', json={
            "token": user1["token"],
            "device_id": "dev_B",
            "device_name": "Phone B"
        })
        self.assertEqual(res3.status_code, 200)

        # Admin revokes Device B
        res_revoke = self.client.delete(f'/api/admin/users/{user1["id"]}/devices/dev_B')
        self.assertEqual(res_revoke.status_code, 200)

        # Admin resets max_devices back to 1
        self.client.post(f'/api/admin/users/{user1["id"]}/devices/max', json={"max_devices": 1})

        # Device B tries again after revoke (with Device A still active and max_devices=1) -> Blocked!
        res4 = self.client.post('/api/open', json={
            "token": user1["token"],
            "device_id": "dev_B",
            "device_name": "Phone B"
        })
        self.assertEqual(res4.status_code, 403)

if __name__ == '__main__':
    unittest.main()
