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

# --- ตารางสายไฟฟ้ากำลัง (THW) อ้างอิงมาตรฐาน วสท. ---
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

# --- ข้อมูลสาย Twisted Pair (Control / Fire Alarm) ---
TWISTED_OD = {
    "RS-485 (1 Pair)": 5.9,
    "Fire Alarm 2x1.5 mm²": 8.0,
    "Fire Alarm 2x2.5 mm²": 10.5,
    "Speaker Cable 2x1.5": 6.5,
    "BAS Control (Multi-core)": 7.2
}

# --- ข้อมูลสาย VTF (เสียงประกาศ / Horn) ---
VTF_OD = {
    "VTF 2x1.5 mm²": 8.2,
    "VTF 2x2.5 mm²": 9.5
}

# ค่า I.D. ของท่อ EMT (mm) สำหรับคำนวณ 40% Area
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
    for pipe in PIPE_DATA:
        allowable_area = (np.pi * ((pipe["id_mm"] / 2)**2)) * 0.40
        if total_area <= allowable_area:
            selected_pipe = pipe["name"]
            break
    return selected_pipe, total_area

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
st.sidebar.info("Developed by Chaianarong")

SAVE_PATH = 'projectlinedata.csv'

# --- หน้า 1: สายไฟฟ้า (Power) ---
if page == "⚡ สายไฟฟ้า (Power)":
    st.title("⚡ Power Wire Sizing")
    col1, col2 = st.columns([1, 1.5])
    wire_choices = list(WIRE_TABLE.keys())
    with col1:
        qty = st.number_input("จำนวนสายไฟหลัก (เส้น)", min_value=1, value=2)
        wire_size = st.selectbox("ขนาดสายเส้นไฟ (mm²)", wire_choices, index=1)
        has_ground = st.checkbox("มีสาย Ground (G)", value=True)
        g_size = st.selectbox("ขนาดสาย G (mm²)", wire_choices, index=0, disabled=not has_ground)
    
    pipe_ans, tot_wires = calculate_conduit_power(qty, wire_size, has_ground, g_size)
    spec_text = f"{qty}-{wire_size}" + (f"/G{g_size}" if has_ground else "")
    with col2:
        st.info(f"สเปกสาย: **{spec_text}**")
        container = st.container(border=True)
        container.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container.title(f"👉 {pipe_ans}")
        st.write(f"จำนวนสายรวม: {tot_wires} เส้น")
    if st.button("💾 บันทึกสเปกนี้"):
        new_data = pd.DataFrame([{"Spec": spec_text, "Conduit": pipe_ans, "Type": "Power"}])
        new_data.to_csv(SAVE_PATH, mode='a' if os.path.exists(SAVE_PATH) else 'w', header=not os.path.exists(SAVE_PATH), index=False)
        st.success("บันทึกสำเร็จ!")

# --- หน้า 2: สายแลน (LAN) ---
elif page == "🌐 สายแลน (IT/Network)":
    st.title("🌐 LAN Cable Sizing")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        qty_lan = st.number_input("จำนวนสาย LAN (เส้น)", min_value=1, value=1)
        type_lan = st.selectbox("ประเภทสาย LAN", list(LAN_OD.keys()), index=1)
    pipe_lan, area_lan = calculate_conduit_area(qty_lan, LAN_OD[type_lan])
    spec_lan = f"{qty_lan} x {type_lan}"
    with col2:
        st.info(f"สเปกสาย: **{spec_lan}**")
        container = st.container(border=True)
        container.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container.title(f"👉 {pipe_lan}")
        st.write(f"พื้นที่รวม: {area_lan:.2f} mm²")
    if st.button("💾 บันทึกสเปกนี้"):
        new_data = pd.DataFrame([{"Spec": spec_lan, "Conduit": pipe_lan, "Type": "LAN"}])
        new_data.to_csv(SAVE_PATH, mode='a' if os.path.exists(SAVE_PATH) else 'w', header=not os.path.exists(SAVE_PATH), index=False)
        st.success("บันทึกสำเร็จ!")

# --- หน้า 3: สายเกลียวคู่ (Twisted Pair) ---
elif page == "🔀 สายเกลียวคู่ (Control/Twisted Pair)":
    st.title("🔀 Control & Twisted Pair Sizing")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        qty_tp = st.number_input("จำนวนสาย (เส้น)", min_value=1, value=1)
        type_tp = st.selectbox("ชนิดสาย (O.D.)", list(TWISTED_OD.keys()), index=1)
    pipe_tp, area_tp = calculate_conduit_area(qty_tp, TWISTED_OD[type_tp])
    spec_tp = f"{qty_tp} x {type_tp}"
    with col2:
        st.info(f"สเปกสาย: **{spec_tp}**")
        container = st.container(border=True)
        container.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container.title(f"👉 {pipe_tp}")
        st.write(f"พื้นที่รวม: {area_tp:.2f} mm²")
    if st.button("💾 บันทึกสเปกนี้"):
        new_data = pd.DataFrame([{"Spec": spec_tp, "Conduit": pipe_tp, "Type": "Twisted Pair"}])
        new_data.to_csv(SAVE_PATH, mode='a' if os.path.exists(SAVE_PATH) else 'w', header=not os.path.exists(SAVE_PATH), index=False)
        st.success("บันทึกสำเร็จ!")

# --- หน้า 4: สาย VTF (เสียงประกาศ) ---
elif page == "🔊 สาย VTF (เสียงประกาศ)":
    st.title("🔊 Speaker & Horn (VTF) Sizing")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        qty_vtf = st.number_input("จำนวนสาย VTF (เส้น)", min_value=1, value=1)
        type_vtf = st.selectbox("ขนาดสาย VTF", list(VTF_OD.keys()), index=1)
    pipe_vtf, area_vtf = calculate_conduit_area(qty_vtf, VTF_OD[type_vtf])
    spec_vtf = f"{qty_vtf} x {type_vtf}"
    with col2:
        st.info(f"สเปกสาย: **{spec_vtf}**")
        container = st.container(border=True)
        container.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container.title(f"👉 {pipe_vtf}")
        st.write(f"พื้นที่รวม: {area_vtf:.2f} mm²")
    if st.button("💾 บันทึกสเปกนี้"):
        new_data = pd.DataFrame([{"Spec": spec_vtf, "Conduit": pipe_vtf, "Type": "VTF"}])
        new_data.to_csv(SAVE_PATH, mode='a' if os.path.exists(SAVE_PATH) else 'w', header=not os.path.exists(SAVE_PATH), index=False)
        st.success("บันทึกสำเร็จ!")
