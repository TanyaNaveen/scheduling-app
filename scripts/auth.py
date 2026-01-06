import streamlit as st

def logout(conn):
    conn.client.auth.sign_out()
    st.session_state.authenticated = False
    st.rerun()


def check_auth(conn, allowed_admins):
    # If 'code' is in the URL, we are returning from Google
    if "code" in st.query_params:
        try:
            auth_code = st.query_params["code"]
            conn.client.auth.exchange_code_for_session({"auth_code": auth_code})
            
            st.query_params.clear()
            st.rerun() 
        except Exception as e:
            st.error(f"Handshake failed: {e}")
            st.stop()

    # Check for user session
    user = None
    try:
        user_res = conn.client.auth.get_user()
        if user_res:
            user = user_res.user
    except:
        pass

    # Authorize user
    if user:
        if user.email in allowed_admins:
            st.session_state.authenticated = True
            return user
        else:
            st.error(f"Access Denied: {user.email} is not an authorized admin.")
            if st.sidebar.button("Log Out"):
                conn.client.auth.sign_out()
                st.rerun()
            st.stop()

    # Login UI
    st.session_state.authenticated = False
    st.title("Admin Login")
    
    redirect_url = st.secrets.get(
        "AUTH_REDIRECT_URL",
        "https://ruf-worship-scheduler.streamlit.app/admin"
    )
    
    # get the response URL
    res = conn.client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_url}
        })
    
    # manually redirect to response URL (google sign in page)
    if res.url:
        st.link_button("Sign in with Google", res.url)

    st.stop() 
