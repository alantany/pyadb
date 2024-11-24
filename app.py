import streamlit as st
import oracledb
import time
import logging
import sys
import platform
import ssl
import requests
from typing import Optional, Dict, List, Any, Tuple

class OracleADB:
    def __init__(self, username: str, password: str, connect_string: str):
        """初始化Oracle ADB连接类"""
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
        """测试数据库连接"""
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
        """执行SQL语句"""
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
        """获取数据库版本信息"""
        try:
            with oracledb.connect(**self.get_connection_params()) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT banner_full FROM v$version WHERE rownum = 1")
                    version = cursor.fetchone()
                    return version[0] if version else "版本信息获取失败"
        except Exception as e:
            self.logger.error(f"获取版本失败: {str(e)}", exc_info=True)
            return "版本信息获取失败"

def get_public_ip() -> Optional[str]:
    """获取公网IPv4地址"""
    try:
        ip_services = [
            'https://api4.ipify.org',
            'https://ipv4.seeip.org',
            'https://v4.ident.me'
        ]
        
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ':' not in ip:  # 确保不是IPv6地址
                        return ip
            except:
                continue
                
        return None
    except Exception:
        return None

# 示例使用
def main():
    st.title("Oracle ADB 连接测试")
    
    # 初始化Oracle ADB连接
    connect_string = """(description= (retry_count=20)(retry_delay=3)
        (address=(protocol=tcps)(port=1522)(host=adb.ap-seoul-1.oraclecloud.com))
        (connect_data=(service_name=ji62b58rdfvmxnj_gp5ldkkvtlevpvtt_low.adb.oraclecloud.com))
        (security=(ssl_server_dn_match=no)))"""
        
    oracle_adb = OracleADB(
        username=st.secrets["oracle"]["username"],
        password=st.secrets["oracle"]["password"],
        connect_string=connect_string
    )
    
    # 显示系统信息
    with st.sidebar:
        st.write("### 系统信息")
        ip = get_public_ip()
        if ip:
            st.success(f"当前IPv4地址: {ip}")
        else:
            st.error("无法获取IPv4地址")
            
        st.write("### 数据库版本")
        st.success(oracle_adb.get_version())
    
    # 添加选项卡
    tab1, tab2 = st.tabs(["连接测试", "SQL执行"])
    
    # 连接测试选项卡
    with tab1:
        if st.button("测试数据库连接", type="primary"):
            success, message, data = oracle_adb.test_connection()
            if success and data:
                st.success("数据库连接测试成功!")
                st.info(f"响应时间: {data['response_time']} ms")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="数据库时间", value=data['date'])
                with col2:
                    st.metric(label="数据库版本", value=data['version'])
                
                st.text(f"完整版本信息: {data['banner']}")
            else:
                st.error(f"连接测试失败: {message}")
    
    # SQL执行选项卡
    with tab2:
        sql_query = st.text_area(
            "输入SQL语句",
            height=150,
            placeholder="输入要执行的SQL语句"
        )
        
        if st.button("执行SQL", type="primary") and sql_query:
            success, message, data = oracle_adb.execute_sql(sql_query)
            if success and data:
                st.success(f"查询执行成功! 耗时: {data['execution_time']}ms")
                
                if data['columns'] and data['results']:
                    st.write("查询结果:")
                    result_data = [dict(zip(data['columns'], row)) for row in data['results']]
                    st.dataframe(result_data)
                    st.info(f"共 {len(data['results'])} 条记录")
                elif data['affected_rows'] is not None:
                    st.success(f"成功执行，影响 {data['affected_rows']} ���")
                else:
                    st.info("查询执行成功，无返回数据")
            else:
                st.error(f"SQL执行失败: {message}")

if __name__ == "__main__":
    main() 