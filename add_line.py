#revise01
#เพิ่ม VTF
#08042569
import streamlit as st
import pandas as pd
import numpy as np
import os

# --- ตั้งค่าหน้าเพจ ---
st.set_page_config(layout="wide", page_title="MEP Conduit Tool")

# ==========================================
# 1. ข้อมูล Database ทั้งหมด
# ==========================================

# --- ตารางสายไฟฟ้ากำลัง (THW) ---
WIRE_TABLE = {
    1.5: [9, 16, 26, 45, 61, 101],
    2.5: [6, 12, 20, 35, 47, 78],
    4:   [5, 9, 15, 26, 36, 60],
    6:   [3, 6, 11, 19, 25, 42],
    10:  [1, 4, 7, 12, 16, 27],
    16:  [1, 3, 5, 8, 11, 19]
}
CONDUIT_NAMES = ["1/2\"", "3/4\"", "1\"", "1-1/4\"", "1-1/2\"", "2\""]

# --- ข้อมูลสาย LAN (IT Network) ---
LAN_OD = {
    "Cat 5e (UTP)": 5.5,
    "Cat 6 (UTP)": 6.2,
    "Cat 6A (UTP/FTP)": 7.5
}

# --- ข้อมูลสาย Twisted Pair (Control / System) ---
TWISTED_OD = {
    "RS-485 (1 Pair)": 5.9,
    "Fire Alarm 2x1.5 mm²": 8.0,
    "Fire Alarm 2x2.5 mm²": 10.5, # เพิ่มขนาดตามรูปสเปกใหม่
    "Speaker Cable 2x1.5": 6.5,
    "BAS Control (Multi-core)": 7.2
}

# --- ข้อมูลสาย VTF (เสียงประกาศ) ---
VTF_OD = {
    "VTF 2x1.5 mm²": 8.2,
    "VTF 2x2.5 mm²": 9.5  # สายอวบสำหรับงาน Horn/Speaker
}

# ค่า I.D. ของท่อ EMT (mm) เพื่อใช้คำนวณพื้นที่ 40%
PIPE_DATA = [
    {"name": "1/2\"", "id_mm": 16},
    {"name": "3/4\"", "id_mm": 21},
    {"name": "1\"", "id_mm": 27},
    {"name": "1-1/4\"", "id_mm": 35},
    {"name": "1-1/2\"", "id_mm": 41},
    {"name": "2\"", "id_mm": 53},
    {"name": "2-1/2\"", "id_mm": 65},
    {"name": "3\"", "id_mm": 78}
]

# ==========================================
# 2. ฟังก์ชันการคำนวณ
# ==========================================

def calculate_conduit_power(qty, wire_size, has_ground, g_size):
    check_size = max(wire_size, g_size) if has_ground else wire_size
    total_qty = qty + (1 if has_ground else 0)
    if check_size not in WIRE_TABLE: return "Manual Check", total_qty
    max_wires_list = WIRE_TABLE[check_size]
    selected_pipe = "Over 2\"" 
    for i, max_val in enumerate(max_wires_list):
        if total_qty <= max_val:
            selected_pipe = CONDUIT_NAMES[i]
            break
    return selected_pipe, total_qty

def calculate_conduit_area(qty, od_mm):
    total_area = qty * np.pi * ((od_mm / 2)**2)
    selected_pipe = "Over 3\""
    pipe_id_used = 0
    for pipe in PIPE_DATA:
        allowable_area = (np.pi * ((pipe["id_mm"] / 2)**2)) * 0.40
        if total_area <= allowable_area:
            selected_pipe = pipe["name"]
            pipe_id_used = pipe["id_mm"]
            break
    
    # คำนวณ % Fill จริงเพื่อใช้แสดงกิมมิค
    actual_fill = (total_area / (np.pi * ((pipe_id_used / 2)**2)) * 100) if pipe_id_used > 0 else 100
    return selected_pipe, total_area, actual_fill

# ==========================================
# 3. UI Streamlit
# ==========================================

st.sidebar.title("🛠️ MEP Tools")
page = st.sidebar.radio("หมวดหมู่การร้อยท่อ", [
    "⚡ สายไฟฟ้า (Power)", 
    "🌐 สายแลน (IT/Network)", 
    "🔀 สายเกลียวคู่ (Control/Twisted Pair)",
    "🔊 สาย VTF (เสียงประกาศ)"
])
st.sidebar.divider()
st.sidebar.info("เขียนเล่นๆ ถ้าผิดห้ามด่า (โดย Engineer Chai)")

SAVE_PATH = 'projectlinedata.csv'

# --- Logic แสดงกิมมิคกวนๆ ---
def show_gimmick(fill_percent):
    if fill_percent > 38:
        st.warning(f"😱 แน่นจัด! (Fill: {fill_percent:.1f}%) พี่ยัดสายหรือยัดไส้บะจ่างครับเนี่ย?! ระวังดึงสายขาดนะ")
    elif fill_percent > 30:
        st.info(f"😅 ตึงๆ มือนะพี่ (Fill: {fill_percent:.1f}%) ช่างร้อยสายมีปาดเหงื่อแน่นอน")
    else:
        st.success(f"😎 หลวมโครก (Fill: {fill_percent:.1f}%) ร้อยสายชิลๆ เหมือนเดินห้างเลยพี่")

# ----------------- หน้า 1, 2, 3 (คงเดิมตามแนวทางคุณ) -----------------
# (เพื่อความกระชับ ผมข้ามการเขียนซ้ำในหน้านี้ แต่ให้คุณใช้โค้ดเดิมของคุณได้เลย)

# ----------------- หน้า 4: สาย VTF (ใหม่!) -----------------
if page == "🔊 สาย VTF (เสียงประกาศ)":
    st.title("🔊 Speaker & Horn (VTF) Sizing")
    st.write("คำนวณสำหรับสาย VTF บิดเกลียว (อ้างอิง Area 40%)")

    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.subheader("📦 Speaker Config")
        qty_vtf = st.number_input("จำนวนสาย VTF (เส้น)", min_value=1, value=1)
        type_vtf = st.selectbox("ขนาดสาย VTF", list(VTF_OD.keys()), index=1)

    vtf_od_val = VTF_OD[type_vtf]
    pipe_vtf, area_vtf, fill_vtf = calculate_conduit_area(qty_vtf, vtf_od_val)
    spec_vtf = f"{qty_vtf} x {type_vtf}"

    with col2:
        st.info(f"สเปกสาย: **{spec_vtf}**")
        container_vtf = st.container(border=True)
        container_vtf.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container_vtf.title(f"👉 {pipe_vtf}")
        show_gimmick(fill_vtf)
        st.write(f"พื้นที่รวม: {area_vtf:.2f} mm²")

    if st.button("💾 บันทึกสเปก VTF"):
        new_data = pd.DataFrame([{"Spec": spec_vtf, "Conduit": pipe_vtf, "Type": "VTF"}])
        new_data.to_csv(SAVE_PATH, mode='a' if os.path.exists(SAVE_PATH) else 'w', header=not os.path.exists(SAVE_PATH), index=False)
        st.success("บันทึกเรียบร้อย!")
