import streamlit as st
import time

# Page config
st.set_page_config(
    page_title="File Converter Hub",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with animations and better styling
st.markdown("""
    <style>
    /* Main container styling */
    .main {
        padding: 2rem;
    }
    
    /* Custom card styling */
    .stButton button {
        width: 100%;
        padding: 0.5rem;
        border-radius: 0.5rem;
        border: none;
        background-color: #2e6bf0;
        color: white;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    
    .stButton button:hover {
        background-color: #1d4ed8;
        transition: all 0.3s ease;
    }
    
    .big-button {
        background-color: white;
        border-radius: 1rem;
        padding: 1.5rem;
        margin: 0.5rem;
        text-align: center;
        transition: all 0.3s ease;
        border: 2px solid #f0f2f6;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .big-button:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    .tool-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    
    .stats-box {
        background-color: #f8fafc;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem;
        text-align: center;
    }
    
    /* Feature list styling */
    .feature-list {
        background-color: #f8fafc;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-top: 1rem;
    }
    
    /* Progress bar styling */
    .stProgress > div > div > div {
        background-color: #2e6bf0;
    }
    </style>
    """, unsafe_allow_html=True)

# Sidebar with user guide and settings
with st.sidebar:
    st.title("⚙️ การตั้งค่า")
    theme = st.selectbox(
        "ธีม",
        ["สว่าง", "มืด", "ระบบ"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 📖 คู่มือการใช้งาน")
    with st.expander("วิธีการใช้งาน"):
        st.markdown("""
        1. เลือกเครื่องมือที่ต้องการใช้
        2. อัปโหลดไฟล์ที่ต้องการแปลง
        3. กำหนดค่าการแปลงไฟล์
        4. กดปุ่มแปลงไฟล์
        5. ดาวน์โหลดไฟล์ผลลัพธ์
        """)
    
    st.markdown("---")
    st.markdown("### 📊 สถิติการใช้งาน")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("การแปลงวันนี้", "150", "+12")
    with col2:
        st.metric("ผู้ใช้งานออนไลน์", "23", "+5")

# Main content
st.title("🔄 File Converter Hub")
st.markdown("### ศูนย์รวมเครื่องมือแปลงไฟล์ที่ใช้งานง่าย รวดเร็ว และมีประสิทธิภาพ")

# Search bar
search = st.text_input("🔍 ค้นหาเครื่องมือ...", placeholder="พิมพ์ชื่อเครื่องมือที่ต้องการ...")

# Tool grid
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
        <div class="big-button">
            <div class="tool-icon">📊</div>
            <h2>Excel to KML</h2>
            <p>แปลงไฟล์ Excel เป็น KML สำหรับแสดงข้อมูลบน Google Earth</p>
            <div class="stats-box">
                <small>ใช้งานแล้ว 1,234 ครั้ง</small>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("เปิดใช้งาน Excel to KML", key="btn1"):
        with st.spinner("กำลังโหลด..."):
            time.sleep(0.5)
            st.switch_page("pages/app.py")

with col2:
    st.markdown("""
        <div class="big-button">
            <div class="tool-icon">📑</div>
            <h2>KML to Excel</h2>
            <p>แปลงไฟล์ KML เป็น Excel เพื่อจัดการข้อมูลได้ง่ายขึ้น</p>
            <div class="stats-box">
                <small>ใช้งานแล้ว 987 ครั้ง</small>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("เปิดใช้งาน KML to Excel", key="btn2"):
        with st.spinner("กำลังโหลด..."):
            time.sleep(0.5)
            st.switch_page("pages/appss.py")

with col3:
    st.markdown("""
        <div class="big-button">
            <div class="tool-icon">〽️</div>
            <h2>สร้างเส้นซ้อน</h2>
            <p>สร้างและแก้ไขเส้นซ้อนบนแผนที่แบบอัตโนมัติ</p>
            <div class="stats-box">
                <small>ใช้งานแล้ว 756 ครั้ง</small>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("เปิดใช้งานสร้างเส้นซ้อน", key="btn3"):
        with st.spinner("กำลังโหลด..."):
            time.sleep(0.5)
            st.switch_page("pages/appsss.py")

with col4:
    st.markdown("""
        <div class="big-button">
            <div class="tool-icon">✂️</div>
            <h2>ตัดพื้นที่</h2>
            <p>ตัดพื้นที่ตามขอบเขตที่กำหนดอย่างแม่นยำ</p>
            <div class="stats-box">
                <small>ใช้งานแล้ว 543 ครั้ง</small>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("เปิดใช้งานตัดพื้นที่", key="btn4"):
        with st.spinner("กำลังโหลด..."):
            time.sleep(0.5)
            st.switch_page("pages/appssss.py")

# Feature highlights
st.markdown("---")
st.markdown("### ✨ คุณสมบัติเด่น")

feature_col1, feature_col2, feature_col3 = st.columns(3)

with feature_col1:
    st.markdown("""
        <div class="feature-list">
            <h4>🚀 ประสิทธิภาพสูง</h4>
            <ul>
                <li>แปลงไฟล์ได้รวดเร็ว</li>
                <li>รองรับไฟล์ขนาดใหญ่</li>
                <li>ประมวลผลแบบ Real-time</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

with feature_col2:
    st.markdown("""
        <div class="feature-list">
            <h4>🔒 ความปลอดภัย</h4>
            <ul>
                <li>การเข้ารหัสข้อมูล</li>
                <li>ลบไฟล์อัตโนมัติ</li>
                <li>ไม่มีการเก็บข้อมูล</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

with feature_col3:
    st.markdown("""
        <div class="feature-list">
            <h4>💡 ใช้งานง่าย</h4>
            <ul>
                <li>อินเตอร์เฟซเรียบง่าย</li>
                <li>มีคู่มือการใช้งาน</li>
                <li>รองรับภาษาไทย</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>© 2024 File Converter Hub. พัฒนาด้วย ❤️ เพื่อผู้ใช้งานทุกท่าน</p>
</div>
""", unsafe_allow_html=True)
