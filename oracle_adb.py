import oracledb
import logging
import ssl
from typing import Optional, Dict, List, Any, Tuple
import time
from openai import OpenAI

class OracleADB:
    """
    Oracle Autonomous Database 连接工具类

    此模块提供了一个用于连接和操作 Oracle Autonomous Database 的工具类。
    主要功能包括：
    - 数据库连接测试
    - SQL语句执行
    - 数据库版本信息获取

    使用示例:
        # 创建连接实例
        connect_string = "(description=(retry_count=20)(retry_delay=3)...)"
        db = OracleADB(username="admin", password="password", connect_string=connect_string)
        
        # 测试连接
        success, message, data = db.test_connection()
        
        # 执行SQL
        success, message, data = db.execute_sql("SELECT * FROM your_table")
        
        # 获取版本
        version = db.get_version()

    注意事项：
    1. 需要先在Oracle Cloud中关闭mTLS认证
    2. 需要在ACL中添加客户端IP
    3. 确保连接字符串格式正确
    """
    def __init__(self, username: str, password: str, connect_string: str):
        """初始化Oracle ADB连接类
        
        Args:
            username: 数据库用户名
            password: 数据库密码
            connect_string: 数据库连接字符串
        """
        self.username = username
        self.password = password
        self.connect_string = connect_string
        self.logger = self._setup_logger()
        
        # 配置SSL
        self.ssl_context = self._setup_ssl()
        oracledb.defaults.ssl_verify_hostname = False
        
        # 初始化OpenAI客户端
        self.openai_client = OpenAI(
            api_key="sk-1pUmQlsIkgla3CuvKTgCrzDZ3r0pBxO608YJvIHCN18lvOrn",
            base_url="https://api.chatanywhere.tech/v1"
        )
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger('oracledb')
        logger.setLevel(logging.DEBUG)
        return logger
        
    def _setup_ssl(self) -> ssl.SSLContext:
        """配置SSL上下文"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
        
    def get_connection_params(self) -> Dict[str, Any]:
        """获取数据库连接参数"""
        return {
            "user": self.username,
            "password": self.password,
            "dsn": self.connect_string,
            "ssl_context": self.ssl_context
        }
        
    def test_connection(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """测试数据库连接
        
        Returns:
            Tuple[bool, str, Optional[Dict[str, Any]]]: 
            - 成功标志
            - 消息
            - 数据（包含响应时间、数据库时间、版本等信息）
        """
        try:
            start_time = time.time()
            with oracledb.connect(**self.get_connection_params()) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT SYSDATE, VERSION FROM V$INSTANCE")
                    date_result, version = cursor.fetchone()
                    
                    cursor.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
                    banner = cursor.fetchone()[0]
                    
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return True, "连接成功", {
                "response_time": response_time,
                "date": date_result.strftime("%Y-%m-%d %H:%M:%S"),
                "version": version,
                "banner": banner
            }
            
        except Exception as e:
            self.logger.error(f"连接失败: {str(e)}", exc_info=True)
            return False, str(e), None
            
    def execute_sql(self, sql_query: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """执行SQL语句
        
        Args:
            sql_query (str): SQL语句
            
        Returns:
            Tuple[bool, str, Optional[Dict[str, Any]]]:
            - 成功标志
            - 消息
            - 数据（包含查询结果、执行时间等信息）
        """
        try:
            start_time = time.time()
            with oracledb.connect(**self.get_connection_params()) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql_query)
                    
                    # 获取列名和结果
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    results = cursor.fetchall() if cursor.description else []
                    
                    execution_time = round((time.time() - start_time) * 1000, 2)
                    
                    return True, "执行成功", {
                        "columns": columns,
                        "results": results,
                        "execution_time": execution_time,
                        "affected_rows": cursor.rowcount if not cursor.description else None
                    }
                    
        except Exception as e:
            self.logger.error(f"SQL执行失败: {str(e)}", exc_info=True)
            return False, str(e), None
            
    def get_version(self) -> str:
        """获取数据库版本信息
        
        Returns:
            str: 数据库版本信息
        """
        try:
            with oracledb.connect(**self.get_connection_params()) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT banner_full FROM v$version WHERE rownum = 1")
                    version = cursor.fetchone()
                    return version[0] if version else "版本信息获取失败"
        except Exception as e:
            self.logger.error(f"获取版本失败: {str(e)}", exc_info=True)
            return "版本信息获取失败"
            
    def analyze_query(self, query: str) -> tuple[bool, str, Optional[list[str]]]:
        """分析自然语言查询，提取相关表名
        
        Args:
            query: 自然语言查询
            
        Returns:
            (success, message, tables): 是否成功,消息,相关表名列表
        """
        try:
            # 构建分析prompt
            prompt = f"""你是一个Oracle数据库专家。请分析以下自然语言问题，列出可能涉及的数据库表名。
            
问题: {query}

请只返回表名列表，每行一个表名，不要包含其他任何信息。
如果无法确定涉及的表，请返回"未知"。
"""
            
            # 调用OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个Oracle数据库专家,专门负责分析SQL查询涉及的表。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            # 解析返回的表名
            tables = []
            result = response.choices[0].message.content.strip()
            if result.lower() != "未知":
                tables = [table.strip().upper() for table in result.split('\n') if table.strip()]
            
            if not tables:
                return False, "无法确定查询涉及的表", None
                
            return True, f"识别到相关表: {', '.join(tables)}", tables
            
        except Exception as e:
            self.logger.error(f"分析查询失败: {str(e)}", exc_info=True)
            return False, f"分析查询失败: {str(e)}", None
            
    def get_schema_info(self, tables: Optional[List[str]] = None) -> tuple[bool, str, Optional[dict]]:
        """获取数据库schema信息
        
        Args:
            tables: 指定要获取schema的表名列表，为None时获取所有表
            
        Returns:
            (success, message, schema_info): 是否成功,消息,schema信息
        """
        try:
            # 构建SQL查询
            schema_sql = """
                SELECT 
                    t.table_name,
                    tc.comments as table_comment,
                    c.column_name,
                    c.data_type,
                    c.data_length,
                    c.nullable,
                    cc.comments as column_comment
                FROM user_tables t
                LEFT JOIN user_tab_comments tc ON t.table_name = tc.table_name
                LEFT JOIN user_tab_columns c ON t.table_name = c.table_name
                LEFT JOIN user_col_comments cc ON c.table_name = cc.table_name 
                    AND c.column_name = cc.column_name
            """
            
            # 如果指定了表名，添加WHERE条件
            if tables:
                table_list = ", ".join(f"'{t}'" for t in tables)
                schema_sql += f" WHERE t.table_name IN ({table_list})"
                
            schema_sql += " ORDER BY t.table_name, c.column_id"
            
            success, message, data = self.execute_sql(schema_sql)
            if not success:
                return False, f"获取schema失败: {message}", None
                
            # 组织schema信息
            schema_info = {}
            for row in data['results']:
                table_name = row[0]
                if table_name not in schema_info:
                    schema_info[table_name] = {
                        'comment': row[1] or '',
                        'columns': []
                    }
                    
                schema_info[table_name]['columns'].append({
                    'name': row[2],
                    'type': row[3],
                    'length': row[4],
                    'nullable': row[5] == 'Y',
                    'comment': row[6] or ''
                })
                
            return True, "获取schema成功", schema_info
            
        except Exception as e:
            self.logger.error(f"获取schema失败: {str(e)}", exc_info=True)
            return False, f"获取schema失败: {str(e)}", None
            
    def natural_language_to_sql(self, query: str) -> tuple[bool, str, Optional[str]]:
        """将自然语言转换为SQL查询
        
        Args:
            query: 自然语言查询
            
        Returns:
            (success, message, sql): 转换是否成功,消息,SQL语句
        """
        # 1. 分析查询涉及的表
        success, message, tables = self.analyze_query(query)
        if not success:
            return False, message, None
            
        # 2. 获取相关表的schema信息
        success, message, schema_info = self.get_schema_info(tables)
        if not success:
            return False, message, None
            
        # 3. 构建SQL生成prompt
        prompt = f"""你是一个Oracle SQL专家。请根据以下数据库schema和自然语言问题生成对应的Oracle SQL查询语句。

数据库Schema信息:
```
{schema_info}
```

自然语言问题:
{query}

要求:
1. 只返回SQL语句本身,不需要其他解释
2. 确保SQL语句符合Oracle语法规范
3. 如果无法生成有效的SQL,返回"无法生成有效的SQL查询"
4. 不要生成任何DDL(CREATE/ALTER/DROP)语句
5. 只生成查询相关的SQL(SELECT)语句
"""
        
        try:
            # 4. 调用OpenAI API生成SQL
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个Oracle SQL专家,专门负责将自然语言转换为SQL查询语句。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                top_p=0.9,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            # 5. 获取并验证SQL
            sql = response.choices[0].message.content.strip()
            
            if sql.lower().startswith(("select", "with")):
                return True, "成功生成SQL查询", sql
            elif sql == "无法生成有效的SQL查询":
                return False, "无法理解该问题或生成对应的SQL查询", None
            else:
                return False, "生成的SQL不是有效的查询语句", None
                
        except Exception as e:
            self.logger.error(f"调用OpenAI失败: {str(e)}", exc_info=True)
            return False, f"调用OpenAI失败: {str(e)}", None