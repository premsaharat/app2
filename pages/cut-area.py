import os, copy
import streamlit as st
import tempfile
import zipfile
import time
from lxml import etree
from shapely.geometry import Point, Polygon

# Set page configuration
st.set_page_config(
    page_title="KML Area Clipper",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    :root {
        --bg-primary: #121212;
        --bg-secondary: #1e1e1e;
        --bg-tertiary: #2a2a2a;
        --text-primary: #e0e0e0;
        --text-secondary: #b0b0b0;
        --accent-primary: #4f8bf9;
        --accent-secondary: #3776cc;
        --success-color: #1db954;
        --warning-color: #ff9800;
        --error-color: #f44336;
        --border-color: #444444;
    }

    .main-header {
        font-size: 2.5rem;
        color: var(--accent-primary);
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: var(--accent-secondary);
        margin-top: 2rem;
    }
    .info-box {
        background-color: var(--bg-secondary);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: var(--text-primary);
    }
    .success-message {
        background-color: var(--success-color);
        color: var(--text-primary);
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        text-align: center;
        font-weight: bold;
    }
    .stButton>button {
        background-color: var(--accent-primary);
        color: var(--text-primary);
        font-weight: bold;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: var(--accent-secondary);
    }
    .download-btn {
        background-color: var(--success-color);
        color: var (--text-primary);
        font-weight: bold;
    }
    .footer {
        text-align: center;
        margin-top: 2rem;
        color: var(--text-secondary);
        font-size: 0.8rem;
    }
    .upload-section {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: var(--bg-secondary);
        margin-bottom: 1rem;
        color: var(--text-primary);
    }
    .progress-bar {
        height: 10px;
        background-color: var(--bg-tertiary);
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .progress-bar-fill {
        height: 100%;
        background-color: var(--accent-primary);
        border-radius: 5px;
        transition: width 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for processing status
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'progress' not in st.session_state:
    st.session_state.progress = 0
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'combined_kml' not in st.session_state:
    st.session_state.combined_kml = None

# ฟังก์ชันสำหรับตัดพื้นที่ที่อยู่นอกขอบเขต
def clip_and_combine(input_kml, boundary_polygon, output_kml):
    try:
        tree = etree.parse(input_kml)
        root = tree.getroot()
        placemarks_to_remove = []  
        total_placemarks = len(root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"))
        processed_placemarks = 0

        for placemark in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
            # 0) ตรวจสอบว่ามี Point ไหม ถ้ามีให้เช็คว่าอยู่ในขอบเขตหรือไม่
            point_elem = placemark.find(
                ".//{http://www.opengis.net/kml/2.2}Point"
            )
            if point_elem is not None:
                coords_elem = point_elem.find(
                    ".//{http://www.opengis.net/kml/2.2}coordinates"
                )
                if coords_elem is not None:
                    lon, lat = map(float, coords_elem.text.strip().split(',')[:2])
                    from shapely.geometry import Point as ShapelyPoint
                    pt = ShapelyPoint(lon, lat)
                    # ถ้าอยู่นอกขอบเขต ให้ลบ
                    if not pt.within(boundary_polygon):
                        placemarks_to_remove.append(placemark)
                # อัพเดต progress แล้วข้ามไปเลย
                processed_placemarks += 1
                st.session_state.progress = processed_placemarks / total_placemarks
                continue

            # 1) หาองค์ประกอบ Geometry (LineString หรือ Polygon)
            line_elem = placemark.find(".//{http://www.opengis.net/kml/2.2}LineString")
            poly_elem = placemark.find(".//{http://www.opengis.net/kml/2.2}Polygon")
            coords_elem = None
            geom = None

            if line_elem is not None:
                coords_elem = line_elem.find(".//{http://www.opengis.net/kml/2.2}coordinates")
                if coords_elem is not None:
                    pts = [
                        tuple(map(float, c.split(',')[:2]))
                        for c in coords_elem.text.strip().split()
                    ]
                    from shapely.geometry import LineString
                    geom = LineString(pts)

            elif poly_elem is not None:
                coords_elem = poly_elem.find(".//{http://www.opengis.net/kml/2.2}outerBoundaryIs//{http://www.opengis.net/kml/2.2}coordinates")
                if coords_elem is not None:
                    pts = [
                        tuple(map(float, c.split(',')[:2]))
                        for c in coords_elem.text.strip().split()
                    ]
                    from shapely.geometry import Polygon
                    geom = Polygon(pts)

            # 2) ถ้ามี geometry ให้ตัดด้วย boundary_polygon
            if geom:
                clipped = geom.intersection(boundary_polygon)
                if clipped.is_empty:
                    placemarks_to_remove.append(placemark)
                else:
                    # เตรียม list เก็บทุกส่วนที่มีพิกัด
                    new_pts = []
                    from shapely.geometry import LineString, Polygon, MultiLineString, MultiPolygon, GeometryCollection

                    def collect_coords(g):
                        if isinstance(g, Polygon):
                            return list(g.exterior.coords)
                        elif isinstance(g, LineString):
                            return list(g.coords)
                        return []

                    # ถ้าเป็น single geometry
                    if isinstance(clipped, (Polygon, LineString)):
                        new_pts = collect_coords(clipped)
                    # ถ้าเป็น multi-part หรือ collection
                    elif isinstance(clipped, (MultiPolygon, MultiLineString, GeometryCollection)):
                        for part in clipped.geoms:
                            new_pts += collect_coords(part)

                    # อัปเดต coordinates element
                    if new_pts:
                        coords_elem.text = " ".join(f"{x},{y}" for x, y in new_pts)

            processed_placemarks += 1
            st.session_state.progress = processed_placemarks / total_placemarks

        # เอา placemark ที่ไม่ผ่านเงื่อนไขออก
        for placemark in placemarks_to_remove:
            placemark.getparent().remove(placemark)

        # Set the name within the KML content
        document_elem = root.find(".//{http://www.opengis.net/kml/2.2}Document")
        if document_elem is not None:
            name_elem = document_elem.find(".//{http://www.opengis.net/kml/2.2}name")
            if name_elem is None:
                name_elem = etree.SubElement(document_elem, "name")
            name_elem.text = os.path.basename(output_kml)

        # Create temp file for output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_output:
            tree.write(tmp_output.name, encoding="utf-8", xml_declaration=True)
            return tmp_output.name
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการตัดข้อมูล: {e}")
        return None

# ฟังก์ชันสำหรับประมวลผลทุกขอบเขต
def process_areas_with_red(input_kml, boundary_kml):
    output_files = []
    try:
        boundary_tree = etree.parse(boundary_kml)
        boundary_root = boundary_tree.getroot()
        
        boundaries = boundary_root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
        total_boundaries = len(boundaries)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, boundary_placemark in enumerate(boundaries):
            boundary_coords = boundary_placemark.find(".//{http://www.opengis.net/kml/2.2}coordinates")
            if boundary_coords is not None:
                coords = boundary_coords.text.strip().split()
                boundary_points = [(float(coord.split(',')[0]), float(coord.split(',')[1])) for coord in coords]
                boundary_polygon = Polygon(boundary_points)

                area_name = boundary_placemark.find(".//{http://www.opengis.net/kml/2.2}name")
                area_name = area_name.text if area_name is not None else f"area_{i+1}"
                
                status_text.text(f"กำลังประมวลผลพื้นที่: {area_name} ({i+1}/{total_boundaries})")

                output_kml = f"{area_name}.kml"
                clipped_kml = clip_and_combine(input_kml, boundary_polygon, output_kml)
                if clipped_kml:
                    output_files.append((clipped_kml, area_name))
            
            progress_bar.progress((i + 1) / total_boundaries)
            
        status_text.text("ประมวลผลเสร็จสิ้น!")
        time.sleep(1)
        status_text.empty()
        progress_bar.empty()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์ขอบเขต: {e}")
    return output_files

# ฟังก์ชันรวมไฟล์ KML
def combine_kml_files(output_files, input_file_name, boundary_kml):
    combined_output_kml = tempfile.NamedTemporaryFile(delete=False, suffix='.kml')
    kml_elem = etree.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document_elem = etree.SubElement(kml_elem, "Document")

    # Add a name element to the KML document
    name_elem = etree.SubElement(document_elem, "name")
    name_elem.text = os.path.splitext(input_file_name)[0]  # Set name to input file name without extension

    # Add styles for better visualization in Google Earth
    style_elem = etree.SubElement(document_elem, "Style", id="normalPlacemark")
    line_style = etree.SubElement(style_elem, "LineStyle")
    etree.SubElement(line_style, "color").text = "ff0000ff"  # Red
    etree.SubElement(line_style, "width").text = "2"
    
    poly_style = etree.SubElement(style_elem, "PolyStyle")
    etree.SubElement(poly_style, "color").text = "7f0000ff"  # Semi-transparent red
    etree.SubElement(poly_style, "outline").text = "1"

    # ===== สไตล์สำหรับขอบเขตพื้นที่ =====
    boundary_style = etree.SubElement(document_elem, "Style", id="boundaryPlacemark")
    # เส้นขอบ
    ls_b = etree.SubElement(boundary_style, "LineStyle")
    etree.SubElement(ls_b, "color").text = "ff00ff00"   # ทึบเขียว
    etree.SubElement(ls_b, "width").text = "3"
    # พื้นที่เติม
    ps_b = etree.SubElement(boundary_style, "PolyStyle")
    etree.SubElement(ps_b, "color").text   = "4000ff00"  # 25% โปร่งใสเขียว
    etree.SubElement(ps_b, "fill").text    = "1"         # เปิดเติมสี
    etree.SubElement(ps_b, "outline").text = "1"         # แสดงเส้นขอบด้วย

    # ===== สไตล์สำหรับขอบเขตพื้นที่ =====
    boundary_style = etree.SubElement(document_elem, "Style", id="boundaryPlacemark")
    # เส้นขอบ
    ls_b = etree.SubElement(boundary_style, "LineStyle")
    etree.SubElement(ls_b, "color").text = "ff00ff00"   # เส้นขอบเขียวทึบ
    etree.SubElement(ls_b, "width").text = "3"
    # พื้นที่เติม
    ps_b = etree.SubElement(boundary_style, "PolyStyle")
    etree.SubElement(ps_b, "color").text   = "0000ff00"  # เติมสีเขียว แต่ alpha=00 => มองไม่เห็น
    etree.SubElement(ps_b, "fill").text    = "1"         # เปิดเติม (แต่โปร่งใสหมด)
    etree.SubElement(ps_b, "outline").text = "1"         # แสดงเส้นขอบ

    # โหลด boundary KML มาเก็บตามชื่อ
    boundary_tree = etree.parse(boundary_kml)
    boundary_root = boundary_tree.getroot()
    boundary_dict = {}
    for b in boundary_root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
        nm = b.find(".//{http://www.opengis.net/kml/2.2}name")
        if nm is not None:
            boundary_dict[nm.text] = b

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, (file, area_name) in enumerate(output_files):
        try:
            status_text.text(f"กำลังรวมพื้นที่: {area_name}")
            tree = etree.parse(file)
            root = tree.getroot()
            folder_elem = etree.SubElement(document_elem, "Folder")
            folder_name_elem = etree.SubElement(folder_elem, "name")
            folder_name_elem.text = area_name

            # ----- เพิ่มขอบเขตเดิมก่อน placemark ที่ตัดแล้ว -----
            if area_name in boundary_dict:
                b_placemark = copy.deepcopy(boundary_dict[area_name])
                style_url = etree.SubElement(b_placemark, "styleUrl")
                style_url.text = "#boundaryPlacemark"
                folder_elem.append(b_placemark)

            for placemark in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
                # Add style reference to each placemark
                style_url = etree.SubElement(placemark, "styleUrl")
                style_url.text = "#normalPlacemark"
                folder_elem.append(placemark)
                
            # Remove the temporary file after it's been processed
            os.unlink(file)
            
            progress_bar.progress((i + 1) / len(output_files))
            
        except Exception as e:
            st.error(f"ไม่สามารถรวมไฟล์ {area_name}: {e}")

    combined_tree = etree.ElementTree(kml_elem)
    combined_tree.write(combined_output_kml.name, encoding="utf-8", xml_declaration=True)
    
    status_text.text("รวมไฟล์เสร็จสิ้น!")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()
    
    return combined_output_kml.name

# ฟังก์ชันสำหรับการแยกไฟล์ KML จาก ZIP
def extract_kml_from_zip(zip_file):
    kml_files = []
    with zipfile.ZipFile(zip_file, 'r') as zipf:
        all_files = zipf.namelist()
        kml_files_in_zip = [f for f in all_files if f.endswith('.kml')]
        total_files = len(kml_files_in_zip)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, file_name in enumerate(kml_files_in_zip):
            status_text.text(f"กำลังแยกไฟล์: {file_name}")
            with zipf.open(file_name) as kml_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as temp_file:
                    temp_file.write(kml_file.read())
                    kml_files.append(temp_file.name)
            progress_bar.progress((i + 1) / total_files)
        
        status_text.text(f"แยกไฟล์เสร็จสิ้น! พบไฟล์ KML จำนวน {len(kml_files)} ไฟล์")
        time.sleep(1)
        status_text.empty()
        progress_bar.empty()
        
    return kml_files

# ฟังก์ชันเริ่มประมวลผล
def start_processing():
    if st.session_state.input_file and st.session_state.boundary_file:
        st.session_state.processing = True
        
        # Create spinner while processing
        with st.spinner("กำลังประมวลผลข้อมูล..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{st.session_state.input_file.name.split('.')[-1]}") as tmp_input:
                tmp_input.write(st.session_state.input_file.getvalue())
                input_path = tmp_input.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                tmp_boundary.write(st.session_state.boundary_file.getvalue())
                boundary_path = tmp_boundary.name

            try:
                output_files = []

                if st.session_state.input_file.name.endswith(".zip"):
                    st.info("กำลังแยกไฟล์ KML จาก ZIP...")
                    extracted_kml_files = extract_kml_from_zip(input_path)
                    
                    if len(extracted_kml_files) == 0:
                        st.error("ไม่พบไฟล์ KML ในไฟล์ ZIP")
                        st.session_state.processing = False
                        return
                        
                    st.info(f"เริ่มประมวลผลไฟล์ KML จำนวน {len(extracted_kml_files)} ไฟล์...")
                    # Use the first KML file for processing
                    output_files = process_areas_with_red(extracted_kml_files[0], boundary_path)
                    # Remove unused extracted files
                    for file in extracted_kml_files[1:]:
                        os.unlink(file)
                else:
                    st.info("เริ่มประมวลผลไฟล์ KML...")
                    output_files = process_areas_with_red(input_path, boundary_path)

                if output_files:
                    st.info("กำลังรวมไฟล์ KML...")
                    combined_kml = combine_kml_files(output_files, st.session_state.input_file.name, boundary_path)
                    st.session_state.combined_kml = combined_kml
                    st.session_state.processed_files = [name for _, name in output_files]
                    
                    st.success(f"ประมวลผลเสร็จสิ้น! ได้ทั้งหมด {len(output_files)} พื้นที่")
                else:
                    st.error("ไม่พบข้อมูลที่ตรงกับเงื่อนไข")
            finally:
                os.unlink(input_path)
                os.unlink(boundary_path)
                st.session_state.processing = False
        
    else:
        st.error("กรุณาเลือกไฟล์ให้ครบถ้วน")

# Streamlit UI
def main():
    # Header
    st.markdown("<h1 class='main-header'>🗺️ โปรแกรมตัดพื้นที่จากไฟล์ KML</h1>", unsafe_allow_html=True)
    st.markdown("<div class='info-box'>โปรแกรมสำหรับตัดพื้นที่จากไฟล์ KML ตามขอบเขตที่กำหนด</div>", unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2 = st.tabs(["📋 ประมวลผลข้อมูล", "ℹ️ คำแนะนำการใช้งาน"])
    
    with tab1:
        # Upload section
        st.markdown("<h2 class='sub-header'>อัปโหลดไฟล์</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
            st.file_uploader(
                "📁 เลือกไฟล์ KML หรือ ZIP ที่มี KML", 
                type=['zip', 'kml'],
                help="กรณีไฟล์ KML มีขนาดใหญ่ให้ทำเป็นไฟล์ ZIP",
                key="input_file"
            )
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col2:
            st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
            st.file_uploader(
                "📁 เลือกไฟล์ขอบเขต KML",
                type=['kml'],
                help="ไฟล์ KML ที่กำหนดขอบเขตพื้นที่ที่ต้องการตัด",
                key="boundary_file"
            )
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Process button
        if st.session_state.processing:
            st.button("⏳ กำลังประมวลผล...", disabled=True)
        else:
            st.button("🚀 เริ่มประมวลผล", on_click=start_processing, key="process_button")
        
        # Show results
        if st.session_state.combined_kml:
            st.markdown("<div class='success-message'>✅ ประมวลผลเสร็จสิ้น</div>", unsafe_allow_html=True)
            
            # Show processed areas
            if st.session_state.processed_files:
                with st.expander("📋 พื้นที่ที่ประมวลผล"):
                    for i, area in enumerate(st.session_state.processed_files):
                        st.write(f"{i+1}. {area}")
            
            # Download button
            with open(st.session_state.combined_kml, "rb") as f:
                download_label = "🔗 ดาวน์โหลดไฟล์ KML รวม"
                input_file_name = os.path.splitext(st.session_state.input_file.name)[0]
                combined_file_name = f"{input_file_name}_combined.kml"
                
                st.download_button(
                    label=download_label,
                    data=f,
                    file_name=combined_file_name,
                    mime="application/vnd.google-earth.kml+xml",
                    key="download_button"
                )
    
    with tab2:
        st.markdown("""
        ## 📌 คำแนะนำการใช้งาน
        
        ### วิธีการใช้งาน
        1. อัปโหลดไฟล์ KML ที่ต้องการตัดพื้นที่ (หรือไฟล์ ZIP ที่มี KML อยู่ภายใน)
            - กรณีที่ไฟล์ KML มีขนาดใหญ่ ให้บีบอัดเป็นไฟล์ ZIP ก่อนอัปโหลด
            - โปรแกรมจะใช้ไฟล์ KML ไฟล์แรกที่พบในไฟล์ ZIP
        
        2. อัปโหลดไฟล์ขอบเขต KML
            - ไฟล์นี้จะกำหนดขอบเขตพื้นที่ที่ต้องการตัด
            - สามารถมีหลายพื้นที่ (Placemark) ในไฟล์เดียวกัน
        
        3. กดปุ่ม "เริ่มประมวลผล" เพื่อดำเนินการ
            - โปรแกรมจะตัดพื้นที่ตามขอบเขตที่กำหนด
            - ผลลัพธ์จะถูกรวมเป็นไฟล์ KML เดียว โดยแบ่งตามพื้นที่
        
        4. ดาวน์โหลดไฟล์ KML ผลลัพธ์
        
        ### หมายเหตุ
        - พื้นที่ที่อยู่นอกขอบเขตจะถูกตัดออก
        - ชื่อของแต่ละพื้นที่จะถูกนำมาจากชื่อ Placemark ในไฟล์ขอบเขต
        - ไฟล์ผลลัพธ์สามารถเปิดด้วย Google Earth หรือโปรแกรมอื่นๆ ที่รองรับไฟล์ KML
        """)

if __name__ == "__main__":
    main()
