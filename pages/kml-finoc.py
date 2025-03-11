import streamlit as st
import pandas as pd
from lxml import etree
import re
import base64
import io
import datetime

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="KML Excel Updater",
    page_icon="🌍",
    layout="wide"
)

# สไตล์ CSS แบบเรียบง่าย
st.markdown("""
<style>
    .main-title {
        font-size: 2rem;
        margin-bottom: 20px;
        color: #1E88E5;
    }
    
    .section-title {
        font-size: 1.5rem;
        margin-top: 15px;
        margin-bottom: 10px;
        color: #1976D2;
    }
    
    .download-button {
        display: inline-block;
        padding: 10px 20px;
        background-color: #2196F3;
        color: white;
        text-decoration: none;
        border-radius: 5px;
        margin-top: 10px;
    }
    
    .download-button:hover {
        background-color: #1976D2;
    }
    
    .stButton > button {
        background-color: #2196F3;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 1. อ่านไฟล์ KML
def read_kml(kml_file):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(kml_file, parser)
    return tree

# 2. อ่านไฟล์ Excel และทำความสะอาดข้อมูล
def read_excel(excel_file):
    df = pd.read_excel(excel_file)
    
    # แน่ใจว่าคอลัมน์ "Cable Name" เป็น string
    if 'Cable Name' in df.columns:
        df['Cable Name'] = df['Cable Name'].astype(str)
    
    # ทำความสะอาดชื่อคอลัมน์ (ลบช่องว่างตรงขอบ)
    df.columns = df.columns.str.strip()
    
    return df

# 3. อัพเดทข้อมูลใน KML โดยใช้ข้อมูลจาก Excel
def update_kml_with_excel_data(kml_tree, excel_df):
    root = kml_tree.getroot()
    
    # หา namespace ของ KML
    nsmap = root.nsmap
    kml_ns = '{' + nsmap.get(None, 'http://www.opengis.net/kml/2.2') + '}'
    
    # ค้นหา Placemarks ทั้งหมด
    placemarks = root.findall('.//' + kml_ns + 'Placemark')
    
    # ใช้ทุกคอลัมน์จาก Excel (ตอนนี้ทุกชื่อคอลัมน์ได้รับการทำความสะอาดแล้ว)
    required_columns = [
        'No.', 'Cable Name', 'Cable ID', 'Type', 'Cable Type', 'Standard', 'Brand', 
        'กรรมสิทธิ์', 'จำนวน core', 'ระยะทาง(m)', 'Core.km', 'Used core (max.)', 
        'End_A', 'End_B', 'Type_A', 'Type_B', 'Site_A', 'Site_B', 'Zone_A', 'Zone_B',
        'Province_A', 'Province_B', 'LatLng_A', 'LatLng_B', 'โครงการ', 'Network', 
        'ส่วนงาน', 'Status', 'Staff', 'Update'
    ]
    
    # ตรวจสอบว่ามีคอลัมน์ที่กำหนดในไฟล์ Excel หรือไม่
    missing_columns = [col for col in required_columns if col not in excel_df.columns]
    
    if missing_columns:
        st.warning(f"คำเตือน: คอลัมน์ต่อไปนี้หายไปจากไฟล์ Excel: {', '.join(missing_columns)}")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_placemarks = len(placemarks)
    updated_count = 0
    
    for i, placemark in enumerate(placemarks):
        # อัพเดท progress bar
        progress_bar.progress(int((i + 1) / total_placemarks * 100))
        status_text.text(f"กำลังประมวลผล... {i+1}/{total_placemarks}")
        
        # หาชื่อของ placemark
        name_elem = placemark.find(kml_ns + 'name')
        if name_elem is None:
            continue
        
        placemark_name = name_elem.text
        
        # ค้นหาข้อมูลที่ตรงกันใน Excel
        matching_row = excel_df[excel_df['Cable Name'] == placemark_name]
        
        if not matching_row.empty:
            updated_count += 1
            # สร้างหรืออัพเดท description
            desc_elem = placemark.find(kml_ns + 'description')
            if desc_elem is None:
                desc_elem = etree.SubElement(placemark, kml_ns + 'description')
            
            # สร้าง description ที่มีข้อมูลจาก Excel ใช้เฉพาะคอลัมน์ที่มีอยู่
            description = f"""
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #4285F4; color: white;">
                    <th colspan="2" style="padding: 8px; text-align: center;">ข้อมูลสาย {placemark_name}</th>
                </tr>
            """
            
            for column in required_columns:
                if column in matching_row.columns:
                    value = matching_row[column].values[0]
                    # ตรวจสอบค่า NaN และแสดงเป็น "-" ถ้าเป็น NaN
                    if pd.isna(value):
                        display_value = "-"
                    else:
                        display_value = value
                    
                    description += f"""
                    <tr>
                        <td style="padding: 6px; border: 1px solid #ddd; font-weight: bold; width: 30%; background-color: #f2f2f2;">{column}</td>
                        <td style="padding: 6px; border: 1px solid #ddd;">{display_value}</td>
                    </tr>
                    """
            
            # เพิ่มวันที่อัพเดท
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            description += f"""
                <tr>
                    <td style="padding: 6px; border: 1px solid #ddd; font-weight: bold; width: 30%; background-color: #f2f2f2;">Last Updated</td>
                    <td style="padding: 6px; border: 1px solid #ddd;">{current_time}</td>
                </tr>
            </table>
            """
            
            desc_elem.text = etree.CDATA(description)
    
    status_text.text(f"อัพเดทข้อมูลแล้ว {updated_count} รายการจากทั้งหมด {total_placemarks} รายการ")
    return kml_tree, updated_count

# 4. เพิ่มฟังก์ชั่นลบหมุด (Placemarks) ที่ไม่มีข้อมูลใน Excel
def remove_placemarks_not_in_excel(kml_tree, excel_df):
    root = kml_tree.getroot()
    
    # หา namespace ของ KML
    nsmap = root.nsmap
    kml_ns = '{' + nsmap.get(None, 'http://www.opengis.net/kml/2.2') + '}'
    
    # ค้นหา Placemarks ทั้งหมด
    placemarks = root.findall('.//' + kml_ns + 'Placemark')
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_placemarks = len(placemarks)
    removed_count = 0
    
    # รายการของ placemarks ที่จะลบ (เราไม่สามารถลบในระหว่างการวนลูปได้)
    placemarks_to_remove = []
    
    # สร้างชุดของชื่อใน Excel เพื่อการค้นหาที่เร็วขึ้น
    excel_names = set(excel_df['Cable Name'].astype(str).values)
    
    for i, placemark in enumerate(placemarks):
        # อัพเดท progress bar
        progress_bar.progress(int((i + 1) / total_placemarks * 100))
        status_text.text(f"กำลังตรวจสอบหมุด... {i+1}/{total_placemarks}")
        
        # หาชื่อของ placemark
        name_elem = placemark.find(kml_ns + 'name')
        if name_elem is None:
            continue
        
        placemark_name = name_elem.text
        
        # ตรวจสอบว่าชื่อมีอยู่ใน Excel หรือไม่
        if placemark_name not in excel_names:
            # เพิ่มเข้าไปในรายการที่จะลบ
            placemarks_to_remove.append(placemark)
            removed_count += 1
    
    # ลบ placemarks ที่ไม่พบใน Excel
    for placemark in placemarks_to_remove:
        parent = placemark.getparent()
        if parent is not None:
            parent.remove(placemark)
    
    status_text.text(f"ลบหมุดที่ไม่พบใน Excel แล้ว {removed_count} รายการจากทั้งหมด {total_placemarks} รายการ")
    return kml_tree, removed_count

# ฟังก์ชั่นใหม่สำหรับลบเฉพาะหมุดที่ไม่มีข้อมูลใน Excel
def remove_points_not_in_excel(kml_tree, excel_df):
    root = kml_tree.getroot()
    
    # หา namespace ของ KML
    nsmap = root.nsmap
    kml_ns = '{' + nsmap.get(None, 'http://www.opengis.net/kml/2.2') + '}'
    
    # ค้นหา Placemarks ทั้งหมด
    placemarks = root.findall('.//' + kml_ns + 'Placemark')
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_placemarks = len(placemarks)
    removed_count = 0
    
    # รายการของ placemarks ที่จะลบ (เราไม่สามารถลบในระหว่างการวนลูปได้)
    placemarks_to_remove = []
    
    # สร้างชุดของชื่อใน Excel เพื่อการค้นหาที่เร็วขึ้น
    excel_names = set(excel_df['Cable Name'].astype(str).values)
    
    for i, placemark in enumerate(placemarks):
        # อัพเดท progress bar
        progress_bar.progress(int((i + 1) / total_placemarks * 100))
        status_text.text(f"กำลังตรวจสอบหมุด... {i+1}/{total_placemarks}")
        
        # หาชื่อของ placemark
        name_elem = placemark.find(kml_ns + 'name')
        if name_elem is None:
            continue
        
        placemark_name = name_elem.text
        
        # ตรวจสอบประเภทของ Placemark (Point หรือ LineString)
        is_point = False
        geometry = placemark.find('.//' + kml_ns + 'Point')
        
        # ถ้าเป็น Point (หมุด) ให้ตรวจสอบว่ามีในไฟล์ Excel หรือไม่
        if geometry is not None:
            is_point = True
            
            # ถ้าเป็นหมุดและไม่มีใน Excel ให้เพิ่มเข้ารายการที่จะลบ
            if placemark_name not in excel_names:
                placemarks_to_remove.append(placemark)
                removed_count += 1
    
    # ลบเฉพาะ placemark ที่เป็นหมุดและไม่พบใน Excel
    for placemark in placemarks_to_remove:
        parent = placemark.getparent()
        if parent is not None:
            parent.remove(placemark)
    
    status_text.text(f"ลบหมุด (จุด) ที่ไม่พบใน Excel แล้ว {removed_count} รายการ")
    return kml_tree, removed_count

# 5. เพิ่มฟังก์ชั่นจัดกลุ่มและจัดการสีตามประเภท Cable
def style_placemarks_by_type(kml_tree, excel_df, style_column='Type'):
    if style_column not in excel_df.columns:
        return kml_tree, "ไม่พบคอลัมน์ที่ต้องการใช้สำหรับการจัดกลุ่ม"
    
    root = kml_tree.getroot()
    
    # หา namespace ของ KML
    nsmap = root.nsmap
    kml_ns = '{' + nsmap.get(None, 'http://www.opengis.net/kml/2.2') + '}'
    
    # สร้าง Document node ถ้าไม่มี
    document = root.find('.//' + kml_ns + 'Document')
    if document is None:
        document = etree.SubElement(root, kml_ns + 'Document')
    
    # ค้นหาประเภททั้งหมดจาก Excel
    types = excel_df[style_column].dropna().unique()
    
    # การกำหนดสีสำหรับแต่ละประเภท (แบบพื้นฐาน)
    colors = [
        'ff0000ff',  # แดง
        'ff00ff00',  # เขียว
        'ffff0000',  # น้ำเงิน
        'ff00ffff',  # เหลือง
        'ffff00ff',  # ม่วง
        'ff7f00ff',  # ส้ม
    ]
    
    # สร้าง style สำหรับแต่ละประเภท
    type_styles = {}
    
    for i, type_name in enumerate(types):
        # ใช้สีแบบวนลูป
        color_index = i % len(colors)
        color = colors[color_index]
        
        # สร้าง Style
        style_id = f"style_{re.sub(r'[^a-zA-Z0-9]', '_', str(type_name))}"
        style = etree.SubElement(document, kml_ns + 'Style', id=style_id)
        
        # LineStyle
        line_style = etree.SubElement(style, kml_ns + 'LineStyle')
        color_elem = etree.SubElement(line_style, kml_ns + 'color')
        color_elem.text = color
        width = etree.SubElement(line_style, kml_ns + 'width')
        width.text = '4'
        
        # เก็บความสัมพันธ์ระหว่างประเภทและ style
        type_styles[type_name] = style_id
    
    # ค้นหา Placemarks ทั้งหมดและกำหนด Style ตามประเภท
    placemarks = root.findall('.//' + kml_ns + 'Placemark')
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_placemarks = len(placemarks)
    styled_count = 0
    
    for i, placemark in enumerate(placemarks):
        # อัพเดท progress bar
        progress_bar.progress(int((i + 1) / total_placemarks * 100))
        status_text.text(f"กำลังกำหนดรูปแบบ... {i+1}/{total_placemarks}")
        
        # หาชื่อของ placemark
        name_elem = placemark.find(kml_ns + 'name')
        if name_elem is None:
            continue
        
        placemark_name = name_elem.text
        
        # ค้นหาข้อมูลที่ตรงกันใน Excel
        matching_row = excel_df[excel_df['Cable Name'] == placemark_name]
        
        if not matching_row.empty and style_column in matching_row.columns:
            type_value = matching_row[style_column].values[0]
            if pd.notna(type_value) and type_value in type_styles:
                # เพิ่ม Style URL ไปยัง Placemark
                style_url_elem = placemark.find(kml_ns + 'styleUrl')
                if style_url_elem is None:
                    style_url_elem = etree.SubElement(placemark, kml_ns + 'styleUrl')
                
                style_url_elem.text = f'#{type_styles[type_value]}'
                styled_count += 1
    
    status_text.text(f"กำหนดรูปแบบตามประเภทแล้ว {styled_count} รายการจากทั้งหมด {total_placemarks} รายการ")
    return kml_tree, f"จัดกลุ่มตาม {style_column} สำเร็จ {styled_count} รายการ"

# สร้างฟังก์ชันสำหรับสร้างลิงก์ดาวน์โหลด
def get_download_link(file_content, filename, text):
    b64 = base64.b64encode(file_content).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}" class="download-button" style="color: #FFFFFF;">{text}</a>'
    return href

# Main Streamlit app
def main():
    # ส่วนหัวของแอป
    st.markdown("<h1 class='main-title'>🌍 ปรับข้อมูล KML จาก FINOC</h1>", unsafe_allow_html=True)
    st.write("แอปพลิเคชันนี้ช่วยในการอัพเดทข้อมูลใน KML โดยใช้ข้อมูลจากไฟล์ Excel")
    
    # สร้างแท็บสำหรับการทำงาน
    tab1, tab2 = st.tabs(["📤 อัพโหลดและประมวลผล", "ℹ️ วิธีใช้งาน"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<h3 class='section-title'>อัพโหลดไฟล์ KML</h3>", unsafe_allow_html=True)
            kml_file = st.file_uploader("เลือกไฟล์ KML", type=['kml'])
        
        with col2:
            st.markdown("<h3 class='section-title'>อัพโหลดไฟล์ Excel</h3>", unsafe_allow_html=True)
            excel_file = st.file_uploader("เลือกไฟล์ Excel", type=['xlsx', 'xls'])
        
        st.markdown("<h3 class='section-title'>ตั้งค่าการประมวลผล</h3>", unsafe_allow_html=True)
        
        output_filename = st.text_input("ชื่อไฟล์ผลลัพธ์", "output_updated.kml")
        
        # ตัวเลือกเพิ่มเติม
        col1, col2, col3 = st.columns(3)
        
        with col1:
            remove_points = st.checkbox("🔹 ลบเฉพาะหมุด (จุด) ที่ไม่พบในไฟล์ Excel")
        
        with col2:
            remove_all_placemarks = st.checkbox("🔹 ลบทั้งหมด (หมุดและเส้น) ที่ไม่พบในไฟล์ Excel")
            
            # ป้องกันการเลือกทั้งสองตัวเลือกพร้อมกัน
            if remove_all_placemarks and remove_points:
                remove_points = False
                st.warning("คุณไม่สามารถเลือกทั้งสองตัวเลือกการลบพร้อมกันได้")
        
        with col3:
            style_by_type = st.checkbox("🔹 จัดกลุ่มและกำหนดสีตามประเภท")
        
        if style_by_type:
            style_column = st.selectbox("เลือกคอลัมน์สำหรับการจัดกลุ่ม", 
                                      ['Type', 'Cable Type'])
        
        process_btn = st.button("▶️ ประมวลผล")
        
        if process_btn:
            if kml_file is None or excel_file is None:
                st.error("กรุณาอัพโหลดทั้งไฟล์ KML และ Excel")
            else:
                with st.spinner("กำลังประมวลผล..."):
                    try:
                        # อ่านไฟล์
                        kml_tree = read_kml(kml_file)
                        excel_df = read_excel(excel_file)
                        
                        # แสดงผลข้อมูล Excel สำหรับตรวจสอบ
                        st.subheader("ตัวอย่างข้อมูลจาก Excel")
                        st.dataframe(excel_df.head())
                        
                        # อัพเดทข้อมูล
                        updated_kml, updated_count = update_kml_with_excel_data(kml_tree, excel_df)
                        
                        # ถ้าผู้ใช้เลือกลบหมุด (จุด) ที่ไม่พบในไฟล์ Excel
                        removed_count = 0
                        removed_all_count = 0
                        
                        if remove_points:
                            updated_kml, removed_count = remove_points_not_in_excel(updated_kml, excel_df)
                        
                        # ถ้าผู้ใช้เลือกลบทั้งหมดที่ไม่พบในไฟล์ Excel
                        elif remove_all_placemarks:
                            updated_kml, removed_all_count = remove_placemarks_not_in_excel(updated_kml, excel_df)
                        
                        # ถ้าผู้ใช้เลือกจัดกลุ่มตามประเภท
                        style_result = ""
                        if style_by_type:
                            updated_kml, style_result = style_placemarks_by_type(updated_kml, excel_df, style_column)
                        
                        # แปลงกลับเป็น bytes สำหรับดาวน์โหลด
                        output = io.BytesIO()
                        updated_kml.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8')
                        output.seek(0)
                        
                        # สร้างลิงก์ดาวน์โหลด
                        success_msg = f"✅ อัพเดทข้อมูลเรียบร้อยแล้ว {updated_count} รายการ"
                        if remove_points and removed_count > 0:
                            success_msg += f"\n✅ ลบเฉพาะหมุด (จุด) ที่ไม่พบในไฟล์ Excel {removed_count} รายการ"
                        elif remove_all_placemarks and removed_all_count > 0:
                            success_msg += f"\n✅ ลบทั้งหมด (หมุดและเส้น) ที่ไม่พบในไฟล์ Excel {removed_all_count} รายการ"
                        if style_by_type and style_result:
                            success_msg += f"\n✅ {style_result}"
                        
                        st.success(success_msg)
                        st.markdown(get_download_link(output.getvalue(), output_filename, 
                                                    f"📥 ดาวน์โหลดไฟล์ KML ที่อัพเดทแล้ว ({output_filename})"), 
                                    unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {str(e)}")
    
    with tab2:
        st.markdown("<h3 class='section-title'>วิธีการใช้งาน</h3>", unsafe_allow_html=True)
        st.write("""
        1. อัพโหลดไฟล์ KML ที่ต้องการอัพเดท
        2. อัพโหลดไฟล์ Excel ที่มีข้อมูลสำหรับอัพเดท
        3. ตั้งชื่อไฟล์ผลลัพธ์ที่ต้องการ
        4. เลือกตัวเลือกเพิ่มเติมตามต้องการ:
           - ลบหมุดที่ไม่พบในไฟล์ Excel
           - จัดกลุ่มและกำหนดสีตามประเภท
        5. กดปุ่ม "ประมวลผล"
        6. ดาวน์โหลดไฟล์ KML ที่อัพเดทแล้ว
        """)
        
        st.markdown("<h3 class='section-title'>โครงสร้างข้อมูล Excel ที่รองรับ</h3>", unsafe_allow_html=True)
        st.write("""
        แอปพลิเคชันนี้คาดหวังให้ไฟล์ Excel มีคอลัมน์ดังต่อไปนี้:
        * Cable Name - ชื่อสายเคเบิล (ใช้สำหรับจับคู่กับชื่อหมุดใน KML)
        * คอลัมน์ข้อมูลอื่นๆ เช่น Type, Cable ID, Standard, Brand, จำนวน core เป็นต้น
        
        หมายเหตุ: คอลัมน์ Cable Name จำเป็นต้องมีในไฟล์ Excel และต้องตรงกับชื่อหมุดใน KML
        """)
        
        st.info("ในกรณีที่ต้องการรูปแบบไฟล์ Excel ตัวอย่าง โปรดติดต่อฝ่ายสนับสนุน")

if __name__ == "__main__":
    main()
