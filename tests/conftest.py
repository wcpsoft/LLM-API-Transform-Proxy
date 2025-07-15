import sys
import os
import shutil
import pytest
import yaml

# 自动将项目根目录加入sys.path，确保pytest能import src.xxx
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db', 'api_log_test.duckdb'))
DB_YML_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'db.yml')
DB_YML_BAK = DB_YML_PATH + '.bak'

@pytest.fixture(scope="session", autouse=True)
def init_duckdb():
    # 备份原db.yml
    if os.path.exists(DB_YML_PATH):
        shutil.copyfile(DB_YML_PATH, DB_YML_BAK)
    # 修改db.yml为测试库（绝对路径）
    with open(DB_YML_PATH, 'r', encoding='utf-8') as f:
        conf = yaml.safe_load(f)
    conf['duckdb']['path'] = TEST_DB_PATH
    with open(DB_YML_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(conf, f, allow_unicode=True)
    # 每次测试session前强制删除并重建测试库
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    from src.utils.init_db_sql import init_db as sql_init_db
    sql_init_db(TEST_DB_PATH)
    yield
    # 恢复db.yml
    if os.path.exists(DB_YML_BAK):
        shutil.move(DB_YML_BAK, DB_YML_PATH)
    # 可选：测试结束后删除测试库
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH) 