import logging

def get_logger(name):
    return logging.getLogger(name)

# 默认logger实例
logger = logging.getLogger(__name__)