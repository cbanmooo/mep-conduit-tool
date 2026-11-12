# revise02 - Updated for Revit BIM Parameter Standard & EIT 31%/40% Rule
import streamlit as st
import pandas as pd
import numpy as np
import os

# --- ตั้งค่าหน้าเพจ ---
st.set_page_config(layout="wide", page_title="MEP Conduit & Revit BIM Tool")

# ==========================================
# 1. ข้อมูล Database ทั้งหมด (อ้างอิงมาตรฐาน วสท.)
# ==========================================

WIRE_TABLE = {
    1.5: [9, 16, 26, 45, 61, 101],
    2.5: [6, 12, 20, 35, 47, 78],
    4.0: [5, 9, 15, 26, 36, 60],
    6.0: [3, 6, 11, 19, 25, 42],
    10.0: [1, 4, 7, 12, 16, 27],
    16.0: [1, 3, 5, 8, 11, 19]
}
CONDUIT_NAMES = ["1/2\"", "3/4\"", "1\"", "1-1/4\"", "1-1/2\"", "2\""]

# --- ข้อมูลสาย LAN (IT Network) ---
LAN_OD = {
    "Cat 5e (UTP)": {"od": 5.5, "param": "wire_cat5e", "short": "CAT5e"},
    "Cat 6 (UTP)": {"od": 6.2, "param": "wire_cat6", "short": "CAT6"},
    "Cat 6A (UTP/FTP)": {"od": 7.5, "param": "wire_cat6a", "short": "CAT6A"}
}

# --- ข้อมูลสาย FRC & Twisted Pair (Fire Alarm / Control) ---
TWISTED_OD = {
    "FRC 2C1.5 mm² (Fire Alarm/Speaker)": {"od": 8.0, "param": "wire_frc_2C1.5", "short": "FRC 2C1.5"},
    "FRC 2C2.5 mm² (Horn/Strobe)": {"od": 10.5, "param": "wire_frc_2C2.5", "short": "FRC 2C2.5"},
    "Twisted Pair 2C-1.5 (Shielded)": {"od": 6.8, "param": "wire_twisted_2_1.5", "short": "Twisted Pair 2-1.5"},
    "RS-485 (1 Pair)": {"od": 5.9, "param": "wire_rs485", "short": "RS-485"},
    "BAS Control (Multi-core)": {"od": 7.2, "param": "wire_bas", "short": "BAS Control"}
}

# --- ข้อมูลสาย VTF & VCT (เสียงประกาศ / สายเคเบิล) ---
VTF_OD = {
    "VTF 2C1.5 mm²": {"od": 8.2, "param": "wire_vtf_2C1.5", "short": "VTF 2C1.5"},
    "VTF 2C2.5 mm² (สายแยกเข้าลำโพง)": {"od": 9.5, "param": "wire_vtf_2C2.5", "short": "VTF 2C2.5"},
    "VTF 4C2.5 mm² (สายเมน Riser PA)": {"od": 11.5, "param": "wire_vtf_4C2.5", "short": "VTF 4C2.5"},
    "VCT 2C2.5 mm²": {"od": 11.0, "param": "wire_vct_2C2.5", "short": "VCT 2C2.5"}
}

# ค่า I.D. ของท่อ EMT (mm) แก้ไขให้ถูกต้องตามมาตรฐาน
PIPE_DATA = [
    {"name": "1/2\"", "id_mm": 16},
    {"name": "3/4\"", "id_mm": 21},
    {"name": "1\"", "id_mm": 27},
    {"name": "1-1/4\"", "id_mm": 35},
    {"name": "1-1/2\"", "id_mm": 41},
    {"name": "2\"", "id_mm": 53},
    {"name": "2-1/2\"", "id_mm": 65},
    {"name": "3\"", "id_mm": 78},
    {"name": "4\"", "id_mm": 103}
]

# ==========================================
# 2. ฟังก์ชันการคำนวณ
# ==========================================

def calculate_conduit_power(qty, wire_size, has_ground, g_size):
    check_size = max(wire_size, g_size) if has_ground else wire_size
    total_qty = qty + (1 if has_ground else 0)
    if check_size not in WIRE_TABLE:
        return "Manual Check", total_qty
    max_wires_list = WIRE_TABLE[check_size]
    selected_pipe = "Over 2\""
    for i, max_val in enumerate(max_wires_list):
        if total_qty <= max_val:
            selected_pipe = CONDUIT_NAMES[i]
            break
    return selected_pipe, total_qty

def calculate_conduit_area(qty, od_mm):
    total_area = qty * np.pi * ((od_mm / 2) ** 2)
    # อ้างอิงมาตรฐาน วสท.: สาย 2 เส้น คิดพื้นที่ท่อไม่เกิน 31%, กรณีอื่นคิด 40%
    fill_ratio = 0.31 if qty == 2 else 0.40
    selected_pipe = "Over 4\""
    for pipe in PIPE_DATA:
        allowable_area = (np.pi * ((pipe["id_mm"] / 2) ** 2)) * fill_ratio
        if total_area <= allowable_area:
            selected_pipe = pipe["name"]
            break
    return selected_pipe, total_area, fill_ratio

# ==========================================
# 3. UI Streamlit
# ==========================================

st.sidebar.title("🛠️ MEP & Revit BIM Tool")
page = st.sidebar.radio("หมวดหมู่การร้อยท่อ", [
    "⚡ สายไฟฟ้า (Power THW)",
    "🌐 สายแลน (IT/Network)",
    "🔥 สายทนไฟ FRC & Control",
    "🔊 สายลำโพง VTF & VCT"
])
st.sidebar.divider()
st.sidebar.info("Developed by Chainarong (Rev.02 BIM Standard)")

SAVE_PATH = 'projectlinedata.csv'

# --- หน้า 1: สายไฟฟ้า (Power) ---
if page == "⚡ สายไฟฟ้า (Power THW)":
    st.title("⚡ Power Wire Sizing (THW / IEC 01)")
    col1, col2 = st.columns([1, 1.5])
    wire_choices = list(WIRE_TABLE.keys())
    with col1:
        qty = st.number_input("จำนวนสายไฟหลัก L/N (เส้น)", min_value=1, value=2)
        wire_size = st.selectbox("ขนาดสายไฟหลัก (mm²)", wire_choices, index=1)
        has_ground = st.checkbox("มีสาย Ground (G)", value=True)
        g_size = st.selectbox("ขนาดสาย G (mm²)", wire_choices, index=0, disabled=not has_ground)

    pipe_ans, tot_wires = calculate_conduit_power(qty, wire_size, has_ground, g_size)
    w_str = int(wire_size) if wire_size == int(wire_size) else wire_size
    g_str = int(g_size) if g_size == int(g_size) else g_size
    spec_text = f"THW {qty}-{w_str}" + (f"/G{g_str}" if has_ground else "")
    revit_type_name = f"{spec_text} in {pipe_ans} EMT"

    with col2:
        st.info(f"ชื่อ Conduit Type ใน Revit: **`{revit_type_name}`**")
        container = st.container(border=True)
        container.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container.title(f"👉 {pipe_ans}")
        st.write(f"จำนวนสายรวมในท่อ: **{tot_wires} เส้น**")
        if has_ground and wire_size == g_size:
            st.code(f"wire_thw_{wire_size} = {qty + 1}", language="text")
        elif has_ground:
            st.code(f"wire_thw_{wire_size} = {qty}\nwire_thw_{g_size} = 1", language="text")
        else:
            st.code(f"wire_thw_{wire_size} = {qty}", language="text")

    if st.button("💾 บันทึกสเปกนี้"):
        new_data = pd.DataFrame([{"Revit_Type": revit_type_name, "Spec": spec_text, "Conduit": pipe_ans, "Category": "Power"}])
        new_data.to_csv(SAVE_PATH, mode='a' if os.path.exists(SAVE_PATH) else 'w', header=not os.path.exists(SAVE_PATH), index=False)
        st.success("บันทึกสำเร็จ!")

# --- หน้า 2: สายแลน (LAN) ---
elif page == "🌐 สายแลน (IT/Network)":
    st.title("🌐 LAN & Telephone Cable Sizing")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        qty_lan = st.number_input("จำนวนสาย LAN (เส้น)", min_value=1, value=2)
        type_lan = st.selectbox("ประเภทสาย LAN", list(LAN_OD.keys()), index=1)

    lan_info = LAN_OD[type_lan]
    pipe_lan, area_lan, ratio_lan = calculate_conduit_area(qty_lan, lan_info["od"])
    spec_lan = f"{lan_info['short']} {qty_lan}-4P"
    revit_type_name = f"{spec_lan} in {pipe_lan} EMT"

    with col2:
        st.info(f"ชื่อ Conduit Type ใน Revit: **`{revit_type_name}`**")
        container = st.container(border=True)
        container.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container.title(f"👉 {pipe_lan}")
        st.write(f"พื้นที่สายรวม: **{area_lan:.2f} mm²** (เกณฑ์คิดพื้นที่ท่อ {int(ratio_lan*100)}%)")
        st.code(f"{lan_info['param']} = {qty_lan}", language="text")

    if st.button("💾 บันทึกสเปกนี้"):
        new_data = pd.DataFrame([{"Revit_Type": revit_type_name, "Spec": spec_lan, "Conduit": pipe_lan, "Category": "LAN"}])
        new_data.to_csv(SAVE_PATH, mode='a' if os.path.exists(SAVE_PATH) else 'w', header=not os.path.exists(SAVE_PATH), index=False)
        st.success("บันทึกสำเร็จ!")

# --- หน้า 3: สาย FRC & Twisted Pair ---
elif page == "🔥 สายทนไฟ FRC & Control":
    st.title("🔥 FRC (Fire Alarm) & Control Cable Sizing")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        qty_tp = st.number_input("จำนวนสายเคเบิล (เส้น)", min_value=1, value=1)
        type_tp = st.selectbox("ชนิดสายเคเบิล (O.D.)", list(TWISTED_OD.keys()), index=0)

    tp_info = TWISTED_OD[type_tp]
    pipe_tp, area_tp, ratio_tp = calculate_conduit_area(qty_tp, tp_info["od"])
    spec_tp = f"{tp_info['short']}" if qty_tp == 1 else f"{tp_info['short']} ({qty_tp} เส้น)"
    revit_type_name = f"{spec_tp} in {pipe_tp} EMT"

    with col2:
        st.info(f"ชื่อ Conduit Type ใน Revit: **`{revit_type_name}`**")
        container = st.container(border=True)
        container.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container.title(f"👉 {pipe_tp}")
        st.write(f"พื้นที่สายรวม: **{area_tp:.2f} mm²** (เกณฑ์คิดพื้นที่ท่อ {int(ratio_tp*100)}%)")
        st.code(f"{tp_info['param']} = {qty_tp}", language="text")

    if st.button("💾 บันทึกสเปกนี้"):
        new_data = pd.DataFrame([{"Revit_Type": revit_type_name, "Spec": spec_tp, "Conduit": pipe_tp, "Category": "FRC_Control"}])
        new_data.to_csv(SAVE_PATH, mode='a' if os.path.exists(SAVE_PATH) else 'w', header=not os.path.exists(SAVE_PATH), index=False)
        st.success("บันทึกสำเร็จ!")

# --- หน้า 4: สาย VTF & VCT ---
elif page == "🔊 สายลำโพง VTF & VCT":
    st.title("🔊 Speaker (VTF) & Multi-Core (VCT) Sizing")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        qty_vtf = st.number_input("จำนวนสายเคเบิล (เส้น)", min_value=1, value=1)
        type_vtf = st.selectbox("ขนาดสายเคเบิล", list(VTF_OD.keys()), index=1)

    vtf_info = VTF_OD[type_vtf]
    pipe_vtf, area_vtf, ratio_vtf = calculate_conduit_area(qty_vtf, vtf_info["od"])
    spec_vtf = f"{vtf_info['short']}" if qty_vtf == 1 else f"{vtf_info['short']} ({qty_vtf} เส้น)"
    revit_type_name = f"{spec_vtf} in {pipe_vtf} EMT"

    with col2:
        st.info(f"ชื่อ Conduit Type ใน Revit: **`{revit_type_name}`**")
        container = st.container(border=True)
        container.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container.title(f"👉 {pipe_vtf}")
        st.write(f"พื้นที่สายรวม: **{area_vtf:.2f} mm²** (เกณฑ์คิดพื้นที่ท่อ {int(ratio_vtf*100)}%)")
        st.code(f"{vtf_info['param']} = {qty_vtf}", language="text")

    if st.button("💾 บันทึกสเปกนี้"):
        new_data = pd.DataFrame([{"Revit_Type": revit_type_name, "Spec": spec_vtf, "Conduit": pipe_vtf, "Category": "VTF_VCT"}])
        new_data.to_csv(SAVE_PATH, mode='a' if os.path.exists(SAVE_PATH) else 'w', header=not os.path.exists(SAVE_PATH), index=False)
        st.success("บันทึกสำเร็จ!")
