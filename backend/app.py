from flask import Flask,jsonify,request
import pymysql
from functools import wraps


app=Flask(__name__)

VALID_TOKENS = set()#存token

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


def get_conn():
    return pymysql.connect(host="127.0.0.1",user="root",password="123456",database="my_user_api",charset='utf8mb4',autocommit=True)


@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json()
    if body.get("username") == "admin" and body.get("password") == "123456":
        token = "test_token_123456"
        VALID_TOKENS.add(token)
        return jsonify({"code": 0, "data": {"token": token}})
    return jsonify({"code": 401, "msg": "用户名或密码错误"}), 401



@app.route('/api/users')
@require_token
def list_users():
    conn=get_conn()
    cur=conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("select * from t_user")
    users=cur.fetchall()
    conn.close()
    return jsonify({'code': 0, 'data': users})

@app.route('/api/users/<int:uid>')
@require_token
def get_user(uid):
    conn=get_conn()
    cur=conn.cursor(pymysql.cursors.DictCursor)
    cur.execute('SELECT * FROM t_user WHERE id=%s',(uid,))
    user=cur.fetchone()
    conn.close()
    if not user:
        return jsonify({'code': 404, 'message': 'user not found'}),404
    return jsonify({'code':0, 'data': user})

@app.route('/api/users', methods=['POST'])
@require_token
def create_user():
    body=request.get_json()
    name,email=body.get('name'),body.get('email')
    status=body.get('status',1)
    if not name or not email:
        return jsonify({'code': 400, 'msg': 'name和email必填'}), 400
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO t_user (name, email, status) VALUES (%s,%s,%s)',
                    (name, email, status))
        new_id = cur.lastrowid
        return jsonify({'code': 0, 'data': {'id': new_id}, 'msg': '创建成功'}), 201
    except pymysql.err.IntegrityError as e:
        if e.args[0] == 1062:
            return jsonify({'code': 409, 'msg': '邮箱已被占用'}), 409
        return jsonify({'code': 500, 'msg': '数据库错误'}), 500
    finally:
        conn.close()

@app.route('/api/users/<int:uid>', methods=['PUT'])
@require_token
def update_user(uid):
    body = request.get_json()
    conn = get_conn()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # 先查出当前用户
    cur.execute('SELECT * FROM t_user WHERE id=%s', (uid,))
    user = cur.fetchone()
    if not user:
        conn.close()
        return jsonify({'code': 404, 'msg': '用户不存在'}), 404

    # 用请求体里的字段覆盖，没传的保留原值
    new_name = body.get('name', user['name'])
    new_email = body.get('email', user['email'])
    new_status = body.get('status', user['status'])

    cur.execute('UPDATE t_user SET name=%s, email=%s, status=%s WHERE id=%s',
                (new_name, new_email, new_status, uid))
    conn.close()
    return jsonify({'code': 0, 'msg': '更新成功'})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@require_token
def delete_user(uid):
    conn=get_conn()
    cur=conn.cursor()
    cur.execute('DELETE FROM t_user WHERE id=%s', (uid,))
    affected=cur.rowcount
    conn.close()
    if affected == 0:
        return jsonify({'code': 404, 'msg': '用户不存在'}), 404
    return jsonify({'code': 0, 'msg': '删除成功'})



if __name__ == '__main__':
    app.run(port=5000, debug=True)