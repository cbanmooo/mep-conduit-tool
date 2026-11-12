# revise05 - Added Saved Spec Table Viewer, CSV Download, and Clear Data Controls
import streamlit as st
import pandas as pd
import numpy as np
import os

# --- ตั้งค่าหน้าเพจ ---
st.set_page_config(layout="wide", page_title="MEP Conduit & Revit BIM Tool")

# ==========================================
# 1. ข้อมูล Database ทั้งหมด (อ้างอิงมาตรฐาน วสท.)
# ==========================================

# จำนวนสายสูงสุดในท่อ EMT (1/2", 3/4", 1", 1-1/4", 1-1/2", 2")
WIRE_TABLE = {
    1.5: [9, 16, 26, 45, 61, 101],
    2.5: [6, 12, 20, 35, 47, 78],
    4.0: [5, 9, 15, 26, 36, 60],
    6.0: [3, 6, 11, 19, 25, 42],
    10.0: [1, 4, 7, 12, 16, 27],
    16.0: [1, 3, 5, 8, 11, 19]
}
CONDUIT_NAMES = ["1/2\"", "3/4\"", "1\"", "1-1/4\"", "1-1/2\"", "2\""]

# พิกัดกระแสสาย THW (IEC 01) เดินในท่อร้อยสาย ที่อุณหภูมิโดยรอบ 40°C (วสท. ตารางที่ 5-20)
AMPACITY_BASE = {
    1.5: 15.0,
    2.5: 21.0,
    4.0: 28.0,
    6.0: 36.0,
    10.0: 50.0,
    16.0: 68.0
}

# ตัวคูณปรับลดกระแสตามจำนวนวงจรในท่อเดียวกัน (วสท. ตารางที่ 5-8 / IEC 60364-5-52)
GROUPING_FACTOR = {
    1: 1.00,
    2: 0.80,
    3: 0.70,
    4: 0.65,
    5: 0.60,
    6: 0.57,
    7: 0.54,
    8: 0.52,
    9: 0.50,
    10: 0.48,
    11: 0.46,
    12: 0.45,
    13: 0.44,
    14: 0.43,
    15: 0.42,
    16: 0.41,
    17: 0.40,
    18: 0.39,
    19: 0.39,
    20: 0.38
}

# ขนาดต่ำสุดของสายดินทองแดงตามขนาดเครื่องป้องกันกระแสเกิน AT (วสท. ตารางที่ 4-1)
EIT_GROUND_TABLE = [
    (15, 1.5),
    (20, 2.5),
    (30, 4.0),
    (40, 6.0),
    (60, 10.0),
    (100, 16.0),
]

BREAKER_RATINGS = [10, 16, 20, 25, 32, 40, 50, 63]

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

# ค่า I.D. ของท่อ EMT (mm) ตามมาตรฐาน
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

CSV_COLUMNS = [
    "Revit_Type",
    "Spec",
    "Conduit",
    "Category",
    "Circuits",
    "Breaker_AT",
    "Derated_Amp",
    "Min_G_mm2",
    "Status"
]

# ==========================================
# 2. ฟังก์ชันการคำนวณและจัดการข้อมูล
# ==========================================

def fmt_size(val):
    return str(int(val)) if val == int(val) else str(val)

def get_derating_factor(num_circuits):
    if num_circuits <= 1:
        return 1.00
    return GROUPING_FACTOR.get(num_circuits, 0.38)

def get_min_ground_size(breaker_at, phase_wire_size=None, is_phase_ok=True):
    """
    ตรวจสอบขนาดสายดินทองแดงขั้นต่ำตามตารางที่ 4-1 ของ วสท.
    หมายเหตุตามมาตรฐาน วสท.: ขนาดสายดินไม่จำเป็นต้องใหญ่กว่าขนาดสายตัวนำของวงจร
    """
    min_g = 16.0
    for max_at, g_sqmm in EIT_GROUND_TABLE:
        if breaker_at <= max_at:
            min_g = g_sqmm
            break
    if is_phase_ok and phase_wire_size is not None:
        min_g = min(min_g, phase_wire_size)
    return min_g

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

def recommend_wire_and_pipe(breaker_at, factor, qty_ln, has_ground, g_size):
    for size, base_amp in AMPACITY_BASE.items():
        if base_amp * factor >= breaker_at:
            rec_g = get_min_ground_size(breaker_at, size, True)
            effective_g = max(g_size, rec_g) if has_ground else g_size
            pipe_rec, _ = calculate_conduit_power(qty_ln, size, has_ground, effective_g)
            return size, base_amp * factor, pipe_rec
    return None, None, None

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

def save_spec_row(save_path, row_dict):
    df_new = pd.DataFrame([row_dict], columns=CSV_COLUMNS)
    if os.path.exists(save_path):
        try:
            df_existing = pd.read_csv(save_path)
            if list(df_existing.columns) != CSV_COLUMNS:
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                for col in CSV_COLUMNS:
                    if col not in df_combined.columns:
                        df_combined[col] = "-"
                df_combined = df_combined[CSV_COLUMNS]
                df_combined.to_csv(save_path, index=False, encoding="utf-8-sig")
                return
        except Exception:
            pass
        df_new.to_csv(save_path, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df_new.to_csv(save_path, mode="w", header=True, index=False, encoding="utf-8-sig")

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
st.sidebar.info("Developed by Chainarong (Rev.05 BIM & EIT Standard)")

SAVE_PATH = "projectlinedata.csv"

# --- หน้า 1: สายไฟฟ้า (Power) ---
if page == "⚡ สายไฟฟ้า (Power THW)":
    st.title("⚡ Power Wire Sizing, Derating & Ground Check")
    col1, col2 = st.columns([1.1, 1.4])
    wire_choices = list(WIRE_TABLE.keys())

    with col1:
        phase_mode = st.radio(
            "ระบบวงจรไฟฟ้า",
            ["1 เฟส (2 เส้น L+N / วงจร)", "3 เฟส (4 เส้น L1,L2,L3+N / วงจร)"],
            horizontal=True
        )
        wires_per_ckt = 2 if "1 เฟส" in phase_mode else 4

        num_circuits = st.number_input("จำนวนวงจรในท่อเดียวกัน (วงจร)", min_value=1, max_value=20, value=1)
        breaker_at = st.selectbox("ขนาดเซอร์กิตเบรกเกอร์สูงสุดในท่อ (AT)", BREAKER_RATINGS, index=2)
        wire_size = st.selectbox("ขนาดสายไฟหลัก (mm²)", wire_choices, index=2)
        has_ground = st.checkbox("มีสาย Ground (G) ร่วมในท่อ 1 เส้น", value=True)
        g_size = st.selectbox("ขนาดสาย G (mm²)", wire_choices, index=1, disabled=not has_ground)

    qty = num_circuits * wires_per_ckt
    pipe_ans, tot_wires = calculate_conduit_power(qty, wire_size, has_ground, g_size)

    # 1) ตรวจสอบพิกัดกระแสและตัวคูณปรับลด (วสท. ตารางที่ 5-8)
    factor = get_derating_factor(num_circuits)
    base_amp = AMPACITY_BASE[wire_size]
    derated_amp = base_amp * factor
    is_amp_ok = derated_amp >= breaker_at

    # 2) ตรวจสอบขนาดสายดินขั้นต่ำตามเบรกเกอร์ (วสท. ตารางที่ 4-1)
    min_g_req = get_min_ground_size(breaker_at, wire_size, is_amp_ok)
    is_ground_ok = (g_size >= min_g_req) if has_ground else True

    w_str = fmt_size(wire_size)
    g_str = fmt_size(g_size)
    min_g_str = fmt_size(min_g_req)
    spec_text = f"THW {qty}-{w_str}" + (f"/G{g_str}" if has_ground else "")
    revit_type_name = f"{spec_text} in {pipe_ans} EMT"

    with col2:
        # แสดงผลตรวจพิกัดสายไฟหลัก
        if is_amp_ok:
            st.success(
                f"✅ **สายไฟหลักผ่านเกณฑ์ วสท. (ตารางที่ 5-8):** สาย {w_str} mm² = {base_amp:.0f} A × ตัวคูณ {factor:.2f} "
                f"= **{derated_amp:.1f} A** (≥ เบรกเกอร์ {breaker_at} AT)"
            )
        else:
            rec_w, rec_amp, rec_pipe = recommend_wire_and_pipe(breaker_at, factor, qty, has_ground, g_size)
            rec_msg = (
                f"แนะนำให้ขยับสายหลักเป็น **{fmt_size(rec_w)} mm²** (รับได้ {rec_amp:.1f} A) ในท่อ **{rec_pipe} EMT**"
                if rec_w else "แนะนำให้แยกท่อลดจำนวนวงจรต่อท่อลง"
            )
            st.error(
                f"⚠️ **เตือน! พิกัดสายไฟหลักต่ำกว่าเบรกเกอร์:** สาย {w_str} mm² ({base_amp:.0f} A) × ตัวคูณ {factor:.2f} ({num_circuits} วงจร) "
                f"เหลือเพียง **{derated_amp:.1f} A** (< เบรกเกอร์ {breaker_at} AT)\n\n👉 {rec_msg}"
            )

        # แสดงผลตรวจขนาดสายดิน (Ground)
        if has_ground:
            if is_ground_ok:
                st.success(
                    f"✅ **สายดิน (Ground) ผ่านเกณฑ์ วสท. (ตารางที่ 4-1):** เบรกเกอร์ {breaker_at} AT "
                    f"กำหนดสายดินขั้นต่ำ **{min_g_str} mm²** (เลือกใช้ {g_str} mm²)"
                )
            else:
                rec_pipe_g, _ = calculate_conduit_power(qty, wire_size, True, min_g_req)
                st.error(
                    f"⚠️ **เตือน! ขนาดสายดินเล็กเกินไป:** เบรกเกอร์ {breaker_at} AT ตามตารางที่ 4-1 วสท. "
                    f"ต้องใช้สายดินขั้นต่ำ **{min_g_str} mm²** (ปัจจุบันเลือก {g_str} mm²)\n\n"
                    f"👉 แนะนำให้เปลี่ยนสาย G เป็น **{min_g_str} mm²** (ใช้ท่อ **{rec_pipe_g} EMT**)"
                )
        else:
            st.warning(
                f"ℹ️ **ไม่ได้เลือกสายดิน (G):** หากเป็นวงจรเต้ารับหรือบริภัณฑ์ที่ต้องต่อลงดิน "
                f"ต้องมีสายดินอย่างน้อย **{min_g_str} mm²** ตามตารางที่ 4-1 วสท."
            )

        st.info(f"ชื่อ Conduit Type ใน Revit: **`{revit_type_name}`**")
        container = st.container(border=True)
        container.write("### ไซส์ท่อ EMT ที่เหมาะสมคือ")
        container.title(f"👉 {pipe_ans}")
        st.write(f"จำนวนสายรวมในท่อ: **{tot_wires} เส้น** ({num_circuits} วงจร | Derating Factor = **{factor:.2f}**)")

        if has_ground and wire_size == g_size:
            st.code(f"wire_thw_{wire_size} = {qty + 1}", language="text")
        elif has_ground:
            st.code(f"wire_thw_{wire_size} = {qty}\nwire_thw_{g_size} = 1", language="text")
        else:
            st.code(f"wire_thw_{wire_size} = {qty}", language="text")

    overall_pass = is_amp_ok and is_ground_ok
    if st.button("💾 บันทึกสเปกนี้"):
        save_spec_row(SAVE_PATH, {
            "Revit_Type": revit_type_name,
            "Spec": spec_text,
            "Conduit": pipe_ans,
            "Category": "Power",
            "Circuits": num_circuits,
            "Breaker_AT": breaker_at,
            "Derated_Amp": round(derated_amp, 1),
            "Min_G_mm2": min_g_req if has_ground else 0,
            "Status": "PASS" if overall_pass else "FAIL"
        })
        if overall_pass:
            st.success("บันทึกสำเร็จ!")
        else:
            st.warning("บันทึกข้อมูลแล้ว (หมายเหตุ: รายการนี้มีจุดที่ไม่ผ่านเกณฑ์มาตรฐาน วสท.)")

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
        save_spec_row(SAVE_PATH, {
            "Revit_Type": revit_type_name,
            "Spec": spec_lan,
            "Conduit": pipe_lan,
            "Category": "LAN",
            "Circuits": "-",
            "Breaker_AT": "-",
            "Derated_Amp": "-",
            "Min_G_mm2": "-",
            "Status": "PASS"
        })
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
        save_spec_row(SAVE_PATH, {
            "Revit_Type": revit_type_name,
            "Spec": spec_tp,
            "Conduit": pipe_tp,
            "Category": "FRC_Control",
            "Circuits": "-",
            "Breaker_AT": "-",
            "Derated_Amp": "-",
            "Min_G_mm2": "-",
            "Status": "PASS"
        })
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
        save_spec_row(SAVE_PATH, {
            "Revit_Type": revit_type_name,
            "Spec": spec_vtf,
            "Conduit": pipe_vtf,
            "Category": "VTF_VCT",
            "Circuits": "-",
            "Breaker_AT": "-",
            "Derated_Amp": "-",
            "Min_G_mm2": "-",
            "Status": "PASS"
        })
        st.success("บันทึกสำเร็จ!")

# ==========================================
# 4. ส่วนแสดงตารางรายการที่บันทึกไว้, ดาวน์โหลด และล้างข้อมูล
# ==========================================
st.divider()
st.subheader("📋 รายการสเปกท่อร้อยสายที่บันทึกไว้ทั้งโปรเจกต์")

if os.path.exists(SAVE_PATH):
    try:
        df_saved = pd.read_csv(SAVE_PATH)
        if not df_saved.empty:
            # ตัวกรองหมวดหมู่สำหรับเช็กสเปกสะดวกขึ้น
            categories = ["ทั้งหมด"] + sorted(df_saved["Category"].dropna().unique().tolist())
            selected_cat = st.selectbox("กรองตามหมวดหมู่ระบบ", categories, key="filter_saved_cat")

            df_display = df_saved if selected_cat == "ทั้งหมด" else df_saved[df_saved["Category"] == selected_cat]

            st.dataframe(df_display, use_container_width=True, hide_index=True)
            st.caption(f"แสดง {len(df_display)} จากทั้งหมด {len(df_saved)} รายการ (ไฟล์: {SAVE_PATH})")

            btn_col1, btn_col2, _ = st.columns([1.2, 1.2, 3])
            with btn_col1:
                csv_bytes = df_saved.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์ CSV",
                    data=csv_bytes,
                    file_name="projectlinedata.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with btn_col2:
                if st.button("🗑️ ล้างข้อมูลทั้งหมด", type="secondary", use_container_width=True):
                    os.remove(SAVE_PATH)
                    st.rerun()
        else:
            st.info("ยังไม่มีรายการที่บันทึกไว้")
    except Exception as e:
        st.error(f"ไม่สามารถอ่านไฟล์ {SAVE_PATH} ได้ ({e})")
        if st.button("🗑️ รีเซ็ตไฟล์ข้อมูลที่เสียหาย"):
            os.remove(SAVE_PATH)
            st.rerun()
else:
    st.info("ยังไม่มีรายการที่บันทึกไว้ กดปุ่ม '💾 บันทึกสเปกนี้' ด้านบนเพื่อสร้างตารางสรุปสเปกของโปรเจกต์")
