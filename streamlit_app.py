import streamlit as st

st.set_page_config(
    page_title="Worship Scheduler",
    initial_sidebar_state="collapsed",
)

form_page = st.Page("views/form.py", title="Worship Scheduling Form", default=True)
admin_page = st.Page("views/admin.py", title="Admin Dashboard")

# Create navigation
pg = st.navigation([form_page, admin_page], expanded=False)
pg.run()