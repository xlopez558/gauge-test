import streamlit as st
import pandas as pd
import os
import pytz
from datetime import datetime, date, timedelta
from fpdf import FPDF

# --- PAGE CONFIGURATION & CUSTOM CSS ---
st.set_page_config(layout="wide")

st.markdown("""
    <style>
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
    
    /* Hides the default Streamlit "Press Enter to apply" text */
    div[data-testid="InputInstructions"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🏭 Tenaris Quality Lab - Gauge Kiosk")

# --- SESSION STATE INITIALIZATION & STICKY HEADERS ---
if 'unlocked_gauges' not in st.session_state: st.session_state.unlocked_gauges = {}
if 'unlocked_standards' not in st.session_state: st.session_state.unlocked_standards = {}
if 'current_readings' not in st.session_state: st.session_state.current_readings = {}

# Sticky memory for Location ONLY
if 'last_location' not in st.session_state: st.session_state.last_location = ""


# --- DATABASE CONNECTIONS ---
DB_FILE = "gauges.csv"
LOG_FILE = "shift_log.csv" 

# Set timezone explicitly to Central Time for accurate logging
tz = pytz.timezone('America/Chicago')

def load_gauge_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE, dtype={'gauge_id': str, 'standard_id': str})
    else:
        st.error("Database file missing! Please contact the Lab Lead.")
        return pd.DataFrame()

df_gauges = load_gauge_data()

def is_valid_date(date_str):
    if pd.isna(date_str) or str(date_str).strip().upper() == "N/A": return True
    # Compare against Central Time current date
    try: return datetime.strptime(str(date_str), "%Y-%m-%d").date() >= datetime.now(tz).date()
    except ValueError: return False


# --- THE PDF & CSV ENGINE ---
def save_calibration_log(header_data, readings_data):
    # 1. DYNAMIC CSV GENERATION
    log_entries = []
    for gid, data in readings_data.items():
        entry = {**header_data, **data}
        log_entries.append(entry)
        
    df_log = pd.DataFrame(log_entries)
    csv_filename = f"Shift_Log_{header_data['log_date']}_{header_data['shift']}.csv"
    
    if not os.path.exists(csv_filename): 
        df_log.to_csv(csv_filename, index=False)
    else: 
        df_log.to_csv(csv_filename, mode='a', header=False, index=False)

    # 2. GENERATE COMPLIANT PDF REPORT
    time_str_file = datetime.strptime(header_data['timestamp'], "%Y-%m-%d %H:%M:%S").strftime('%H%M%S')
    report_filename = f"Verification_PDF_{header_data['log_date']}_{header_data['shift']}_{time_str_file}.pdf"
    
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=8) 
    pdf.add_page()
    
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 297, 22, 'F') 
    pdf.set_y(6)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 6, 'TENARIS QUALITY LAB - SHIFT CALIBRATION LOG', 0, 1, 'C')
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 5, 'Official API Q1 & ISO 9001 Verification Record', 0, 1, 'C')
    pdf.ln(8)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(240, 240, 240)
    rh = 7 
    
    log_time = header_data['timestamp'].split(" ")[1] 
    
    pdf.cell(25, rh, ' Date:', 1, 0, 'L', fill=True)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, rh, f" {header_data['log_date']}", 1, 0, 'L')
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, rh, ' Time:', 1, 0, 'L', fill=True)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, rh, f" {log_time}", 1, 0, 'L')
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, rh, ' Shift:', 1, 0, 'L', fill=True)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, rh, f" {header_data['shift']}", 1, 1, 'L')
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, rh, ' Location:', 1, 0, 'L', fill=True)
    pdf.set_font('Arial', '', 9)
    pdf.cell(40, rh, f" {header_data['location']}", 1, 0, 'L')
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, rh, ' Operator ID:', 1, 0, 'L', fill=True)
    pdf.set_font('Arial', '', 9)
    pdf.cell(105, rh, f" {header_data['operator_id']}", 1, 1, 'L')
    pdf.ln(6)
    
    pdf.set_font('Arial', 'B', 8)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(30, rh, 'Gauge Type', 1, 0, 'C', fill=True)
    pdf.cell(15, rh, 'ID', 1, 0, 'C', fill=True)
    pdf.cell(22, rh, 'Cal Due', 1, 0, 'C', fill=True)    
    pdf.cell(15, rh, 'Std. ID', 1, 0, 'C', fill=True)    
    pdf.cell(22, rh, 'Std. Due', 1, 0, 'C', fill=True)   
    pdf.cell(20, rh, 'Reading', 1, 0, 'C', fill=True)
    pdf.cell(12, rh, 'Vis.', 1, 0, 'C', fill=True)
    pdf.cell(22, rh, 'Status', 1, 0, 'C', fill=True)
    pdf.cell(119, rh, 'Comments', 1, 1, 'C', fill=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    
    for gid, data in readings_data.items():
        pdf.cell(30, rh, str(data['gauge_type'])[:15], 1)
        pdf.cell(15, rh, str(gid), 1, 0, 'C')
        pdf.cell(22, rh, str(data['cal_due']), 1, 0, 'C')
        pdf.cell(15, rh, str(data['standard_id'])[:8], 1, 0, 'C')
        pdf.cell(22, rh, str(data['std_due']), 1, 0, 'C')
        pdf.cell(20, rh, str(data['standard_reading']), 1, 0, 'C')
        vis_status = "Y" if data['visual_ok'] else "N"
        pdf.cell(12, rh, vis_status, 1, 0, 'C')
        pdf.set_text_color(22, 101, 52)
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(22, rh, 'VERIFIED', 1, 0, 'C')
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 8)
        pdf.cell(119, rh, str(data['comments'])[:75], 1, 1)

    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(135, rh, '___________________________________', 0, 0, 'C')
    pdf.cell(135, rh, '___________________________________', 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(135, 5, f'Operator Signature (ID: {header_data["operator_id"]})', 0, 0, 'C')
    pdf.cell(135, 5, 'QA Lead / Supervisor Review', 0, 1, 'C')
    
    # Return the filename so the main app can access it
    pdf.output(report_filename)
    return report_filename


# --- 🧪 DEVELOPMENT CHEAT MENU ---
with st.sidebar:
    st.markdown("### 🛠️ Developer Tools")
    if st.button("⚡ Quick-Fill Mock Data", type="primary"):
        st.session_state.last_location = "TEST-LINE-1"
        for index, row in df_gauges.iterrows():
            gid = str(row['gauge_id']).strip()
            sid = str(row['standard_id']).strip()
            req_std = str(row['requires_standard']).strip().lower() == "true"
            g_type = str(row['gauge_type']).lower()
            
            st.session_state.unlocked_gauges[gid] = True
            st.session_state[f"in_g_{gid}"] = gid[-2:] 
            
            if req_std:
                st.session_state.unlocked_standards[sid] = True
                st.session_state[f"in_s_{gid}_{sid}"] = sid[-2:] 
                
                if "depth mic" in g_type:
                    st.session_state[f"raw_read_{gid}"] = "1.0"
                elif "mrp" in g_type or "lead" in g_type:
                    st.session_state[f"raw_read_{gid}"] = "0"
                else:
                    st.session_state[f"raw_read_{gid}"] = "5"
        st.rerun()


# --- GLOBAL HEADER ---
st.markdown("### 📋 Shift Information")

# Pulling current Central Time
now = datetime.now(tz)

if now.hour < 6:
    production_date = (now.date() - timedelta(days=1)).strftime("%Y-%m-%d")
    auto_shift = "Night"
elif 6 <= now.hour < 18:
    production_date = now.date().strftime("%Y-%m-%d")
    auto_shift = "Day"
else:
    production_date = now.date().strftime("%Y-%m-%d")
    auto_shift = "Night"

col1, col2, col3, col4 = st.columns(4)

with col1: 
    st.text_input("Date", value=production_date, disabled=True)
    log_date = production_date
    
with col2: 
    default_index = 0 if auto_shift == "Day" else 1
    shift = st.selectbox("Shift", options=["Day", "Night"], index=default_index)
    
with col3: 
    location = st.text_input("Location", value=st.session_state.last_location, placeholder="e.g., Line 1", autocomplete="off")
    if location != "" and not location.strip(): st.error("Location cannot be blank spaces.")
    
with col4: 
    operator_sig = st.text_input("Operator ID", placeholder="e.g., 60012345", max_chars=8, autocomplete="off")
    op_id = operator_sig.strip()
    if op_id:
        if not (len(op_id) == 8 and op_id.startswith("600") and op_id.isdigit()):
            st.error("⚠️ Invalid ID: Must be exactly 8 digits starting with '600'")
st.divider()


# --- CONNECTION ROUTING & DYNAMIC UI ---
connection = st.selectbox("Select a connection...", ["", "TXP/BTC/TPN", "Wedge 441/461", "Wedge 451"])

if connection:
    st.info(f"Active Job: {connection}")
    assigned_gauges = df_gauges[df_gauges['connection'] == connection]
    
    if assigned_gauges.empty:
        st.warning("No gauges mapped to this connection.")
    else:
        st.markdown("### 🗜️ Gauge Verification")
        missing_readings = []
        
        for index, row in assigned_gauges.iterrows():
            gid = str(row['gauge_id']).strip()
            requires_standard = str(row['requires_standard']).strip().lower() == "true"
            
            if gid not in st.session_state.unlocked_gauges:
                st.session_state.unlocked_gauges[gid] = False
                
            if gid not in st.session_state.current_readings:
                st.session_state.current_readings[gid] = {
                    "connection": connection,
                    "gauge_type": row['gauge_type'],
                    "gauge_id": gid,
                    "cal_due": str(row['cal_due']).strip(), 
                    "standard_id": str(row['standard_id']).strip() if requires_standard else "N/A",
                    "std_due": str(row['std_due']).strip() if requires_standard else "N/A",
                    "standard_reading": "N/A",
                    "visual_ok": True,
                    "comments": ""
                }
            
            with st.container(border=True):
                # --- STATE 1: GAUGE IS LOCKED ---
                if not st.session_state.unlocked_gauges[gid]:
                    missing_readings.append(f"{row['gauge_type']} (Needs Gauge Unlock)")
                    lock_col1, lock_col2, lock_col3 = st.columns([1, 1, 2])
                    lock_col1.markdown(f"**{row['gauge_type']}**")
                    lock_col1.caption("🔒 *Gauge Information Hidden*")
                    
                    user_input = lock_col2.text_input("Last 2 Digits of Gauge ID", max_chars=2, key=f"in_g_{gid}", autocomplete="off")
                    lock_col3.write("") 
                    btn_clicked = lock_col3.button("Verify Gauge", key=f"btn_g_{gid}")
                    
                    if user_input.strip() == gid[-2:]:
                        st.session_state.unlocked_gauges[gid] = True
                        st.rerun()
                    elif btn_clicked and user_input != "":
                        st.error("Incorrect gauge digits.")
                
                # --- STATE 2: GAUGE IS UNLOCKED ---
                else:
                    gauge_valid = is_valid_date(row['cal_due'])
                    g_info1, g_info2, g_info3 = st.columns([2, 1, 1])
                    g_info1.markdown(f"**{row['gauge_type']}** (ID: `{gid}`)")
                    if gauge_valid: g_info2.success(f"Gauge Cal Due: {row['cal_due']} ✅")
                    else: g_info2.error(f"GAUGE EXPIRED: {row['cal_due']} ❌")
                    
                    st.markdown("---") 

                    if not requires_standard:
                        act_col1, act_col2, act_col3 = st.columns([2, 1, 2])
                        with act_col1:
                            st.success("Gauge Verified ✅")
                            st.session_state.current_readings[gid]["standard_reading"] = "Verified"
                        with act_col2:
                            vis_ok = st.checkbox("Visual OK", value=True, key=f"vis_{gid}")
                            st.session_state.current_readings[gid]["visual_ok"] = vis_ok
                        with act_col3:
                            com = st.text_input("Comments", placeholder="Optional remarks...", label_visibility="collapsed", key=f"com_{gid}", autocomplete="off")
                            st.session_state.current_readings[gid]["comments"] = com
                    
                    else:
                        sid = str(row['standard_id']).strip()
                        if sid not in st.session_state.unlocked_standards:
                            st.session_state.unlocked_standards[sid] = False
                        
                        # --- STATE 2A: STANDARD IS LOCKED ---
                        if not st.session_state.unlocked_standards[sid]:
                            missing_readings.append(f"{row['gauge_type']} (Needs Standard Unlock)")
                            s_lock1, s_lock2, s_lock3 = st.columns([1, 1, 2])
                            s_lock1.markdown("**Standard Required**")
                            s_lock1.caption("🔒 *Standard Information Hidden*")
                            
                            s_input = s_lock2.text_input("Last 2 Digits of Standard ID", max_chars=2, key=f"in_s_{gid}_{sid}", autocomplete="off")
                            s_lock3.write("")
                            s_btn_clicked = s_lock3.button("Verify Standard", key=f"btn_s_{gid}_{sid}")
                            
                            if s_input.strip() == sid[-2:]:
                                st.session_state.unlocked_standards[sid] = True
                                st.rerun()
                            elif s_btn_clicked and s_input != "":
                                st.error("Incorrect standard digits.")
                        
                        # --- STATE 2B: STANDARD IS UNLOCKED ---
                        else:
                            std_valid = is_valid_date(row['std_due'])
                            s_info1, s_info2, s_info3 = st.columns([2, 1, 1])
                            s_info1.markdown(f"**Standard Verified** (ID: `{sid}`)")
                            if std_valid: s_info2.success(f"Standard Due: {row['std_due']} ✅")
                            else: s_info2.error(f"STANDARD EXPIRED: {row['std_due']} ❌")
                            
                            act_col1, act_col2, act_col3 = st.columns([2, 1, 2])
                            
                            with act_col1:
                                raw_read = st.text_input("Standard Reading", placeholder="Type reading here", key=f"raw_read_{gid}", autocomplete="off")
                                
                                if raw_read:
                                    if "depth mic" in str(row['gauge_type']).lower():
                                        st.success(f"Recorded Value: **{raw_read}\"**")
                                        st.session_state.current_readings[gid]["standard_reading"] = f"{raw_read}\""
                                    else:
                                        clean_read = "".join(c for c in raw_read if c.isdigit() or c == '-')
                                        if clean_read and clean_read != '-':
                                            calc_val = int(clean_read) / 10000.0
                                            st.success(f"Recorded Value: **{calc_val:.4f}\"**")
                                            st.session_state.current_readings[gid]["standard_reading"] = f"{calc_val:.4f}\""
                                        else:
                                            st.error("Numbers only.")
                                            missing_readings.append(f"{row['gauge_type']} (Needs valid number)")
                                else:
                                    missing_readings.append(f"{row['gauge_type']} (Missing reading)")
                            
                            with act_col2:
                                vis_ok = st.checkbox("Visual OK", value=True, key=f"vis_{gid}")
                                st.session_state.current_readings[gid]["visual_ok"] = vis_ok
                            with act_col3:
                                com = st.text_input("Comments", placeholder="Optional remarks...", label_visibility="collapsed", key=f"com_{gid}", autocomplete="off")
                                st.session_state.current_readings[gid]["comments"] = com

        st.divider()
        
        # --- THE MASTER GATEKEEPER ---
        header_errors = []
        if not location.strip(): header_errors.append("Location")
        if not op_id or len(op_id) != 8 or not op_id.startswith("600") or not op_id.isdigit():
            header_errors.append("Valid Operator ID")
            
        all_errors = header_errors + missing_readings
        
        if all_errors:
            st.warning(f"⚠️ **Action Required Before Submission:** Please complete the following: {', '.join(all_errors)}")
            
        if st.button("💾 Submit & Save Calibration Log", type="primary", use_container_width=True, disabled=len(all_errors) > 0):
            header_data = {
                "log_date": log_date,
                "shift": shift,
                "location": location,
                "operator_id": op_id,
                # Explicitly pass the Central Time object here
                "timestamp": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Capture the returned filename
            generated_pdf = save_calibration_log(header_data, st.session_state.current_readings)
            
            # Save the filename to session state so it survives the rerun
            st.session_state.ready_pdf = generated_pdf
            
            st.session_state.last_location = location
            
            del st.session_state['unlocked_gauges']
            del st.session_state['unlocked_standards']
            del st.session_state['current_readings']
            
            st.rerun()

        # --- PDF DOWNLOAD HANDLER ---
        if 'ready_pdf' in st.session_state:
            st.success("✅ Log successfully written! CSV appended and unique PDF generated.")
            
            try:
                with open(st.session_state.ready_pdf, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Download Calibration PDF",
                        data=pdf_file,
                        file_name=st.session_state.ready_pdf,
                        mime="application/pdf"
                    )
            except FileNotFoundError:
                st.error("Error: The PDF file could not be found for download.")
