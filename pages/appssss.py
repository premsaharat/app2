import os
import shutil
import tempfile
import streamlit as st
import geopandas as gpd

def clip_and_combine(input_kml, boundary_geom, output_kml):
    # อ่านไฟล์ KML ด้วย geopandas
    input_gdf = gpd.read_file(input_kml)
    if input_gdf.empty:
        st.error(f"ไม่สามารถเปิดไฟล์: {input_kml}")
        return
    
    # ตรวจสอบว่า geodataframe มีข้อมูลและตัดพื้นที่
    clipped_gdf = input_gdf[input_gdf.geometry.intersects(boundary_geom)]
    clipped_gdf['geometry'] = clipped_gdf.geometry.intersection(boundary_geom)

    # เขียนผลลัพธ์ลงไฟล์ KML
    clipped_gdf.to_file(output_kml, driver='KML')
    st.success(f"สร้างไฟล์ใหม่สำเร็จ: {output_kml}")

def process_areas_with_red(input_kml_path, boundary_kml_path, output_dir):
    boundary_gdf = gpd.read_file(boundary_kml_path)
    if boundary_gdf.empty:
        st.error(f"ไม่สามารถเปิดไฟล์: {boundary_kml_path}")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    progress_bar = st.progress(0)
    status_text = st.empty()

    total_features = len(boundary_gdf)
    for i, boundary_row in boundary_gdf.iterrows():
        boundary_geom = boundary_row.geometry
        area_name = boundary_row.get("name", f"area_{i}")

        area_output_dir = os.path.join(output_dir, area_name)
        if not os.path.exists(area_output_dir):
            os.makedirs(area_output_dir)

        output_kml = os.path.join(area_output_dir, f"{area_name}.kml")
        clip_and_combine(input_kml_path, boundary_geom, output_kml)

        progress = (i + 1) / total_features
        progress_bar.progress(progress)
        status_text.text(f"กำลังประมวลผล: {area_name} ({i+1}/{total_features})")

    status_text.text("การประมวลผลเสร็จสิ้น!")
    st.success("การประมวลผลเสร็จสิ้น!")

    return output_dir

def main():
    st.set_page_config(page_title="โปรแกรมตัดพื้นที่จากไฟล์ KML", layout="wide")
    st.title("🗺️ โปรแกรมตัดพื้นที่จากไฟล์ KML")
    st.markdown("---")

    input_file = st.file_uploader("📁 เลือกไฟล์พื้นที่สีแดง (area.kml)", type=['kml'])
    boundary_file = st.file_uploader("📁 เลือกไฟล์ขอบเขต (boundary.kml)", type=['kml'])
    output_dir = st.text_input("📂 ระบุโฟลเดอร์สำหรับเก็บผลลัพธ์")

    if st.button("🚀 เริ่มประมวลผล", disabled=not (input_file and boundary_file)):
        if input_file and boundary_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_input:
                tmp_input.write(input_file.getvalue())
                input_path = tmp_input.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                tmp_boundary.write(boundary_file.getvalue())
                boundary_path = tmp_boundary.name

            try:
                result_dir = process_areas_with_red(input_path, boundary_path, output_dir or tempfile.mkdtemp())
                if output_dir == "":  # ถ้าไม่ได้กรอกโฟลเดอร์
                    # บีบอัดโฟลเดอร์เพื่อให้ดาวน์โหลด
                    shutil.make_archive(result_dir, 'zip', result_dir)
                    zip_file = f"{result_dir}.zip"
                    with open(zip_file, "rb") as f:
                        st.download_button(
                            label="📥 ดาวน์โหลดไฟล์ผลลัพธ์",
                            data=f,
                            file_name="result.zip",
                            mime="application/zip"
                        )
            finally:
                os.unlink(input_path)
                os.unlink(boundary_path)

        else:
            st.error("กรุณาเลือกไฟล์ให้ครบถ้วน")

if __name__ == "__main__":
    main()
