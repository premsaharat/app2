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

# ฟังก์ชันดึงพิกัดจากข้อความที่มีหลายพิกัด
def parse_multiple_coordinates(coord_str):
    try:
        coord_pairs = re.findall(r"\(([^)]+)\)", coord_str)
        coordinates = [parse_coordinates(pair) for pair in coord_pairs]
        return [coord for coord in coordinates if coord is not None]
    except Exception:
        return []

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

# ฟังก์ชันแปลงพิกัดที่ตกหล่นเป็น KML
def convert_missing_coords_to_kml(additional_coords_str, status_text, description_dict=None):
    try:
        status_text.text("📌 กำลังประมวลผล...")

        # ✅ สร้างไฟล์ KML
        kml = simplekml.Kml()

        # ✅ สร้างโฟลเดอร์หลัก
        main_folder = kml.newfolder(name="พิกัดที่ตกหล่น")

        # ✅ เพิ่มพิกัดเพิ่มเติมถ้ามี
        if additional_coords_str:
            additional_coords = parse_multiple_coordinates(additional_coords_str)

            # ✅ สร้างเส้น (LineString) ในโฟลเดอร์หลัก
            linestring_name = f"{description_dict.get('ชื่อชุมสาย', '')} {description_dict.get('id', '')}"
            linestring = main_folder.newlinestring(name=linestring_name)
            linestring.coords = additional_coords
            linestring.style.linestyle.color = simplekml.Color.blue
            linestring.style.linestyle.width = 3
            
            # ✅ เพิ่ม description ให้กับ LineString
            if description_dict:
                desc_text = "\n".join([f"{key}: {value}" for key, value in description_dict.items()])
                linestring.description = desc_text

            # ✅ เพิ่มจุด (Point) สำหรับแต่ละพิกัด
            for i, coord in enumerate(additional_coords):
                point = main_folder.newpoint(name=f"จุดที่ {i+1}", coords=[coord])
                point.style.iconstyle.color = simplekml.Color.red
                
                # ✅ เพิ่ม description ให้กับแต่ละจุด
                if description_dict:
                    point.description = desc_text

        # ✅ ใช้โฟลเดอร์ชั่วคราวแทน `/tmp/`
        temp_dir = tempfile.gettempdir()
        output_filename = f"{description_dict.get('id', 'missing_coords')}.kml"
        if not description_dict.get('id'):
            output_filename = "missing_coords.kml"
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

# 🔹 ส่วนสำหรับเพิ่มพิกัดที่ตกหล่น
st.header("📍 เพิ่มพิกัดที่ตกหล่น")
additional_coords_str = st.text_area("📍 เพิ่มพิกัดเพิ่มเติม (รูปแบบ: (lat,lon)(lat,lon))", key="missing_coords_text_area")

# ✅ เพิ่มส่วนสำหรับใส่ description
st.subheader("รายละเอียด (Description)")

# ✅ ถ้ามีไฟล์ Excel ให้ดึงชื่อ column มาแสดงเป็นตัวเลือกให้ผู้ใช้กรอก
if uploaded_file is not None:
    try:
        # ✅ อ่านไฟล์ Excel และดึงชื่อคอลัมน์
        excel_data = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        columns = excel_data.columns.tolist()
        
        # สร้าง dictionary เก็บข้อมูล description
        description_dict = {}
        
        # ✅ สร้าง input field สำหรับแต่ละคอลัมน์
        headers = ["id", "วันที่สร้าง", "รหัสอุปกรณ์", "ชื่ออุปกรณ์", "รายละเอียด", "unit_in", "รุ่น", "ยี่ห้อ", "ชื่อโปรเจค", "ชื่อศูนย์บริการ", "ชื่อชุมสาย", "type", "ระยะทาง", "ลำดับพิกัด"]
        for header in headers:
            if header in columns:
                value = st.text_input(f"{header}")
                if value:  # เก็บเฉพาะข้อมูลที่ผู้ใช้กรอก
                    description_dict[header] = value
    
    except Exception as e:
        # ถ้าไม่สามารถอ่านคอลัมน์ได้ ให้ใช้ input fields ทั่วไป
        headers = ["id", "วันที่สร้าง", "รหัสอุปกรณ์", "ชื่ออุปกรณ์", "รายละเอียด", "unit_in", "รุ่น", "ยี่ห้อ", "ชื่อโปรเจค", "ชื่อศูนย์บริการ", "ชื่อชุมสาย", "type", "ระยะทาง", "ลำดับพิกัด"]
        description_dict = {header: st.text_input(f"{header}") for header in headers}
else:
    # ✅ ถ้าไม่มีไฟล์ Excel ให้สร้าง input fields พื้นฐาน
    headers = ["id", "วันที่สร้าง", "รหัสอุปกรณ์", "ชื่ออุปกรณ์", "รายละเอียด", "unit_in", "รุ่น", "ยี่ห้อ", "ชื่อโปรเจค", "ชื่อศูนย์บริการ", "ชื่อชุมสาย", "type", "ระยะทาง", "ลำดับพิกัด"]
    description_dict = {header: st.text_input(f"{header}") for header in headers}

remove_points = st.checkbox("❌ ลบหมุด (Point)", key="missing_coords_remove_points")

if st.button("🚀 สร้างไฟล์ KML จากพิกัดที่ตกหล่น"):
    status_text = st.empty()
    # ✅ ส่ง description_dict ไปยัง function
    temp_file_path, output_filename, kml_bytes = convert_missing_coords_to_kml(additional_coords_str, status_text, description_dict)

    if kml_bytes:
        st.success("✅ สร้างไฟล์ KML สำเร็จ!")

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
