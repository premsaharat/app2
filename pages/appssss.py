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
    st.success(f"สร้างไฟล์ใหม่สำเร็จ: {output_kml}")

def process_areas_with_red(input_kml_path, boundary_kml_path, output_dir):
    # อ่านไฟล์ขอบเขต (boundary KML)
    boundary_gdf = gpd.read_file(boundary_kml_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    progress_bar = st.progress(0)
    status_text = st.empty()  # สร้าง text placeholder
    output_dir_name = os.path.basename(output_dir)  # ชื่อของโฟลเดอร์ที่บีบอัด

    total_features = len(boundary_gdf)
    for i, boundary_feature in boundary_gdf.iterrows():
        boundary_geom = boundary_feature.geometry
        area_name = boundary_feature.get('name', 'Unnamed Area')  # ใช้ get สำหรับค่าที่อาจไม่มีก็ได้
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

    status_text.text("การประมวลผลเสร็จสิ้น!")  # แสดงข้อความเมื่อการประมวลผลเสร็จสิ้น
    st.success("การประมวลผลเสร็จสิ้น!")

    # บีบอัดโฟลเดอร์เป็น .zip
    zip_file = shutil.make_archive(output_dir_name, 'zip', output_dir)

    # การดาวน์โหลดไฟล์ .zip
    with open(zip_file, "rb") as f:
        st.download_button(
            label=f"📥 ดาวน์โหลดไฟล์ทั้งหมด ({os.path.basename(zip_file)})",
            data=f,
            file_name=os.path.basename(zip_file),
            mime="application/zip"
        )

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
    output_dir = st.text_input("📂 ระบุโฟลเดอร์สำหรับเก็บผลลัพธ์ (เว้นว่างไว้หากไม่ต้องการ)")

    if st.button("🚀 เริ่มประมวลผล", disabled=not (input_file and boundary_file)):
        if input_file and boundary_file:
            # กำหนดโฟลเดอร์ output ถ้าไม่ได้ระบุ
            if not output_dir:
                output_dir = tempfile.mkdtemp()

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
        3. ระบุโฟลเดอร์สำหรับเก็บผลลัพธ์ (หรือเว้นว่างหากไม่ต้องการ)
        4. กดปุ่ม "เริ่มประมวลผล"
        5. รอจนกว่าการประมวลผลจะเสร็จสิ้น
        """)

if __name__ == "__main__":
    main()
