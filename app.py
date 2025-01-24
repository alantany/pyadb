import streamlit as st
import requests
from typing import Optional
from oracle_adb import OracleADB

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

def main():
    st.title("Oracle ADB 连接测试")
    
    # 初始化Oracle ADB连接
    oracle_adb = OracleADB(
        username=st.secrets["oracle"]["username"],
        password=st.secrets["oracle"]["password"],
        connect_string="""(description=(retry_count=20)(retry_delay=3)
            (address=(protocol=tcps)(port=1522)(host=adb.ap-seoul-1.oraclecloud.com))
            (connect_data=(service_name=ji62b58rdfvmxnj_gp5ldkkvtlevpvtt_low.adb.oraclecloud.com))
            (security=(ssl_server_dn_match=no)))"""
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
        
        # 添加开发者信息
        st.markdown("---")
        st.markdown("### 开发者")
        st.markdown("**Huaiyuan Tan**")
    
    # 添加选项卡
    tab1, tab2, tab3 = st.tabs(["连接测试", "SQL执行", "自然语言查询"])
    
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
                    st.success(f"成功执行，影响 {data['affected_rows']} 行")
                else:
                    st.info("查询执行成功，无返回数据")
            else:
                st.error(f"SQL执行失败: {message}")
    
    # 自然语言查询选项卡
    with tab3:
        st.markdown("""
        ### 支持的自然语言查询示例：
        - 显示所有表
        - 显示表结构 xxx
        - 显示表 xxx
        - 显示表 xxx 的前 10 条数据
        - 统计表 xxx 的记录数
        """)
        
        nl_query = st.text_area(
            "输入自然语言查询",
            height=100,
            placeholder="例如：显示所有表"
        )
        
        if st.button("执行查询", type="primary") and nl_query:
            # 转换自然语言到SQL
            success, message, sql = oracle_adb.natural_language_to_sql(nl_query)
            
            if success and sql:
                st.info(f"理解为: {message}")
                st.code(sql, language="sql")
                
                # 执行SQL查询
                success, message, data = oracle_adb.execute_sql(sql)
                if success and data:
                    st.success(f"查询执行成功! 耗时: {data['execution_time']}ms")
                    
                    if data['columns'] and data['results']:
                        st.write("查询结果:")
                        result_data = [dict(zip(data['columns'], row)) for row in data['results']]
                        st.dataframe(result_data)
                        st.info(f"共 {len(data['results'])} 条记录")
                    elif data['affected_rows'] is not None:
                        st.success(f"成功执行，影响 {data['affected_rows']} 行")
                    else:
                        st.info("查询执行成功，无返回数据")
                else:
                    st.error(f"SQL执行失败: {message}")
            else:
                st.error(message)

if __name__ == "__main__":
    main() 