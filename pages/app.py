import os
import re
import pandas as pd
import simplekml
import streamlit as st
from io import BytesIO
import tempfile
from datetime import datetime
import xml.etree.ElementTree as ET

# Set up page configuration with custom theme
st.set_page_config(
    page_title="Excel to KML Converter (NTSP)",
    page_icon="🗺️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS to enhance the UI
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-weight: 600;
    }
    .uploadedFile {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stSelectbox {
        margin: 1rem 0;
    }
    .success-message {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        color: #155724;
        margin: 1rem 0;
    }
    .error-message {
        padding: 1rem;
        border-radius: 5px;
        background-color: #f8d7da;
        color: #721c24;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Header section with logo and title
st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='color: #2c3e50;'>🗺️ Excel to KML Converter</h1>
        <p style='color: #7f8c8d;'>แปลงไฟล์ Excel เป็น KML สำหรับแสดงผลใน Google Earth</p>
    </div>
""", unsafe_allow_html=True)

# Create containers for better organization
upload_container = st.container()
settings_container = st.container()
progress_container = st.container()
download_container = st.container()

with upload_container:
    st.markdown("### 📂 อัปโหลดไฟล์")
    uploaded_file = st.file_uploader(
        "เลือกไฟล์ Excel ของคุณ (รองรับ .xlsx, .xls)",
        type=["xlsx", "xls"],
        help="อัปโหลดไฟล์ Excel ที่มีข้อมูลพิกัด"
    )

if uploaded_file is not None:
    with settings_container:
        st.markdown("### ⚙️ ตั้งค่าการแปลงไฟล์")
        
        # Create two columns for settings
        col1, col2 = st.columns(2)
        
        with col1:
            # Sheet selection
            excel_data = pd.ExcelFile(uploaded_file)
            sheet_names = excel_data.sheet_names
            sheet_name = st.selectbox(
                "📄 เลือก Sheet",
                sheet_names,
                help="เลือก Sheet ที่มีข้อมูลพิกัด"
            )

        with col2:
            # Point removal option
            remove_points = st.checkbox(
                "❌ ลบหมุด (Point)",
                help="เลือกตัวเลือกนี้เพื่อลบหมุดออกจากไฟล์ KML"
            )

    with progress_container:
        status_text = st.empty()
        
        if st.button("🚀 เริ่มแปลงไฟล์", help="คลิกเพื่อเริ่มการแปลงไฟล์"):
            with st.spinner("กำลังประมวลผล..."):
                try:
                    temp_file_path, output_filename, kml_bytes = convert_excel_to_kml(uploaded_file, sheet_name)
                    
                    if kml_bytes:
                        if remove_points:
                            try:
                                tree = ET.parse(temp_file_path)
                                root = tree.getroot()
                                for doc_or_folder in root.findall(".//kml:Document", namespace) + root.findall(".//kml:Folder", namespace):
                                    remove_point_placemarks(doc_or_folder)
                                output_kml = os.path.join(tempfile.gettempdir(), output_filename)
                                tree.write(output_kml, encoding="utf-8", xml_declaration=True)
                                with open(output_kml, "rb") as f:
                                    kml_bytes = BytesIO(f.read())
                                st.success("✅ ลบหมุดเรียบร้อยแล้ว")
                            except Exception as e:
                                st.error(f"❌ เกิดข้อผิดพลาดในการลบหมุด: {str(e)}")
                        
                        with download_container:
                            st.markdown("### 📥 ดาวน์โหลดไฟล์")
                            st.download_button(
                                label="⬇️ ดาวน์โหลดไฟล์ KML",
                                data=kml_bytes,
                                file_name=output_filename,
                                mime="application/vnd.google-earth.kml+xml",
                                help="คลิกเพื่อดาวน์โหลดไฟล์ KML"
                            )
                            
                            st.success("""
                            ✅ การแปลงไฟล์เสร็จสมบูรณ์!
                            \n- คลิกปุ่มด้านบนเพื่อดาวน์โหลดไฟล์ KML
                            \n- เปิดไฟล์ด้วย Google Earth เพื่อดูผลลัพธ์
                            """)
                            
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
else:
    st.info("📝 โปรดอัปโหลดไฟล์ Excel เพื่อเริ่มต้นใช้งาน")

# Footer
st.markdown("""
    <div style='text-align: center; margin-top: 2rem; padding: 1rem; background-color: #f8f9fa; border-radius: 5px;'>
        <p style='color: #6c757d; font-size: 0.9em;'>
            Made with ❤️ by NTSP Team<br>
            <small>Version 1.0.0</small>
        </p>
    </div>
""", unsafe_allow_html=True)
