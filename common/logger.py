# 日志模块

import logging
import os
from logging.handlers import RotatingFileHandler


def get_logger(name="api_test"):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # 日志轮转：单文件最大 5MB，保留 3 个备份，避免 test.log 无限增长
    fh = RotatingFileHandler(
        os.path.join(log_dir, 'test.log'),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


if __name__ == '__main__':
    log = get_logger()
    log.info("test")
