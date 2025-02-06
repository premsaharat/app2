import streamlit as st
from lxml import etree
from concurrent.futures import ThreadPoolExecutor
import os
import tempfile

# ------------------------------
# 🌟 ตกแต่ง UI ด้วย CSS และ Bootstrap
# ------------------------------
st.set_page_config(page_title="KML Processor", page_icon="🌍", layout="wide")

st.markdown("""
    <style>
    body {
        background-color: #f8f9fa;
    }
    .main-title {
        color: #007bff;
        text-align: center;
        font-size: 36px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .sub-title {
        color: #6c757d;
        text-align: center;
        font-size: 18px;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #28a745;
        color: white;
        font-size: 16px;
        border-radius: 10px;
        padding: 12px 20px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #218838;
        transform: scale(1.05);
    }
    .stDownloadButton>button {
        background-color: #007bff;
        color: white;
        font-size: 16px;
        border-radius: 10px;
        padding: 12px 20px;
        transition: 0.3s;
    }
    .stDownloadButton>button:hover {
        background-color: #0056b3;
        transform: scale(1.05);
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------
# 🚀 ฟังก์ชันประมวลผล KML
# ------------------------------
def offset_coordinates_multiple(coords, index, offset_step_lat=0.00002, offset_step_lon=0.00002):
    """ปรับตำแหน่งพิกัดให้ขยับตาม index เพื่อแยกเส้นที่ซ้ำซ้อน"""
    offset_coords = []
    for coord in coords:
        lon, lat, *alt = map(float, coord.split(','))
        lon += offset_step_lon * index
        lat += offset_step_lat * index
        offset_coords.append(f"{lon},{lat},{alt[0] if alt else 0}")
    return offset_coords

def process_single_placemark(placemark_data):
    """สร้าง Placemark ใหม่ที่มีพิกัดถูกเลื่อน"""
    placemark, coords, index, offset_step_lat, offset_step_lon = placemark_data
    new_coords = offset_coordinates_multiple(coords, index, offset_step_lat, offset_step_lon)
    new_placemark = etree.Element("{http://www.opengis.net/kml/2.2}Placemark")

    for tag in ("name", "description"):
        element = placemark.find(f"{{http://www.opengis.net/kml/2.2}}{tag}")
        if element is not None:
            new_elem = etree.SubElement(new_placemark, f"{{http://www.opengis.net/kml/2.2}}{tag}")
            new_elem.text = element.text

    new_line_string = etree.SubElement(new_placemark, "{http://www.opengis.net/kml/2.2}LineString")
    new_coordinates = etree.SubElement(new_line_string, "{http://www.opengis.net/kml/2.2}coordinates")
    new_coordinates.text = "\n".join(new_coords)

    return new_placemark

def create_separated_lines(input_kml, output_filename, offset_step_lat=0.00002, offset_step_lon=0.00002):
    """แยกเส้นที่ซ้ำซ้อนและรวมเป็นไฟล์ KML เดียว"""
    nsmap = {"kml": "http://www.opengis.net/kml/2.2"}
    
    # อ่าน Placemark ทั้งหมด
    context = etree.iterparse(input_kml, events=("end",), tag="{http://www.opengis.net/kml/2.2}Placemark")
    placemarks = []
    
    for _, elem in context:
        line_string = elem.find(".//{http://www.opengis.net/kml/2.2}LineString")
        if line_string is not None:
            coordinates = line_string.find("{http://www.opengis.net/kml/2.2}coordinates")
            if coordinates is not None:
                coords = coordinates.text.strip().split()
                placemarks.append((elem, coords))

    # ค้นหาเส้นที่ซ้ำกัน
    coord_map = {}
    for placemark, coords in placemarks:
        coords_tuple = tuple(coords)
        if coords_tuple not in coord_map:
            coord_map[coords_tuple] = []
        coord_map[coords_tuple].append(placemark)

    overlapping_groups = [group for group in coord_map.values() if len(group) > 1]

    # เตรียมข้อมูลเพื่อประมวลผลแบบขนาน
    placemark_data_list = [
        (placemark, coords, index, offset_step_lat, offset_step_lon)
        for group in overlapping_groups
        for index, placemark in enumerate(group)
        for coords in [placemark.find(".//{http://www.opengis.net/kml/2.2}LineString").find("{http://www.opengis.net/kml/2.2}coordinates").text.strip().split()]
    ]

    # ใช้ ThreadPoolExecutor เพื่อเร่งความเร็ว
    with ThreadPoolExecutor(max_workers=4) as executor:
        new_placemarks = list(executor.map(process_single_placemark, placemark_data_list))

    # สร้างไฟล์ KML เดียวที่รวมทุก Placemark
    new_doc = etree.Element("{http://www.opengis.net/kml/2.2}kml", nsmap=nsmap)
    new_folder = etree.SubElement(new_doc, "{http://www.opengis.net/kml/2.2}Folder")
    
    for new_placemark in new_placemarks:
        new_folder.append(new_placemark)

    output_path = os.path.join(tempfile.gettempdir(), output_filename)
    with open(output_path, 'wb') as f:
        f.write(etree.tostring(new_doc, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    return output_path

# ------------------------------
# 🎯 ส่วน UI ของ Streamlit
# ------------------------------
st.markdown('<p class="main-title">KML Processor 🚀</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">🗺️ ประมวลผลไฟล์ KML และเพิ่มเส้นที่ทับซ้อน</p>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 เลือกไฟล์ KML ( * ไฟล์ kml เท่านั้น * ) ", type=["kml"])

if uploaded_file:
    if st.button("⚡ ประมวลผล"):
        with st.status("⏳ กำลังประมวลผล...", expanded=True) as status:
            input_filename = os.path.splitext(uploaded_file.name)[0] + "_processed.kml"
            temp_kml_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
            
            with open(temp_kml_path, "wb") as f:
                f.write(uploaded_file.read())

            output_file = create_separated_lines(temp_kml_path, input_filename)

            if output_file:
                status.update(label="✅ เสร็จสิ้น!", state="complete")
                with open(output_file, "rb") as f:
                    st.download_button(
                        label=f"📥 ดาวน์โหลด {input_filename}",
                        data=f,
                        file_name=input_filename,
                        mime="application/vnd.google-earth.kml+xml"
                    )
            else:
                status.update(label="⚠️ ไม่มีข้อมูลใหม่", state="error")
