import streamlit as st
import oracledb
import time
import os
import logging
import sys
import platform
import ssl

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('oracledb')
logger.setLevel(logging.DEBUG)

# 强制跳过 SSL 验证
oracledb.defaults.ssl_verify_hostname = False

# 创建一个不验证证书的SSL上下文
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def test_connection():
    try:
        start_time = time.time()
        
        # 使用相对路径
        wallet_path = "Wallet_GP5LDKKVTLEVPVTT"
        
        st.info(f"Wallet完整路径: {wallet_path}")
            
        # 配置连接参数
        params = {
            "user": st.secrets["oracle"]["username"],
            "password": st.secrets["oracle"]["password"],
            "dsn": st.secrets["oracle"]["dsn"],
            "config_dir": wallet_path
        }
        
        # 显示连接参数（隐藏敏感信息）
        st.info("连接参数:")
        st.json({
            "user": params["user"],
            "dsn": params["dsn"],
            "config_dir": params["config_dir"]
        })
        
        # 检查wallet文件
        st.info("Wallet文件检查:")
        if os.path.exists(wallet_path):
            wallet_files = os.listdir(wallet_path)
            for file in wallet_files:
                file_path = os.path.join(wallet_path, file)
                st.text(f"{file}: {os.path.getsize(file_path)} bytes")
        else:
            st.error(f"Wallet目录不存在: {wallet_path}")
            return
        
        # 尝试连接
        st.info("正在尝试连接...")
        logger.info("开始建立数据库连接...")
        
        # 使用with语句自动管理连接
        with oracledb.connect(**params, ssl_context=ssl_context) as connection:
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
            "Wallet路径": wallet_path,
            "Wallet文件": os.listdir(wallet_path) if os.path.exists(wallet_path) else "路径不存在",
            "当前目录": os.getcwd()
        })

def main():
    st.title("Oracle ADB 连接测试")
    
    if st.button("测试数据库连接"):
        test_connection()

if __name__ == "__main__":
    main() 