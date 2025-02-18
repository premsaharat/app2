import pandas as pd
import streamlit as st
import numpy as np

# ตั้งค่าหน้าเว็บของ Streamlit
st.set_page_config(page_title="โปรแกรมวิเคราะห์ข้อมูลสายสื่อสาร", layout="wide")

# Header ของเว็บ
st.title("📊 โปรแกรมวิเคราะห์ข้อมูลสายสื่อสาร")

# อัปโหลดไฟล์ Excel
uploaded_file = st.file_uploader("📂 อัปโหลดไฟล์ Excel", type=["xlsx"])

@st.cache
def load_excel(file):
    return pd.ExcelFile(file)

@st.cache
def process_sheet(xls, sheet_name):
    df = pd.read_excel(xls, sheet_name=sheet_name, header=[0,1], skiprows=6)
    df.columns = [' '.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
    return df

if uploaded_file:
    xls = load_excel(uploaded_file)
    selected_sheet = st.selectbox("📑 เลือก Sheet ที่ต้องการใช้", xls.sheet_names)

    if selected_sheet:
        df = process_sheet(xls, selected_sheet)

        def find_closest_column(df, column_name):
            return next((col for col in df.columns if column_name in col), None)

        col_total = find_closest_column(df, "จำนวนเสา(ต้น) ทั้งหมด")
        col_in_area = find_closest_column(df, "จำนวนเสา(ต้น) ในพื้นที่")

        if col_total and col_in_area:
            df["ตรวจสอบ"] = df[col_total] == df[col_in_area]
        else:
            st.error(f"❌ ไม่พบคอลัมน์: {col_total}, {col_in_area}")
            st.stop()

        st.write("📌 **ตัวอย่างข้อมูลที่โหลดมา:**")
        st.dataframe(df.head())

        def rename_column(df, expected_name):
            correct_col = next((col for col in df.columns if expected_name in col), None)
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

        df_match = df[df["ตรวจสอบ"]].copy()
        df_not_match = df[~df["ตรวจสอบ"]].copy()

        df_match["ตรวจสอบความถูกต้อง"] = "✅ ตรงกัน"
        df_not_match["ตรวจสอบความถูกต้อง"] = "❌ ไม่ตรงกัน"

        def clean_and_split_tags(tags):
            if pd.isna(tags):
                return []
            return [tag.strip() for tag in str(tags).split(',') if tag.strip()]

        df_match["tag เสาไฟฟ้าที่ผ่าน"] = df_match["tag เสาไฟฟ้าที่ผ่าน"].apply(clean_and_split_tags)
        df_tags_match = df_match.explode("tag เสาไฟฟ้าที่ผ่าน").reset_index(drop=True)

        def process_tags_by_area_order(df):
            result_rows = []
            used_tags = set()

            for comm_tag, comm_group in df.groupby("tag ของสายสื่อสาร"):
                used_tags = set()
                for idx, (area_idx, row) in enumerate(comm_group.iterrows()):
                    tags = clean_and_split_tags(row["tag เสาไฟฟ้าที่ผ่าน"])
                    count_in_area = int(row["จำนวนเสา(ต้น)ในพื้นที่"])
                    available_tags = [tag for tag in tags if tag not in used_tags]

                    if idx == 0:
                        if len(available_tags) > count_in_area:
                            available_tags = available_tags[-count_in_area:]
                        available_tags.reverse()
                    else:
                        if len(available_tags) > count_in_area:
                            available_tags = available_tags[:count_in_area]

                    used_tags.update(available_tags)

                    for tag in available_tags:
                        new_row = row.copy()
                        new_row["tag เสาไฟฟ้าที่ผ่าน"] = tag
                        result_rows.append(new_row)

            return pd.DataFrame(result_rows)

        def calculate_diameter_class(df_match, df_not_match):
            combined_df = pd.concat([df_match, df_not_match])
            grouped = combined_df.groupby(["พื้นที่รับผิดชอบของ กฟภ.", "tag เสาไฟฟ้าที่ผ่าน"]).agg({
                "เส้นผ่านศูนย์กลาง(มม.)": "sum"
            }).reset_index()
            grouped = grouped.rename(columns={"เส้นผ่านศูนย์กลาง(มม.)": "เส้นผ่านศูนย์กลางรวม"})
            grouped["ประเภท"] = grouped["เส้นผ่านศูนย์กลางรวม"].apply(lambda x: "น้อยกว่า 63" if x < 63 else "มากกว่า 63")
            return grouped

        def summarize_by_area(summary_df):
            summary = summary_df.groupby("พื้นที่รับผิดชอบของ กฟภ.")["ประเภท"].value_counts().unstack(fill_value=0)
            summary = summary.rename(columns={"น้อยกว่า 63": "จำนวน_tag_น้อยกว่า_63", "มากกว่า 63": "จำนวน_tag_มากกว่า_63"})
            summary["จำนวน_tag"] = summary["จำนวน_tag_น้อยกว่า_63"] + summary["จำนวน_tag_มากกว่า_63"]

            summary["จำนวน_tag_น้อยกว่า_63"] = summary["จำนวน_tag_น้อยกว่า_63"].astype(int)
            summary["จำนวน_tag_มากกว่า_63"] = summary["จำนวน_tag_มากกว่า_63"].astype(int)
            summary["จำนวน_tag"] = summary["จำนวน_tag"].astype(int)

            summary["ค่าพาดสายประจำปี"] = (summary["จำนวน_tag_น้อยกว่า_63"] * 55) + (summary["จำนวน_tag_มากกว่า_63"] * 100)

            summary["จำนวน_tag_น้อยกว่า_63"] = summary["จำนวน_tag_น้อยกว่า_63"].astype(str)
            summary["จำนวน_tag_มากกว่า_63"] = summary["จำนวน_tag_มากกว่า_63"].astype(str)
            summary["จำนวน_tag"] = summary["จำนวน_tag"].astype(str)

            total_value = summary["ค่าพาดสายประจำปี"].sum()
            summary.loc["รวมทั้งหมด"] = ['-', '-', '-', total_value]

            return summary.reset_index()

        df_tags_match = df_match.explode("tag เสาไฟฟ้าที่ผ่าน")
        df_tags_not_match = process_tags_by_area_order(df_not_match)
        summary_df = calculate_diameter_class(df_tags_match, df_tags_not_match)
        summarized_area_df = summarize_by_area(summary_df)

        st.write("📌 **ผลลัพธ์:**")
        st.write("🔹 **ข้อมูลที่ตรงกัน**")
        st.dataframe(df_tags_match.head())
        st.write("🔹 **ข้อมูลที่ไม่ตรงกัน**")
        st.dataframe(df_tags_not_match.head())
        st.write("🔹 **ผลรวมเส้นผ่านศูนย์กลาง**")
        st.dataframe(summary_df)
        st.write("🔹 **ผลรวมตามเขต กฟภ.**")
        st.dataframe(summarized_area_df)

        output_file = "output_summary.xlsx"
        with pd.ExcelWriter(output_file) as writer:
            df_tags_match.to_excel(writer, sheet_name="ตรงกัน", index=False)
            df_tags_not_match.to_excel(writer, sheet_name="ไม่ตรงกัน", index=False)
            df_combined = pd.concat([df_tags_match, df_tags_not_match])
            df_combined.to_excel(writer, sheet_name="รวม", index=False)
            summary_df.to_excel(writer, sheet_name="ผลรวมเส้นผ่านศูนย์กลาง", index=False)
            summarized_area_df.to_excel(writer, sheet_name="ผลรวมตามเขต กฟภ.", index=False)

        with open(output_file, "rb") as file:
            st.download_button("📥 ดาวน์โหลดไฟล์ Excel", file, file_name="output_summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
