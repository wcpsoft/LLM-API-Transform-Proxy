import pytest
from src.utils.exception import ProxyException, exception_handler

def test_proxy_exception():
    with pytest.raises(ProxyException):
        raise ProxyException("test error")

def test_exception_handler_decorator():
    @exception_handler
    def will_fail():
        raise ValueError("fail")
    with pytest.raises(ProxyException) as exc:
        will_fail()
    assert "代理异常" in str(exc.value) 