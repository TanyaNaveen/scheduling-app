import streamlit as st

form_page = st.Page("views/form.py", title="Worship Scheduling Form", default=True)
admin_page = st.Page("views/admin.py", title="Admin Dashboard")

# Create navigation
pg = st.navigation([form_page], expanded=False)
pg.run()