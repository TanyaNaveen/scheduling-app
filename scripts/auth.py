import streamlit as st
import os 

def logout(conn):
    conn.client.auth.sign_out()
    st.session_state.authenticated = False
    st.rerun()


def check_auth(conn, allowed_admins):
    # If 'code' is in the URL, we are returning from Google
    if "code" in st.query_params:
        print("code is there    ")
        try:
            auth_code = st.query_params["code"]
            # Force the handshake
            conn.client.auth.exchange_code_for_session({"auth_code": auth_code})
            
            # CLEAR THE URL: This is vital. It removes the code and triggers a clean rerun
            st.query_params.clear()
            st.rerun() 
        except Exception as e:
            st.error(f"Handshake failed: {e}")
            st.stop()

    # 2. CHECK FOR USER SESSION
    # This will now work because the code was exchanged above
    user = None
    try:
        user_res = conn.client.auth.get_user()
        if user_res:
            user = user_res.user
    except:
        pass

    # 3. VERIFY & AUTHORIZE
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

    # 4. LOGIN UI (Only shows if no user is found)
    st.session_state.authenticated = False
    st.title("Admin Login")
    
    redirect_url = st.secrets.get(
        "AUTH_REDIRECT_URL",
        "https://ruf-worship-scheduler.streamlit.app/admin"
    )

    print(redirect_url)
    
    res = conn.client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_url}
        })
    
    if res.url:
        st.link_button("Sign in with Google", res.url)
        
        
        # Use HTML redirect to avoid the 'link_button' extra click
        st.markdown(f'<meta http-equiv="refresh" content="0;url={res.url}">', unsafe_allow_html=True)
        
        st.stop()

    st.stop() 




import streamlit as st

def logout(conn):
    conn.client.auth.sign_out()
    st.session_state.authenticated = False
    st.rerun()


def check_auth(conn, allowed_admins):
    # 1. Check for existing Supabase session
    user = None
    try:
        res = conn.client.auth.get_user()
        if res:
            user = res.user
    except:
        pass

    # 2. Authorized user
    if user:
        if user.email in allowed_admins:
            st.session_state.authenticated = True
            return user
        else:
            st.error(f"Access denied: {user.email}")
            if st.button("Log out"):
                logout(conn)
            st.stop()

    # 3. Login UI
    st.session_state.authenticated = False
    st.title("Admin Login")

    redirect_url = st.secrets.get(
        "AUTH_REDIRECT_URL",
        "https://ruf-worship-scheduler.streamlit.app/admin"
    )

    if st.button("Sign in with Google"):
        auth_url = conn.client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_url}
        }).url

        st.link_button("Continue to Google", auth_url)
        st.stop()

    st.stop()
