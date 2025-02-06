import tempfile
import os
import geopandas as gpd
import streamlit as st
import shutil

def clip_and_combine(input_kml, boundary_geom, output_kml):
    input_gdf = gpd.read_file(input_kml)
    clipped_gdf = input_gdf[input_gdf.intersects(boundary_geom)]
    clipped_gdf.to_file(output_kml, driver="KML")

def process_areas(input_kml_path, boundary_kml_path, output_dir, input_filename):
    boundary_gdf = gpd.read_file(boundary_kml_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_files = []
    
    for i, boundary_feature in boundary_gdf.iterrows():
        boundary_geom = boundary_feature.geometry
        area_name = boundary_feature.get('name', f'{os.path.splitext(input_filename)[0]}_area_{i}')
        output_kml = os.path.join(output_dir, f"{area_name}.kml")
        
        clip_and_combine(input_kml_path, boundary_geom, output_kml)
        output_files.append(output_kml)
        
        # Show progress
        progress = (i + 1) / len(boundary_gdf)
        st.progress(progress)
        st.write(f"กำลังประมวลผล: {area_name}")
    
    return output_files

st.title("โปรแกรมตัดพื้นที่จากไฟล์ KML")

# File uploaders
input_file = st.file_uploader("เลือกไฟล์พื้นที่สีแดง (area.kml)", type=['kml'])
boundary_file = st.file_uploader("เลือกไฟล์ขอบเขต (boundary.kml)", type=['kml'])
output_dir = st.text_input("ระบุโฟลเดอร์สำหรับเก็บผลลัพธ์ (เว้นว่างไว้หากไม่ต้องการ)")

if st.button("เริ่มประมวลผล", disabled=not (input_file and boundary_file)):
    try:
        # Create temp directory if no output dir specified
        if not output_dir:
            output_dir = tempfile.mkdtemp()
            
        # Save uploaded files to temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_input:
            tmp_input.write(input_file.getvalue())
            input_path = tmp_input.name
            input_filename = os.path.basename(tmp_input.name)  # Get the uploaded file name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
            tmp_boundary.write(boundary_file.getvalue())
            boundary_path = tmp_boundary.name

        # Process files
        output_files = process_areas(input_path, boundary_path, output_dir, input_filename)
        
        # Show download buttons
        st.success("การประมวลผลเสร็จสิ้น!")
        
        if output_dir == tempfile.mkdtemp():  # Check if the output is temporary
            # Compress the output directory into a zip file for download
            zip_output = f"{output_dir}.zip"
            shutil.make_archive(zip_output.replace('.zip', ''), 'zip', output_dir)
            
            with open(zip_output, "rb") as f:
                st.download_button(
                    "ดาวน์โหลดโฟลเดอร์ผลลัพธ์ (ZIP)",
                    data=f,
                    file_name=os.path.basename(zip_output),
                    mime="application/zip"
                )
        else:
            for i, file in enumerate(output_files):
                with open(file, "rb") as f:
                    st.download_button(
                        f"ดาวน์โหลด {os.path.basename(file)}",
                        data=f,
                        file_name=os.path.basename(file),
                        mime="application/vnd.google-earth.kml+xml",
                        key=f"btn_{i}"
                    )
                
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {str(e)}")
        
    finally:
        # Cleanup temp files
        if 'input_path' in locals(): os.unlink(input_path)
        if 'boundary_path' in locals(): os.unlink(boundary_path)

st.markdown("""
### คำแนะนำการใช้งาน
1. อัปโหลดไฟล์พื้นที่สีแดง (area.kml)
2. อัปโหลดไฟล์ขอบเขต (boundary.kml)
3. ระบุโฟลเดอร์สำหรับเก็บผลลัพธ์ (หรือเว้นว่างไว้)
4. กดปุ่ม "เริ่มประมวลผล"
""")
