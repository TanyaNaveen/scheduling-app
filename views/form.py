import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.title("Worship Scheduling Availability")

# Initialize Connection
conn = st.connection("supabase", type=SupabaseConnection)

# Initialize Session State
if "form_data" not in st.session_state:
    st.session_state.form_data = {}

if "done" not in st.session_state:
    st.session_state.done = False

if st.session_state.done:
    st.success("Thank you! Successfully saved your response!")
    st.info("To edit your response, refresh this page and submit the form again with any updated info.")
    st.stop()

with st.form("user_form"):
    st.subheader("Personal Information")
    name = st.text_input("Name", key="name_input")
    email = st.text_input("Email", key="email_input").strip().lower()
    phone = st.text_input("Phone", key="phone_input")

    st.divider()
    st.subheader("Availability")
    st.write("Please select all weeks that you are available!")
    availability = {}
    weeks = ["Jan 14", "Jan 21", "Jan 28", "Feb 4", "Feb 11", "Feb 18", "Feb 25", "March 4", "March 11"]
    for i in range(0, len(weeks)):
        key = f"w{i + 2}"
        availability[key] = st.checkbox(f"Week {i + 2}: {weeks[i]}", key=f"check_{key}")

    st.divider()
    st.subheader("Instruments")
    st.write("Please select all instruments that you are willing to play!")
    inst_names = ['Vocals', 'Acoustic Guitar', 'Piano', 'Cajon', 'Strings', 'Electric Guitar', 'Bass Guitar'] # TODO: Add bass
    instruments = {}
    for inst in inst_names:
        key = inst.replace(' ', '_').lower()
        instruments[key] = st.checkbox(inst, key=f"check_{key}")    

    st.divider()
    st.subheader("Scheduling Preferences")
    freq_options = {
        "Once": 1, 
        "Twice": 2, 
        "Around once a month": 3, 
        "Around once every few weeks": 4
    }
    freq = st.radio(
        label="How often would you like to be scheduled this quarter?",
        options=list(freq_options.keys()),
        index=None,
        key="freq_input"
    )

    submitted = st.form_submit_button("Submit")
    
if submitted:
    # Validation Logic
    missing_info = not (name and email and phone and freq)
    any_availability = any(availability.values())
    any_instrument = any(instruments.values())

    if missing_info:
        st.error("Please fill out all personal information and select a frequency.")
    elif not any_availability:
        st.error("Please select at least one week of availability.")
    elif not any_instrument:
        st.error("Please select at least one instrument.")
    else:
        form_payload = {
            "name": name,
            "email": email,
            "phone": phone,
            "num_weeks": freq_options[freq],
            **availability,
            **instruments
        }
        
        # DB Write
        try:
            conn.table("team_availability").upsert(form_payload, on_conflict="email").execute()
            st.session_state.done = True
            st.rerun()
        except Exception as e:
            st.error(f"Database Error: {e}")
