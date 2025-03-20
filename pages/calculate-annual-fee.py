import pandas as pd
import streamlit as st
import numpy as np
from io import BytesIO

# Set up Streamlit page configuration
st.set_page_config(page_title="โปรแกรมวิเคราะห์ข้อมูลสายสื่อสาร", layout="wide", initial_sidebar_state="expanded")

# Header
st.title("📊 โปรแกรมวิเคราะห์ข้อมูลสายสื่อสาร")
st.markdown("จัดการและวิเคราะห์ข้อมูลสายสื่อสารอย่างมีประสิทธิภาพด้วยเครื่องมือนี้")

# File uploader
uploaded_file = st.file_uploader("📂 อัปโหลดไฟล์ Excel", type=["xlsx"], help="รองรับไฟล์ .xlsx เท่านั้น")

if uploaded_file:
    # Load Excel file
    xls = pd.ExcelFile(uploaded_file)
    
    # Sheet selection
    st.subheader("📑 เลือก Sheet ที่ต้องการวิเคราะห์")
    selected_sheet = st.selectbox("เลือก Sheet", xls.sheet_names, help="เลือก Sheet จากไฟล์ Excel ที่อัปโหลด")
    
    if selected_sheet:
        # Load data
        with st.spinner("กำลังโหลดข้อมูล..."):
            df = pd.read_excel(xls, sheet_name=selected_sheet, header=[0,1], skiprows=6)
            df.columns = [' '.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]

        # Function to find closest column
        def find_closest_column(df, column_name):
            return next((col for col in df.columns if column_name in col), None)

        # Find required columns
        col_total = find_closest_column(df, "จำนวนเสา(ต้น) ทั้งหมด")
        col_in_area = find_closest_column(df, "จำนวนเสา(ต้น) ในพื้นที่")

        if col_total and col_in_area:
            df["ตรวจสอบ"] = df[col_total] == df[col_in_area]
        else:
            st.error(f"❌ ไม่พบคอลัมน์: {col_total}, {col_in_area}")
            st.stop()

        # Rename columns for consistency
        def rename_column(df, expected_name):
            correct_col = find_closest_column(df, expected_name)
            if correct_col:
                df.rename(columns={correct_col: expected_name}, inplace=True)

        rename_column(df, "tag เสาไฟฟ้าที่ผ่าน")
        rename_column(df, "tag ของสายสื่อสาร")
        rename_column(df, "พื้นที่รับผิดชอบของ กฟภ.")
        rename_column(df, "เส้นผ่านศูนย์กลาง(มม.)")

        df.rename(columns={
            "จำนวนเสา(ต้น) ทั้งหมด": "จำนวนเสา(ต้น)ทั้งหมด",
            "จำนวนเสา(ต้น) ในพื้นที่": "จำนวนเสา(ต้น)ในพื้นที่",
            "พิกัด ต้น": "พิกัดต้น",
            "พิกัด ปลาย": "พิกัดปลาย",
        }, inplace=True)

        df["ตรวจสอบ"] = df["จำนวนเสา(ต้น)ทั้งหมด"] == df["จำนวนเสา(ต้น)ในพื้นที่"]

        # Split data into matching and non-matching
        df_match = df[df["ตรวจสอบ"]].copy()
        df_not_match = df[~df["ตรวจสอบ"]].copy()

        df_match["ตรวจสอบความถูกต้อง"] = "✅ ตรงกัน"
        df_not_match["ตรวจสอบความถูกต้อง"] = "❌ ไม่ตรงกัน"

        # Clean and split tags
        def clean_and_split_tags(tags):
            if pd.isna(tags):
                return []
            return [tag.strip() for tag in str(tags).split(',') if tag.strip()]

        df_match["tag เสาไฟฟ้าที่ผ่าน"] = df_match["tag เสาไฟฟ้าที่ผ่าน"].apply(clean_and_split_tags)
        df_not_match["tag เสาไฟฟ้าที่ผ่าน"] = df_not_match["tag เสาไฟฟ้าที่ผ่าน"].apply(clean_and_split_tags)

        # ฟังก์ชันใหม่สำหรับการหาเขตการไฟฟ้าของ tag จาก sheet ที่ตรงกัน
        def find_utility_area_for_tag(tag, df_match):
            # ขยาย DataFrame เพื่อให้มี 1 tag ต่อ 1 แถว
            df_match_exploded = df_match.explode("tag เสาไฟฟ้าที่ผ่าน")
            # กรองเอาเฉพาะแถวที่มี tag ตรงกับค่าที่ต้องการ
            matches = df_match_exploded[df_match_exploded["tag เสาไฟฟ้าที่ผ่าน"] == tag]
            if not matches.empty:
                # คืนค่าเขตการไฟฟ้าของ tag นี้
                return matches["พื้นที่รับผิดชอบของ กฟภ."].iloc[0]
            return None

        # Tag assignment logic (แก้ไขใหม่)
        unique_comm_tags = df_not_match["tag ของสายสื่อสาร"].unique()
        tag_assignments = {}

        def display_communication_tag_details(comm_tag, comm_data, df_match, unique_areas, area_details, all_unique_tags):
            """
            แสดงรายละเอียดของ tag สายสื่อสารในรูปแบบที่แยกตามสถานะการค้นหา
            
            Parameters:
            -----------
            comm_tag : str
                Tag ของสายสื่อสาร
            comm_data : DataFrame
                ข้อมูลของ tag สายสื่อสารนี้
            df_match : DataFrame
                ข้อมูลที่มีความตรงกัน
            unique_areas : array
                พื้นที่รับผิดชอบที่เกี่ยวข้องกับ tag นี้
            area_details : list
                รายละเอียดของแต่ละพื้นที่
            all_unique_tags : list
                รายการ tag เสาไฟฟ้าทั้งหมดที่เกี่ยวข้อง
            
            Returns:
            --------
            dict
                ข้อมูลการจัดสรร tag
            """
            st.write(f"**ข้อมูล tag ของสายสื่อสาร: {comm_tag} (จำนวนแถว: {len(comm_data)})**")
            
            # ค้นหาคอลัมน์ "ชื่อเส้นทาง" ที่ใกล้เคียง
            route_col = find_closest_column(comm_data, "ชื่อเส้นทาง")
            if not route_col:
                route_col = "ชื่อเส้นทาง"  # ถ้าไม่เจอ ใช้ชื่อนี้เป็น fallback

            # ดึงข้อมูลสำหรับทุกแถวใน comm_data โดยใช้คอลัมน์ที่ต้องการ
            comm_tag_details = []
            for _, row in comm_data.iterrows():
                comm_tag_details.append({
                    "tag ของสายสื่อสาร": comm_tag,
                    "ชื่อเส้นทาง": row.get(route_col, "ไม่ระบุ") if route_col in comm_data.columns else "ไม่ระบุ",
                    "พิกัดต้น": row["พิกัดต้น"],
                    "พิกัดปลาย": row["พิกัดปลาย"],
                    "การไฟฟ้า": row["พื้นที่รับผิดชอบของ กฟภ."]
                })
            comm_tag_df = pd.DataFrame(comm_tag_details)
            
            if not comm_tag_df.empty:
                # Swap the coordinates in 'พิกัดต้น' and 'พิกัดปลาย'
                comm_tag_df["พิกัดต้น"] = comm_tag_df["พิกัดต้น"].apply(lambda x: ', '.join(reversed(x.split(', '))))
                comm_tag_df["พิกัดปลาย"] = comm_tag_df["พิกัดปลาย"].apply(lambda x: ', '.join(reversed(x.split(', '))))
                
                st.dataframe(
                    comm_tag_df[["tag ของสายสื่อสาร", "ชื่อเส้นทาง", "พิกัดต้น", "พิกัดปลาย", "การไฟฟ้า"]],
                    use_container_width=True,
                    height=max(68, min(500, len(comm_tag_df) * 30))
                )
            else:
                st.write("ไม่มีข้อมูลสำหรับ tag นี้")

            st.write("**พื้นที่รับผิดชอบและจำนวน tag:**")
            st.dataframe(pd.DataFrame([
                {"พื้นที่": detail["area"], 
                "จำนวนเสาในพื้นที่": detail["poles_in_area"], 
                "จำนวน tag เสาไฟฟ้า": detail["tags_count"]} 
                for detail in area_details
            ]), use_container_width=True)

            # แสดง tag เสาไฟฟ้าที่ผ่านทั้งหมด
            st.write(f"**ตัวอย่าง tag เสาไฟฟ้าที่ผ่านทั้งหมด ({len(all_unique_tags)} tag):**")
            if all_unique_tags:
                st.text_area(
                    "tag ทั้งหมด", 
                    ", ".join(all_unique_tags), 
                    height=max(68, min(150, len(all_unique_tags) * 10)),
                    key=f"all_tags_{comm_tag}"
                )
            else:
                st.write("ไม่มี tag เสาไฟฟ้าที่ผ่านในข้อมูลนี้")
            
            tag_assignments = {}
            # ถ้ามีเพียงพื้นที่เดียว
            if len(unique_areas) == 1:
                return handle_single_area_case(comm_tag, unique_areas, area_details, all_unique_tags)
            # ถ้ามีมากกว่าหนึ่งพื้นที่
            elif len(unique_areas) > 1 and all_unique_tags:
                return handle_multiple_areas_case(comm_tag, unique_areas, area_details, all_unique_tags, df_match)
            else:
                return {comm_tag: {}}

        def handle_single_area_case(comm_tag, unique_areas, area_details, all_unique_tags):
            """
            จัดการกรณีที่มีพื้นที่เดียว
            """
            tag_assignments = {comm_tag: {}}
            area = unique_areas[0]
            area_index = 0  # มีแค่พื้นที่เดียว
            
            # UI สำหรับพื้นที่เดียว
            st.subheader("🔍 กรณีพื้นที่เดียว")
            
            if all_unique_tags:
                detail = area_details[area_index]
                poles_in_area = detail["poles_in_area"]
                
                st.info(f"มีเพียงเขตการไฟฟ้าเดียว ({area}) จำนวนเสา(ต้น)ในพื้นที่: {poles_in_area} ต้น")
                
                # ให้ผู้ใช้เลือกวิธีการจัดสรร tag
                tag_selection_method = st.radio(
                    "เลือกวิธีการจัดสรร tag:",
                    ["ต้นทาง", "ปลายทาง", "ระบุเอง"],
                    key=f"tag_selection_method_{comm_tag}"
                )
                
                is_custom_input = tag_selection_method == "ระบุเอง"  # ตัวแปรตรวจสอบว่าเป็นการระบุเองหรือไม่
                selected_tags = []  # กำหนดค่าเริ่มต้น
                can_proceed = True  # ตัวแปรควบคุมว่าสามารถยืนยันได้หรือไม่
                
                if is_custom_input:
                    # ให้ผู้ใช้ใส่ tag เอง
                    custom_tags_input = st.text_area(
                        f"ระบุ tag ที่ต้องการจัดสรรให้ {area} (คั่นด้วยเครื่องหมายคอมม่า ,)",
                        value="",
                        height=150,
                        key=f"custom_tags_{comm_tag}_{area}"
                    )
                    
                    # แปลงข้อความที่ผู้ใช้ใส่เป็นรายการ tag
                    if custom_tags_input.strip():
                        selected_tags = [tag.strip() for tag in custom_tags_input.split(",") if tag.strip()]
                        
                        # ตรวจสอบว่า tag ที่ใส่มาอยู่ใน all_unique_tags หรือไม่
                        invalid_tags = [tag for tag in selected_tags if tag not in all_unique_tags]
                        if invalid_tags:
                            st.error(f"พบ tag ที่ไม่อยู่ในรายการ: {', '.join(invalid_tags)}")
                            can_proceed = False
                        
                        # ตรวจสอบ tag ซ้ำ
                        duplicate_tags = []
                        seen_tags = set()
                        for tag in selected_tags:
                            if tag in seen_tags:
                                duplicate_tags.append(tag)
                            else:
                                seen_tags.add(tag)
                        
                        if duplicate_tags:
                            st.error(f"พบ tag ซ้ำกัน: {', '.join(duplicate_tags)}")
                            can_proceed = False
                        
                        # แจ้งเตือนจำนวน tag ที่ไม่ตรงกับจำนวนเสา แต่ยังให้ดำเนินการต่อได้
                        if len(selected_tags) != poles_in_area:
                            if len(selected_tags) < poles_in_area:
                                st.warning(f"จำนวน tag ({len(selected_tags)} tag) น้อยกว่าจำนวนเสาในพื้นที่ ({poles_in_area} ต้น)")
                            else:
                                st.warning(f"จำนวน tag ({len(selected_tags)} tag) มากกว่าจำนวนเสาในพื้นที่ ({poles_in_area} ต้น)")
                        
                        # แสดงตัวอย่าง tag ที่เลือก (แสดงเสมอเมื่อมีการใส่ข้อมูล)
                        st.write(f"จัดสรร {len(selected_tags)} tag จาก {len(all_unique_tags)} tag ให้กับ {area}")
                        st.text_area(
                            f"tag ที่จัดสรรให้ {area}",
                            ", ".join(selected_tags),
                            height=100,
                            key=f"selected_tags_{comm_tag}_{area}",
                            disabled=True
                        )
                    else:
                        st.warning("กรุณาระบุ tag อย่างน้อย 1 รายการ")
                        
                    # แสดงปุ่มยืนยันทันทีเมื่อเลือก "ระบุเอง" โดยไม่สนใจเงื่อนไขอื่น
                    if st.button(f"ยืนยันการจัดสรร tag สำหรับ {area}", key=f"confirm_{comm_tag}_{area}"):
                        if not selected_tags:
                            st.error("กรุณาระบุ tag อย่างน้อย 1 รายการก่อนยืนยัน")
                        elif not can_proceed:
                            st.error("กรุณาแก้ไขข้อผิดพลาดก่อนยืนยัน")
                        else:
                            st.success(f"จัดสรร tag สำหรับ {area} เรียบร้อยแล้ว")
                            # เก็บผลการจัดสรร
                            tag_assignments[comm_tag] = {area: selected_tags}
                    else:
                        # ยังไม่ยืนยัน ใส่ค่าว่างไว้ก่อน
                        tag_assignments[comm_tag] = {area: []}
                        
                else:
                    # จำนวน tag ที่จะเลือก
                    num_tags_to_select = min(int(poles_in_area), len(all_unique_tags))
                    
                    # ตรวจสอบว่ามี tag เพียงพอหรือไม่
                    if num_tags_to_select < poles_in_area:
                        st.error(f"มี tag ไม่เพียงพอสำหรับจำนวนเสาในพื้นที่ ({poles_in_area} ต้น) มี tag เพียง {len(all_unique_tags)} tag")
                        can_proceed = False
                    
                    # เลือก tag ตามลำดับที่ผู้ใช้เลือก
                    if tag_selection_method == "ต้นทาง":
                        selected_tags = all_unique_tags[:num_tags_to_select]
                    else:  # จากท้ายรายการ
                        selected_tags = all_unique_tags[-num_tags_to_select:]
                    
                    # แสดงตัวอย่าง tag ที่เลือก
                    if selected_tags:
                        st.write(f"จัดสรร {len(selected_tags)} tag จาก {len(all_unique_tags)} tag ให้กับ {area}")
                        st.text_area(
                            f"tag ที่จัดสรรให้ {area}",
                            ", ".join(selected_tags),
                            height=100,
                            key=f"selected_tags_{comm_tag}_{area}",
                            disabled=True
                        )
                    
                    # สำหรับกรณีที่ไม่ใช่การระบุเอง ให้เก็บค่าเลย
                    tag_assignments[comm_tag] = {area: selected_tags}
            else:
                st.warning(f"มีเพียงเขตการไฟฟ้าเดียว ({area}) แต่ไม่มี tag เสาไฟฟ้าที่ผ่าน")
                tag_assignments[comm_tag] = {area: []}
            
            return tag_assignments
                
        def handle_multiple_areas_case(comm_tag, unique_areas, area_details, all_unique_tags, df_match):
            """
            จัดการกรณีที่มีหลายพื้นที่
            """
            tag_assignments = {comm_tag: {area: [] for area in unique_areas}}
            st.subheader(f"🔀 การจัดสรร tag เสาไฟฟ้าสำหรับ: {comm_tag}")
            
            # กรณีมีมากกว่า 2 การไฟฟ้า
            if len(unique_areas) > 2:
                return handle_more_than_two_areas(comm_tag, unique_areas, area_details, all_unique_tags)
            
            # กรณีมี 2 การไฟฟ้า - ค้นหา tag ในข้อมูลที่ตรงกัน
            last_tag = all_unique_tags[-1] if all_unique_tags else None
            first_tag = all_unique_tags[0] if all_unique_tags else None
            
            # ทางเลือกที่ 1: ตรวจสอบ tag สุดท้าย
            if last_tag:
                found_area, found_tag = check_tag_in_matched_data(last_tag, unique_areas, df_match)
                if found_area:
                    return handle_found_tag_case(comm_tag, unique_areas, area_details, all_unique_tags, found_area, found_tag, "ท้าย", df_match)
            
            # ทางเลือกที่ 2: ตรวจสอบ tag แรก
            if first_tag:
                found_area, found_tag = check_tag_in_matched_data(first_tag, unique_areas, df_match)
                if found_area:
                    return handle_found_tag_case(comm_tag, unique_areas, area_details, all_unique_tags, found_area, found_tag, "ต้น", df_match)
            
            # ทางเลือกที่ 3: ไม่พบ tag ในข้อมูลที่ตรงกัน
            if last_tag and first_tag:
                st.warning(f"⚠️ ไม่พบทั้ง tag สุดท้าย '{last_tag}' และ tag แรก '{first_tag}' ในข้อมูลที่ตรงกัน หรืออยู่ในเขตการไฟฟ้าที่ไม่เกี่ยวข้อง")
            
            return handle_manual_assignment(comm_tag, unique_areas, area_details, all_unique_tags)

        def check_tag_in_matched_data(tag, unique_areas, df_match):
            """
            ตรวจสอบว่า tag อยู่ในข้อมูลที่ตรงกันหรือไม่
            """
            # ขยาย DataFrame เพื่อให้มี 1 tag ต่อ 1 แถว
            df_match_exploded = df_match.explode("tag เสาไฟฟ้าที่ผ่าน")
            # กรองเอาเฉพาะแถวที่มี tag ตรงกับค่าที่ต้องการ
            matches = df_match_exploded[df_match_exploded["tag เสาไฟฟ้าที่ผ่าน"] == tag]
            if not matches.empty:
                # ตรวจสอบว่าพื้นที่ที่พบอยู่ในพื้นที่ที่เกี่ยวข้องหรือไม่
                found_area = matches["พื้นที่รับผิดชอบของ กฟภ."].iloc[0]
                if found_area in unique_areas:
                    return found_area, tag
            return None, None

        def handle_found_tag_case(comm_tag, unique_areas, area_details, all_unique_tags, found_area, found_tag, tag_position, df_match):
            """
            จัดการกรณีที่พบ tag ในข้อมูลที่ตรงกัน
            """
            st.success(f"✅ พบ tag {tag_position} '{found_tag}' ในเขตการไฟฟ้า {found_area} จากข้อมูลที่ตรงกัน")
            
            # จัดเรียงพื้นที่โดยให้พื้นที่ที่พบ tag มาก่อน
            other_areas = [area for area in unique_areas if area != found_area]
            sorted_areas = [found_area] + other_areas
            
            # แสดงลำดับการจัดสรร
            with st.container():
                st.write("**ลำดับการจัดสรร tag:**")
                for i, area in enumerate(sorted_areas, 1):
                    area_index = list(unique_areas).index(area)
                    detail = area_details[area_index]
                    st.write(f"{i}. {area}: {detail['poles_in_area']} ต้น")
            
            # การจัดสรร tag ตามพื้นที่ที่พบ
            tag_assignments = {comm_tag: {area: [] for area in unique_areas}}
            remaining_tags = all_unique_tags.copy()
            
            # ค้นหา index ของ tag ที่พบ
            if found_tag in remaining_tags:
                # จัดสรร tag ให้กับการไฟฟ้าที่พบในข้อมูลตรงกัน
                area_index = list(unique_areas).index(found_area)
                detail = area_details[area_index]
                poles_needed = detail["poles_in_area"]
                
                # กรณีที่ tag ที่พบอยู่ต้นรายการ
                if tag_position == "ต้น":
                    assigned_tags = remaining_tags[:int(poles_needed)]
                # กรณีที่ tag ที่พบอยู่ท้ายรายการ
                else:
                    assigned_tags = remaining_tags[-int(poles_needed):]
                
                tag_assignments[comm_tag][found_area] = assigned_tags
                remaining_tags = [tag for tag in remaining_tags if tag not in assigned_tags]
            
            # จัดสรร tag ที่เหลือให้กับการไฟฟ้าอื่นๆ
            for area in sorted_areas:
                if area != found_area:  # ข้ามการไฟฟ้าที่จัดสรรไปแล้ว
                    area_index = list(unique_areas).index(area)
                    detail = area_details[area_index]
                    poles_needed = detail["poles_in_area"]
                    if poles_needed <= len(remaining_tags):
                        assigned_tags = remaining_tags[:int(poles_needed)]
                        tag_assignments[comm_tag][area] = assigned_tags
                        remaining_tags = [tag for tag in remaining_tags if tag not in assigned_tags]
                    else:
                        tag_assignments[comm_tag][area] = remaining_tags
                        remaining_tags = []
            
            # แสดงผลการจัดสรร
            display_tag_assignment_results(sorted_areas, tag_assignments, comm_tag)
            
            return tag_assignments

        def handle_more_than_two_areas(comm_tag, unique_areas, area_details, all_unique_tags):
            """
            จัดการกรณีที่มีมากกว่า 2 การไฟฟ้า
            """
            st.warning(f"⚠️ มี tag สายสื่อสารที่มีมากกว่า 2 การไฟฟ้า ({len(unique_areas)} การไฟฟ้า) ไม่ต้องไปดู sheet ที่ตรงกัน")
            return handle_manual_assignment(comm_tag, unique_areas, area_details, all_unique_tags)

        def handle_manual_assignment(comm_tag, unique_areas, area_details, all_unique_tags):
            """
            จัดการกรณีที่ต้องให้ผู้ใช้กำหนดลำดับเอง หรือระบุ tag เอง โดยใช้ session state
            และมีปุ่มยืนยันเพียงปุ่มเดียวต่อกลุ่ม
            """
            # สร้าง key สำหรับ session state
            ss_key = f"order_data_{comm_tag}"
            result_key = f"result_{comm_tag}"
            custom_tags_key = f"custom_tags_{comm_tag}"
            
            # เริ่มต้นค่าใน session state ถ้ายังไม่มี
            if ss_key not in st.session_state:
                st.session_state[ss_key] = {area: i + 1 for i, area in enumerate(unique_areas)}
            if result_key not in st.session_state:
                st.session_state[result_key] = None
            if custom_tags_key not in st.session_state:
                st.session_state[custom_tags_key] = {area: "" for area in unique_areas}

            # เตรียมค่าเริ่มต้นสำหรับ return
            tag_assignments = {comm_tag: {area: [] for area in unique_areas}}

            st.write(f"กำหนดลำดับพื้นที่หรือระบุ tag เองสำหรับการจัดสรร tag เสาไฟฟ้าสำหรับ: {comm_tag}")
            
            # เพิ่มตัวเลือกวิธีการจัดสรร
            assignment_method = st.radio(
                "เลือกวิธีการจัดสรร tag:",
                ["กำหนดลำดับอัตโนมัติ", "ระบุ tag เอง"],
                key=f"assignment_method_{comm_tag}"
            )
            
            if assignment_method == "กำหนดลำดับอัตโนมัติ":
                # ฟอร์มสำหรับกำหนดลำดับ
                with st.form(key=f"order_form_{comm_tag}"):
                    cols = st.columns(len(unique_areas))
                    order_values = {}
                    
                    for i, area in enumerate(unique_areas):
                        with cols[i]:
                            order_values[area] = st.number_input(
                                f"{area}",
                                min_value=1,
                                max_value=len(unique_areas),
                                value=st.session_state[ss_key][area],
                                key=f"input_{comm_tag}_{area}"
                            )
                    
                    submit_button = st.form_submit_button(label="ยืนยันการจัดลำดับ")
                    
                    if submit_button:
                        st.session_state[ss_key] = order_values
                        sorted_areas = sorted(unique_areas, key=lambda x: st.session_state[ss_key][x])
                        tag_assignments = {comm_tag: {area: [] for area in unique_areas}}
                        remaining_tags = all_unique_tags.copy()
                        
                        for area in sorted_areas:
                            area_index = list(unique_areas).index(area)
                            detail = area_details[area_index]
                            poles_needed = detail["poles_in_area"]
                            if poles_needed <= len(remaining_tags):
                                assigned_tags = remaining_tags[:int(poles_needed)]
                                tag_assignments[comm_tag][area] = assigned_tags
                                remaining_tags = [tag for tag in remaining_tags if tag not in assigned_tags]
                            else:
                                tag_assignments[comm_tag][area] = remaining_tags
                                remaining_tags = []
                        
                        st.session_state[result_key] = {
                            "sorted_areas": sorted_areas,
                            "tag_assignments": tag_assignments
                        }
            
            else:  # ระบุ tag เอง
                # ฟอร์มสำหรับระบุ tag เอง
                with st.form(key=f"custom_tags_form_{comm_tag}"):
                    custom_tags = {}
                    for area in unique_areas:
                        area_index = list(unique_areas).index(area)
                        detail = area_details[area_index]
                        poles_needed = detail["poles_in_area"]
                        st.write(f"{area}: จำนวนเสาที่ต้องการ {poles_needed} ต้น")
                        custom_tags[area] = st.text_area(
                            f"ระบุ tag สำหรับ {area} (คั่นด้วยเครื่องหมายคอมม่า , แนะนำให้ใส่ {poles_needed} tag)",
                            value=st.session_state[custom_tags_key][area],
                            height=100,
                            key=f"custom_tags_input_{comm_tag}_{area}"
                        )
                    
                    submit_custom_button = st.form_submit_button(label="ยืนยันการระบุ tag")
                    
                    if submit_custom_button:
                        temp_tag_assignments = {comm_tag: {area: [] for area in unique_areas}}
                        valid = True
                        has_warnings = False
                        
                        # เก็บ tag ทั้งหมดที่ถูกเลือกไปแล้วเพื่อตรวจสอบความซ้ำซ้อน
                        used_tags = []
                        
                        for area in unique_areas:
                            area_index = list(unique_areas).index(area)
                            detail = area_details[area_index]
                            poles_needed = detail["poles_in_area"]
                            
                            if custom_tags[area].strip():
                                selected_tags = [tag.strip() for tag in custom_tags[area].split(",") if tag.strip()]
                                
                                # ตรวจสอบและแจ้งเตือนเมื่อจำนวน tag ไม่ตรงกับที่ต้องการ
                                if len(selected_tags) != poles_needed:
                                    st.warning(f"จำนวน tag ที่ระบุสำหรับ {area} ({len(selected_tags)}) ไม่ตรงกับจำนวนเสา ({poles_needed}) ที่แนะนำ")
                                    has_warnings = True
                                
                                # แจ้งเตือนเมื่อมี tag ที่ไม่อยู่ในรายการ
                                invalid_tags = [tag for tag in selected_tags if tag not in all_unique_tags]
                                if invalid_tags:
                                    st.warning(f"พบ tag ที่ไม่อยู่ในรายการสำหรับ {area}: {', '.join(invalid_tags)}")
                                    has_warnings = True
                                
                                # ตรวจสอบความซ้ำกันภายในพื้นที่เดียวกัน (ไม่อนุญาตให้มี tag ซ้ำกัน)
                                duplicates_in_area = set([tag for tag in selected_tags if selected_tags.count(tag) > 1])
                                if duplicates_in_area:
                                    st.error(f"พบ tag ซ้ำกันภายในพื้นที่ {area}: {', '.join(duplicates_in_area)}")
                                    valid = False
                                
                                # ตรวจสอบความซ้ำกันระหว่างพื้นที่ (ไม่อนุญาตให้มี tag ซ้ำกัน)
                                duplicates_across_areas = set([tag for tag in selected_tags if tag in used_tags])
                                if duplicates_across_areas:
                                    st.error(f"พบ tag ที่ถูกใช้ในพื้นที่อื่นแล้วสำหรับ {area}: {', '.join(duplicates_across_areas)}")
                                    valid = False
                                
                                if valid:
                                    # เพิ่ม tag ที่เลือกเข้าไปในรายการที่ใช้แล้ว
                                    used_tags.extend(selected_tags)
                                    temp_tag_assignments[comm_tag][area] = selected_tags
                                    st.session_state[custom_tags_key][area] = custom_tags[area]
                        
                        if valid:
                            tag_assignments = temp_tag_assignments
                            st.session_state[result_key] = {
                                "sorted_areas": unique_areas,
                                "tag_assignments": tag_assignments
                            }
                            
                            if has_warnings:
                                st.info("มีคำเตือนบางประการ แต่ได้บันทึกการระบุ tag เรียบร้อยแล้ว")
                            else:
                                st.success("บันทึกการระบุ tag เรียบร้อยแล้ว")
                        else:
                            st.error("กรุณาแก้ไขข้อผิดพลาดก่อนที่จะบันทึกข้อมูล")
                
            # แสดงผลการจัดสรรเมื่อมีข้อมูลใน session state
            if st.session_state[result_key]:
                sorted_areas = st.session_state[result_key]["sorted_areas"]
                tag_assignments = st.session_state[result_key]["tag_assignments"]
                
                st.write("**ลำดับการจัดสรร tag:**")
                for i, area in enumerate(sorted_areas, 1):
                    area_index = list(unique_areas).index(area)
                    detail = area_details[area_index]
                    poles_needed = detail["poles_in_area"]
                    assigned = tag_assignments[comm_tag][area]
                    st.write(f"{i}. {area}: ต้องการ {poles_needed} ต้น, ระบุไว้ {len(assigned)} tag")
                
                st.write("**การจัดสรร tag เสาไฟฟ้า:**")
                for area in sorted_areas:
                    assigned = tag_assignments[comm_tag][area]
                    st.write(f"{area}: {len(assigned)} tag")
                    if assigned:
                        st.text_area(
                            f"tag ที่จัดสรรให้ {area}",
                            ", ".join(assigned),
                            height=100,
                            key=f"tags_{comm_tag}_{area}",
                            disabled=True
                        )
            
            # ส่งคืนค่า tag_assignments ในทุกกรณี
            return tag_assignments
                
        def display_tag_assignment_results(sorted_areas, tag_assignments, comm_tag):
            """
            แสดงผลการจัดสรร tag
            """
            st.write("**การจัดสรร tag เสาไฟฟ้า:**")
            for area in sorted_areas:
                assigned = tag_assignments[comm_tag][area]
                st.write(f"{area}: {len(assigned)} tag")
                if assigned:
                    st.text_area(
                        f"tag ที่จัดสรรให้ {area}", 
                        ", ".join(assigned), 
                        height=100, 
                        key=f"tags_{comm_tag}_{area}"
                    )

        def group_comm_tags_by_case(df_not_match, df_match):
            unique_comm_tags = df_not_match["tag ของสายสื่อสาร"].unique()
            
            # สร้างกลุ่มกรณีต่างๆ
            tag_groups = {
                "found_tag": [],  # กรณีพบ tag ในข้อมูลที่ตรงกัน
                "not_found_tag": [],  # กรณีไม่พบทั้ง tag สุดท้ายและ tag แรก
                "more_than_two_areas": [],  # กรณีมีมากกว่า 2 การไฟฟ้า
                "single_area": []  # กรณีมีพื้นที่เดียว
            }
            
            # จัดกลุ่ม tag ตามกรณีที่พบ
            for comm_tag in unique_comm_tags:
                comm_data = df_not_match[df_not_match["tag ของสายสื่อสาร"] == comm_tag]
                unique_areas = comm_data["พื้นที่รับผิดชอบของ กฟภ."].unique()
                
                # รวบรวม tag ทั้งหมด
                all_tags = []
                for _, row in comm_data.iterrows():
                    if not pd.isna(row["tag เสาไฟฟ้าที่ผ่าน"]).all() and isinstance(row["tag เสาไฟฟ้าที่ผ่าน"], list):
                        all_tags.extend(row["tag เสาไฟฟ้าที่ผ่าน"])
                
                # ตรวจสอบให้แน่ใจว่ามี tag
                all_unique_tags = list(dict.fromkeys(all_tags)) if all_tags else []
                
                # ตรวจสอบกรณีต่างๆ
                if len(unique_areas) == 1:
                    tag_groups["single_area"].append(comm_tag)
                elif len(unique_areas) > 2:
                    tag_groups["more_than_two_areas"].append(comm_tag)
                else:
                    # ตรวจสอบว่าพบ tag ในข้อมูลที่ตรงกันหรือไม่
                    tag_found = False
                    
                    # ตรวจสอบทั้ง tag แรกและ tag สุดท้าย
                    check_tags = []
                    if all_unique_tags:
                        check_tags = [all_unique_tags[0]]  # Tag แรก
                        if len(all_unique_tags) > 1:
                            check_tags.append(all_unique_tags[-1])  # Tag สุดท้าย
                    
                    for tag in check_tags:
                        # ขยาย DataFrame เพื่อให้มี 1 tag ต่อ 1 แถว
                        df_match_exploded = df_match.explode("tag เสาไฟฟ้าที่ผ่าน")
                        # กรองเอาเฉพาะแถวที่มี tag ตรงกับค่าที่ต้องการ
                        matches = df_match_exploded[df_match_exploded["tag เสาไฟฟ้าที่ผ่าน"] == tag]
                        
                        if not matches.empty:
                            # ตรวจสอบว่าพื้นที่ที่พบอยู่ในพื้นที่ที่เกี่ยวข้องหรือไม่
                            found_area = matches["พื้นที่รับผิดชอบของ กฟภ."].iloc[0]
                            if found_area in unique_areas:
                                tag_groups["found_tag"].append(comm_tag)
                                tag_found = True
                                break
                    
                    if not tag_found:
                        tag_groups["not_found_tag"].append(comm_tag)
            
            return tag_groups

        # ในส่วนที่เกี่ยวกับการแสดงผล tag สายสื่อสาร
        if len(df_not_match) > 0:
            st.subheader("🔍 วิเคราะห์ข้อมูลสายสื่อสารที่ไม่ตรงกัน")
            
            # จัดกลุ่ม tag สายสื่อสารตามกรณีที่พบ
            tag_groups = group_comm_tags_by_case(df_not_match, df_match)
            
            # แสดงตัวเลือกดูข้อมูลตามกลุ่ม
            tabs = st.tabs([
                f"✅ ระบุ tag เสากับการไฟฟ้าได้ ({len(tag_groups['found_tag'])} tags)",
                f"⚠️ ระบุ tag เสากับการไฟฟ้าไม่ได้  ({len(tag_groups['not_found_tag'])} tags)",
                f"⚠️ tag เสาที่พาดข้ามมากกว่า 2 การไฟฟ้า ({len(tag_groups['more_than_two_areas'])} tags)",
                f"⚠️ tag สายที่ข้ามไป กฟภ.อื่น ({len(tag_groups['single_area'])} tags)"
            ])
            
            # แสดงข้อมูลในแต่ละแท็บ
            for i, (tab, group_name, group_tags) in enumerate(zip(
                tabs, 
                ["found_tag", "not_found_tag", "more_than_two_areas", "single_area"],
                [tag_groups["found_tag"], tag_groups["not_found_tag"], tag_groups["more_than_two_areas"], tag_groups["single_area"]]
            )):
                with tab:
                    # กรณีพบ tag ในข้อมูลที่ตรงกัน ไม่ต้องแสดงรายละเอียด
                    if group_name == "found_tag":
                        if len(group_tags) > 0:
                            st.info(f"มี {len(group_tags)} tag สายสื่อสารที่พบ tag ในข้อมูลที่ตรงกัน")
                        else:
                            st.info("ไม่มี tag สายสื่อสารในกลุ่มนี้")
                    # กลุ่มอื่นๆ แสดงรายละเอียดเหมือนเดิม
                    else:
                        if len(group_tags) > 0:
                            for comm_tag in group_tags:
                                comm_data = df_not_match[df_not_match["tag ของสายสื่อสาร"] == comm_tag]
                                unique_areas = comm_data["พื้นที่รับผิดชอบของ กฟภ."].unique()
                                
                                area_details = []
                                for area in unique_areas:
                                    area_data = comm_data[comm_data["พื้นที่รับผิดชอบของ กฟภ."] == area]
                                    total_poles = area_data["จำนวนเสา(ต้น)ทั้งหมด"].sum()
                                    poles_in_area = area_data["จำนวนเสา(ต้น)ในพื้นที่"].sum()
                                    all_tags = [tag for tag_list in area_data["tag เสาไฟฟ้าที่ผ่าน"] for tag in tag_list]
                                    unique_tags = list(dict.fromkeys(all_tags))
                                    area_details.append({
                                        "area": area,
                                        "poles_in_area": poles_in_area,
                                        "unique_tags": unique_tags,
                                        "tags_count": len(unique_tags)
                                    })
                                
                                all_unique_tags = [tag for detail in area_details for tag in detail["unique_tags"]]
                                all_unique_tags = list(dict.fromkeys(all_unique_tags))
                                
                                with st.expander(f"📋 รายละเอียดสำหรับ {comm_tag}", expanded=False):
                                    # เรียกใช้ฟังก์ชันแสดงรายละเอียด tag สายสื่อสาร
                                    tag_assignment = display_communication_tag_details(comm_tag, comm_data, df_match, unique_areas, area_details, all_unique_tags)
                                    tag_assignments.update(tag_assignment)
                        else:
                            st.info(f"ไม่มี tag สายสื่อสารในกลุ่มนี้")

        if st.button("🚀 เริ่มประมวลผลใหม่", use_container_width=True):
            with st.spinner("กำลังประมวลผล..."):
                # ...existing code...           
                def process_tags_by_assignment(df_not_match, tag_assignments):
                    result_rows = []
                    for comm_tag in tag_assignments.keys():
                        comm_group = df_not_match[df_not_match["tag ของสายสื่อสาร"] == comm_tag]
                        for area, assigned_tags in tag_assignments[comm_tag].items():
                            area_data = comm_group[comm_group["พื้นที่รับผิดชอบของ กฟภ."] == area]
                            if not area_data.empty:
                                template_row = area_data.iloc[0].copy()
                                for tag in assigned_tags:
                                    new_row = template_row.copy()
                                    new_row["tag เสาไฟฟ้าที่ผ่าน"] = tag
                                    new_row["การเรียงค่า"] = "ระบบเรียงค่าให้" if comm_tag in tag_groups["found_tag"] else "ผู้ใช้เรียงค่าเอง"
                                    result_rows.append(new_row)
                    for comm_tag in df_not_match["tag ของสายสื่อสาร"].unique():
                        if comm_tag not in tag_assignments:
                            comm_group = df_not_match[df_not_match["tag ของสายสื่อสาร"] == comm_tag]
                            for area, area_group in comm_group.groupby("พื้นที่รับผิดชอบของ กฟภ."):
                                template_row = area_group.iloc[0].copy()
                                all_tags = [tag for tag_list in area_group["tag เสาไฟฟ้าที่ผ่าน"] for tag in tag_list]
                                unique_tags = list(dict.fromkeys(all_tags))
                                for tag in unique_tags[:int(template_row["จำนวนเสา(ต้น)ในพื้นที่"])]:
                                    new_row = template_row.copy()
                                    new_row["tag เสาไฟฟ้าที่ผ่าน"] = tag
                                    new_row["การเรียงค่า"] = "ผู้ใช้เรียงค่าเอง"
                                    result_rows.append(new_row)
                    return pd.DataFrame(result_rows)

                # ...existing code...

                def calculate_diameter_class(df_match, df_not_match):
                    combined_df = pd.concat([df_match.explode("tag เสาไฟฟ้าที่ผ่าน"), df_not_match])
                    grouped = combined_df.groupby(["พื้นที่รับผิดชอบของ กฟภ.", "tag เสาไฟฟ้าที่ผ่าน"]).agg({
                        "เส้นผ่านศูนย์กลาง(มม.)": "sum"
                    }).reset_index()
                    grouped = grouped.rename(columns={"เส้นผ่านศูนย์กลาง(มม.)": "เส้นผ่านศูนย์กลางรวม"})
                    grouped["ประเภท"] = grouped["เส้นผ่านศูนย์กลางรวม"].apply(lambda x: "น้อยกว่า 63" if x < 63 else "มากกว่า 63")
                    return grouped

                def summarize_by_area(summary_df):
                    summary = summary_df.groupby("พื้นที่รับผิดชอบของ กฟภ.")["ประเภท"].value_counts().unstack(fill_value=0)
                    summary = summary.rename(columns={"น้อยกว่า 63": "จำนวน_tag_น้อยกว่า_63", "มากกว่า 63": "จำนวน_tag_มากกว่า_63"})
                    
                    # Ensure the columns exist
                    summary = summary.reindex(columns=["จำนวน_tag_น้อยกว่า_63", "จำนวน_tag_มากกว่า_63"], fill_value=0)
                    
                    summary["จำนวน_tag"] = summary["จำนวน_tag_น้อยกว่า_63"] + summary["จำนวน_tag_มากกว่า_63"]
                    summary["ค่าพาดสายประจำปี"] = (summary["จำนวน_tag_น้อยกว่า_63"] * 55) + (summary["จำนวน_tag_มากกว่า_63"] * 100)
                    total_value = summary["ค่าพาดสายประจำปี"].sum()
                    summary.loc["รวมทั้งหมด"] = [0, 0, 0, total_value]
                    for col in ["จำนวน_tag_น้อยกว่า_63", "จำนวน_tag_มากกว่า_63", "จำนวน_tag", "ค่าพาดสายประจำปี"]:
                        summary[col] = summary[col].astype('float64')
                    return summary.reset_index()

                def summarize_tag_areas(df):
                    tag_area_summary = df.groupby("tag ของสายสื่อสาร")["พื้นที่รับผิดชอบของ กฟภ."].apply(lambda x: ', '.join(x.unique())).reset_index()
                    tag_area_summary = tag_area_summary.rename(columns={"พื้นที่รับผิดชอบของ กฟภ.": "การไฟฟ้าที่รับผิดชอบ"})
                    tag_area_summary["จำนวนพื้นที่รับผิดชอบ"] = tag_area_summary["การไฟฟ้าที่รับผิดชอบ"].apply(lambda x: len(x.split(', ')))
                    return tag_area_summary

                # Process data
                df_tags_match = df_match.explode("tag เสาไฟฟ้าที่ผ่าน").reset_index(drop=True)
                df_tags_not_match = process_tags_by_assignment(df_not_match, tag_assignments)
                summary_df = calculate_diameter_class(df_match, df_tags_not_match)
                tag_area_summary = summarize_tag_areas(df_tags_not_match)
                summarized_area_df = summarize_by_area(summary_df)

                # Combine the data from "ตรงกัน" and "ไม่ตรงกัน" sheets
                combined_df = pd.concat([df_tags_match, df_tags_not_match])

                # Display results in tabs
                tabs = st.tabs(["ข้อมูลที่ตรงกัน", "ข้อมูลที่ไม่ตรงกัน", "รวม", "ผลรวมเส้นผ่านศูนย์กลาง", "จำนวนพื้นที่รับผิดชอบ", "ผลรวมตามเขต กฟภ."])
                with tabs[0]:
                    st.dataframe(df_tags_match.head(), use_container_width=True)
                with tabs[1]:
                    st.dataframe(df_tags_not_match.head(), use_container_width=True)
                with tabs[2]:
                    st.dataframe(summary_df, use_container_width=True)
                with tabs[3]:
                    st.dataframe(tag_area_summary, use_container_width=True)
                with tabs[4]:
                    st.dataframe(summarized_area_df, use_container_width=True)
                with tabs[5]:
                    st.dataframe(combined_df.head(), use_container_width=True)

                # Download button
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_tags_match.to_excel(writer, sheet_name="ตรงกัน", index=False)
                    df_tags_not_match.to_excel(writer, sheet_name="ไม่ตรงกัน", index=False)
                    combined_df.to_excel(writer, sheet_name="รวม", index=False)
                    summary_df.to_excel(writer, sheet_name="ผลรวมเส้นผ่านศูนย์กลาง", index=False)
                    tag_area_summary.to_excel(writer, sheet_name="จำนวนพื้นที่รับผิดชอบ", index=False)
                    summarized_area_df.to_excel(writer, sheet_name="ผลรวมตามเขต กฟภ.", index=False)
                st.download_button(
                    "📥 ดาวน์โหลดไฟล์ Excel", 
                    data=output.getvalue(), 
                    file_name="output_summary.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
