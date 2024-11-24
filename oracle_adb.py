import oracledb
import logging
import ssl
from typing import Optional, Dict, List, Any, Tuple
import time

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
            username (str): 数据库用户名
            password (str): 数据库密码
            connect_string (str): 数据库连接字符串
        """
        self.username = username
        self.password = password
        self.connect_string = connect_string
        self.logger = self._setup_logger()
        
        # 配置SSL
        self.ssl_context = self._setup_ssl()
        oracledb.defaults.ssl_verify_hostname = False
        
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