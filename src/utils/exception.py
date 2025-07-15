class ProxyException(Exception):
    """自定义代理异常"""
    pass


def exception_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 这里可以扩展日志记录等
            raise ProxyException(f"代理异常: {e}") from e
    return wrapper 