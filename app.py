"""
ระบบควบคุมเปิดไม้กั้น HIP WIEGAND W.G. 1002 TCP/IP
- สำหรับเจ้าหน้าที่ที่ได้รับอนุมัติเท่านั้น (Authorized Staff)
- เข้าใช้งานผ่านมือถือได้สะดวก รวดเร็ว (One-touch / Token / PIN / Device Binding)
- มีระบบผู้ดูแลระบบ (Admin) สำหรับอนุมัติ/ระงับสิทธิ์ และสร้าง QR Code / Direct Link
"""

import socket
import struct
import logging
import threading
import datetime
import os
import uuid
import io
import base64
import qrcode
from flask import Flask, render_template, jsonify, request, session
from config import Config
import db

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Initialize Database (MariaDB with JSON fallback)
db.init_db()

# Controller Configuration — WG-1002
CONTROLLER_CONFIG = {
    "serial_number": Config.CONTROLLER_SN,
    "ip_address":    Config.CONTROLLER_IP,
    "port":          Config.CONTROLLER_PORT,
    "timeout":       5,
}

ADMIN_PASSWORD = Config.ADMIN_PASSWORD
lock = threading.Lock()

# UHPPOTE Protocol Constants
MSG_TYPE   = 0x17
CMD_OPEN   = 0x40
CMD_STATUS = 0x20
PACKET_LEN = 64

def _build_packet(command: int, payload: bytes = b"") -> bytes:
    sn_bytes = struct.pack("<I", CONTROLLER_CONFIG["serial_number"])
    header   = bytes([MSG_TYPE, command, 0x00, 0x00]) + sn_bytes
    body     = header + payload
    return (body + bytes(PACKET_LEN - len(body)))[:PACKET_LEN]

def _send_udp(packet: bytes) -> bytes | None:
    ip, port, tout = (CONTROLLER_CONFIG["ip_address"],
                      CONTROLLER_CONFIG["port"],
                      CONTROLLER_CONFIG["timeout"])
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(tout)
            s.sendto(packet, (ip, port))
            logger.info(f"-> Sent to {ip}:{port}  [{packet[:16].hex(' ')} ...]")
            resp, addr = s.recvfrom(1024)
            logger.info(f"<- Recv from {addr}  [{resp[:16].hex(' ')} ...]")
            return resp
    except socket.timeout:
        logger.warning("Timeout: no response from WG-1002")
        return None
    except OSError as e:
        logger.error(f"Network error: {e}")
        return None

def trigger_open_relay():
    """ส่งคำสั่งเปิดไปยัง WG-1002 (Door 1 relay)"""
    payload = bytes([0x01])  # Door 1
    resp = _send_udp(_build_packet(CMD_OPEN, payload))
    if resp is not None and len(resp) >= 9:
        result_byte = resp[8]
        success = (result_byte == 0x01)
        msg = "ส่งสัญญาณเปิดไม้กั้นสำเร็จ ✅" if success else f"Controller ตอบกลับ (code={result_byte:#04x})"
        return success, msg
    elif resp is None:
        return False, "Timeout: ไม่ได้รับสัญญาณตอบกลับจากบอร์ด WG-1002"
    else:
        return False, "Response จาก Controller ไม่ถูกต้อง"

def get_best_host_ip():
    """หา IP Address สำหรับให้มือถือเข้าใช้งาน"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((CONTROLLER_CONFIG["ip_address"], CONTROLLER_CONFIG["port"]))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "13.0.0.172"

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('LOGO_MTH_TOP.png')

# ============================================================
# Routes: หน้าหลักสำหรับเจ้าหน้าที่ (Mobile First)
# ============================================================
@app.route("/")
def index():
    token = request.args.get("token")
    user = None
    if token:
        user = db.find_user_by_token(token)
        if user:
            session["user_token"] = token

    token_in_session = session.get("user_token")
    if not user and token_in_session:
        user = db.find_user_by_token(token_in_session)

    host_ip = get_best_host_ip()
    return render_template("index.html", user=user, host_ip=host_ip)

@app.route("/api/verify_pin", methods=["POST"])
def api_verify_pin():
    data = request.get_json(silent=True) or {}
    pin = data.get("pin", "").strip()
    bound_token = data.get("bound_token") or data.get("token")
    
    success, user, message = db.verify_pin_for_bound_device(pin, bound_token)
    if not success or not user:
        return jsonify({"success": False, "message": message}), 401 if "ไม่ถูกต้อง" in message else 403

    session["user_token"] = user["token"]
    return jsonify({
        "success": True,
        "message": message,
        "user": {
            "name": user["name"],
            "role": user["role"],
            "token": user["token"]
        }
    })

@app.route("/api/open", methods=["POST"])
def api_open():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or session.get("user_token")

    if not token:
        return jsonify({"success": False, "message": "ไม่พบสิทธิ์การใช้งาน (Unauthorized)"}), 401

    user = db.find_user_by_token(token)
    if not user:
        return jsonify({"success": False, "message": "ไม่พบข้อมูลผู้ใช้งาน หรือสิทธิ์หมดอายุ"}), 401

    if user.get("status") != "active":
        db.log_event("พยายามเปิดไม้กั้น", user["name"], False, "สิทธิ์ถูกระงับ (Account blocked)", user.get("id"))
        return jsonify({"success": False, "message": "สิทธิ์การใช้งานของคุณถูกระงับ (Blocked)"}), 403

    # ส่งสัญญาณเปิดไม้กั้น
    success, msg = trigger_open_relay()

    # อัปเดตเวลาใช้งานล่าสุด
    db.update_user_last_used(user["id"])
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.log_event("เปิดไม้กั้น", user["name"], success, msg, user.get("id"))
    return jsonify({
        "success": success,
        "message": msg,
        "user_name": user["name"],
        "timestamp": now_str
    })

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("user_token", None)
    return jsonify({"success": True})

# ============================================================
# Routes: หน้า Admin (จัดการเจ้าหน้าที่ & ลิงก์เข้าใช้งาน)
# ============================================================
@app.route("/admin")
def admin_page():
    is_logged = session.get("is_admin", False)
    base_url = request.host_url.rstrip("/")
    return render_template("admin.html", is_logged=is_logged, base_url=base_url)

@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    if password == ADMIN_PASSWORD:
        session["is_admin"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "รหัสผ่านผู้ดูแลระบบไม่ถูกต้อง"}), 401

@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.pop("is_admin", None)
    return jsonify({"success": True})

@app.route("/api/admin/users", methods=["GET"])
def api_admin_users_get():
    if not session.get("is_admin"):
        return jsonify({"success": False, "message": "ต้องเข้าสู่ระบบแอดมินก่อน"}), 401
    return jsonify(db.load_users())

@app.route("/api/admin/users", methods=["POST"])
def api_admin_users_add():
    if not session.get("is_admin"):
        return jsonify({"success": False, "message": "ต้องเข้าสู่ระบบแอดมินก่อน"}), 401

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    role = data.get("role", "เจ้าหน้าที่รักษาความปลอดภัย").strip()
    pin  = data.get("pin", "").strip()

    if not name:
        return jsonify({"success": False, "message": "กรุณาระบุชื่อเจ้าหน้าที่"}), 400

    if pin:
        if not pin.isdigit():
            return jsonify({"success": False, "message": "รหัส PIN ต้องเป็นตัวเลขเท่านั้น"}), 400
        if len(pin) != 6:
            return jsonify({"success": False, "message": "รหัส PIN ต้องมี 6 หลักพอดี (ห้ามเกินหรือขาด)"}), 400
    else:
        pin = f"{uuid.uuid4().int % 900000 + 100000}"

    new_user = db.add_user(name, role, pin)
    return jsonify({"success": True, "user": new_user})

@app.route("/api/admin/users/<user_id>", methods=["PUT"])
def api_admin_user_update(user_id):
    if not session.get("is_admin"):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    role = data.get("role", "").strip()
    pin  = data.get("pin", "").strip()

    if not name:
        return jsonify({"success": False, "message": "กรุณาระบุชื่อเจ้าหน้าที่"}), 400

    if pin:
        if not pin.isdigit():
            return jsonify({"success": False, "message": "รหัส PIN ต้องเป็นตัวเลขเท่านั้น"}), 400
        if len(pin) != 6:
            return jsonify({"success": False, "message": "รหัส PIN ต้องมี 6 หลักพอดี (ห้ามเกินหรือขาด)"}), 400

    ok = db.update_user_details(user_id, name, role, pin)
    if ok:
        return jsonify({"success": True, "message": "อัปเดตข้อมูลสำเร็จ"})
    return jsonify({"success": False, "message": "ไม่พบผู้ใช้นี้ในระบบ"}), 404

@app.route("/api/admin/users/<user_id>/toggle", methods=["POST"])
def api_admin_user_toggle(user_id):
    if not session.get("is_admin"):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    ok = db.toggle_user_status(user_id)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "User not found"}), 404

@app.route("/api/admin/users/<user_id>", methods=["DELETE"])
def api_admin_user_delete(user_id):
    if not session.get("is_admin"):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    ok = db.suspend_user(user_id)
    if ok:
        return jsonify({"success": True, "message": "ระงับสิทธิ์เจ้าหน้าที่เรียบร้อยแล้ว (ไม่ลบออกจาก Log)"})
    return jsonify({"success": False, "message": "ไม่พบผู้ใช้ในระบบ"}), 404

@app.route("/api/admin/qrcode/<token>")
def api_admin_qrcode(token):
    base_url = request.host_url.rstrip("/")
    target_url = f"{base_url}/?token={token}"

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    return jsonify({"qrcode": f"data:image/png;base64,{img_b64}", "url": target_url})

@app.route("/api/events")
def api_events():
    return jsonify(db.load_events())

@app.route("/api/status")
def api_status():
    packet = _build_packet(CMD_STATUS)
    resp = _send_udp(packet)
    online = (resp is not None and len(resp) >= 64)
    return jsonify({"online": online})

if __name__ == "__main__":
    host_ip = get_best_host_ip()
    print("=" * 65)
    print("  ระบบเปิดไม้กั้น HIP WIEGAND W.G. 1002 (สำหรับเจ้าหน้าที่)")
    print(f"  Controller IP : {CONTROLLER_CONFIG['ip_address']}:{CONTROLLER_CONFIG['port']}")
    print(f"  Mobile Web    : http://{host_ip}:5000")
    print(f"  Admin Web     : http://{host_ip}:5000/admin")
    print("=" * 65)
    app.run(host="0.0.0.0", port=5000, debug=True)
