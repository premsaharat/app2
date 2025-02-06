import os
import re
import pandas as pd
import simplekml
import streamlit as st
from io import BytesIO
from datetime import datetime

# ฟังก์ชันดึงค่าพิกัดจากข้อความโดยใช้ Regex
def parse_coordinates(coord_str):
    try:
        matches = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", coord_str)
        if len(matches) != 2:
            raise ValueError("Invalid coordinate format")
        lat, lon = map(float, matches)
        return lon, lat
    except Exception:
        return None

# ฟังก์ชันแปลง Excel เป็น KML และบันทึกลงโฟลเดอร์
def convert_excel_to_kml(uploaded_file, sheet_name, base_folder):
    try:
        status_text.text("📌 กำลังประมวลผล...")

        # ✅ อ่านไฟล์ Excel
        data = pd.read_excel(uploaded_file, sheet_name=sheet_name)

        # ลบช่องว่างจากชื่อคอลัมน์
        data.columns = data.columns.str.strip()

        # แปลงค่าพิกัด
        data['พิกัด'] = data['พิกัด'].apply(lambda x: parse_coordinates(str(x)) if pd.notna(x) else None)
        data = data.dropna(subset=['พิกัด'])

        # จัดกลุ่มข้อมูลตาม ID
        grouped = data.groupby('id')

        # ✅ สร้างโฟลเดอร์ใหม่ตามวันเวลา
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_folder = os.path.join(base_folder, f"KML_Output_{timestamp}")
        os.makedirs(save_folder, exist_ok=True)

        # ✅ เก็บไฟล์ที่บันทึก
        saved_files = []

        for device_id, group in grouped:
            kml = simplekml.Kml()
            coords = group.sort_values('ลำดับพิกัด')['พิกัด'].tolist()

            # สร้างเส้น (LineString)
            linestring = kml.newlinestring(name=f"{group['ชื่อชุมสาย'].iloc[0]} {device_id}")
            linestring.coords = coords
            linestring.style.linestyle.color = simplekml.Color.blue
            linestring.style.linestyle.width = 3

            # ดึงข้อมูลทั้งหมดเป็น description
            description = "\n".join([f"{col}: {group[col].iloc[0]}" for col in data.columns if col != 'พิกัด'])
            linestring.description = description

            # เพิ่มจุด (Point) สำหรับแต่ละพิกัด
            for _, row in group.iterrows():
                point = kml.newpoint(name=f"จุดที่ {row['ลำดับพิกัด']}", coords=[row['พิกัด']])
                point.description = "\n".join([f"{col}: {row[col]}" for col in data.columns if col != 'พิกัด'])
                point.style.iconstyle.color = simplekml.Color.red

            # ✅ บันทึกไฟล์ KML ลงโฟลเดอร์ที่เลือก
            kml_filename = os.path.join(save_folder, f"{device_id}.kml")
            kml.save(kml_filename)
            saved_files.append(kml_filename)

        status_text.text("✅ ประมวลผลเสร็จสิ้น!")
        return save_folder, saved_files
    except Exception as e:
        status_text.text("❌ เกิดข้อผิดพลาด!")
        st.error(f"เกิดข้อผิดพลาด: {e}")
        return None, None

# ✅ แสดง UI ของเว็บแอป
st.set_page_config(page_title="Excel to KML Converter", layout="centered")
st.title("📍 Excel to KML Converter")

# 🔹 **เพิ่มตัวเลือกไฟล์อัปโหลด**
uploaded_file = st.file_uploader("📂 **เลือกไฟล์ Excel**", type=["xlsx", "xls"])

# 🔹 **เพิ่มช่องให้ใส่โฟลเดอร์หลัก**
base_folder = st.text_input("📁 **ระบุโฟลเดอร์หลักสำหรับเก็บไฟล์ KML**", value=os.getcwd())

# 🔹 ตรวจสอบว่ามีไฟล์หรือไม่
if uploaded_file is not None:
    try:
        # ✅ อ่าน Excel และดึงชื่อ Sheet
        excel_data = pd.ExcelFile(uploaded_file)
        sheet_names = excel_data.sheet_names
        sheet_name = st.selectbox("📄 **เลือก Sheet**", sheet_names)

        # 🔹 ปุ่มเริ่มแปลงไฟล์
        status_text = st.empty()
        if st.button("🚀 เริ่มแปลงเป็น KML"):
            save_folder, saved_files = convert_excel_to_kml(uploaded_file, sheet_name, base_folder)

            if saved_files:
                st.success(f"✅ บันทึกไฟล์ KML สำเร็จที่ `{save_folder}`")
                
                # 🔹 แสดงโฟลเดอร์ที่บันทึก
                st.write(f"📂 **โฟลเดอร์ที่บันทึก:** `{save_folder}`")

                # 🔹 แสดงไฟล์ที่บันทึกสำเร็จ
                for filename in saved_files:
                    st.write(f"📌 `{filename}`")
    except Exception as e:
        st.error(f"❌ ไม่สามารถโหลดไฟล์: {e}")
