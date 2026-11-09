import yaml


def read_yaml(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_test_cases(yaml_data, key_name):
    case_list = yaml_data.get(key_name, [])
    id_list = [case.get("case_name", "未命名") for case in case_list]
    return case_list, id_list