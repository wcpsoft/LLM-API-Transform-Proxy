import duckdb
import os

# 建表SQL语句列表
create_tables_sql = [
    '''
    CREATE TABLE IF NOT EXISTS system_config (
        id BIGINT,
        config_key VARCHAR NOT NULL UNIQUE,
        config_value VARCHAR,
        config_type VARCHAR DEFAULT 'string',
        description VARCHAR,
        is_sensitive BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS apirequestlog (
        id BIGINT,
        timestamp TIMESTAMP,
        source_api VARCHAR,
        target_api VARCHAR,
        source_model VARCHAR,
        target_model VARCHAR,
        source_prompt VARCHAR,
        target_prompt VARCHAR,
        source_params VARCHAR,
        target_params VARCHAR,
        source_response VARCHAR,
        target_response VARCHAR,
        headers VARCHAR
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS modelconfig (
        id BIGINT,
        route_key VARCHAR,
        target_model VARCHAR,
        provider VARCHAR,
        prompt_keywords VARCHAR,
        description VARCHAR,
        enabled BOOLEAN,
        api_key VARCHAR,
        api_base VARCHAR,
        auth_header VARCHAR,
        auth_format VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS apiroute (
        id BIGINT,
        path VARCHAR,
        method VARCHAR,
        description VARCHAR,
        enabled BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS api_key_pool (
        id BIGINT,
        provider VARCHAR NOT NULL,
        api_key VARCHAR NOT NULL,
        auth_header VARCHAR DEFAULT 'Authorization',
        auth_format VARCHAR DEFAULT 'Bearer {key}',
        is_active BOOLEAN DEFAULT TRUE,
        requests_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        last_used_at TIMESTAMP,
        rate_limit_reset_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider, api_key)
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS api_key_stats (
        id BIGINT,
        provider VARCHAR NOT NULL,
        api_key VARCHAR NOT NULL,
        date DATE NOT NULL,
        requests_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        status_codes VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider, api_key, date)
    );
    '''
]

def init_db(db_path=None):
    if db_path is None:
        db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'db', 'api_log.duckdb'))
    else:
        db_path = os.path.abspath(db_path)
    print("DuckDB init path:", db_path)
    con = duckdb.connect(db_path)
    con.execute('''
    CREATE TABLE IF NOT EXISTS apirequestlog (
        id BIGINT,
        timestamp TIMESTAMP,
        source_api VARCHAR,
        target_api VARCHAR,
        source_model VARCHAR,
        target_model VARCHAR,
        source_prompt VARCHAR,
        target_prompt VARCHAR,
        source_params VARCHAR,
        target_params VARCHAR,
        source_response VARCHAR,
        target_response VARCHAR,
        headers VARCHAR
    );
    ''')
    con.execute('''
    CREATE TABLE IF NOT EXISTS modelconfig (
        id BIGINT,
        route_key VARCHAR,
        target_model VARCHAR,
        provider VARCHAR,
        prompt_keywords VARCHAR,
        description VARCHAR,
        enabled BOOLEAN,
        api_key VARCHAR,
        api_base VARCHAR,
        auth_header VARCHAR,
        auth_format VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    con.execute('''
    CREATE TABLE IF NOT EXISTS apiroute (
        id BIGINT,
        path VARCHAR,
        method VARCHAR,
        description VARCHAR,
        enabled BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    
    # API密钥池管理表
    con.execute('''
    CREATE TABLE IF NOT EXISTS api_key_pool (
        id BIGINT,
        provider VARCHAR NOT NULL,
        api_key VARCHAR NOT NULL,
        auth_header VARCHAR DEFAULT 'Authorization',
        auth_format VARCHAR DEFAULT 'Bearer {key}',
        is_active BOOLEAN DEFAULT TRUE,
        requests_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        last_used_at TIMESTAMP,
        rate_limit_reset_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider, api_key)
    );
    ''')
    
    # API密钥使用统计表
    con.execute('''
    CREATE TABLE IF NOT EXISTS api_key_stats (
        id BIGINT,
        provider VARCHAR NOT NULL,
        api_key VARCHAR NOT NULL,
        date DATE NOT NULL,
        requests_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        status_codes VARCHAR, -- JSON格式存储状态码统计
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider, api_key, date)
    );
    ''')
    con.close()

if __name__ == "__main__":
    init_db()
    print("DuckDB tables created.")