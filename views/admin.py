import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from scripts.scheduling_logic import ScheduleBuilder 
from scripts.auth import check_auth, logout 

# 1. Connection
conn = st.connection("supabase", type=SupabaseConnection)

# 2. Authentication Gatekeeper
# This will stop execution if the user isn't logged in or authorized
user = check_auth(conn, allowed_admins=["tanyanaveen04@gmail.com"])

# 3. Global Sidebar (Logout)
st.sidebar.success(f"Logged in: {user.email}")
if st.sidebar.button("Log Out"):
    logout(conn)

# 4. State Initialization (Only if we passed auth)
if 'solutions' not in st.session_state:
    st.session_state.update({
        'solutions': None,
        'curr_sol': 0,
        'edited_schedule': None
    })

def handle_generate():
    # Use the 'df' defined later or pass it as an argument
    scheduler = ScheduleBuilder(data=df, n=5)
    scheduler.build_model()
    sols = scheduler.get_solutions()
    if sols:
        st.session_state.solutions = sols
        st.session_state.curr_sol = 0
    else:
        st.session_state.solutions = []

def next_schedule():
    if st.session_state.solutions:
        st.session_state.curr_sol = (st.session_state.curr_sol + 1) % len(st.session_state.solutions)

def prev_schedule():
    if st.session_state.solutions:
        st.session_state.curr_sol = (st.session_state.curr_sol - 1) % len(st.session_state.solutions)

# --- UI LOGIC ---
st.title("Admin Scheduling Dashboard")

# 5. Data Fetching
response = conn.table("team_availability").select("*").execute()
df = pd.DataFrame(response.data)

if df.empty:
    st.warning("No responses yet")
    st.stop()

else:
    st.subheader("View Responses")
    st.dataframe(df)


    # 5. Leader Selection (Optimized)
    with st.expander("Manage Leaders", expanded=False):
        st.subheader("Assign Leadership Status")
        name_list = df['name'].tolist()
        
        with st.form("leader_form"):
            is_leader_map = dict(zip(df['name'], df.get('is_leader', [False]*len(df))))
            
            selected_leaders = {}
            for name in name_list:
                selected_leaders[name] = st.checkbox(name, value=is_leader_map.get(name, False))
                
            if st.form_submit_button("Update All Leaders"):
                for name, is_lead in selected_leaders.items():
                    conn.table("team_availability").update({"is_leader": is_lead}).eq("name", name).execute()
                st.success("Leadership updated!")
                st.rerun()

    # 6. Generator Section
    st.divider()
    st.button("🚀 Generate New Schedules", on_click=handle_generate, type="primary")

    if st.session_state.solutions is not None:
        if not st.session_state.solutions:
            st.error("No feasible schedules found with current constraints.")
        else:
            curr_idx = st.session_state.curr_sol
            sols_count = len(st.session_state.solutions)
            
            st.subheader(f"Schedule Option {curr_idx + 1} of {sols_count}")
            
            # Extract current solution
            raw_schedule, raw_diags = st.session_state.solutions[curr_idx]
            
            # Formatting for display
            schedule_df = pd.DataFrame(raw_schedule).map(
                lambda x: ", ".join(x) if isinstance(x, list) else str(x)
            )
            diag_df = pd.DataFrame(raw_diags)

            # Navigation Columns
            col1, col2, col3 = st.columns([1, 1, 4])
            col1.button("Prev", on_click=prev_schedule)
            col2.button("Next", on_click=next_schedule)

            # 7. Editable Schedule Area
            # We store the edited version in state so it persists during the session
            edited_df = st.data_editor(
                schedule_df,
                key=f"editor_{curr_idx}", # Key change triggers refresh on new solution
                width="stretch"
            )
            st.session_state.edited_schedule = edited_df

            # 8. Export Actions
            csv = edited_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download this Schedule (CSV)",
                data=csv,
                file_name=f"worship_schedule_opt_{curr_idx+1}.csv",
                mime="text/csv",
            )

            with st.expander("View Details"):
                st.dataframe(diag_df, use_container_width=True)
