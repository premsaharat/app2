import streamlit as st
from lxml import etree
from concurrent.futures import ThreadPoolExecutor
import os
import tempfile
from shapely.geometry import LineString
from shapely.ops import split
import numpy as np

# CSS สำหรับปรับแต่งรูปแบบ UI ที่รองรับทั้งโหมดมืดและโหมดสว่าง
st.markdown("""
<style>
    /* ตั้งค่าสีหลักสำหรับทั้งโหมดมืดและสว่าง */
    :root {
        --bg-primary: #ffffff;
        --bg-secondary: #f0f0f0;
        --bg-tertiary: #e0e0e0;
        --text-primary: #000000;
        --text-secondary: #333333;
        --accent-primary: #4f8bf9;
        --accent-secondary: #3776cc;
        --success-color: #1db954;
        --warning-color: #ff9800;
        --error-color: #f44336;
        --border-color: #cccccc;
    }
    
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-primary: #121212;
            --bg-secondary: #1e1e1e;
            --bg-tertiary: #2a2a2a;
            --text-primary: #e0e0e0;
            --text-secondary: #b0b0b0;
            --border-color: #444444;
        }
    }
    
    /* สไตล์หลัก */
    .main-header {
        color: var(--text-primary);
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        text-align: center;
    }
    
    .sub-header {
        color: var(--text-secondary);
        font-size: 1.2rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    /* ส่วนของ Radio Button */
    .stRadio > div {
        background-color: var(--bg-tertiary);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid var(--border-color);
    }
    
    /* ปุ่มต่างๆ */
    .stButton > button {
        background-color: var(--accent-primary) !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
    }
    
    .stButton > button:hover {
        background-color: var(--accent-secondary) !important;
    }
    
    /* พื้นที่อัปโหลด */
    .upload-section {
        background-color: var(--bg-tertiary);
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        border: 1px solid var(--border-color);
    }
    
    /* พื้นที่แสดงผลลัพธ์ */
    .result-section {
        background-color: var(--bg-tertiary);
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        border: 1px solid var(--accent-primary);
    }
    
    /* ปุ่มดาวน์โหลด */
    .download-btn {
        text-align: center;
        margin: 20px 0;
    }
    
    /* ข้อความแสดงสถานะ */
    .status-info {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .info {
        background-color: rgba(79, 139, 249, 0.2);
        border-left: 4px solid var(--accent-primary);
    }
    
    .success {
        background-color: rgba(29, 185, 84, 0.2);
        border-left: 4px solid var(--success-color);
    }
    
    .warning {
        background-color: rgba(255, 152, 0, 0.2);
        border-left: 4px solid var(--warning-color);
    }
    
    .error {
        background-color: rgba(244, 67, 54, 0.2);
        border-left: 4px solid var(--error-color);
    }
    
    /* เส้นแบ่ง */
    hr {
        margin: 30px 0;
        border: none;
        height: 1px;
        background-color: var(--border-color);
    }
    
    /* ปรับสีข้อความใน streamlit elements */
    .stNumberInput label, .stRadio label, .stFileUploader label, .stExpander label {
        color: var(--text-primary) !important;
    }
    
    .stText, .stInfoMessage, .stErrorMessage, .stWarningMessage, .stSuccessMessage {
        color: var(--text-primary) !important;
    }
    
    /* ปรับสี widget อื่นๆ */
    div[data-testid="stExpanderDetails"] {
        background-color: var(--bg-tertiary);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid var(--border-color);
    }
    
    /* ส่วนของหัวข้อและไอคอน */
    .section-header {
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        color: var(--text-primary);
    }
    
    .section-header svg {
        margin-right: 10px;
        fill: var(--accent-primary);
    }
</style>
""", unsafe_allow_html=True)

# ฟังก์ชันที่มีอยู่ใน code เดิม
def process_single_placemark(placemark_data):
    """สร้าง Placemark ใหม่ที่มีพิกัดถูกเลื่อน"""
    try:
        placemark, coords, index, offset_step_lat, offset_step_lon = placemark_data
        new_coords = offset_coordinates_multiple(coords, index, offset_step_lat, offset_step_lon)
        
        # สร้าง Placemark ใหม่
        new_placemark = etree.Element("{http://www.opengis.net/kml/2.2}Placemark")
        
        # คัดลอก name และ description ถ้ามี
        for tag in ("name", "description"):
            element = placemark.find(f"{{http://www.opengis.net/kml/2.2}}{tag}")
            if element is not None:
                new_elem = etree.SubElement(new_placemark, f"{{http://www.opengis.net/kml/2.2}}{tag}")
                new_elem.text = element.text
        
        # สร้าง LineString
        new_line_string = etree.SubElement(new_placemark, "{http://www.opengis.net/kml/2.2}LineString")
        new_coordinates = etree.SubElement(new_line_string, "{http://www.opengis.net/kml/2.2}coordinates")
        new_coordinates.text = "\n".join(new_coords)
        
        return new_placemark
    except Exception as e:
        st.error(f"Error processing placemark: {str(e)}")
        return None

def offset_coordinates_multiple(coords, index, offset_step_lat=0.00002, offset_step_lon=0.00002):
    """ปรับตำแหน่งพิกัดให้ขยับตาม index"""
    try:
        offset_coords = []
        for coord in coords:
            parts = coord.strip().split(',')
            if len(parts) >= 2:
                lon = float(parts[0])
                lat = float(parts[1])
                alt = float(parts[2]) if len(parts) > 2 else 0
                
                lon += offset_step_lon * index
                lat += offset_step_lat * index
                offset_coords.append(f"{lon},{lat},{alt}")
        return offset_coords
    except Exception as e:
        st.error(f"Error processing coordinates: {str(e)}")
        return []

def check_endpoints_overlap(coords1, coords2):
    """ตรวจสอบว่าจุดต้นและจุดท้ายของเส้นตรงซ้อนทับกันหรือไม่"""
    try:
        if not coords1 or not coords2:
            return False
            
        start1 = tuple(map(float, coords1[0].split(',')[:2]))
        end1 = tuple(map(float, coords1[-1].split(',')[:2]))
        start2 = tuple(map(float, coords2[0].split(',')[:2]))
        end2 = tuple(map(float, coords2[-1].split(',')[:2]))
        
        return (start1 == start2 or end1 == end2) or (start1 == end2 or end1 == start2)
    except Exception:
        return False

def check_lines_overlap(coords1, coords2, tolerance=1e-5):
    """ตรวจสอบว่าเส้นซ้อนทับกันหรือไม่"""
    try:
        if not coords1 or not coords2:
            return False
            
        line1_coords = [(float(c.split(',')[0]), float(c.split(',')[1])) for c in coords1]
        line2_coords = [(float(c.split(',')[0]), float(c.split(',')[1])) for c in coords2]
        
        if len(line1_coords) < 2 or len(line2_coords) < 2:
            return False
            
        line1 = LineString(line1_coords)
        line2 = LineString(line2_coords)
        
        return line1.intersects(line2) and line1.intersection(line2).length > tolerance
    except Exception:
        return False

def extract_coordinates(placemark):
    """ดึงข้อมูลพิกัดจาก Placemark"""
    try:
        line_string = placemark.find(".//{http://www.opengis.net/kml/2.2}LineString")
        if line_string is not None:
            coordinates = line_string.find("{http://www.opengis.net/kml/2.2}coordinates")
            if coordinates is not None and coordinates.text:
                return coordinates.text.strip().split()
        return None
    except Exception:
        return None

def calculate_overlap_percentage(coords1, coords2, threshold=0.00001):
    """Calculate the percentage of overlap between two sets of coordinates."""
    points1 = [tuple(map(float, c.split(','))) for c in coords1]
    points2 = [tuple(map(float, c.split(','))) for c in coords2]
    
    if len(points1) < 3 or len(points2) < 3:
        return 0
    
    overlap_count = 0
    short_points, long_points = (points1, points2) if len(points1) <= len(points2) else (points2, points1)
    
    for p1 in short_points:
        for p2 in long_points:
            dist = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
            if dist < threshold:
                overlap_count += 1
                break
    
    return (overlap_count / len(short_points)) * 100

def create_separated_lines_endpoints(input_kml, output_filename, offset_step_lat=0.00002, offset_step_lon=0.00002):
    """แยกเส้นที่ซ้ำซ้อนเฉพาะเส้นที่มีจุดต้นหรือจุดท้ายตรงกัน และรวมเส้นที่ไม่ซ้อนทับด้วย"""
    try:
        nsmap = {"kml": "http://www.opengis.net/kml/2.2"}
        
        # อ่าน Placemark ทั้งหมด
        context = etree.iterparse(input_kml, events=("end",), tag="{http://www.opengis.net/kml/2.2}Placemark")
        placemarks = []
        
        for _, elem in context:
            coords = extract_coordinates(elem)
            if coords:
                placemarks.append((elem, coords))
        
        with st.spinner("กำลังตรวจสอบจำนวน placemarks..."):
            st.markdown(f'<div class="status-info info">จำนวน placemarks ทั้งหมด: {len(placemarks)}</div>', unsafe_allow_html=True)

        # จัดกลุ่มเส้นที่มีจุดต้นหรือจุดท้ายตรงกัน
        overlapping_groups = []
        non_overlapping_placemarks = []
        processed = set()
        
        with st.spinner("กำลังจัดกลุ่มเส้นที่ซ้อนทับ..."):
            for i, (placemark1, coords1) in enumerate(placemarks):
                if i in processed:
                    continue
                
                current_group = [placemark1]
                processed.add(i)
                
                for j, (placemark2, coords2) in enumerate(placemarks[i+1:], i+1):
                    if j not in processed and check_endpoints_overlap(coords1, coords2):
                        current_group.append(placemark2)
                        processed.add(j)
                
                if len(current_group) > 1:
                    overlapping_groups.append(current_group)
                else:
                    non_overlapping_placemarks.append(placemark1)
            
            st.markdown(f'<div class="status-info info">กลุ่มที่มีเส้นซ้อนทับ: {len(overlapping_groups)}</div>', unsafe_allow_html=True)

        return create_output_kml(overlapping_groups, non_overlapping_placemarks, output_filename, offset_step_lat, offset_step_lon)
    except Exception as e:
        st.markdown(f'<div class="status-info error">Error processing KML file: {str(e)}</div>', unsafe_allow_html=True)
        return None

def create_separated_lines_all_overlapping(input_kml, output_filename, offset_step_lat=0.00002, offset_step_lon=0.00002):
    """แยกเส้นที่ซ้ำซ้อนทั้งหมดและรวมเส้นที่ไม่ซ้ำซ้อนด้วย"""
    try:
        nsmap = {"kml": "http://www.opengis.net/kml/2.2"}
        
        with st.spinner("กำลังอ่านไฟล์ KML..."):
            context = etree.iterparse(input_kml, events=("end",), tag="{http://www.opengis.net/kml/2.2}Placemark")
            placemarks = []
            
            for _, elem in context:
                coords = extract_coordinates(elem)
                if coords:
                    placemarks.append((elem, coords))
            
            st.markdown(f'<div class="status-info info">จำนวน placemarks ทั้งหมด: {len(placemarks)}</div>', unsafe_allow_html=True)

        overlapping_groups = []
        non_overlapping_placemarks = []
        processed = set()
        
        with st.spinner("กำลังวิเคราะห์เส้นที่ซ้อนทับ..."):
            progress_bar = st.progress(0)
            for i, (placemark1, coords1) in enumerate(placemarks):
                if i in processed:
                    continue
                
                current_group = [placemark1]
                processed.add(i)
                
                for j, (placemark2, coords2) in enumerate(placemarks[i+1:], i+1):
                    if j not in processed and calculate_overlap_percentage(coords1, coords2) > 50:
                        current_group.append(placemark2)
                        processed.add(j)
                
                if len(current_group) > 1:
                    overlapping_groups.append(current_group)
                else:
                    non_overlapping_placemarks.append(placemark1)
                
                # อัพเดท progress bar
                progress_bar.progress(min(1.0, (i + 1) / len(placemarks)))
            
            st.markdown(f'<div class="status-info info">กลุ่มที่มีเส้นซ้อนทับ: {len(overlapping_groups)}</div>', unsafe_allow_html=True)

        return create_output_kml(overlapping_groups, non_overlapping_placemarks, output_filename, offset_step_lat, offset_step_lon)
    except Exception as e:
        st.markdown(f'<div class="status-info error">Error processing KML file: {str(e)}</div>', unsafe_allow_html=True)
        return None

def create_output_kml(overlapping_groups, non_overlapping_placemarks, output_filename, offset_step_lat, offset_step_lon):
    """สร้างไฟล์ KML ผลลัพธ์"""
    try:
        with st.spinner("กำลังสร้างไฟล์ KML ใหม่..."):
            nsmap = {"kml": "http://www.opengis.net/kml/2.2"}
            new_doc = etree.Element("{http://www.opengis.net/kml/2.2}kml", nsmap=nsmap)
            new_folder = etree.SubElement(new_doc, "{http://www.opengis.net/kml/2.2}Folder")

            # ประมวลผลเส้นที่ซ้อนทับ
            placemark_data_list = []
            for group in overlapping_groups:
                for index, placemark in enumerate(group):
                    coords = extract_coordinates(placemark)
                    if coords:
                        placemark_data_list.append((placemark, coords, index, offset_step_lat, offset_step_lon))

            st.markdown(f'<div class="status-info info">กำลังประมวลผลเส้นที่ซ้อนทับจำนวน {len(placemark_data_list)} เส้น...</div>', unsafe_allow_html=True)
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                new_placemarks = list(executor.map(process_single_placemark, placemark_data_list))

            # เพิ่มเส้นที่ประมวลผลแล้ว
            processed_count = 0
            for new_placemark in new_placemarks:
                if new_placemark is not None:
                    new_folder.append(new_placemark)
                    processed_count += 1

            st.markdown(f'<div class="status-info success">เส้นที่ประมวลผลสำเร็จ: {processed_count}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="status-info info">เส้นที่ไม่ซ้อนทับ: {len(non_overlapping_placemarks)}</div>', unsafe_allow_html=True)

            # เพิ่มเส้นที่ไม่ซ้อนทับ
            for placemark in non_overlapping_placemarks:
                new_folder.append(placemark)

            output_path = os.path.join(tempfile.gettempdir(), output_filename)
            with open(output_path, 'wb') as f:
                f.write(etree.tostring(new_doc, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

            return output_path
    except Exception as e:
        st.markdown(f'<div class="status-info error">Error creating output KML: {str(e)}</div>', unsafe_allow_html=True)
        return None

# ส่วนของ UI
st.markdown('<h1 class="main-header">🌏 เครื่องมือแยกเส้นที่ซ้อนทับในไฟล์ KML</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">KML Processor Tool</p>', unsafe_allow_html=True)

# สร้างส่วนของการตั้งค่า
st.markdown("""
<div class="section-header">
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
        <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
    </svg>
    <h3>ตั้งค่าการประมวลผล</h3>
</div>
""", unsafe_allow_html=True)

with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        process_type = st.radio(
            "🔄 เลือกวิธีการประมวลผล:",
            ["เส้นที่ซ้อนทับตามจุดต้น-จุดท้าย", "เส้นที่ซ้อนทับทั้งหมด"]
        )
    
    with col2:
        st.markdown("##### การเลื่อนตำแหน่ง")
        
        # เพิ่มคำอธิบายที่เข้าใจง่าย
        st.markdown("""
        <div class="status-info info">
            <p><strong>วิธีการทำงาน:</strong> เมื่อพบเส้นที่ซ้อนทับกัน ระบบจะเลื่อนตำแหน่งให้มองเห็นแยกจากกันได้</p>
        </div>
        """, unsafe_allow_html=True)
        
        # เพิ่มตัวเลือกแบบง่ายเพียง 3 ระดับตามที่ต้องการ
        offset_preset = st.radio(
            "เลือกระยะการเลื่อน:",
            ["น้อย", "ปานกลาง", "มาก"]
        )
        
        # แปลงค่าที่เลือกเป็นค่าที่ใช้จริง
        if offset_preset == "น้อย":
            offset_lat = 0.00002
            offset_lon = 0.00002
        elif offset_preset == "ปานกลาง":
            offset_lat = 0.00005
            offset_lon = 0.00005
        elif offset_preset == "มาก":
            offset_lat = 0.0001
            offset_lon = 0.0001
        
        # แสดงค่าที่ใช้จริง
        st.markdown(f"""
        <div class="status-info info" style="margin-top: 10px;">
            <p><strong>ค่าที่ใช้:</strong> {offset_lat:.7f}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # เพิ่มตัวอย่างภาพประกอบอย่างง่าย
        st.markdown(f"""
        <div style="text-align: center; margin-top: 15px;">
            <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                <div style="text-align: center;">
                    <div style="height: 60px; position: relative; width: 100px; margin: 0 auto;">
                        <div style="position: absolute; height: 4px; width: 80px; background-color: blue; top: 30px; left: 10px;"></div>
                    </div>
                    <p style="font-size: 12px;">ก่อน</p>
                </div>
                <div style="text-align: center;">
                    <div style="height: 60px; position: relative; width: 100px; margin: 0 auto;">
                        <div style="position: absolute; height: 4px; width: 80px; background-color: blue; top: 20px; left: 10px;"></div>
                        <div style="position: absolute; height: 4px; width: 80px; background-color: red; top: {30 + (offset_lat/0.00001) * 2}px; left: 10px;"></div>
                    </div>
                    <p style="font-size: 12px;">หลัง</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ส่วนของการอัปโหลด
st.markdown("""
<div class="section-header">
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
        <path d="M19 9h-4V3H9v6H5l7 7 7-7zm-8 2V5h2v6h1.17L12 13.17 9.83 11H11zm-6 7h14v2H5v-2z"/>
    </svg>
    <h3>อัปโหลดไฟล์</h3>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="upload-section">', unsafe_allow_html=True)
uploaded_file = st.file_uploader("เลือกไฟล์ KML", type=["kml"], help="อัปโหลดเฉพาะไฟล์นามสกุล .kml เท่านั้น")
st.markdown('</div>', unsafe_allow_html=True)

# ส่วนของการประมวลผล
if uploaded_file:
    if st.button("🚀 เริ่มประมวลผล", use_container_width=True):
        with st.status("กำลังประมวลผล...", expanded=True) as status:
            try:
                input_filename = os.path.splitext(uploaded_file.name)[0] + "_processed.kml"
                temp_kml_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
                
                with open(temp_kml_path, "wb") as f:
                    f.write(uploaded_file.read())

                st.markdown('<div class="result-section">', unsafe_allow_html=True)
                if process_type == "เส้นที่ซ้อนทับตามจุดต้น-จุดท้าย":
                    output_file = create_separated_lines_endpoints(temp_kml_path, input_filename, offset_lat, offset_lon)
                else:
                    output_file = create_separated_lines_all_overlapping(temp_kml_path, input_filename, offset_lat, offset_lon)
                st.markdown('</div>', unsafe_allow_html=True)

                if output_file:
                    status.update(label="✅ ประมวลผลเสร็จสิ้น!", state="complete")
                    st.markdown('<div class="status-info success">สร้างไฟล์ผลลัพธ์สำเร็จ</div>', unsafe_allow_html=True)
                    
                    st.markdown('<div class="download-btn">', unsafe_allow_html=True)
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label=f"📥 ดาวน์โหลด {input_filename}",
                            data=f,
                            file_name=input_filename,
                            mime="application/vnd.google-earth.kml+xml",
                            use_container_width=True
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    status.update(label="⚠️ ไม่มีข้อมูลใหม่", state="error")
            except Exception as e:
                st.markdown(f'<div class="status-info error">เกิดข้อผิดพลาด: {str(e)}</div>', unsafe_allow_html=True)
                status.update(label="❌ เกิดข้อผิดพลาด", state="error")
else:
    st.info("กรุณาอัปโหลดไฟล์ KML เพื่อเริ่มต้นใช้งาน")

# เพิ่มข้อมูลวิธีใช้งาน
with st.expander("📝 วิธีใช้งาน"):
    st.markdown("""
    1. เลือกวิธีการประมวลผล:
       - **เส้นที่ซ้อนทับตามจุดต้น-จุดท้าย**: แยกเฉพาะเส้นที่มีจุดเริ่มต้นหรือจุดสิ้นสุดซ้อนทับกัน
       - **เส้นที่ซ้อนทับทั้งหมด**: แยกเส้นที่มีการซ้อนทับกันทั้งหมด (มีความซ้อนทับมากกว่า 50%)
    2. ปรับค่าระยะการเลื่อนตำแหน่ง (หากต้องการ)
    3. อัปโหลดไฟล์ KML ที่ต้องการประมวลผล
    4. กดปุ่ม "เริ่มประมวลผล" และรอจนกระบวนการเสร็จสิ้น
    5. ดาวน์โหลดไฟล์ผลลัพธ์
    """)
