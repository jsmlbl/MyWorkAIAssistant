import streamlit as st
from streamlit_paste_button import paste_image_button as pbutton

# 刷新按钮
if st.button("🔄 刷新页面"):
    st.rerun()

# 粘贴图像按钮
paste_result = pbutton("📋 Paste an image")

if paste_result.image_data is not None:
    st.write('Pasted image:')
    st.image(paste_result.image_data)
