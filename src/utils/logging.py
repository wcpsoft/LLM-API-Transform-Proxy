import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_file_logging():
    """设置文件日志记录"""
    # 创建logs目录
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建文件处理器（按大小轮转）
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'claude-proxy.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # 创建每日日志文件处理器
    daily_log_file = os.path.join(logs_dir, f'claude-proxy-{datetime.now().strftime("%Y-%m-%d")}.log')
    daily_handler = logging.FileHandler(daily_log_file)
    daily_handler.setFormatter(formatter)
    daily_handler.setLevel(logging.INFO)
    
    # 获取根logger并添加处理器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)
    if not any(isinstance(h, logging.FileHandler) and 'claude-proxy-' in h.baseFilename for h in root_logger.handlers):
        root_logger.addHandler(daily_handler)
    
    return root_logger

def get_logger(name):
    """获取logger实例"""
    return logging.getLogger(name)

def log_api_request(source_api: str, target_api: str, request_data: dict, response_data: dict = None, 
                   status_code: int = 200, error_message: str = None, processing_time: float = 0):
    """记录API请求到文件"""
    api_logger = get_logger('api_requests')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'source_api': source_api,
        'target_api': target_api,
        'status_code': status_code,
        'processing_time': processing_time,
        'request_size': len(str(request_data)) if request_data else 0,
        'response_size': len(str(response_data)) if response_data else 0
    }
    
    if error_message:
        log_entry['error'] = error_message
        api_logger.error(f"API请求失败: {log_entry}")
    else:
        api_logger.info(f"API请求成功: {log_entry}")

# 初始化文件日志
setup_file_logging()

# 默认logger实例
logger = logging.getLogger(__name__)