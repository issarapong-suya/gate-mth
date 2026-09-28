"""
MTH GATE - Database Access Layer
Supports MariaDB and SQLite Relational Databases.
No JSON files are used for operations once migrated.
"""

import os
import json
import logging
import datetime
import uuid
import sqlite3
from config import Config

logger = logging.getLogger(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), "mth_gate.db")
USERS_JSON = os.path.join(os.path.dirname(__file__), "users.json")
DEVICES_JSON = os.path.join(os.path.dirname(__file__), "user_devices.json")
EVENTS_JSON = os.path.join(os.path.dirname(__file__), "events.json")


_active_engine = None

def get_db_connection():
    """Returns a database connection and engine type ('mariadb' or 'sqlite')."""
    global _active_engine

    if _active_engine == "sqlite":
        import sqlite3
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

    if Config.USE_MARIADB == "true":
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
                connect_timeout=1
            )
            _active_engine = "mariadb"
            return conn, "mariadb"
        except Exception as e:
            logger.warning(f"MariaDB connection failed ({e}), switching to SQLite database ({DB_FILE}).")

    _active_engine = "sqlite"
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def execute_sql(sql, params=(), fetch_all=False, fetch_one=False):
    """Executes SQL query on the active database engine (MariaDB or SQLite)."""
    conn, db_type = get_db_connection()
    try:
        if db_type == "sqlite":
            sql = sql.replace("%s", "?")

        if db_type == "mariadb":
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                conn.commit()
                if fetch_all:
                    return cursor.fetchall()
                if fetch_one:
                    return cursor.fetchone()
                return cursor.lastrowid
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                if fetch_all:
                    return [dict(row) for row in cursor.fetchall()]
                if fetch_one:
                    row = cursor.fetchone()
                    return dict(row) if row else None
                return cursor.lastrowid
    except Exception as e:
        logger.error(f"SQL Error ({db_type}): {e} | Query: {sql}")
        raise e
    finally:
        conn.close()


def init_db():
    """Initializes SQL database tables and migrates any existing legacy JSON records."""
    conn, db_type = get_db_connection()
    try:
        if db_type == "mariadb":
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
                      `max_devices` INT DEFAULT 1,
                      `created_at` VARCHAR(50) DEFAULT NULL,
                      `updated_at` VARCHAR(50) DEFAULT NULL,
                      `last_used` VARCHAR(50) DEFAULT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS `user_devices` (
                      `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                      `user_id` VARCHAR(64) NOT NULL,
                      `device_id` VARCHAR(255) NOT NULL,
                      `device_name` VARCHAR(255) DEFAULT 'อุปกรณ์มือถือ',
                      `status` VARCHAR(20) DEFAULT 'active',
                      `registered_at` VARCHAR(50) DEFAULT NULL,
                      `last_used` VARCHAR(50) DEFAULT NULL,
                      UNIQUE KEY `user_device_unique` (`user_id`, `device_id`)
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
        else:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                      id TEXT NOT NULL PRIMARY KEY,
                      name TEXT NOT NULL,
                      role TEXT DEFAULT 'เจ้าหน้าที่รักษาความปลอดภัย',
                      pin TEXT NOT NULL,
                      token TEXT NOT NULL UNIQUE,
                      status TEXT DEFAULT 'active',
                      device_id TEXT DEFAULT NULL,
                      max_devices INTEGER DEFAULT 1,
                      created_at TEXT DEFAULT NULL,
                      updated_at TEXT DEFAULT NULL,
                      last_used TEXT DEFAULT NULL
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_devices (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT NOT NULL,
                      device_id TEXT NOT NULL,
                      device_name TEXT DEFAULT 'อุปกรณ์มือถือ',
                      status TEXT DEFAULT 'active',
                      registered_at TEXT DEFAULT NULL,
                      last_used TEXT DEFAULT NULL,
                      UNIQUE(user_id, device_id)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      time TEXT NOT NULL,
                      user_name TEXT NOT NULL,
                      action TEXT NOT NULL,
                      status TEXT NOT NULL,
                      detail TEXT DEFAULT NULL,
                      user_id TEXT DEFAULT NULL
                    );
                """)

        logger.info(f"Database ({db_type}) tables initialized successfully.")
        migrate_json_files_if_needed()
    except Exception as e:
        logger.error(f"Error initializing DB tables: {e}")
    finally:
        conn.close()


def migrate_json_files_if_needed():
    """Migrates legacy records from JSON files into the Database if not already present."""
    # 1. Migrate Users
    if os.path.exists(USERS_JSON):
        try:
            with open(USERS_JSON, "r", encoding="utf-8") as f:
                users_data = json.load(f)
            for u in users_data:
                existing = execute_sql("SELECT id FROM users WHERE id=%s", (u["id"],), fetch_one=True)
                if not existing:
                    sql = """
                        INSERT INTO users (id, name, role, pin, token, status, max_devices, created_at, updated_at, last_used)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    execute_sql(sql, (
                        u["id"], u["name"], u.get("role", "เจ้าหน้าที่รักษาความปลอดภัย"),
                        u["pin"], u["token"], u.get("status", "active"),
                        u.get("max_devices", 1), u.get("created_at"),
                        u.get("updated_at"), u.get("last_used")
                    ))
            logger.info("Migrated users.json to database successfully.")
        except Exception as e:
            logger.error(f"Error migrating users.json: {e}")

    # 2. Migrate User Devices
    if os.path.exists(DEVICES_JSON):
        try:
            with open(DEVICES_JSON, "r", encoding="utf-8") as f:
                devs_data = json.load(f)
            for d in devs_data:
                existing = execute_sql("SELECT id FROM user_devices WHERE user_id=%s AND device_id=%s", (d["user_id"], d["device_id"]), fetch_one=True)
                if not existing:
                    sql = """
                        INSERT INTO user_devices (user_id, device_id, device_name, status, registered_at, last_used)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    execute_sql(sql, (
                        d["user_id"], d["device_id"], d.get("device_name", "อุปกรณ์มือถือ"),
                        d.get("status", "active"), d.get("registered_at"), d.get("last_used")
                    ))
            logger.info("Migrated user_devices.json to database successfully.")
        except Exception as e:
            logger.error(f"Error migrating user_devices.json: {e}")

    # 3. Migrate Events
    if os.path.exists(EVENTS_JSON):
        try:
            with open(EVENTS_JSON, "r", encoding="utf-8") as f:
                events_data = json.load(f)
            for ev in events_data:
                existing = execute_sql("SELECT id FROM events WHERE time=%s AND user_name=%s AND action=%s", (ev["time"], ev["user_name"], ev["action"]), fetch_one=True)
                if not existing:
                    sql = """
                        INSERT INTO events (time, user_name, action, status, detail, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    execute_sql(sql, (
                        ev["time"], ev["user_name"], ev["action"],
                        ev["status"], ev.get("detail", ""), ev.get("user_id")
                    ))
            logger.info("Migrated events.json to database successfully.")
        except Exception as e:
            logger.error(f"Error migrating events.json: {e}")


# --- Staff / User Operations ---

def load_users():
    return execute_sql("SELECT * FROM users ORDER BY created_at ASC", fetch_all=True) or []


def add_user(name, role="เจ้าหน้าที่รักษาความปลอดภัย", pin=None, max_devices=1):
    user_id = f"u-{uuid.uuid4().hex[:8]}"
    token   = f"gate-{uuid.uuid4().hex[:12]}"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not pin or not str(pin).isdigit() or len(str(pin)) != 6:
        pin = f"{uuid.uuid4().int % 900000 + 100000}"
    else:
        pin = str(pin).strip()

    max_devs = int(max_devices) if max_devices is not None else 1

    new_user = {
        "id": user_id,
        "name": name,
        "role": role or "เจ้าหน้าที่รักษาความปลอดภัย",
        "pin": pin,
        "token": token,
        "status": "active",
        "max_devices": max_devs,
        "created_at": now_str,
        "updated_at": now_str,
        "last_used": None
    }

    sql = """
        INSERT INTO users (id, name, role, pin, token, status, max_devices, created_at, updated_at, last_used)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute_sql(sql, (user_id, name, new_user["role"], pin, token, "active", max_devs, now_str, now_str, None))
    return new_user


def update_user_last_used(user_id):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_sql("UPDATE users SET last_used=%s WHERE id=%s", (now_str, user_id))


def update_user_details(user_id, name, role, pin, max_devices=None):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if max_devices is not None:
        sql = "UPDATE users SET name=%s, role=%s, pin=%s, max_devices=%s, updated_at=%s WHERE id=%s"
        execute_sql(sql, (name, role, str(pin).strip(), int(max_devices), now_str, user_id))
    else:
        sql = "UPDATE users SET name=%s, role=%s, pin=%s, updated_at=%s WHERE id=%s"
        execute_sql(sql, (name, role, str(pin).strip(), now_str, user_id))
    return True


def suspend_user(user_id):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_sql("UPDATE users SET status='suspended', updated_at=%s WHERE id=%s", (now_str, user_id))
    return True


def toggle_user_status(user_id):
    user = execute_sql("SELECT status FROM users WHERE id=%s", (user_id,), fetch_one=True)
    if not user:
        return False
    current_status = user.get("status", "active")
    next_status = "active" if current_status != "active" else "suspended"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_sql("UPDATE users SET status=%s, updated_at=%s WHERE id=%s", (next_status, now_str, user_id))
    return True


def find_user_by_token(token):
    if not token:
        return None
    return execute_sql("SELECT * FROM users WHERE token=%s", (token,), fetch_one=True)


def find_user_by_pin(pin):
    if not pin:
        return None
    return execute_sql("SELECT * FROM users WHERE pin=%s", (str(pin).strip(),), fetch_one=True)


# --- User Devices Management ---

def load_user_devices(user_id):
    return execute_sql("SELECT * FROM user_devices WHERE user_id=%s AND status='active' ORDER BY registered_at DESC", (user_id,), fetch_all=True) or []


def register_or_verify_device(user_id, device_id, device_name="อุปกรณ์มือถือ"):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = execute_sql("SELECT * FROM users WHERE id=%s", (user_id,), fetch_one=True)
    if not user:
        return False, "ไม่พบข้อมูลผู้ใช้งาน"

    max_devs = int(user.get("max_devices") or 1)
    if not device_id:
        device_id = f"dev-fallback-{user_id[:8]}"

    active_devs = load_user_devices(user_id)
    existing_dev = next((d for d in active_devs if d.get("device_id") == device_id), None)

    if existing_dev:
        execute_sql("UPDATE user_devices SET last_used=%s, device_name=%s WHERE user_id=%s AND device_id=%s", (now_str, device_name, user_id, device_id))
        return True, "ยืนยันอุปกรณ์เรียบร้อย"

    if len(active_devs) >= max_devs:
        return False, f"อุปกรณ์นี้ยังไม่ได้รับอนุมัติใช้งาน (จำกัดสูงสุด {max_devs} เครื่อง) กรุณาติดต่อผู้ดูแลระบบเพื่อจัดการอุปกรณ์"

    revoked_dev = execute_sql("SELECT * FROM user_devices WHERE user_id=%s AND device_id=%s", (user_id, device_id), fetch_one=True)
    if revoked_dev:
        execute_sql("UPDATE user_devices SET status='active', last_used=%s, device_name=%s WHERE user_id=%s AND device_id=%s", (now_str, device_name, user_id, device_id))
    else:
        execute_sql("INSERT INTO user_devices (user_id, device_id, device_name, status, registered_at, last_used) VALUES (%s, %s, %s, %s, %s, %s)", (user_id, device_id, device_name, "active", now_str, now_str))
    return True, "ลงทะเบียนอุปกรณ์ใหม่เรียบร้อยแล้ว"


def update_user_max_devices(user_id, max_devices):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    max_devs = int(max_devices) if int(max_devices) >= 1 else 1
    execute_sql("UPDATE users SET max_devices=%s, updated_at=%s WHERE id=%s", (max_devs, now_str, user_id))
    return True


def revoke_user_device(user_id, device_id):
    execute_sql("UPDATE user_devices SET status='revoked' WHERE user_id=%s AND device_id=%s", (user_id, device_id))
    return True


def verify_pin_for_bound_device(pin, bound_token=None, device_id=None, device_name="อุปกรณ์มือถือ"):
    pin_str = str(pin).strip()
    if not bound_token:
        return False, None, "อุปกรณ์นี้ยังไม่ได้ผูกสิทธิ์ กรุณาสแกน QR Code หรือเปิดผ่านลิงก์ส่วนตัวเพื่อลงทะเบียนก่อน"

    user = find_user_by_token(bound_token)
    if not user:
        return False, None, "สิทธิ์การใช้งานของคุณไม่สมบูรณ์ กรุณาสแกน QR Code เพื่อเปิดใช้งานใหม่"

    if user.get("pin") != pin_str:
        return False, None, "รหัส PIN ไม่ถูกต้องสำหรับผู้ใช้งานเครื่องนี้"

    if user.get("status") != "active":
        return False, None, "สิทธิ์การใช้งานของคุณถูกระงับ กรุณาติดต่อผู้ดูแลระบบ"

    allowed, dev_msg = register_or_verify_device(user["id"], device_id, device_name)
    if not allowed:
        return False, None, dev_msg

    return True, user, "ยืนยันรหัส PIN สำเร็จ"


# --- Events / Audit Logs ---

def load_events():
    return execute_sql("SELECT time, action, user_name, status, detail FROM events ORDER BY id DESC LIMIT 200", fetch_all=True) or []


def log_event(action: str, user_name: str, success: bool, detail: str, user_id: str = None):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_str = "สำเร็จ" if success else "ผิดพลาด"
    execute_sql(
        "INSERT INTO events (time, user_name, action, status, detail, user_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (now_str, user_name, action, status_str, detail, user_id)
    )
    return now_str
