import os
import json
import logging
import threading
import datetime
import uuid
from config import Config

logger = logging.getLogger(__name__)

# Lock for JSON fallback thread safety
lock = threading.Lock()

USERS_FILE = "users.json"
EVENTS_FILE = "events.json"

def get_mariadb_connection():
    if Config.USE_MARIADB == "false":
        return None
    try:
        import pymysql
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=3
        )
        return conn
    except Exception as e:
        if Config.USE_MARIADB == "true":
            logger.error(f"Failed to connect to MariaDB: {e}")
        return None

def init_db():
    conn = get_mariadb_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS `users` (
                      `id` VARCHAR(64) NOT NULL PRIMARY KEY,
                      `name` VARCHAR(255) NOT NULL,
                      `role` VARCHAR(255) DEFAULT 'เจ้าหน้าที่รักษาความปลอดภัย',
                      `pin` VARCHAR(10) NOT NULL,
                      `token` VARCHAR(128) NOT NULL UNIQUE,
                      `status` VARCHAR(20) DEFAULT 'active',
                      `device_id` VARCHAR(255) DEFAULT NULL,
                      `created_at` VARCHAR(50) DEFAULT NULL,
                      `updated_at` VARCHAR(50) DEFAULT NULL,
                      `last_used` VARCHAR(50) DEFAULT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS `events` (
                      `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                      `time` VARCHAR(50) NOT NULL,
                      `user_name` VARCHAR(255) NOT NULL,
                      `action` VARCHAR(100) NOT NULL,
                      `status` VARCHAR(50) NOT NULL,
                      `detail` TEXT DEFAULT NULL,
                      `user_id` VARCHAR(64) DEFAULT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)
                conn.commit()
                logger.info("MariaDB initialized successfully.")
                migrate_json_to_mariadb(conn)
        except Exception as e:
            logger.error(f"Error initializing MariaDB tables: {e}")
        finally:
            conn.close()

def migrate_json_to_mariadb(conn):
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM users")
            row = cursor.fetchone()
            if row and row['count'] == 0 and os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    json_users = json.load(f)
                for u in json_users:
                    cursor.execute("""
                        INSERT INTO users (id, name, role, pin, token, status, created_at, updated_at, last_used)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        u.get("id"), u.get("name"), u.get("role"), u.get("pin"),
                        u.get("token"), u.get("status", "active"),
                        u.get("created_at"), u.get("updated_at"), u.get("last_used")
                    ))
                conn.commit()
                logger.info(f"Migrated {len(json_users)} users from JSON to MariaDB.")
    except Exception as e:
        logger.error(f"Migration error: {e}")

# --- Data Access Functions ---

def load_users():
    conn = get_mariadb_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users ORDER BY created_at ASC")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error loading users from MariaDB: {e}")
        finally:
            conn.close()
            
    # Fallback to JSON
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_users(users):
    with lock:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

def add_user(name, role, pin):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = f"u-{uuid.uuid4().hex[:8]}"
    token = f"gate-{uuid.uuid4().hex[:12]}"
    new_user = {
        "id": user_id,
        "name": name,
        "role": role or "เจ้าหน้าที่รักษาความปลอดภัย",
        "pin": str(pin).strip(),
        "token": token,
        "status": "active",
        "created_at": now_str,
        "last_used": None,
        "updated_at": now_str
    }

    conn = get_mariadb_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (id, name, role, pin, token, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, name, new_user["role"], new_user["pin"], token, "active", now_str, now_str))
                conn.commit()
                return new_user
        except Exception as e:
            logger.error(f"Error adding user to MariaDB: {e}")
        finally:
            conn.close()

    users = load_users()
    users.append(new_user)
    save_users(users)
    return new_user

def update_user_last_used(user_id):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_mariadb_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET last_used=%s WHERE id=%s", (now_str, user_id))
                conn.commit()
                return
        except Exception as e:
            logger.error(f"Error updating last_used in MariaDB: {e}")
        finally:
            conn.close()

    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u["last_used"] = now_str
            break
    save_users(users)

def update_user_details(user_id, name, role, pin):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_mariadb_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users SET name=%s, role=%s, pin=%s, updated_at=%s WHERE id=%s
                """, (name, role, str(pin).strip(), now_str, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating user in MariaDB: {e}")
            return False
        finally:
            conn.close()

    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u["name"] = name
            u["role"] = role
            u["pin"] = str(pin).strip()
            u["updated_at"] = now_str
            break
    save_users(users)
    return True

def suspend_user(user_id):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_mariadb_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET status='suspended', updated_at=%s WHERE id=%s", (now_str, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error suspending user in MariaDB: {e}")
            return False
        finally:
            conn.close()

    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u["status"] = "suspended"
            u["updated_at"] = now_str
            break
    save_users(users)
    return True

def toggle_user_status(user_id):
    users = load_users()
    current_status = "active"
    for u in users:
        if u["id"] == user_id:
            current_status = u.get("status", "active")
            break

    next_status = "active" if current_status != "active" else "suspended"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_mariadb_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET status=%s, updated_at=%s WHERE id=%s", (next_status, now_str, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error toggling user status in MariaDB: {e}")
            return False
        finally:
            conn.close()

    for u in users:
        if u["id"] == user_id:
            u["status"] = next_status
            u["updated_at"] = now_str
            break
    save_users(users)
    return True

def find_user_by_token(token):
    if not token:
        return None
    users = load_users()
    for u in users:
        if u.get("token") == token:
            return u
    return None

def find_user_by_pin(pin):
    if not pin:
        return None
    users = load_users()
    for u in users:
        if u.get("pin") == str(pin).strip():
            return u
    return None

def verify_pin_for_bound_device(pin, bound_token=None):
    """
    Device Binding Verification:
    Device MUST be bound via QR Code or Direct Link first.
    Once bound, PIN verification checks against the bound user's PIN ONLY.
    """
    pin_str = str(pin).strip()
    if not bound_token:
        return False, None, "อุปกรณ์นี้ยังไม่ได้ผูกสิทธิ์ กรุณาสแกน QR Code เพื่อยืนยันตัวตนก่อน"

    user = find_user_by_token(bound_token)
    if not user:
        return False, None, "สิทธิ์การใช้งานของคุณไม่สมบูรณ์ กรุณาสแกน QR Code เพื่อเปิดใช้งานใหม่"

    if user.get("pin") != pin_str:
        return False, None, "รหัส PIN ไม่ถูกต้องสำหรับผู้ใช้งานเครื่องนี้"

    if user.get("status") != "active":
        return False, None, "สิทธิ์การใช้งานของคุณถูกระงับ กรุณาติดต่อผู้ดูแลระบบ"

    return True, user, "ยืนยันรหัส PIN สำเร็จ"

# --- Events / Audit Logs ---

def load_events():
    conn = get_mariadb_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT time, action, user_name, status, detail FROM events ORDER BY id DESC LIMIT 100")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error loading events from MariaDB: {e}")
        finally:
            conn.close()

    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def log_event(action: str, user_name: str, success: bool, detail: str, user_id: str = None):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_str = "สำเร็จ" if success else "ผิดพลาด"

    conn = get_mariadb_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO events (time, user_name, action, status, detail, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (now_str, user_name, action, status_str, detail, user_id))
                conn.commit()
                return now_str
        except Exception as e:
            logger.error(f"Error logging event to MariaDB: {e}")
        finally:
            conn.close()

    entry = {
        "time": now_str,
        "action": action,
        "user_name": user_name,
        "status": status_str,
        "detail": detail
    }
    with lock:
        events = load_events()
        events.insert(0, entry)
        if len(events) > 200:
            events = events[:200]
        try:
            with open(EVENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return now_str
