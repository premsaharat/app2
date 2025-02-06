import os
import streamlit as st
import geopandas as gpd
import tempfile

def clip_and_combine(input_kml, boundary_geom, output_kml):
    # อ่านไฟล์ KML ด้วย GeoPandas
    input_gdf = gpd.read_file(input_kml, driver='KML')
    
    # ทำการ clip
    clipped = gpd.clip(input_gdf, boundary_geom)
    
    # บันทึกผลลัพธ์
    clipped.to_file(output_kml, driver='KML')
    st.success(f"สร้างไฟล์ใหม่สำเร็จ: {output_kml}")

def process_areas_with_red(input_kml_path, boundary_kml_path, output_dir):
    # อ่านไฟล์ขอบเขต
    boundary_gdf = gpd.read_file(boundary_kml_path, driver='KML')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_features = len(boundary_gdf)
    
    for i, (idx, boundary_row) in enumerate(boundary_gdf.iterrows()):
        boundary_geom = boundary_row.geometry
        area_name = boundary_row.get('name', f'area_{i}')
        
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
