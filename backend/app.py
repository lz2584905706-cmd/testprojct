import os
from flask import Flask, jsonify, request
import pymysql
from functools import wraps


app = Flask(__name__)

VALID_TOKENS = set()  # 存token

NAME_MAX = 50      # 与建表语句 VARCHAR(50) 保持一致
EMAIL_MAX = 100    # 与建表语句 VARCHAR(100) 保持一致


def require_token(f):          # f 是被装饰的那个接口函数（比如 get_users）
    @wraps(f)                  # 保持原函数名字不变
    def decorated(*args, **kwargs):   # 新函数，先做检查；*args, **kwargs让函数接收任意数量的参数，不用管被装饰的函数要几个参数。
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        # 从请求头拿 Authorization 字段，去掉 "Bearer " 前缀，得到纯 token

        if token not in VALID_TOKENS:
            # token 不在有效列表里 → 拒绝
            return jsonify({"code": 401, "msg": "未登录或token失效"}), 401

        # token 对 → 放行，执行真正的接口函数
        return f(*args, **kwargs)
    return decorated


DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_NAME = os.getenv("DB_NAME", "my_user_api")


def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        autocommit=True,
    )


def bad_request(msg):
    """400 参数校验失败的统一响应"""
    return jsonify({"code": 400, "msg": msg}), 400


def check_email_format(email):
    """只做最基本的格式检查：必须有 @，且 @ 后面带点"""
    return "@" in email and "." in email.split("@")[-1]


@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    if body.get("username") == "admin" and body.get("password") == "123456":
        token = "test_token_123456"
        VALID_TOKENS.add(token)
        return jsonify({"code": 0, "data": {"token": token}})
    return jsonify({"code": 401, "msg": "用户名或密码错误"}), 401


@app.route("/api/users")
@require_token
def list_users():
    conn = get_conn()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("select * from t_user")
        users = cur.fetchall()
        return jsonify({"code": 0, "data": users})
    finally:
        conn.close()


@app.route("/api/users/<int:uid>")
@require_token
def get_user(uid):
    conn = get_conn()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT * FROM t_user WHERE id=%s", (uid,))
        user = cur.fetchone()
        if not user:
            return jsonify({"code": 404, "msg": "用户不存在"}), 404
        return jsonify({"code": 0, "data": user})
    finally:
        conn.close()


@app.route("/api/users", methods=["POST"])
@require_token
def create_user():
    body = request.get_json(silent=True) or {}
    name, email = body.get("name"), body.get("email")
    status = body.get("status", 1)

    # ---- 参数校验 ----
    if not name or not email:
        return bad_request("name和email必填")
    if not isinstance(name, str) or len(name) > NAME_MAX:
        return bad_request("name长度不能超过%d" % NAME_MAX)
    if not isinstance(email, str) or len(email) > EMAIL_MAX:
        return bad_request("email长度不能超过%d" % EMAIL_MAX)
    if not check_email_format(email):
        return bad_request("email格式不正确")
    if status not in (0, 1):
        return bad_request("status只能是0或1")

    conn = get_conn()
    try:
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO t_user (name, email, status) VALUES (%s,%s,%s)",
                        (name, email, status))
            new_id = cur.lastrowid
            return jsonify({"code": 0, "data": {"id": new_id}, "msg": "创建成功"}), 201
        except pymysql.err.IntegrityError as e:
            if e.args[0] == 1062:
                return jsonify({"code": 409, "msg": "邮箱已被占用"}), 409
            return jsonify({"code": 500, "msg": "数据库错误"}), 500
    finally:
        conn.close()


@app.route("/api/users/<int:uid>", methods=["PUT"])
@require_token
def update_user(uid):
    body = request.get_json(silent=True) or {}

    conn = get_conn()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 先查出当前用户，不存在直接 404
        cur.execute("SELECT * FROM t_user WHERE id=%s", (uid,))
        user = cur.fetchone()
        if not user:
            return jsonify({"code": 404, "msg": "用户不存在"}), 404

        # 用请求体里的字段覆盖，没传的保留原值
        new_name = body.get("name", user["name"])
        new_email = body.get("email", user["email"])
        new_status = body.get("status", user["status"])

        # ---- 只校验本次传了的字段，没传的不动 ----
        if "name" in body:
            if not isinstance(new_name, str) or not new_name or len(new_name) > NAME_MAX:
                return bad_request("name不能为空且长度不能超过%d" % NAME_MAX)
        if "email" in body:
            if not isinstance(new_email, str) or not new_email or len(new_email) > EMAIL_MAX:
                return bad_request("email不能为空且长度不能超过%d" % EMAIL_MAX)
            if not check_email_format(new_email):
                return bad_request("email格式不正确")
        if "status" in body and new_status not in (0, 1):
            return bad_request("status只能是0或1")

        try:
            cur.execute("UPDATE t_user SET name=%s, email=%s, status=%s WHERE id=%s",
                        (new_name, new_email, new_status, uid))
        except pymysql.err.IntegrityError as e:
            # 改成已存在的邮箱：语义上是资源冲突，应该返回 409 而不是 500
            if e.args[0] == 1062:
                return jsonify({"code": 409, "msg": "邮箱已被占用"}), 409
            return jsonify({"code": 500, "msg": "数据库错误"}), 500

        return jsonify({"code": 0, "msg": "更新成功"})
    finally:
        conn.close()


@app.route("/api/users/<int:uid>", methods=["DELETE"])
@require_token
def delete_user(uid):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM t_user WHERE id=%s", (uid,))
        affected = cur.rowcount
        if affected == 0:
            return jsonify({"code": 404, "msg": "用户不存在"}), 404
        return jsonify({"code": 0, "msg": "删除成功"})
    finally:
        conn.close()


if __name__ == "__main__":
    # 安全规范：debug 模式由环境变量控制，默认 False，防止公网/容器环境下 Werkzeug 调试器被利用执行任意代码 (RCE)
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
