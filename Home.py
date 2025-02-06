import streamlit as st

st.set_page_config(page_title="File Converter", layout="wide")

# CSS
st.markdown("""
    <style>
    .big-button {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px;
        text-align: center;
        transition: transform 0.2s;
    }
    .big-button:hover {
        transform: scale(1.02);
        background-color: #e0e2e6;
    }
    </style>
    """, unsafe_allow_html=True)

# หน้าหลัก
st.title("🏠 File Converter Hub")
st.markdown("### เลือกเครื่องมือที่ต้องการใช้งาน")

# แก้ไขเป็น 3 คอลัมน์
col1, col2, col3 ,col4 = st.columns(4)

with col1:
    st.markdown("""
        <div class="big-button">
            <h2>📊 Excel to KML</h2>
            <p>แปลงไฟล์ Excel เป็น KML</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("เปิด Excel to KML จากหมุด ", key="btn1"):
        st.switch_page("pages/app.py")

with col2:
    st.markdown("""
        <div class="big-button">
            <h2>📑 KML to Excel</h2>
            <p>แปลงไฟล์ KML เป็น Excel</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("เปิด KML to Excel", key="btn2"):
        st.switch_page("pages/appss.py")

with col3:
    st.markdown("""
        <div class="big-button">
            <h2>📑 โปรแกรมที่ 3</h2>
            <p>คำอธิบายโปรแกรมที่ 3</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("เปิดสร้างเส้นซ้อน", key="btn3"):
        st.switch_page("pages/appsss.py")

with col4:
    st.markdown("""
        <div class="big-button">
            <h2> ตัดพื้นที่ </h2>
            <p> ตัดพื้นที่ตามขอบเขต </p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("เปิดตัดพื้นที่ตามขอบเขต", key="btn4"):
        st.switch_page("pages/appssss.py")

# เพิ่มข้อมูลเพิ่มเติม
st.markdown("---")
st.markdown("""
### 📌 คำแนะนำการใช้งาน
1. เลือกเครื่องมือที่ต้องการใช้งานจากปุ่มด้านบน
2. อัปโหลดไฟล์ตามที่ต้องการ
3. ทำการแปลงไฟล์
""")
