import os
import re
import yaml
from common.data_faker import DYNAMIC_FUNCTIONS


def resolve_dynamic_placeholders(data):

    exact_pattern = re.compile(r"^\$\{(\w+)\(\)}$")
    inline_pattern = re.compile(r"\$\{(\w+)\(\)}")

    if isinstance(data, dict):
        return {k: resolve_dynamic_placeholders(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [resolve_dynamic_placeholders(item) for item in data]
    elif isinstance(data, str):
        # 场景 1：完全匹配单一占位符（如 "${random_name()}"），保持原始生成数据类型
        exact_match = exact_pattern.match(data)
        if exact_match:
            func_name = exact_match.group(1)
            if func_name in DYNAMIC_FUNCTIONS:
                return DYNAMIC_FUNCTIONS[func_name]()
            return data

        # 场景 2：嵌入在较长文本里的占位符（如 "prefix_${random_name()}_suffix"）
        def _replacer(match):
            matched_func = match.group(1)
            if matched_func in DYNAMIC_FUNCTIONS:
                return str(DYNAMIC_FUNCTIONS[matched_func]())
            return match.group(0)

        return inline_pattern.sub(_replacer, data)

    return data


def read_yaml(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"YAML 文件不存在: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"YAML 文件内容为空: {file_path}")

    # 动态参数化引擎：在解析后的安全数据结构中递归求值替换
    return resolve_dynamic_placeholders(data)


def get_test_cases(yaml_data, key_name):
    if not isinstance(yaml_data, dict):
        raise TypeError(f"yaml_data 必须是字典类型，实际收到: {type(yaml_data)}")

    if key_name not in yaml_data:
        available_keys = list(yaml_data.keys())
        raise KeyError(
            f"YAML 数据中未找到键名 [{key_name}]！可用的键名有: {available_keys}，请检查是否拼写错误。"
        )

    case_list = yaml_data[key_name]
    if not case_list:
        raise ValueError(f"YAML 中键名 [{key_name}] 对应的用例列表为空，请检查测试数据！")

    id_list = [case.get("case_name", f"case_{i}") for i, case in enumerate(case_list)]
    return case_list, id_list
