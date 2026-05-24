import streamlit as st
from datetime import datetime
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="HR OT Tracker", layout="wide")

# Initialize session state
if 'days_list' not in st.session_state:
    st.session_state.days_list = []

st.title("🕒 HR Attendance & OT Tracker")

# 1. Global Settings
with st.sidebar:
    st.header("Settings")
    name_user = st.text_input("Employee Name", value="Employee").strip()
    
    st.divider()
    # Checkbox for Manual Shift Override
    override_shift = st.checkbox("Manual Shift Override", value=False)
    
    if override_shift:
        const_hours = st.number_input("Manual Standard Shift (Hours)", value=8.0, step=0.5)
    else:
        st.write("💡 *Shift rules applied automatically:*")
        st.write("- Weekdays: **8.0 Hours**")
        st.write("- Saturdays: **5.0 Hours**")
    
    st.divider()
    if st.button("Reset Entire Month", type="primary"):
        st.session_state.days_list = []
        st.rerun()

# 2. Input Section
with st.expander("➕ Add Daily Entry", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        date_in = st.date_input("Select Date", datetime.now())
    with c2:
        check_in = st.text_input("Check-In (HH.MM or HH:MM)", value="08.00")
    with c3:
        check_out = st.text_input("Check-Out (HH.MM or HH:MM)", value="17.00")
    with c4:
        lunch_break = st.number_input("Lunch (Minutes)", value=60, step=5)

    if st.button("Save Entry"):
        selected_date_str = date_in.strftime("%Y-%m-%d")
        is_duplicate = any(d["Date"] == selected_date_str for d in st.session_state.days_list)

        if is_duplicate:
            st.error(f"Entry for {selected_date_str} already exists!")
        else:
            try:
                # Determine Standard Shift Boundary (Automatic vs Manual Override)
                if override_shift:
                    # Uses the hours from the sidebar manual input
                    final_const_hours = const_hours 
                else:
                    # Automatic system calculation
                    if date_in.weekday() == 5:
                        final_const_hours = 5.0
                    else:
                        final_const_hours = 8.0

                # Support both dot (.) and colon (:) formats
                check_in_clean = check_in.strip().replace(".", ":")
                check_out_clean = check_out.strip().replace(".", ":")

                fmt = "%H:%M"
                t1 = datetime.strptime(check_in_clean, fmt)
                t2 = datetime.strptime(check_out_clean, fmt)
                
                gross_hours = (t2 - t1).total_seconds() / 3600
                net_hours = gross_hours - (lunch_break / 60)
                ot_hours = max(0.0, net_hours - final_const_hours)
                
                st.session_state.days_list.append({
                    "Date": selected_date_str,
                    "Check-In": check_in_clean,
                    "Check-Out": check_out_clean,
                    "Lunch (min)": lunch_break,
                    "Total Worked": round(net_hours, 2),
                    "OT Hours": round(ot_hours, 2)
                })
                st.success(f"Saved: {selected_date_str}")
                st.rerun()
                
            except ValueError:
                st.error("Invalid Time Format. Please use HH.MM or HH:MM (e.g., 08.30 or 17:00).")

# 3. Data Display & Export
if st.session_state.days_list:
    st.session_state.days_list.sort(key=lambda x: x['Date'])
    df = pd.DataFrame(st.session_state.days_list)
    
    st.subheader("Monthly Log")
    
    # Header for the interactive table
    cols = st.columns([2, 1, 1, 1, 1, 1, 1])
    fields = ["Date", "Check-In", "Check-Out", "Total", "OT", "Action"]
    for col, field in zip(cols, fields):
        col.write(f"**{field}**")

    # Row display with Delete Button
    for i, row in enumerate(st.session_state.days_list):
        r_cols = st.columns([2, 1, 1, 1, 1, 1, 1])
        r_cols[0].write(row["Date"])
        r_cols[1].write(row["Check-In"])
        r_cols[2].write(row["Check-Out"])
        r_cols[3].write(str(row["Total Worked"]))
        r_cols[4].write(str(row["OT Hours"]))
        
        # Delete Function logic
        if r_cols[5].button("🗑️", key=f"delete_{i}"):
            st.session_state.days_list.pop(i)
            st.rerun()
    
    total_w = df["Total Worked"].sum()
    total_ot = df["OT Hours"].sum()
    
    st.divider()
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Hours", f"{total_w:.2f} hrs")
    col_b.metric("Total OT", f"{total_ot:.2f} hrs")
    
    clean_name = name_user.replace(" ", "_")
    report_date = datetime.now().strftime('%Y-%m')

    # --- CSV Export ---
    df_export = df.copy()
    summary_row = pd.DataFrame([{
        "Date": "TOTAL", "Check-In": "", "Check-Out": "", 
        "Total Worked": round(total_w, 2), "OT Hours": round(total_ot, 2)
    }])
    df_export = pd.concat([df_export, summary_row], ignore_index=True)
    csv = df_export.to_csv(index=False).encode('utf-8')

    # --- PDF Export Function ---
    def create_pdf(dataframe, name, total_worked, total_ot_hrs):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"HR Attendance & OT Report", ln=True, align="C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Employee: {name}", ln=True, align="C")
        pdf.cell(0, 10, f"Report Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align="C")
        pdf.ln(10)

        # Table Header
        pdf.set_font("Arial", "B", 10)
        pdf_cols = ["Date", "Check-In", "Check-Out", "Total Worked", "OT Hours"]
        col_width = 190 / len(pdf_cols)
        for col in pdf_cols:
            pdf.cell(col_width, 10, col, 1)
        pdf.ln()

        # Table Body
        pdf.set_font("Arial", "", 10)
        for _, row in dataframe.iterrows():
            for col in pdf_cols:
                pdf.cell(col_width, 10, str(row[col]), 1)
            pdf.ln()

        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"Total Monthly Worked Hours: {total_worked:.2f} hrs", ln=True)
        pdf.cell(0, 10, f"Total Monthly OT Hours: {total_ot_hrs:.2f} hrs", ln=True)
        
        return pdf.output(dest='S').encode('latin-1')

    # Export Buttons
    st.divider()
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"HR_Report_{clean_name}_{report_date}.csv",
            mime="text/csv",
        )
    
    with btn_col2:
        try:
            pdf_bytes = create_pdf(df, name_user, total_w, total_ot)
            st.download_button(
                label="📄 Download PDF",
                data=pdf_bytes,
                file_name=f"HR_Report_{clean_name}_{report_date}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"Error generating PDF: {e}")

else:
    st.info("No data entered for this month yet.")