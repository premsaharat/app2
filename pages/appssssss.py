import streamlit as st
import xml.etree.ElementTree as ET
import re
import zipfile
import os
from io import BytesIO
from tornado.websocket import WebSocketClosedError

def handle_uploaded_file(uploaded_file):
    """จัดการไฟล์ที่อัปโหลดและตรวจสอบประเภทไฟล์"""
    try:
        file_details = {
            "FileName": uploaded_file.name,
            "FileType": uploaded_file.type,
            "FileSize": f"{uploaded_file.size / 1024:.2f} KB"
        }
        st.write("รายละเอียดไฟล์:", file_details)
        
        if uploaded_file.name.lower().endswith('.zip'):
            return handle_zip_file(uploaded_file)
        elif uploaded_file.name.lower().endswith('.kml'):
            if uploaded_file.name == "ข้อมูลละเมิดในพื้นที่_จังหวัดยะลา.kml":
                return handle_special_kml_file(uploaded_file)
            return BytesIO(uploaded_file.getvalue())
        else:
            st.error(f"ประเภทไฟล์ไม่รองรับ: {uploaded_file.name}")
            return None
    except WebSocketClosedError:
        st.error("การเชื่อมต่อ WebSocket ถูกปิดอย่างไม่คาดคิด")
        return None

def handle_special_kml_file(kml_file):
    """จัดการไฟล์ KML พิเศษสำหรับข้อมูลละเมิดในพื้นที่_จังหวัดยะลา.kml"""
    try:
        kml_content = kml_file.getvalue()
        st.write("กำลังประมวลผลไฟล์ KML พิเศษ: ข้อมูลละเมิดในพื้นที่_จังหวัดยะลา.kml")
        return BytesIO(kml_content)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์ KML พิเศษ: {str(e)}")
        return None

def handle_zip_file(zip_file):
    """จัดการไฟล์ ZIP และแสดงรายการไฟล์ภายใน"""
    with zipfile.ZipFile(zip_file) as z:
        # แสดงรายการไฟล์ทั้งหมดใน ZIP
        st.write("ไฟล์ใน ZIP archive:")
        file_list = z.namelist()
        for file in file_list:
            st.write(f"- {file} ({z.getinfo(file).file_size / 1024:.2f} KB)")
        
        # หาไฟล์ KML ทั้งหมด
        kml_files = [f for f in file_list if f.lower().endswith('.kml')]
        
        if not kml_files:
            st.error("ไม่พบไฟล์ KML ใน ZIP archive")
            return None
        
        # ถ้ามีหลายไฟล์ ให้ผู้ใช้เลือก
        if len(kml_files) > 1:
            selected_kml = st.selectbox("เลือกไฟล์ KML ที่จะประมวลผล:", kml_files)
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
            st.warning("ไม่พบแท็กในไฟล์")
            return None
            
        # แสดงตัวอย่าง tags
        st.write("ตัวอย่างแท็ก:")
        for i, tag in enumerate(tags[:5]):  # แสดง 5 tags แรก
            st.write(f"{i+1}. {tag}")
        if len(tags) > 5:
            st.write(f"... และอีก {len(tags)-5} แท็ก")
            
        return tags
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์แท็ก: {str(e)}")
        return None

def extract_tag_from_description(description_text):
    """
    สกัด tag จากข้อความ description ในรูปแบบต่างๆ
    รองรับทั้งรูปแบบ HTML table และ plain text
    """
    if not description_text:
        return None
        
    # แบบที่ 1: รูปแบบ HTML table <td>field_3</td><td>TCF0020028232</td>
    table_match = re.search(r'<td>field_3</td>\s*<td>(.*?)</td>', description_text)
    if table_match:
        return table_match.group(1).strip()
        
    # แบบที่ 2: รูปแบบ plain text "tag ของสายสื่อสาร TCF0020028487"
    plain_match = re.search(r'tag ของสายสื่อสาร\s*(\S+)', description_text)
    if plain_match:
        return plain_match.group(1).strip()
        
    # แบบที่ 3: หารูปแบบ TCF ทั่วไป (fallback)
    tcf_match = re.search(r'(TCF\d+)', description_text)
    if tcf_match:
        return tcf_match.group(1).strip()
        
    return None

def filter_kml_by_tag(kml_file, target_tags, show_details=False):
    try:
        if isinstance(kml_file, BytesIO):
            kml_file.seek(0)  # รีเซ็ตตัวชี้ไฟล์ไปที่จุดเริ่มต้น
            tree = ET.parse(kml_file)
        else:
            tree = ET.parse(kml_file)
        root = tree.getroot()

        # หา namespace ของ KML
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        filtered_placemarks = []
        placemarks = root.findall('.//kml:Placemark', ns)
        
        # สร้าง expander สำหรับแสดงรายละเอียดการประมวลผล
        with st.expander("รายละเอียดการประมวลผล", expanded=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_placemarks = len(placemarks)
            processed = 0
            matched = 0
            
            st.write(f"พบ {total_placemarks} placemarks ในไฟล์ KML")

            for placemark in placemarks:
                processed += 1
                
                # ดึงข้อมูล description ทั้งรูปแบบ HTML และ plain text
                description = placemark.find('./kml:description', ns)
                
                progress_bar.progress(processed / total_placemarks)
                status_text.text(f"กำลังประมวลผล: {processed}/{total_placemarks} placemarks")
                
                if description is not None and description.text:
                    if show_details:
                        # แสดงตัวอย่างข้อความ description (เฉพาะส่วนแรก)
                        preview = description.text[:100] + "..." if len(description.text) > 100 else description.text
                        st.write(f"Placemark #{processed}: {preview}")
                    
                    # สกัด tag จาก description
                    placemark_tag = extract_tag_from_description(description.text)
                    
                    if placemark_tag:
                        if show_details:
                            st.write(f"พบแท็ก: {placemark_tag}")
                        if placemark_tag in target_tags:
                            filtered_placemarks.append(placemark)
                            matched += 1
                            if show_details:
                                st.write(f"✅ แท็กที่ตรงกัน: {placemark_tag}")
                        else:
                            if show_details:
                                st.write(f"❌ แท็กที่ไม่ตรงกัน: {placemark_tag}")
                    else:
                        if show_details:
                            st.write("❓ ไม่พบแท็กใน placemark นี้")
                else:
                    if show_details:
                        st.write(f"Placemark #{processed}: ไม่พบ description")

            st.write(f"ประมวลผลทั้งหมด: {processed}")
            st.write(f"แท็กที่ตรงกันทั้งหมด: {matched}")
            
        return filtered_placemarks
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผล KML: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def write_filtered_kml(filtered_placemarks, original_kml):
    if filtered_placemarks is None:
        return None
        
    try:
        # อ่าน KML ต้นฉบับเพื่อคัดลอก Style และองค์ประกอบอื่นๆ
        if isinstance(original_kml, BytesIO):
            original_kml.seek(0)  # รีเซ็ตตัวชี้ไฟล์ไปที่จุดเริ่มต้น
            tree = ET.parse(original_kml)
        else:
            tree = ET.parse(original_kml)
        root = tree.getroot()
        
        # หา namespace ของ KML
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        # สร้าง KML ใหม่
        kml_root = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml_root, 'Document')
        
        # คัดลอก Style จาก KML ต้นฉบับ
        for style in root.findall('.//kml:Style', ns) + root.findall('.//kml:StyleMap', ns):
            document.append(style)
            
        # คัดลอก Folder ถ้ามี
        folders = root.findall('.//kml:Folder', ns)
        if folders:
            folder = ET.SubElement(document, 'Folder')
            folder_name = folders[0].find('./kml:name', ns)
            if folder_name is not None:
                name = ET.SubElement(folder, 'name')
                name.text = folder_name.text + " (Filtered)"
            
            for placemark in filtered_placemarks:
                folder.append(placemark)
        else:
            # ถ้าไม่มี Folder ให้เพิ่ม Placemark ลงใน Document โดยตรง
            for placemark in filtered_placemarks:
                document.append(placemark)

        if not filtered_placemarks:
            st.warning("ไม่พบ placemarks ที่จะเขียน")
            return None

        # สร้างไฟล์ KML ใหม่
        tree = ET.ElementTree(kml_root)
        output = BytesIO()
        tree.write(output, xml_declaration=True, encoding='utf-8')
        return output.getvalue()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการสร้างไฟล์ผลลัพธ์: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def main():
    st.title('🗺️ ตัวกรองไฟล์ KML')
    st.write("อัปโหลดไฟล์ KML และไฟล์แท็กของคุณเพื่อกรอง placemarks")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📁 ไฟล์ KML")
        uploaded_file = st.file_uploader(
            "อัปโหลดไฟล์ KML/ZIP",
            type=['kml', 'zip'],
            help="อัปโหลดไฟล์ .kml หรือ .zip ที่มีไฟล์ KML"
        )

    with col2:
        st.subheader("🏷️ ไฟล์แท็ก")
        uploaded_tags = st.file_uploader(
            "อัปโหลดไฟล์แท็ก",
            type=['txt'],
            help="อัปโหลดไฟล์ข้อความที่มีแท็ก หนึ่งแท็กต่อบรรทัด"
        )

    show_details = st.checkbox("แสดงบันทึกการประมวลผลโดยละเอียด", value=False)

    if uploaded_file and uploaded_tags:
        with st.spinner("กำลังประมวลผลไฟล์..."):
            kml_file = handle_uploaded_file(uploaded_file)
            target_tags = read_tags_from_file(uploaded_tags)
            
            if kml_file and target_tags:
                filtered_placemarks = filter_kml_by_tag(kml_file, target_tags, show_details)
                filtered_kml = write_filtered_kml(filtered_placemarks, kml_file)
                
                if filtered_kml:
                    st.success("การประมวลผลเสร็จสิ้น!")
                    st.download_button(
                        label="⬇️ ดาวน์โหลดไฟล์ KML ที่กรองแล้ว",
                        data=filtered_kml,
                        file_name="filtered_output.kml",
                        mime="application/vnd.google-earth.kml+xml"
                    )

    with st.expander("ℹ️ วิธีใช้งาน"):
        st.write("""
        1. อัปโหลดไฟล์ KML ของคุณ หรือไฟล์ ZIP ที่มีไฟล์ KML
        2. อัปโหลดไฟล์ข้อความที่มีแท็ก (หนึ่งแท็กต่อบรรทัด)
        3. โปรแกรมจะประมวลผลไฟล์ของคุณและแสดงรายละเอียดการประมวลผล
        4. ดาวน์โหลดไฟล์ KML ที่ผ่านการคัดกรองเมื่อการประมวลผลเสร็จสิ้น

        ประเภทไฟล์ที่รองรับ:
        - ไฟล์ KML (.kml)
        - ไฟล์ ZIP ที่มีไฟล์ KML (.zip)
        - ไฟล์ข้อความสำหรับแท็ก (.txt)
        """)

if __name__ == "__main__":
    main()
