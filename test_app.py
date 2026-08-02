
import streamlit as st
with st.form('my_form'):
    st.data_editor([{'A': 1}])
    st.form_submit_button('Submit')
