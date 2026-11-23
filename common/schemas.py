"""
接口响应契约定义中心 (JsonSchema)
用于严格约束后端接口返回的数据结构、必填字段及字段类型，防止契约破坏导致前端崩溃。
"""

# 单个用户详情对象的契约规范
USER_ITEM_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "email", "status"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string", "maxLength": 50},
        "email": {"type": "string"},
        "status": {"type": "integer", "enum": [0, 1]},
    },
    "additionalProperties": True,
}

# 1. 查询单个用户详情接口响应契约 (GET /api/users/<id>)
USER_DETAIL_SCHEMA = {
    "type": "object",
    "required": ["code", "data"],
    "properties": {
        "code": {"type": "integer"},
        "msg": {"type": "string"},
        "data": USER_ITEM_SCHEMA,
    },
    "additionalProperties": False,
}
# 2. 查询用户列表接口响应契约 (GET /api/users)
USER_LIST_SCHEMA = {
    "type": "object",
    "required": ["code", "data"],
    "properties": {
        "code": {"type": "integer"},
        "msg": {"type": "string"},
        "data": {
            "type": "array",
            "items": USER_ITEM_SCHEMA,
        },
    },
    "additionalProperties": False,
}
# 3. 创建用户成功响应契约 (POST /api/users -> 201)
USER_CREATE_SCHEMA = {
    "type": "object",
    "required": ["code", "data", "msg"],
    "properties": {
        "code": {"type": "integer", "enum": [0]},
        "msg": {"type": "string"},
        "data": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "integer"}
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}
# 4. 更新用户成功响应契约 (PUT /api/users/<id> -> 200)
USER_UPDATE_SCHEMA = {
    "type": "object",
    "required": ["code", "msg"],
    "properties": {
        "code": {"type": "integer", "enum": [0]},
        "msg": {"type": "string"},
    },
    "additionalProperties": False,
}
# 5. 删除用户成功响应契约 (DELETE /api/users/<id> -> 200)
USER_DELETE_SCHEMA = {
    "type": "object",
    "required": ["code", "msg"],
    "properties": {
        "code": {"type": "integer", "enum": [0]},
        "msg": {"type": "string"},
    },
    "additionalProperties": False,
}

# 6. 用户登录成功响应契约 (POST /api/login -> 200)
LOGIN_SUCCESS_SCHEMA = {
    "type": "object",
    "required": ["code", "data"],
    "properties": {
        "code": {"type": "integer", "enum": [0]},
        "data": {
            "type": "object",
            "required": ["token"],
            "properties": {
                "token": {"type": "string", "minLength": 1}
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

# 7. 全局统一错误响应契约 (400, 401, 404, 409 等通用错误结构)
ERROR_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["code", "msg"],
    "properties": {
        "code": {"type": "integer"},
        "msg": {"type": "string"},
    },
    "additionalProperties": False,
}
