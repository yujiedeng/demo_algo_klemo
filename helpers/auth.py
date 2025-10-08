import streamlit as st
import os 


def check_password():
    """Returns `True` if the user entered the correct password."""
    
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]["PWD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        elif st.session_state["password"] == os.getenv('APP_PASSWORD'):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # --- Password not entered yet ---
    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False

    # --- Incorrect password ---
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False

    # --- Correct password ---
    else:
        return True