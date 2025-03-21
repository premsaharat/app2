import streamlit as st
import time
import xml.etree.ElementTree as ET
import os

# Initialize session state for theme if not exists
if 'theme' not in st.session_state:
    st.session_state.theme = 'สว่าง'

# Function to apply theme
def apply_theme(theme_name):
    if theme_name == 'มืด':
        return """
        <style>
        .big-button {
            background-color: #1e1e1e !important;
            border: 2px solid #333 !important;
            color: white !important;
        }
        .stats-box {
            background-color: #2d2d2d !important;
            color: white !important;
        }
        .stApp {
            background-color: #121212;
            color: white;
        }
        </style>
        """
    elif theme_name == 'สว่าง':
        return """
        <style>
        .big-button {
            background-color: white !important;
            border: 2px solid #f0f2f6 !important;
            color: black !important;
        }
        .stats-box {
            background-color: #f8fafc !important;
            color: black !important;
        }
        .stApp {
            background-color: white;
            color: black;
        }
        </style>
        """
    else:  # System theme
        return ""

# Page config
st.set_page_config(
    page_title="โปรแกรม จัดการข้อมูลสายสื่อสาร",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem;
        text-align: center;
    }
    
    .stProgress > div > div > div {
        background-color: #2e6bf0;
    }
    </style>
    """, unsafe_allow_html=True)

# Tools data - with consistent page paths
tools = [
    {
        "icon": "📊",
        "title": "Excel to KML",
        "description": "แปลงไฟล์ Excel เป็น KML สำหรับแสดงข้อมูลบน Google Earth (NTSP)",
        "usage_count": 1234,
        "page": "pages/excel-to-kml.py"
    },
    {
        "icon": "📑",
        "title": "KML to Excel",
        "description": "แปลงไฟล์ KML เป็น Excel เพื่อจัดการข้อมูลได้ง่ายขึ้น",
        "usage_count": 987,
        "page": "pages/kml-to-excel.py"
    },
    {
        "icon": "〽️",
        "title": "สร้างเส้นซ้อน",
        "description": "สร้างและแก้ไขเส้นซ้อนบนแผนที่แบบอัตโนมัติ",
        "usage_count": 756,
        "page": "pages/create-overlay-lines.py"
    },
    {
        "icon": "✂️",
        "title": "ตัดพื้นที่",
        "description": "ตัดพื้นที่ตามขอบเขตที่กำหนดอย่างแม่นยำ",
        "usage_count": 543,
        "page": "pages/cut-area.py"
    },
    {
        "icon": "📊",
        "title": "คำนวณค่าพาดสายประจำปี",
        "description": "วิเคราะห์ค่าพาดสายประจำปีจากไฟล์ Excel",
        "usage_count": 325,
        "page": "pages/calculate-annual-fee.py"
    },
    {
        "icon": "🗺️",
        "title": "KML TO TAG",
        "description": "กรองข้อมูล KML ตาม tags ที่กำหนด รองรับไฟล์ KML และ ZIP",
        "usage_count": 289,
        "page": "pages/kml-by-tag.py"
    },
    {
        "icon": "🌍",
        "title": "ปรับข้อมูล KML จาก FINOC",
        "description": "อัพเดทข้อมูลใน KML โดยใช้ข้อมูลจากไฟล์ Excel",
        "usage_count": 121,
        "page": "pages/kml-finoc.py"  # Corrected path
    },
]

# Function to verify if all page files exist
def verify_pages():
    missing_pages = []
    for tool in tools:
        if not os.path.exists(tool['page']):
            missing_pages.append(tool['title'])
    
    if missing_pages:
        st.warning(f"ไม่พบไฟล์หน้าต่อไปนี้: {', '.join(missing_pages)}")

# Run the verification
verify_pages()

# Sidebar with user guide and settings
with st.sidebar:
    st.title("⚙️ การตั้งค่า")
    selected_theme = st.selectbox(
        "ธีม",
        ["สว่าง", "มืด", "ระบบ"],
        index=["สว่าง", "มืด", "ระบบ"].index(st.session_state.theme)
    )
    
    # Apply theme when changed
    if selected_theme != st.session_state.theme:
        st.session_state.theme = selected_theme
        st.markdown(apply_theme(selected_theme), unsafe_allow_html=True)
    
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

# Function to count lines in KML file
def count_lines_in_kml(kml_file):
    tree = ET.parse(kml_file)
    root = tree.getroot()
    namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
    lines = root.findall('.//kml:LineString', namespace)
    return len(lines)

# Main content
st.title("🔄 โปรแกรม จัดการข้อมูลสายสื่อสาร")

# KML file upload
uploaded_kml = st.file_uploader("🔍 ตรวจสอบและนับเส้นทางทั้งหมดในไฟล์ KML ของคุณ!", type=["kml"])
if uploaded_kml is not None:
    num_lines = count_lines_in_kml(uploaded_kml)
    st.success(f"ไฟล์ KML นี้มี {num_lines} เส้น")

# Search functionality
search = st.text_input("🔍 ค้นหาเครื่องมือ...", placeholder="พิมพ์ชื่อเครื่องมือที่ต้องการ...")

# Filter tools based on search
if search:
    filtered_tools = [tool for tool in tools if search.lower() in tool['title'].lower() or search.lower() in tool['description'].lower()]
else:
    filtered_tools = tools

# Display tools in 2-column grid
for i in range(0, len(filtered_tools), 2):
    col1, col2 = st.columns(2)
    
    # First column
    with col1:
        tool = filtered_tools[i]
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
        if st.button(f"เปิดใช้งาน {tool['title']}", key=f"btn{i+1}"):
            with st.spinner("กำลังโหลด..."):
                time.sleep(0.5)
                try:
                    # Make sure the path is correct
                    page_path = tool['page']
                    if not page_path.startswith("pages/") and "." in page_path:
                        page_path = "pages/" + page_path
                    st.switch_page(page_path)
                except Exception as e:
                    st.error(f"ไม่สามารถเปิดหน้า {tool['title']} ได้: {str(e)}")
    
    # Second column (if available)
    with col2:
        if i + 1 < len(filtered_tools):
            tool = filtered_tools[i + 1]
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
            if st.button(f"เปิดใช้งาน {tool['title']}", key=f"btn{i+2}"):
                with st.spinner("กำลังโหลด..."):
                    time.sleep(0.5)
                    try:
                        # Make sure the path is correct
                        page_path = tool['page']
                        if not page_path.startswith("pages/") and "." in page_path:
                            page_path = "pages/" + page_path
                        st.switch_page(page_path)
                    except Exception as e:
                        st.error(f"ไม่สามารถเปิดหน้า {tool['title']} ได้: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>© 2024 โปรแกรม จัดการข้อมูลสายสื่อสาร. พัฒนาด้วย ❤️ เพื่อผู้ใช้งานทุกท่าน</p>
</div>
""", unsafe_allow_html=True)
