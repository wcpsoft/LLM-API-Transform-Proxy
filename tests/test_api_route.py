import os
import pytest
from src.utils import db
from src.utils.init_db_sql import init_db as sql_init_db

def test_api_route_crud():
    if os.path.exists(db.db_path):
        os.remove(db.db_path)
    sql_init_db(db.db_path)
    # 添加
    obj = db.add_api_route(path="/test", method="POST", description="desc", enabled=True)
    assert obj.id is not None
    # 查询
    all_routes = db.list_api_routes()
    assert any(r.path == "/test" for r in all_routes)
    # 更新
    updated = db.update_api_route(obj.id, description="updated")
    assert any(r.id == obj.id and r.description == "updated" for r in updated)
    # 删除
    assert db.delete_api_route(obj.id)
    all_routes = db.list_api_routes()
    assert not any(r.path == "/test" for r in all_routes) 