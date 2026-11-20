import os
import yaml


def read_yaml(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"YAML 文件不存在: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"YAML 文件内容为空: {file_path}")
    return data


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
