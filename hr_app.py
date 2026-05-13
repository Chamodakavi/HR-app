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
    const_hours = st.number_input("Standard Shift (Hours)", value=8.0, step=0.5)
    
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
        check_in = st.text_input("Check-In (HH:MM)", value="08:00")
    with c3:
        check_out = st.text_input("Check-Out (HH:MM)", value="17:00")
    with c4:
        lunch_break = st.number_input("Lunch (Minutes)", value=60, step=5)

    if st.button("Save Entry"):
        selected_date_str = date_in.strftime("%Y-%m-%d")
        is_duplicate = any(d["Date"] == selected_date_str for d in st.session_state.days_list)

        if is_duplicate:
            st.error(f"Entry for {selected_date_str} already exists!")
        else:
            try:
                fmt = "%H:%M"
                t1 = datetime.strptime(check_in, fmt)
                t2 = datetime.strptime(check_out, fmt)
                
                gross_hours = (t2 - t1).total_seconds() / 3600
                net_hours = gross_hours - (lunch_break / 60)
                ot_hours = max(0.0, net_hours - const_hours)
                
                st.session_state.days_list.append({
                    "Date": selected_date_str,
                    "Check-In": check_in,
                    "Check-Out": check_out,
                    "Lunch (min)": lunch_break,
                    "Total Worked": round(net_hours, 2),
                    "OT Hours": round(ot_hours, 2)
                })
                st.success(f"Saved: {selected_date_str}")
                st.rerun()
                
            except ValueError:
                st.error("Invalid Time Format. Use HH:MM (24-hour).")

# 3. Data Display & Export
if st.session_state.days_list:
    st.session_state.days_list.sort(key=lambda x: x['Date'])
    df = pd.DataFrame(st.session_state.days_list)
    
    st.subheader("Monthly Log")
    st.table(df)
    
    total_w = df["Total Worked"].sum()
    total_ot = df["OT Hours"].sum()
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Hours", f"{total_w:.2f} hrs")
    col_b.metric("Total OT", f"{total_ot:.2f} hrs")
    
    clean_name = name_user.replace(" ", "_")
    report_date = datetime.now().strftime('%Y-%m')

    # --- CSV Export ---
    df_export = df.copy()
    summary_row = pd.DataFrame([{
        "Date": "TOTAL", "Check-In": "", "Check-Out": "", 
        "Lunch (min)": "", "Total Worked": round(total_w, 2), "OT Hours": round(total_ot, 2)
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
        cols = dataframe.columns.tolist()
        col_width = 190 / len(cols)
        for col in cols:
            pdf.cell(col_width, 10, col, 1)
        pdf.ln()

        # Table Body
        pdf.set_font("Arial", "", 10)
        for _, row in dataframe.iterrows():
            for col in cols:
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