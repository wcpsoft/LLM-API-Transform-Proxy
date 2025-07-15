import os
import pytest
from src.utils import db
from src.utils.init_db_sql import init_db as sql_init_db

def test_log_and_query():
    # 清理测试数据库
    if os.path.exists(db.db_path):
        os.remove(db.db_path)
    sql_init_db(db.db_path)
    db.log_api_conversion(
        source_api="anthropic",
        target_api="openai",
        source_model="claude-3-opus-20240229",
        target_model="gpt-4.1",
        source_prompt="思考一下这个问题",
        target_prompt="Please think about this question",
        source_params="{\"temperature\":1.0}",
        target_params="{\"temperature\":0.7}",
        source_response="Claude回答",
        target_response="OpenAI回答"
    )
    logs = db.query_logs(limit=1)
    assert len(logs) == 1
    log = logs[0]
    assert log.source_api == "anthropic"
    assert log.target_api == "openai"
    assert log.source_model == "claude-3-opus-20240229"
    assert log.target_model == "gpt-4.1"
    assert "思考" in log.source_prompt
    assert "think" in log.target_prompt
    assert "Claude" in log.source_response
    assert "OpenAI" in log.target_response 