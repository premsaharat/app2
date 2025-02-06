import os
import streamlit as st
from osgeo import ogr
import tempfile
import zipfile
from lxml import etree

# ฟังก์ชันสำหรับตัดพื้นที่สีแดง
def clip_and_combine(input_kml, boundary_geom, output_kml):
    try:
        tree = etree.parse(input_kml)
        root = tree.getroot()

        # ค้นหาภายในเอกสาร KML
        for placemark in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
            coordinates = placemark.find(".//{http://www.opengis.net/kml/2.2}coordinates")
            if coordinates is not None:
                # แยกพิกัดและตรวจสอบว่าแต่ละพิกัดมีค่า longitude และ latitude
                coord_list = coordinates.text.strip().split()
                for coord in coord_list:
                    # ตรวจสอบว่าแต่ละพิกัดประกอบด้วย 2 ค่า
                    try:
                        lon, lat = map(float, coord.split(","))
                        # ตรวจสอบว่า point อยู่ใน boundary_geom
                        if lon < boundary_geom["lon_max"] and lon > boundary_geom["lon_min"] and lat < boundary_geom["lat_max"] and lat > boundary_geom["lat_min"]:
                            continue
                        else:
                            placemark.getparent().remove(placemark)  # ลบ Placemark หากอยู่นอกพื้นที่ที่กำหนด
                    except ValueError:
                        # หากไม่สามารถแปลงพิกัดได้ ให้ข้ามไป
                        continue

        # บันทึกไฟล์ KML หลังจากตัดข้อมูล
        tree.write(output_kml)

        return output_kml
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการตัดข้อมูล: {e}")
        return None

# ฟังก์ชันสำหรับประมวลผลทุกเขต
def process_areas_with_red(input_kml, boundary_kml):
    driver = ogr.GetDriverByName("KML")
    boundary_ds = driver.Open(boundary_kml, 0)
    if not boundary_ds:
        st.error(f"ไม่สามารถเปิดไฟล์: {boundary_kml}")
        return None
    
    boundary_layer = boundary_ds.GetLayer()
    output_files = []  # สร้างรายการสำหรับไฟล์ KML ที่ได้

    for boundary_feature in boundary_layer:
        boundary_geom = boundary_feature.GetGeometryRef()
        area_name = boundary_feature.GetField("name")
        if not area_name:
            st.warning("ไม่พบชื่อเขตในข้อมูล")
            continue

        output_kml = f"{area_name}.kml"
        output_kml = clip_and_combine(input_kml, boundary_geom, output_kml)
        if output_kml:
            output_files.append(output_kml)  # เพิ่มไฟล์ KML ลงในรายการ

    boundary_ds = None
    return output_files  # ส่งคืนรายการไฟล์ที่สร้างขึ้น

# ฟังก์ชันสำหรับการรวมไฟล์ KML
def combine_kml_files(output_files):
    driver = ogr.GetDriverByName("KML")
    combined_output_kml = tempfile.NamedTemporaryFile(delete=False, suffix='.kml')

    # สร้างไฟล์ KML ใหม่สำหรับรวมข้อมูลทั้งหมด
    output_ds = driver.CreateDataSource(combined_output_kml.name)
    output_layer = output_ds.CreateLayer("combined", geom_type=ogr.wkbPolygon)

    for file in output_files:
        input_ds = driver.Open(file, 0)
        input_layer = input_ds.GetLayer()

        for feature in input_layer:
            output_layer.CreateFeature(feature)

        input_ds = None

    output_ds = None
    return combined_output_kml.name  # ส่งคืนชื่อไฟล์ KML ที่รวมแล้ว

# ฟังก์ชันสำหรับดาวน์โหลดไฟล์ทั้งหมดในรูปแบบ ZIP
def create_zip_for_download(output_files):
    zip_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    with zipfile.ZipFile(zip_file, 'w') as zipf:
        for file in output_files:
            zipf.write(file, os.path.basename(file))

    return zip_file.name  # ส่งคืนเส้นทางของไฟล์ ZIP

# Streamlit UI
def main():
    st.set_page_config(page_title="โปรแกรมตัดพื้นที่จาก KML", layout="wide")

    st.title("🗺️ โปรแกรมตัดพื้นที่จากไฟล์ KML")
    st.markdown("---")

    # Upload file sections
    input_file = st.file_uploader("📁 เลือกไฟล์เส้นพื้นที่ที่ต้องการตรวจสอบ ( * ไฟล์ kml เท่านั้น * )", type=['kml'])
    boundary_file = st.file_uploader("📁 เลือกไฟล์ขอบเขต ( * ไฟล์ kml เท่านั้น * )", type=['kml'])

    # สร้าง 2 คอลัมน์เพื่อแยกปุ่ม
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 เริ่มประมวลผลแยกไฟล์ KML"):
            if input_file and boundary_file:
                # บันทึกไฟล์ที่อัปโหลดไว้ชั่วคราว
                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_input:
                    tmp_input.write(input_file.getvalue())
                    input_path = tmp_input.name

                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                    tmp_boundary.write(boundary_file.getvalue())
                    boundary_path = tmp_boundary.name

                try:
                    output_files = process_areas_with_red(input_path, boundary_path)
                    
                    if output_files:
                        # ปุ่มดาวน์โหลดไฟล์แยก
                        zip_file_path = create_zip_for_download(output_files)
                        with open(zip_file_path, "rb") as f:
                            st.download_button(
                                label="📦 ดาวน์โหลดไฟล์ KML ทุกไฟล์",
                                data=f,
                                file_name="output_files.zip",
                                mime="application/zip"
                            )

                finally:
                    # ลบไฟล์ชั่วคราว
                    os.unlink(input_path)
                    os.unlink(boundary_path)

            else:
                st.error("กรุณาเลือกไฟล์ให้ครบถ้วน")

    with col2:
        if st.button("🚀 เริ่มประมวลผลรวมไฟล์ KML"):
            if input_file and boundary_file:
                # บันทึกไฟล์ที่อัปโหลดไว้ชั่วคราว
                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_input:
                    tmp_input.write(input_file.getvalue())
                    input_path = tmp_input.name

                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                    tmp_boundary.write(boundary_file.getvalue())
                    boundary_path = tmp_boundary.name

                try:
                    output_files = process_areas_with_red(input_path, boundary_path)
                    
                    if output_files:
                        # ปุ่มดาวน์โหลดไฟล์ KML รวม
                        combined_kml = combine_kml_files(output_files)
                        with open(combined_kml, "rb") as f:
                            st.download_button(
                                label="🔗 ดาวน์โหลดไฟล์ KML รวม",
                                data=f,
                                file_name="combined_output.kml",
                                mime="application/vnd.google-earth.kml+xml"
                            )

                finally:
                    # ลบไฟล์ชั่วคราว
                    os.unlink(input_path)
                    os.unlink(boundary_path)

            else:
                st.error("กรุณาเลือกไฟล์ให้ครบถ้วน")

    # คำแนะนำการใช้งาน
    with st.expander("📌 คำแนะนำการใช้งาน"):
        st.markdown("""
        1. อัปโหลดไฟล์เส้นพื้นที่ที่ต้องการตรวจสอบ ( * ไฟล์ kml เท่านั้น *) 
        2. อัปโหลดไฟล์ขอบเขต ( * ไฟล์ kml เท่านั้น * )
        3. กดปุ่ม "เริ่มประมวลผลแยกไฟล์ KML" เพื่อดาวน์โหลดไฟล์แยกทั้งหมดในรูปแบบ ZIP
        4. กดปุ่ม "เริ่มประมวลผลรวมไฟล์ KML" เพื่อดาวน์โหลดไฟล์ KML ที่รวมทุกเขต
        """)

if __name__ == "__main__":
    main()
