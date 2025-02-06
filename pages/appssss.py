import shutil
import tempfile
import os
import geopandas as gpd
import streamlit as st

# ฟังก์ชันเดิมสำหรับตัดพื้นที่
def clip_and_combine(input_kml, boundary_geom, output_kml):
    # อ่านไฟล์ KML โดยใช้ geopandas
    input_gdf = gpd.read_file(input_kml)
    # ตัดพื้นที่โดยใช้ boundary_geom
    clipped_gdf = input_gdf[input_gdf.intersects(boundary_geom)]
    # บันทึกผลลัพธ์เป็นไฟล์ KML
    clipped_gdf.to_file(output_kml, driver="KML")
    st.success(f"สร้างไฟล์ใหม่สำเร็จ: {output_kml}", key="success_clip")

def process_areas_with_red(input_kml_path, boundary_kml_path, output_dir):
    # อ่านไฟล์ขอบเขต (boundary KML)
    boundary_gdf = gpd.read_file(boundary_kml_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    progress_bar = st.progress(0, key="progress_bar")
    status_text = st.empty()

    total_features = len(boundary_gdf)
    output_files = []  # ลิสต์สำหรับเก็บไฟล์ทั้งหมด
    
    for i, boundary_feature in boundary_gdf.iterrows():
        boundary_geom = boundary_feature.geometry
        area_name = boundary_feature.get('name', f'area_{i}')
        
        output_kml = os.path.join(output_dir, f"{area_name}.kml")
        clip_and_combine(input_kml_path, boundary_geom, output_kml)
        output_files.append(output_kml)

        # อัพเดทความคืบหน้า
        progress = (i + 1) / total_features
        progress_bar.progress(progress)
        status_text.text(f"กำลังประมวลผล: {area_name} ({i+1}/{total_features})")

    status_text.text("การประมวลผลเสร็จสิ้น!")
    st.success("การประมวลผลเสร็จสิ้น!", key="success_final")

    # แสดงปุ่มดาวน์โหลดไฟล์ทั้งหมด
    if output_files:
        for i, file in enumerate(output_files):
            with open(file, "rb") as f:
                st.download_button(
                    label=f"ดาวน์โหลด {os.path.basename(file)}",
                    data=f,
                    file_name=os.path.basename(file),
                    mime="application/vnd.google-earth.kml+xml",
                    key=f"download_{i}"
                )

def main():
    st.set_page_config(page_title="โปรแกรมตัดพื้นที่จากไฟล์ KML", layout="wide")
    
    st.title("โปรแกรมตัดพื้นที่จากไฟล์ KML")
    st.markdown("---")

    # File uploaders
    input_file = st.file_uploader("เลือกไฟล์พื้นที่สีแดง (area.kml)", type=['kml'], key="input_uploader")
    boundary_file = st.file_uploader("เลือกไฟล์ขอบเขต (boundary.kml)", type=['kml'], key="boundary_uploader")
    output_dir = st.text_input("ระบุโฟลเดอร์สำหรับเก็บผลลัพธ์ (เว้นว่างไว้หากไม่ต้องการ)", key="output_dir_input")

    if st.button("เริ่มประมวลผล", disabled=not (input_file and boundary_file), key="start_button"):
        if input_file and boundary_file:
            if not output_dir:
                output_dir = tempfile.mkdtemp()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_input:
                tmp_input.write(input_file.getvalue())
                input_path = tmp_input.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                tmp_boundary.write(boundary_file.getvalue())
                boundary_path = tmp_boundary.name

            try:
                process_areas_with_red(input_path, boundary_path, output_dir)
            finally:
                os.unlink(input_path)
                os.unlink(boundary_path)
        else:
            st.error("กรุณาเลือกไฟล์ให้ครบถ้วน", key="error_message")

    with st.expander("คำแนะนำการใช้งาน", key="help_expander"):
        st.markdown("""
        1. อัปโหลดไฟล์พื้นที่สีแดง (area.kml)
        2. อัปโหลดไฟล์ขอบเขต (boundary.kml)
        3. ระบุโฟลเดอร์สำหรับเก็บผลลัพธ์ (หรือเว้นว่างหากไม่ต้องการ)
        4. กดปุ่ม "เริ่มประมวลผล"
        5. รอจนกว่าการประมวลผลจะเสร็จสิ้น
        """)

if __name__ == "__main__":
    main()
