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
                coord_list = coordinates.text.strip().split()
                points = [Point(map(float, coord.split(",")[:2])) for coord in coord_list]
                
                # ตรวจสอบว่าอย่างน้อยหนึ่งจุดอยู่ใน boundary
                if not any(point.within(boundary_polygon) for point in points):
                    placemarks_to_remove.append(placemark)  

        for placemark in placemarks_to_remove:
            placemark.getparent().remove(placemark)

        tree.write(output_kml)
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

# ฟังก์ชันสำหรับรวมไฟล์ KML
def combine_kml_files(output_files):
    combined_output_kml = tempfile.NamedTemporaryFile(delete=False, suffix='.kml')

    combined_tree = etree.ElementTree(etree.Element("kml"))
    combined_root = combined_tree.getroot()
    combined_root.set("xmlns", "http://www.opengis.net/kml/2.2")
    document_elem = etree.SubElement(combined_root, "Document")

    for file in output_files:
        try:
            tree = etree.parse(file)
            root = tree.getroot()
            for placemark in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
                document_elem.append(placemark)
        except Exception as e:
            st.error(f"ไม่สามารถรวมไฟล์ {file}: {e}")

    combined_tree.write(combined_output_kml.name)
    return combined_output_kml.name  

# ฟังก์ชันสร้างไฟล์ ZIP
def create_zip_for_download(output_files):
    zip_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    with zipfile.ZipFile(zip_file, 'w') as zipf:
        for file in output_files:
            zipf.write(file, os.path.basename(file))
    return zip_file.name  

# Streamlit UI
def main():
    st.set_page_config(page_title="โปรแกรมตัดพื้นที่จาก KML", layout="wide")
    st.title("🗺️ โปรแกรมตัดพื้นที่จากไฟล์ KML")
    st.markdown("---")

    input_file = st.file_uploader("📁 เลือกไฟล์เส้นพื้นที่ที่ต้องการตรวจสอบ ( * ไฟล์ kml เท่านั้น * )", type=['kml'])
    boundary_file = st.file_uploader("📁 เลือกไฟล์ขอบเขต ( * ไฟล์ kml เท่านั้น * )", type=['kml'])

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 เริ่มประมวลผลแยกไฟล์ KML"):
            if input_file and boundary_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_input:
                    tmp_input.write(input_file.getvalue())
                    input_path = tmp_input.name

                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                    tmp_boundary.write(boundary_file.getvalue())
                    boundary_path = tmp_boundary.name

                try:
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
            else:
                st.error("กรุณาเลือกไฟล์ให้ครบถ้วน")

    with col2:
        if st.button("🚀 เริ่มประมวลผลรวมไฟล์ KML"):
            if input_file and boundary_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_input:
                    tmp_input.write(input_file.getvalue())
                    input_path = tmp_input.name

                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_boundary:
                    tmp_boundary.write(boundary_file.getvalue())
                    boundary_path = tmp_boundary.name

                try:
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
        1. อัปโหลดไฟล์เส้นพื้นที่ที่ต้องการตรวจสอบ ( * ไฟล์ kml เท่านั้น * )  
        2. อัปโหลดไฟล์ขอบเขต ( * ไฟล์ kml เท่านั้น * )  
        3. กดปุ่ม "เริ่มประมวลผลแยกไฟล์ KML" เพื่อดาวน์โหลดไฟล์แยก  
        4. กดปุ่ม "เริ่มประมวลผลรวมไฟล์ KML" เพื่อดาวน์โหลดไฟล์ที่รวมทุกเขต  
        """)

if __name__ == "__main__":
    main()
