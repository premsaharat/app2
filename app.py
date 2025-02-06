import os
import re
import pandas as pd
import simplekml
import streamlit as st
from io import BytesIO
import tempfile  # ✅ ใช้โฟลเดอร์ชั่วคราว
from datetime import datetime
import xml.etree.ElementTree as ET

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

# ฟังก์ชันแปลง Excel เป็น KML โดยแยก ID ในโฟลเดอร์
def convert_excel_to_kml(uploaded_file, sheet_name):
    try:
        status_text.text("📌 กำลังประมวลผล...")

        # ✅ อ่านไฟล์ Excel
        data = pd.read_excel(uploaded_file, sheet_name=sheet_name)

        # ลบช่องว่างจากชื่อคอลัมน์
        data.columns = data.columns.str.strip()

        # แปลงค่าพิกัด
        data['พิกัด'] = data['พิกัด'].apply(lambda x: parse_coordinates(str(x)) if pd.notna(x) else None)
        data = data.dropna(subset=['พิกัด'])

        # ✅ สร้างไฟล์ KML
        kml = simplekml.Kml()

        # ✅ สร้างโฟลเดอร์หลัก
        main_folder = kml.newfolder(name="ข้อมูลทั้งหมด")

        # ✅ จัดกลุ่มข้อมูลตาม ID และสร้างโฟลเดอร์แยก
        for device_id, group in data.groupby('id'):
            folder = main_folder.newfolder(name=f"ID: {device_id}")  # ✅ สร้างโฟลเดอร์แยกตาม ID
            coords = group.sort_values('ลำดับพิกัด')['พิกัด'].tolist()

            # ✅ สร้างเส้น (LineString) ในโฟลเดอร์ของแต่ละ ID
            linestring = folder.newlinestring(name=f"{group['ชื่อชุมสาย'].iloc[0]} {device_id}")
            linestring.coords = coords
            linestring.style.linestyle.color = simplekml.Color.blue
            linestring.style.linestyle.width = 3

            # ✅ ดึงข้อมูลทั้งหมดเป็น description
            description = "\n".join([f"{col}: {group[col].iloc[0]}" for col in data.columns if col != 'พิกัด'])
            linestring.description = description

            # ✅ เพิ่มจุด (Point) สำหรับแต่ละพิกัดในโฟลเดอร์ของ ID นั้น
            for _, row in group.iterrows():
                point = folder.newpoint(name=f"จุดที่ {row['ลำดับพิกัด']}", coords=[row['พิกัด']])
                point.description = "\n".join([f"{col}: {row[col]}" for col in data.columns if col != 'พิกัด'])
                point.style.iconstyle.color = simplekml.Color.red

        # ✅ ใช้โฟลเดอร์ชั่วคราวแทน `/tmp/`
        temp_dir = tempfile.gettempdir()
        output_filename = os.path.splitext(uploaded_file.name)[0] + ".kml"
        temp_file_path = os.path.join(temp_dir, output_filename)

        # ✅ บันทึกไฟล์ KML ลงโฟลเดอร์ชั่วคราว
        kml.save(temp_file_path)

        # ✅ โหลดไฟล์ KML กลับเป็น BytesIO
        with open(temp_file_path, "rb") as f:
            kml_bytes = BytesIO(f.read())

        status_text.text("✅ ประมวลผลเสร็จสิ้น!")

        return temp_file_path, output_filename, kml_bytes

    except Exception as e:
        status_text.text("❌ เกิดข้อผิดพลาด!")
        st.error(f"เกิดข้อผิดพลาด: {e}")
        return None, None, None

# ค้นหา Namespace (KML ใช้ namespace)
namespace = {'kml': 'http://www.opengis.net/kml/2.2'}

# ฟังก์ชันลบเฉพาะ Placemark ที่เป็นจุด (Point)
def remove_point_placemarks(parent):
    for placemark in parent.findall("kml:Placemark", namespace):
        # ถ้ามีโหนด <Point> แสดงว่าเป็นหมุด ให้ลบออก
        if placemark.find("kml:Point", namespace) is not None:
            parent.remove(placemark)  

# 🔹 แสดง UI ของเว็บแอป
st.set_page_config(page_title="Excel to KML (NTSP)", layout="centered")
st.title("📍 Excel to KML (NTSP)")

# 🔹 **เพิ่มตัวเลือกไฟล์อัปโหลด**
uploaded_file = st.file_uploader("📂 **เลือกไฟล์ Excel**", type=["xlsx", "xls"])

# 🔹 ตรวจสอบว่ามีไฟล์หรือไม่
if uploaded_file is not None:
    try:
        # ✅ อ่าน Excel และดึงชื่อ Sheet
        excel_data = pd.ExcelFile(uploaded_file)
        sheet_names = excel_data.sheet_names
        sheet_name = st.selectbox("📄 **เลือก Sheet**", sheet_names)

        # 🔹 ปุ่มเริ่มแปลงไฟล์
        status_text = st.empty()
        remove_points = st.checkbox("❌ ลบหมุด (Point)")

        if st.button("🚀 เริ่มแปลงเป็น KML"):
            temp_file_path, output_filename, kml_bytes = convert_excel_to_kml(uploaded_file, sheet_name)

            if kml_bytes:
                st.success("✅ แปลงไฟล์ KML สำเร็จ!")

                # 🔹 ลบหมุดจาก KML ถ้าผู้ใช้เลือก
                if remove_points:
                    try:
                        tree = ET.parse(temp_file_path)
                        root = tree.getroot()

                        # ลบหมุดจากโฟลเดอร์/เอกสารทั้งหมด
                        for doc_or_folder in root.findall(".//kml:Document", namespace) + root.findall(".//kml:Folder", namespace):
                            remove_point_placemarks(doc_or_folder)

                        # ✅ บันทึกไฟล์ KML ใหม่หลังจากลบหมุด
                        output_kml = os.path.join(tempfile.gettempdir(), output_filename)
                        tree.write(output_kml, encoding="utf-8", xml_declaration=True)

                        # ✅ โหลดไฟล์ KML ใหม่ที่ไม่มีหมุด
                        with open(output_kml, "rb") as f:
                            kml_bytes = BytesIO(f.read())

                        st.success("✔ ลบหมุดสำเร็จ!")

                    except Exception as e:
                        st.error(f"❌ เกิดข้อผิดพลาดในการลบหมุด: {e}")
                        st.exception(e)

                # 🔹 ให้ผู้ใช้ดาวน์โหลดไฟล์ KML
                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์ KML",
                    data=kml_bytes,
                    file_name=output_filename,
                    mime="application/vnd.google-earth.kml+xml"
                )

    except Exception as e:
        st.error(f"❌ ไม่สามารถโหลดไฟล์: {e}")
