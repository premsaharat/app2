import os
import streamlit as st
from osgeo import ogr
import tempfile

# ฟังก์ชันเดิมสำหรับตัดพื้นที่
def clip_and_combine(input_kml, boundary_geom, output_kml):
    driver = ogr.GetDriverByName("KML")
    input_ds = driver.Open(input_kml, 0)
    if not input_ds:
        st.error(f"ไม่สามารถเปิดไฟล์: {input_kml}")
        return
    
    input_layer = input_ds.GetLayer()
    if os.path.exists(output_kml):
        os.remove(output_kml)
    output_ds = driver.CreateDataSource(output_kml)
    output_layer = output_ds.CreateLayer("clipped", geom_type=ogr.wkbPolygon)

    for feature in input_layer:
        geom = feature.GetGeometryRef()
        if geom.Intersects(boundary_geom):
            clipped_geom = geom.Intersection(boundary_geom)
            output_feature = ogr.Feature(output_layer.GetLayerDefn())
            output_feature.SetGeometry(clipped_geom)
            for field_index in range(feature.GetFieldCount()):
                output_feature.SetField(field_index, feature.GetField(field_index))
            output_layer.CreateFeature(output_feature)
            output_feature = None

    input_ds = None
    output_ds = None
    st.success(f"สร้างไฟล์ใหม่สำเร็จ: {output_kml}")

def process_areas_with_red(input_kml_path, boundary_kml_path, output_dir):
    driver = ogr.GetDriverByName("KML")
    boundary_ds = driver.Open(boundary_kml_path, 0)
    if not boundary_ds:
        st.error(f"ไม่สามารถเปิดไฟล์: {boundary_kml_path}")
        return
    
    boundary_layer = boundary_ds.GetLayer()
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_features = boundary_layer.GetFeatureCount()
    for i, boundary_feature in enumerate(boundary_layer):
        boundary_geom = boundary_feature.GetGeometryRef()
        area_name = boundary_feature.GetField("name")
        if not area_name:
            st.warning("ไม่พบชื่อเขตในข้อมูล")
            continue

        area_output_dir = os.path.join(output_dir, area_name)
        if not os.path.exists(area_output_dir):
            os.makedirs(area_output_dir)

        output_kml = os.path.join(area_output_dir, f"{area_name}.kml")
        clip_and_combine(input_kml_path, boundary_geom, output_kml)
        
        # อัพเดทความคืบหน้า
        progress = (i + 1) / total_features
        progress_bar.progress(progress)
        status_text.text(f"กำลังประมวลผล: {area_name} ({i+1}/{total_features})")

    boundary_ds = None
    status_text.text("การประมวลผลเสร็จสิ้น!")
    st.success("การประมวลผลเสร็จสิ้น!")

# Streamlit UI
def main():
    st.set_page_config(page_title="โปรแกรมตัดพื้นที่จากไฟล์ KML", layout="wide")
    
    # CSS
    st.markdown("""
        <style>
        .stButton>button {
            width: 100%;
            margin: 10px 0;
        }
        .css-1v0mbdj {
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🗺️ โปรแกรมตัดพื้นที่จากไฟล์ KML")
    st.markdown("---")

    # File uploaders
    input_file = st.file_uploader("📁 เลือกไฟล์พื้นที่สีแดง (area.kml)", type=['kml'])
    boundary_file = st.file_uploader("📁 เลือกไฟล์ขอบเขต (boundary.kml)", type=['kml'])
    output_dir = st.text_input("📂 ระบุโฟลเดอร์สำหรับเก็บผลลัพธ์")

    if st.button("🚀 เริ่มประมวลผล", disabled=not (input_file and boundary_file and output_dir)):
        if input_file and boundary_file and output_dir:
            # บันทึกไฟล์ที่อัปโหลดไว้ชั่วคราว
            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_input:
                tmp_input.write(input_file.getvalue())
                input_path = tmp_input.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                tmp_boundary.write(boundary_file.getvalue())
                boundary_path = tmp_boundary.name

            try:
                process_areas_with_red(input_path, boundary_path, output_dir)
            finally:
                # ลบไฟล์ชั่วคราว
                os.unlink(input_path)
                os.unlink(boundary_path)
        else:
            st.error("กรุณาเลือกไฟล์และระบุโฟลเดอร์ให้ครบถ้วน")

    # คำแนะนำการใช้งาน
    with st.expander("📌 คำแนะนำการใช้งาน"):
        st.markdown("""
        1. อัปโหลดไฟล์พื้นที่สีแดง (area.kml)
        2. อัปโหลดไฟล์ขอบเขต (boundary.kml)
        3. ระบุโฟลเดอร์สำหรับเก็บผลลัพธ์
        4. กดปุ่ม "เริ่มประมวลผล"
        5. รอจนกว่าการประมวลผลจะเสร็จสิ้น
        """)

if __name__ == "__main__":
    main()