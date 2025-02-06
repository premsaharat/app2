import streamlit as st
import time

# Initialize session state for theme if not exists
if 'theme' not in st.session_state:
    st.session_state.theme = 'สว่าง'

# Page config
st.set_page_config(
    page_title="File Converter Hub",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme-based CSS
def get_theme_css():
    if st.session_state.theme == 'มืด':
        return """
        <style>
        /* Dark theme */
        .big-button {
            background-color: #1e1e1e;
            color: white;
            border: 2px solid #333;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
        }
        .stats-box {
            background-color: #2d2d2d;
            color: white;
        }
        .feature-list {
            background-color: #2d2d2d;
            color: white;
        }
        </style>
        """
    else:  # Light theme
        return """
        <style>
        /* Light theme */
        .big-button {
            background-color: white;
            color: black;
            border: 2px solid #f0f2f6;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .stats-box {
            background-color: #f8fafc;
            color: black;
        }
        .feature-list {
            background-color: #f8fafc;
            color: black;
        }
        </style>
        """

# Base CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    
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
        border-radius: 1rem;
        padding: 1.5rem;
        margin: 0.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .big-button:hover {
        transform: translateY(-5px);
    }
    
    .tool-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    
    .stats-box {
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem;
        text-align: center;
    }
    
    .feature-list {
        border-radius: 0.5rem;
        padding: 1rem;
        margin-top: 1rem;
    }
    
    .stProgress > div > div > div {
        background-color: #2e6bf0;
    }
    </style>
    """ + get_theme_css(), unsafe_allow_html=True)

# Sidebar with user guide and settings
with st.sidebar:
    st.title("⚙️ การตั้งค่า")
    
    # Theme selector with functionality
    selected_theme = st.selectbox(
        "ธีม",
        ["สว่าง", "มืด", "ระบบ"],
        index=["สว่าง", "มืด", "ระบบ"].index(st.session_state.theme)
    )
    
    # Update theme if changed
    if selected_theme != st.session_state.theme:
        st.session_state.theme = selected_theme
        st.experimental_rerun()
    
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

# Search functionality
search = st.text_input("🔍 ค้นหาเครื่องมือ...", placeholder="พิมพ์ชื่อเครื่องมือที่ต้องการ...")

# Tools data
tools = [
    {
        "icon": "📊",
        "title": "Excel to KML",
        "description": "แปลงไฟล์ Excel เป็น KML สำหรับแสดงข้อมูลบน Google Earth",
        "usage_count": "1,234",
        "page": "pages/app.py"
    },
    {
        "icon": "📑",
        "title": "KML to Excel",
        "description": "แปลงไฟล์ KML เป็น Excel เพื่อจัดการข้อมูลได้ง่ายขึ้น",
        "usage_count": "987",
        "page": "pages/appss.py"
    },
    {
        "icon": "〽️",
        "title": "สร้างเส้นซ้อน",
        "description": "สร้างและแก้ไขเส้นซ้อนบนแผนที่แบบอัตโนมัติ",
        "usage_count": "756",
        "page": "pages/appsss.py"
    },
    {
        "icon": "✂️",
        "title": "ตัดพื้นที่",
        "description": "ตัดพื้นที่ตามขอบเขตที่กำหนดอย่างแม่นยำ",
        "usage_count": "543",
        "page": "pages/appssss.py"
    }
]

# Filter tools based on search
if search:
    filtered_tools = [tool for tool in tools if search.lower() in tool['title'].lower() or search.lower() in tool['description'].lower()]
else:
    filtered_tools = tools

# Display tools in grid
cols = st.columns(4)
for idx, tool in enumerate(filtered_tools):
    with cols[idx % 4]:
        st.markdown(f"""
            <div class="big-button">
                <div class="tool-icon">{tool['icon']}</div>
                <h2>{tool['title']}</h2>
                <p>{tool['description']}</p>
                <div class="stats-box">
                    <small>ใช้งานแล้ว {tool['usage_count']} ครั้ง</small>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button(f"เปิดใช้งาน {tool['title']}", key=f"btn{idx+1}"):
            with st.spinner("กำลังโหลด..."):
                time.sleep(0.5)
                st.switch_page(tool['page'])

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
