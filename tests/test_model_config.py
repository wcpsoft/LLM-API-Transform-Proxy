import os
import pytest
from src.utils import db
from src.utils.init_db_sql import init_db as sql_init_db

def test_model_config_crud():
    if os.path.exists(db.db_path):
        os.remove(db.db_path)
    sql_init_db(db.db_path)
    # 添加
    obj = db.add_model_config(route_key="test", target_model="test-model", provider="openai", prompt_keywords="test", description="desc", enabled=True, api_key="testkey")
    assert obj.id is not None
    # 查询
    all_models = db.list_model_configs()
    assert any(m.route_key == "test" for m in all_models)
    # 更新
    updated = db.update_model_config(obj.id, description="updated")
    assert any(m.id == obj.id and m.description == "updated" for m in updated)
    # 删除
    assert db.delete_model_config(obj.id)
    all_models = db.list_model_configs()
    assert not any(m.route_key == "test" for m in all_models) 