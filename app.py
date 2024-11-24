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
        # 使用多个IP查询服务以提高可靠性
        ip_services = [
            'https://api.ipify.org',
            'https://api.my-ip.io/ip',
            'https://ip.seeip.org'
        ]
        
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    ip = response.text.strip()
                    st.success(f"当前IP地址: {ip}")
                    return ip
            except:
                continue
                
        st.error("无法获取IP地址")
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
        st.info("正在尝试连接...")
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

def main():
    st.title("Oracle ADB 连接测试")
    
    # 添加IP检测按钮
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("检查当前IP", type="primary"):
            get_public_ip()
            
    with col2:
        if st.button("测试数据库连接"):
            test_connection()
    
    # 添加说明信息
    st.info("""
    注意事项：
    1. 获取到IP地址后，需要将其添加到Oracle Cloud的ACL列表中
    2. 在Oracle Cloud Console中：Database -> [你的数据库] -> Network -> Access Control List
    3. 添加IP地址后等待几分钟生效
    """)

if __name__ == "__main__":
    main() 