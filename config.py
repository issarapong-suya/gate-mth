import os

class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "mth-gate-production-secret-2026")
    ADMIN_PASSWORD = os.environ.get("GATE_ADMIN_PASS", "admin1234")
    
    # MariaDB / MySQL Configuration
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "mth_gate")
    USE_MARIADB = os.environ.get("USE_MARIADB", "true").lower() # 'true', 'auto', or 'false'

    # HIP WG-1002 Controller Config
    CONTROLLER_SN = int(os.environ.get("CONTROLLER_SN", 123341266))
    CONTROLLER_IP = os.environ.get("CONTROLLER_IP", "13.0.0.4")
    CONTROLLER_PORT = int(os.environ.get("CONTROLLER_PORT", 60000))
