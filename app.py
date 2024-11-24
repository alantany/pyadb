import streamlit as st
import oracledb
import time
import logging
import sys
import platform
import ssl
import requests

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('oracledb')
logger.setLevel(logging.DEBUG)

# 强制跳过 SSL 验证
oracledb.defaults.ssl_verify_hostname = False

def get_public_ip():
    """获取公网IP地址"""
    try:
        # 使用专门返回IPv4的服务
        ip_services = [
            'https://api4.ipify.org',  # 专门返回IPv4
            'https://ipv4.seeip.org',  # 专门返回IPv4
            'https://v4.ident.me'      # 专门返回IPv4
        ]
        
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ':' not in ip:  # 确保不是IPv6地址
                        st.success(f"当前IPv4地址: {ip}")
                        return ip
            except:
                continue
                
        st.error("无法获取IPv4地址")
        return None
    except Exception as e:
        st.error(f"获取IP地址失败: {str(e)}")
        return None

def test_connection():
    try:
        start_time = time.time()
        
        # 创建不验证证书的SSL上下文
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # 使用完整的连接字符串
        connect_string = """(description= (retry_count=20)(retry_delay=3)
            (address=(protocol=tcps)(port=1522)(host=adb.ap-seoul-1.oraclecloud.com))
            (connect_data=(service_name=ji62b58rdfvmxnj_gp5ldkkvtlevpvtt_low.adb.oraclecloud.com))
            (security=(ssl_server_dn_match=no)))"""
            
        # 配置连接参数 - 添加SSL上下文
        params = {
            "user": st.secrets["oracle"]["username"],
            "password": st.secrets["oracle"]["password"],
            "dsn": connect_string,
            "ssl_context": ssl_context
        }
        
        # 显示连接参数（隐藏敏感信息）
        st.info("连接参数:")
        st.json({
            "user": params["user"],
            "dsn": params["dsn"],
            "ssl_verify": False
        })
        
        # 尝试连接
        st.info("在尝试连接...")
        logger.info("开始建立数据库连接...")
        
        # 使用with语句自动管理连接
        with oracledb.connect(**params) as connection:
            logger.info("数据库连接已建立")
            
            with connection.cursor() as cursor:
                # 测试基本查询
                cursor.execute("SELECT SYSDATE, VERSION FROM V$INSTANCE")
                date_result, version = cursor.fetchone()
                
                # 测试数据库版本
                cursor.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
                banner = cursor.fetchone()[0]
                
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        
        # 显示连接信息
        st.success("数据库连接测试成功!")
        st.info(f"响应时间: {response_time} ms")
        
        # 使用columns布局显示详细信息
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="数据库时间", value=date_result.strftime("%Y-%m-%d %H:%M:%S"))
        with col2:
            st.metric(label="数据库版本", value=version)
        
        st.text(f"完整版本信息: {banner}")
        
    except Exception as e:
        logger.error(f"连接失败: {str(e)}", exc_info=True)
        st.error(f"连接测试失败: {str(e)}")
        
        # 显示更多调试信息
        st.text("调试信息:")
        st.json({
            "Python版本": sys.version,
            "oracledb版本": oracledb.__version__,
            "操作系统": platform.system(),
            "SSL验证": "已禁用"
        })

def execute_sql(sql_query):
    """执行SQL语句并显示结果"""
    try:
        start_time = time.time()
        
        # 创建SSL上下文
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # 使用完整的连接字符串
        connect_string = """(description= (retry_count=20)(retry_delay=3)
            (address=(protocol=tcps)(port=1522)(host=adb.ap-seoul-1.oraclecloud.com))
            (connect_data=(service_name=ji62b58rdfvmxnj_gp5ldkkvtlevpvtt_low.adb.oraclecloud.com))
            (security=(ssl_server_dn_match=no)))"""
        
        # 连接参数
        params = {
            "user": st.secrets["oracle"]["username"],
            "password": st.secrets["oracle"]["password"],
            "dsn": connect_string,
            "ssl_context": ssl_context
        }
        
        # 执行查询
        with oracledb.connect(**params) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                
                # 获取列名
                columns = [col[0] for col in cursor.description] if cursor.description else []
                
                # 获取结果
                results = cursor.fetchall() if cursor.description else []
                
                # 计算执行时间
                end_time = time.time()
                execution_time = round((end_time - start_time) * 1000, 2)
                
                # 显示执行时间
                st.success(f"查询执行成功! 耗时: {execution_time}ms")
                
                # 如果有结果，显示数据表格
                if columns and results:
                    st.write("查询结果:")
                    # 将结果转换为字典列表
                    data = [dict(zip(columns, row)) for row in results]
                    st.dataframe(data)
                    
                    # 显示记录数
                    st.info(f"共 {len(results)} 条记录")
                else:
                    st.info("查询执行成功，无返回数据")
                    
                # 如果是DML语句，显示影响的行数
                if not cursor.description and cursor.rowcount > -1:
                    st.success(f"成功执行，影响 {cursor.rowcount} 行")
                
    except Exception as e:
        st.error(f"SQL执行失败: {str(e)}")
        logger.error(f"SQL执行失败: {str(e)}", exc_info=True)

def get_db_version():
    """获取数据库版本信息"""
    try:
        # 创建SSL上下文
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # 使用完整的连接字符串
        connect_string = """(description= (retry_count=20)(retry_delay=3)
            (address=(protocol=tcps)(port=1522)(host=adb.ap-seoul-1.oraclecloud.com))
            (connect_data=(service_name=ji62b58rdfvmxnj_gp5ldkkvtlevpvtt_low.adb.oraclecloud.com))
            (security=(ssl_server_dn_match=no)))"""
        
        # 连接参数
        params = {
            "user": st.secrets["oracle"]["username"],
            "password": st.secrets["oracle"]["password"],
            "dsn": connect_string,
            "ssl_context": ssl_context
        }
        
        # 执行查询
        with oracledb.connect(**params) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT banner_full FROM v$version WHERE rownum = 1")
                version = cursor.fetchone()
                if version:
                    return version[0]
        return "版本信息获取失败"
    except Exception as e:
        logger.error(f"获取版本失败: {str(e)}", exc_info=True)
        return "版本信息获取失败"

def main():
    st.title("Oracle ADB 连接测试")
    
    # 自动显示当前IP地址和数据库版本
    with st.sidebar:
        st.write("### 系统信息")
        get_public_ip()
        st.write("### 数据库版本")
        st.success(get_db_version())
    
    # 添加选项卡
    tab1, tab2 = st.tabs(["连接测试", "SQL执行"])
    
    # 连接测试选项卡
    with tab1:
        if st.button("测试数据库连接", type="primary"):
            test_connection()
        
        st.info("""
        注意事项：
        1. 请确保当前IP地址已添加到Oracle Cloud的ACL列表中
        2. 在Oracle Cloud Console中：Database -> [你的数据库] -> Network -> Access Control List
        3. 添加IP地址后等待几分钟生效
        """)
    
    # SQL执行选项卡
    with tab2:
        # SQL输入区域
        sql_query = st.text_area(
            "输入SQL语句",
            height=150,
            placeholder="输入要执行的SQL语句"
        )
        
        col1, col2 = st.columns(2)
        
        # 执行按钮
        with col1:
            if st.button("执行SQL", type="primary") and sql_query:
                execute_sql(sql_query)
                
        # 版本信息查询按钮
        with col2:
            if st.button("查看数据库详细版本"):
                version_sql = """
                SELECT * FROM (
                    SELECT 'Database Version' as COMPONENT, VERSION || ' ' || STATUS as VERSION_INFO FROM V$INSTANCE
                    UNION ALL
                    SELECT 'Database Edition', BANNER FROM V$VERSION WHERE BANNER LIKE '%Edition%'
                    UNION ALL
                    SELECT 'ORACLE_HOME', SYS_CONTEXT('USERENV', 'ORACLE_HOME') FROM DUAL
                    UNION ALL
                    SELECT 'Instance Name', INSTANCE_NAME FROM V$INSTANCE
                    UNION ALL
                    SELECT 'Host Name', HOST_NAME FROM V$INSTANCE
                    UNION ALL
                    SELECT 'Database Name', NAME FROM V$DATABASE
                    UNION ALL
                    SELECT 'Database Role', DATABASE_ROLE FROM V$DATABASE
                    UNION ALL
                    SELECT 'Open Mode', OPEN_MODE FROM V$DATABASE
                    UNION ALL
                    SELECT 'Database ID', TO_CHAR(DBID) FROM V$DATABASE
                    UNION ALL
                    SELECT 'Platform', PLATFORM_NAME FROM V$DATABASE
                    UNION ALL
                    SELECT 'Created', TO_CHAR(CREATED,'DD-MON-YYYY HH24:MI:SS') FROM V$DATABASE
                )
                ORDER BY 1
                """
                execute_sql(version_sql)
        
        # 使用说明
        with st.expander("SQL执行说明"):
            st.markdown("""
            ### 支持的SQL类型：
            1. 查询语句 (SELECT)
            2. DML语句 (INSERT, UPDATE, DELETE)
            3. DDL语句 (CREATE, ALTER, DROP)
            
            ### 注意事项：
            - 请确保SQL语句正确
            - 查询结果较大时可能需要等待
            - DML语句会自动提交
            """)

if __name__ == "__main__":
    main() 