import os
import pytest
from src.utils import db
from src.utils.init_db_sql import init_db as sql_init_db

def test_log_api_conversion():
    # 清理测试数据库
    if os.path.exists(db.db_path):
        os.remove(db.db_path)
    sql_init_db(db.db_path)
    # 写入日志
    db.log_api_conversion(
        source_api="testsrc",
        target_api="testtgt",
        source_model="m1",
        target_model="m2",
        source_prompt="prompt",
        target_prompt="prompt2",
        source_params="{}",
        target_params="{}",
        source_response="resp1",
        target_response="resp2",
        headers={"User-Agent": "pytest"}
    )
    logs = db.query_logs(limit=1)
    assert len(logs) == 1
    log = logs[0]
    assert log.source_api == "testsrc"
    assert log.target_api == "testtgt"
    assert log.source_model == "m1"
    assert log.target_model == "m2"
    assert "prompt" in log.source_prompt
    assert "prompt2" in log.target_prompt
    assert "resp1" in log.source_response
    assert "resp2" in log.target_response 