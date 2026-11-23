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
