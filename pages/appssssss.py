import streamlit as st
import xml.etree.ElementTree as ET
import re
import zipfile
import os
from io import BytesIO

def handle_uploaded_file(uploaded_file):
    """จัดการไฟล์ที่อัปโหลดและตรวจสอบประเภทไฟล์"""
    file_details = {
        "FileName": uploaded_file.name,
        "FileType": uploaded_file.type,
        "FileSize": f"{uploaded_file.size / 1024:.2f} KB"
    }
    st.write("File Details:", file_details)
    
    if uploaded_file.name.lower().endswith('.zip'):
        return handle_zip_file(uploaded_file)
    elif uploaded_file.name.lower().endswith('.kml'):
        return uploaded_file
    else:
        st.error(f"Unsupported file type: {uploaded_file.name}")
        return None

def handle_zip_file(zip_file):
    """จัดการไฟล์ ZIP และแสดงรายการไฟล์ภายใน"""
    with zipfile.ZipFile(zip_file) as z:
        # แสดงรายการไฟล์ทั้งหมดใน ZIP
        st.write("Files in ZIP archive:")
        file_list = z.namelist()
        for file in file_list:
            st.write(f"- {file} ({z.getinfo(file).file_size / 1024:.2f} KB)")
        
        # หาไฟล์ KML ทั้งหมด
        kml_files = [f for f in file_list if f.lower().endswith('.kml')]
        
        if not kml_files:
            st.error("No KML files found in the ZIP archive")
            return None
        
        # ถ้ามีหลายไฟล์ ให้ผู้ใช้เลือก
        if len(kml_files) > 1:
            selected_kml = st.selectbox("Select KML file to process:", kml_files)
        else:
            selected_kml = kml_files[0]
            
        # อ่านไฟล์ KML ที่เลือก
        kml_content = z.read(selected_kml)
        return BytesIO(kml_content)

def read_tags_from_file(uploaded_file):
    """อ่านและตรวจสอบความถูกต้องของไฟล์ tags"""
    try:
        content = uploaded_file.getvalue().decode()
        tags = [line.strip() for line in content.split('\n') if line.strip()]
        
        if not tags:
            st.warning("No tags found in the file")
            return None
            
        # แสดงตัวอย่าง tags
        st.write("Preview of tags:")
        for i, tag in enumerate(tags[:5]):  # แสดง 5 tags แรก
            st.write(f"{i+1}. {tag}")
        if len(tags) > 5:
            st.write(f"... and {len(tags)-5} more tags")
            
        return tags
    except Exception as e:
        st.error(f"Error reading tags file: {str(e)}")
        return None

def filter_kml_by_tag(kml_file, target_tags):
    try:
        if isinstance(kml_file, BytesIO):
            tree = ET.parse(kml_file)
        else:
            tree = ET.parse(kml_file)
        root = tree.getroot()

        filtered_placemarks = []
        placemarks = root.findall('.//{http://www.opengis.net/kml/2.2}Placemark')
        tag_regex = r'<td>tag</td>\s*<td>(.*?)</td>'
        
        # สร้าง expander สำหรับแสดงรายละเอียดการประมวลผล
        with st.expander("Processing Details", expanded=False):
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_placemarks = len(placemarks)
            processed = 0
            matched = 0

            for placemark in placemarks:
                processed += 1
                description = placemark.find('{http://www.opengis.net/kml/2.2}description')
                
                progress_bar.progress(processed / total_placemarks)
                status_text.text(f"Processing: {processed}/{total_placemarks} placemarks")
                
                if description is not None:
                    match = re.search(tag_regex, description.text)
                    if match:
                        placemark_tag = match.group(1).strip()
                        if placemark_tag in target_tags:
                            filtered_placemarks.append(placemark)
                            matched += 1
                            st.write(f"✅ Matched tag: {placemark_tag}")
                        else:
                            st.write(f"❌ Unmatched tag: {placemark_tag}")

            st.write(f"Total processed: {processed}")
            st.write(f"Total matched: {matched}")
            
        return filtered_placemarks
    except Exception as e:
        st.error(f"Error processing KML: {str(e)}")
        return None

def write_filtered_kml(filtered_placemarks):
    if filtered_placemarks is None:
        return None
        
    try:
        kml_root = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml_root, 'Document')

        if not filtered_placemarks:
            st.warning("No placemarks found to write")
            return None

        for placemark in filtered_placemarks:
            document.append(placemark)

        tree = ET.ElementTree(kml_root)
        output = BytesIO()
        tree.write(output, xml_declaration=True, encoding='utf-8')
        return output.getvalue()
    except Exception as e:
        st.error(f"Error creating output file: {str(e)}")
        return None

# Streamlit UI
st.title('🗺️ KML File Filter')
st.write("Upload your KML file and tags file to filter placemarks")

# สร้าง columns สำหรับการอัปโหลดไฟล์
col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 KML File")
    uploaded_file = st.file_uploader(
        "Upload KML/ZIP file",
        type=['kml', 'zip'],
        help="Upload either a .kml file or a .zip containing KML files"
    )

with col2:
    st.subheader("🏷️ Tags File")
    uploaded_tags = st.file_uploader(
        "Upload tags file",
        type=['txt'],
        help="Upload a text file containing tags, one per line"
    )

if uploaded_file and uploaded_tags:
    with st.spinner("Processing files..."):
        # อ่านและตรวจสอบไฟล์
        kml_file = handle_uploaded_file(uploaded_file)
        target_tags = read_tags_from_file(uploaded_tags)
        
        if kml_file and target_tags:
            # ประมวลผลและสร้างไฟล์ผลลัพธ์
            filtered_placemarks = filter_kml_by_tag(kml_file, target_tags)
            filtered_kml = write_filtered_kml(filtered_placemarks)
            
            if filtered_kml:
                st.success("Processing completed!")
                st.download_button(
                    label="⬇️ Download filtered KML",
                    data=filtered_kml,
                    file_name="filtered_output.kml",
                    mime="application/vnd.google-earth.kml+xml"
                )

# แสดงคำแนะนำการใช้งาน
with st.expander("ℹ️ วิธีใช้งาน"):
    st.write("""
    1. อัปโหลดไฟล์ KML ของคุณ หรือไฟล์ ZIP ที่มีไฟล์ KML
    2. อัปโหลดไฟล์ข้อความที่มีแท็ก (หนึ่งแท็กต่อบรรทัด)
    3. แอปจะประมวลผลไฟล์ของคุณและแสดงรายละเอียดการประมวลผล
    4. ดาวน์โหลดไฟล์ KML ที่ผ่านการคัดกรองเมื่อการประมวลผลเสร็จสิ้น

    ประเภทไฟล์ที่รองรับ:
    - ไฟล์ KML (.kml)
    - ไฟล์ ZIP ที่มีไฟล์ KML (.zip)
    - ไฟล์ข้อความสำหรับแท็ก (.txt)
    """)

