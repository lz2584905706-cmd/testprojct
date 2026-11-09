# 日志模块（今天新写）

import logging
import os

def get_logger(name="api_test"):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),"logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        fh = logging.FileHandler(os.path.join(log_dir, 'test.log'),encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger

if __name__ == '__main__':
    log=get_logger()
    log.info("test")
