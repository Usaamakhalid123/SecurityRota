import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Security Rota AI",
    layout="wide",
    page_icon="📅",
    initial_sidebar_state="expanded"
)

# Initialize session state
def init_session_state():
    if 'employees' not in st.session_state:
        st.session_state.employees = [
            {
                'id': 1,
                'name': 'John Smith',
                'phone': '07700 123456',
                'email': 'john.smith@email.com',
                'postcode': 'LE1 1AA',
                'sia_license': 'SIA123456',
                'max_hours': 48,
                'availability': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                'willing_24hr': True
            },
            {
                'id': 2,
                'name': 'Sarah Wilson',
                'phone': '07700 789012',
                'email': 'sarah.wilson@email.com',
                'postcode': 'NN18 8BB',
                'sia_license': 'SIA789012',
                'max_hours': 40,
                'availability': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
                'willing_24hr': False
            }
        ]
    if 'sites' not in st.session_state:
        st.session_state.sites = []
    if 'schedules' not in st.session_state:
        st.session_state.schedules = {}
    if 'current_schedule' not in st.session_state:
        st.session_state.current_schedule = None
    if 'alerts' not in st.session_state:
        st.session_state.alerts = []
    if 'next_employee_id' not in st.session_state:
        st.session_state.next_employee_id = 3
    if 'next_site_id' not in st.session_state:
        st.session_state.next_site_id = 3

# Helper functions
def calculate_shift_hours(start_time, end_time):
    start_h, start_m = map(int, start_time.split(':'))
    end_h, end_m = map(int, end_time.split(':'))
    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60
    return (end_minutes - start_minutes) / 60

def estimate_distance(postcode1, postcode2):
    if not postcode1 or not postcode2:
        return 999
    area1 = ''.join(filter(str.isalpha, postcode1[:3])).upper()
    area2 = ''.join(filter(str.isalpha, postcode2[:3])).upper()
    if area1 == area2:
        return 5
    elif area1[0] == area2[0]:
        return 25
    else:
        return 50

def get_week_dates(start_date):
    start_date = datetime.strptime(str(start_date), "%Y-%m-%d")
    week_dates = {}
    for i, day in enumerate(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
        date = start_date + timedelta(days=i)
        week_dates[day] = date.strftime("%Y-%m-%d")
    return week_dates

# Employee Management
def manage_employees():
    st.title("👥 Manage Employees")
    with st.expander("➕ Add New Employee", expanded=False):
        with st.form("add_employee"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name*")
                phone = st.text_input("Phone Number")
                postcode = st.text_input("Home Postcode*")
                email = st.text_input("Email Address*")
            with col2:
                sia_license = st.text_input("SIA License Number")
                max_hours = st.number_input("Max Weekly Hours", min_value=1, max_value=60, value=48)
                willing_24hr = st.checkbox("Willing to work 24-hour shifts")
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            availability = st.multiselect("Select available days", days, default=days)
            submitted = st.form_submit_button("Add Employee")
            if submitted:
                if name and postcode and email:
                    new_emp = {
                        'id': st.session_state.next_employee_id,
                        'name': name,
                        'phone': phone,
                        'email': email,
                        'postcode': postcode,
                        'sia_license': sia_license,
                        'max_hours': max_hours,
                        'availability': availability,
                        'willing_24hr': willing_24hr
                    }
                    st.session_state.employees.append(new_emp)
                    st.session_state.next_employee_id += 1
                    st.success(f"✅ Added {name} successfully!")
                    st.experimental_rerun()
                else:
                    st.error("Please fill in Name, Postcode, and Email.")
    st.subheader("Current Employees")
    if st.session_state.employees:
        for emp in st.session_state.employees:
            with st.expander(f"👤 {emp['name']} - {emp['postcode']}"):
                st.write(f"**Phone:** {emp['phone'] or 'N/A'}")
                st.write(f"**Email:** {emp['email'] or 'N/A'}")
                st.write(f"**SIA License:** {emp['sia_license'] or 'N/A'}")
                st.write(f"**Max Hours:** {emp['max_hours']}")
                st.write(f"**Available:** {', '.join(emp['availability'])}")
                st.write(f"**24hr Shifts:** {'✅ Yes' if emp['willing_24hr'] else '❌ No'}")
                if st.button("🗑️ Delete Employee", key=f"delete_emp_{emp['id']}"):
                    st.session_state.employees = [e for e in st.session_state.employees if e['id'] != emp['id']]
                    st.success(f"Deleted employee: {emp['name']}")
                    st.experimental_rerun()
    else:
        st.info("No employees added yet.")

# Site Management
def manage_sites():
    st.title("📍 Manage Sites")
    with st.expander("➕ Add New Site", expanded=False):
        with st.form("add_site"):
            col1, col2 = st.columns(2)
            with col1:
                site_name = st.text_input("Site Name*")
                client = st.selectbox("Client", ["Taz", "Servo", "Ayam"])
                postcode = st.text_input("Postcode*")
                guards = st.number_input("Guards Required", min_value=1, max_value=10, value=1)
            with col2:
                shift_start = st.time_input("Shift Start")
                shift_end = st.time_input("Shift End")
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            operation_days = st.multiselect("Select operating days", days, default=days)

            # Weekend shift dynamic input
            weekend_shifts = st.checkbox("Enable Weekend Shifts")
            weekend_guards = None
            shift_type = None
            weekend_day_start = None
            weekend_day_end = None
            weekend_night_start = None
            weekend_night_end = None

            if weekend_shifts:
                weekend_guards = st.number_input("How many guards required for weekends?", min_value=1, max_value=3)
                shift_type = st.radio("Weekend Shift Type", ['Day Shift', 'Night Shift', 'Day & Night'])
                if shift_type == 'Day & Night':
                    weekend_day_start = st.time_input("Day Shift Start Time")
                    weekend_day_end = st.time_input("Day Shift End Time")
                    weekend_night_start = st.time_input("Night Shift Start Time")
                    weekend_night_end = st.time_input("Night Shift End Time")

            submitted = st.form_submit_button("Add Site")
            if submitted:
                if site_name and postcode and shift_start and shift_end:
                    new_site = {
                        'id': st.session_state.next_site_id,
                        'name': site_name,
                        'client': client,
                        'postcode': postcode,
                        'guards_required': guards,
                        'shift_start': shift_start.strftime("%H:%M"),
                        'shift_end': shift_end.strftime("%H:%M"),
                        'weekend_shifts_enabled': weekend_shifts,
                        'weekend_guards': weekend_guards,
                        'shift_type': shift_type,
                        'weekend_day_start': weekend_day_start.strftime("%H:%M") if weekend_day_start else None,
                        'weekend_day_end': weekend_day_end.strftime("%H:%M") if weekend_day_end else None,
                        'weekend_night_start': weekend_night_start.strftime("%H:%M") if weekend_night_start else None,
                        'weekend_night_end': weekend_night_end.strftime("%H:%M") if weekend_night_end else None,
                        'days_operation': operation_days
                    }
                    st.session_state.sites.append(new_site)
                    st.session_state.next_site_id += 1
                    st.success(f"✅ Added {site_name} successfully!")
                    st.experimental_rerun()
                else:
                    st.error("Please fill in all required fields")

    st.subheader("Current Sites")
    if st.session_state.sites:
        for site in st.session_state.sites:
            with st.expander(f"🏢 {site['name']} ({site['client']}) - {site['postcode']}"):
                st.write(f"**Guards Required:** {site['guards_required']}")
                st.write(f"**Shift:** {site['shift_start']} - {site['shift_end']}")
                st.write(f"**Operating Days:** {', '.join(site['days_operation'])}")
                if site.get('weekend_shifts_enabled'):
                    st.write(f"**Weekend Guards:** {site.get('weekend_guards')}")
                    st.write(f"**Weekend Type:** {site.get('shift_type')}")
                    if site.get('shift_type') == 'Day & Night':
                        st.write(f"Day: {site.get('weekend_day_start')} - {site.get('weekend_day_end')}")
                        st.write(f"Night: {site.get('weekend_night_start')} - {site.get('weekend_night_end')}")
                if st.button("🗑️ Delete Site", key=f"delete_site_{site['id']}"):
                    st.session_state.sites = [s for s in st.session_state.sites if s['id'] != site['id']]
                    st.success(f"Deleted site: {site['name']}")
                    st.experimental_rerun()
    else:
        st.info("No sites added yet.")

# The rest of the code (Generate Schedule, View Schedule, Excel Export, etc.)
# can remain as before, using the site dictionary for weekend shifts and dates.
