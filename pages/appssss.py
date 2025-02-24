import os
import streamlit as st
import tempfile
import zipfile
from lxml import etree
from shapely.geometry import Point, Polygon

# ฟังก์ชันสำหรับตัดพื้นที่ที่อยู่นอกขอบเขต
def clip_and_combine(input_kml, boundary_polygon, output_kml):
    try:
        tree = etree.parse(input_kml)
        root = tree.getroot()
        placemarks_to_remove = []  

        for placemark in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
            coordinates = placemark.find(".//{http://www.opengis.net/kml/2.2}coordinates")
            if coordinates is not None:
                coord_text = coordinates.text.strip()
                coord_list = coord_text.split()
                points = [Point(map(float, coord.split(",")[:2])) for coord in coord_list]
                
                if not any(point.within(boundary_polygon) for point in points):
                    placemarks_to_remove.append(placemark)  

        for placemark in placemarks_to_remove:
            placemark.getparent().remove(placemark)

        # Set the name within the KML content
        document_elem = root.find(".//{http://www.opengis.net/kml/2.2}Document")
        if document_elem is not None:
            name_elem = document_elem.find(".//{http://www.opengis.net/kml/2.2}name")
            if name_elem is None:
                name_elem = etree.SubElement(document_elem, "name")
            name_elem.text = os.path.basename(output_kml)

        tree.write(output_kml, encoding="utf-8", xml_declaration=True)
        return output_kml
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการตัดข้อมูล: {e}")
        return None

# ฟังก์ชันสำหรับประมวลผลทุกขอบเขต
def process_areas_with_red(input_kml, boundary_kml):
    output_files = []
    try:
        boundary_tree = etree.parse(boundary_kml)
        boundary_root = boundary_tree.getroot()

        for boundary_placemark in boundary_root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
            boundary_coords = boundary_placemark.find(".//{http://www.opengis.net/kml/2.2}coordinates")
            if boundary_coords is not None:
                coords = boundary_coords.text.strip().split()
                boundary_points = [(float(coord.split(',')[0]), float(coord.split(',')[1])) for coord in coords]
                boundary_polygon = Polygon(boundary_points)

                area_name = boundary_placemark.find(".//{http://www.opengis.net/kml/2.2}name")
                area_name = area_name.text if area_name is not None else "unknown"

                output_kml = f"{area_name}.kml"
                output_kml = clip_and_combine(input_kml, boundary_polygon, output_kml)
                if output_kml:
                    output_files.append(output_kml)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์ขอบเขต: {e}")
    return output_files

# ฟังก์ชันรวมไฟล์ KML
def combine_kml_files(output_files):
    combined_output_kml = tempfile.NamedTemporaryFile(delete=False, suffix='.kml')
    kml_elem = etree.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document_elem = etree.SubElement(kml_elem, "Document")

    # Add a name element to the KML document
    name_elem = etree.SubElement(document_elem, "name")
    name_elem.text = "Combined KML File"

    for file in output_files:
        try:
            tree = etree.parse(file)
            root = tree.getroot()
            for placemark in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
                document_elem.append(placemark)
        except Exception as e:
            st.error(f"ไม่สามารถรวมไฟล์ {file}: {e}")

    combined_tree = etree.ElementTree(kml_elem)
    combined_tree.write(combined_output_kml.name, encoding="utf-8", xml_declaration=True)
    return combined_output_kml.name  

# ฟังก์ชันสร้างไฟล์ ZIP
def create_zip_for_download(output_files):
    zip_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    with zipfile.ZipFile(zip_file, 'w') as zipf:
        for file in output_files:
            zipf.write(file, os.path.basename(file))
    return zip_file.name  

# ฟังก์ชันสำหรับการแยกไฟล์ KML จาก ZIP
def extract_kml_from_zip(zip_file):
    kml_files = []
    with zipfile.ZipFile(zip_file, 'r') as zipf:
        for file_name in zipf.namelist():
            if file_name.endswith('.kml'):
                with zipf.open(file_name) as kml_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as temp_file:
                        temp_file.write(kml_file.read())
                        kml_files.append(temp_file.name)
    return kml_files

# Streamlit UI
def main():
    st.set_page_config(page_title="โปรแกรมตัดพื้นที่จาก KML", layout="wide")
    st.title("🗺️ โปรแกรมตัดพื้นที่จากไฟล์ KML")
    st.markdown("---")

    input_file = st.file_uploader("📁 เลือกไฟล์ KML หรือ ZIP ที่มี KML ( กรณีไฟล์ KML มีขนาดใหญ่ให้ทำเป็นไฟล์ ZIP )", type=['zip', 'kml'])
    boundary_file = st.file_uploader("📁 เลือกไฟล์ขอบเขต KML", type=['kml'])

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 เริ่มประมวลผลแยกไฟล์ KML"):
            if input_file and boundary_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{input_file.name.split('.')[-1]}") as tmp_input:
                    tmp_input.write(input_file.getvalue())
                    input_path = tmp_input.name

                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                    tmp_boundary.write(boundary_file.getvalue())
                    boundary_path = tmp_boundary.name

                try:
                    output_files = []

                    if input_file.name.endswith(".zip"):
                        extracted_kml_files = extract_kml_from_zip(input_path)
                        for kml_file in extracted_kml_files:
                            output_files += process_areas_with_red(kml_file, boundary_path)
                    else:
                        output_files = process_areas_with_red(input_path, boundary_path)

                    if output_files:
                        zip_file_path = create_zip_for_download(output_files)
                        with open(zip_file_path, "rb") as f:
                            st.download_button(
                                label="📦 ดาวน์โหลดไฟล์ KML ทุกไฟล์",
                                data=f,
                                file_name="output_files.zip",
                                mime="application/zip"
                            )
                finally:
                    os.unlink(input_path)
                    os.unlink(boundary_path)

    with col2:
        if st.button("🚀 เริ่มประมวลผลรวมไฟล์ KML"):
            if input_file and boundary_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{input_file.name.split('.')[-1]}") as tmp_input:
                    tmp_input.write(input_file.getvalue())
                    input_path = tmp_input.name

                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                    tmp_boundary.write(boundary_file.getvalue())
                    boundary_path = tmp_boundary.name

                try:
                    output_files = []

                    if input_file.name.endswith(".zip"):
                        extracted_kml_files = extract_kml_from_zip(input_path)
                        for kml_file in extracted_kml_files:
                            output_files += process_areas_with_red(kml_file, boundary_path)
                    else:
                        output_files = process_areas_with_red(input_path, boundary_path)

                    if output_files:
                        combined_kml = combine_kml_files(output_files)
                        with open(combined_kml, "rb") as f:
                            st.download_button(
                                label="🔗 ดาวน์โหลดไฟล์ KML รวม",
                                data=f,
                                file_name="combined_output.kml",
                                mime="application/vnd.google-earth.kml+xml"
                            )
                finally:
                    os.unlink(input_path)
                    os.unlink(boundary_path)

            else:
                st.error("กรุณาเลือกไฟล์ให้ครบถ้วน")

    with st.expander("📌 คำแนะนำการใช้งาน"):
        st.markdown("""
        1. อัปโหลดไฟล์เส้นพื้นที่ที่ต้องการตรวจสอบ ( * เลือกไฟล์ KML หรือ ZIP ที่มี KML * ) ( * กรณีถ้าไฟล์ KML มีขนาดใหญ่ให้ทำเป็นไฟล์ ZIP * )
        2. อัปโหลดไฟล์ขอบเขต ( * ไฟล์ kml เท่านั้น * )  
        3. กดปุ่ม "เริ่มประมวลผลแยกไฟล์ KML" เพื่อดาวน์โหลดไฟล์แยก  
        4. กดปุ่ม "เริ่มประมวลผลรวมไฟล์ KML" เพื่อดาวน์โหลดไฟล์ที่รวมทุกเขต  
        """)

if __name__ == "__main__":
    main()
