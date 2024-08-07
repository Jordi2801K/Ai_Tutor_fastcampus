import streamlit as st
import numpy as np

# # 기본젹인 Chat UI 만들기
# User role Chat UI
with st.chat_message("user") :
    st.write("hello!")

# AI role Chat UI
with st.chat_message("assistant") :
    st.write("hello human!")
    # st.bar_chart(np.random.randn(30, 3))    # 랜덤 바 차트 생성


# # # with 구문 없이 instance를 생성하여 Chat UI를 만들수도 있음
# message = st.chat_message("assistant")
# message.write("hello human")
# message.bar_chart(np.random.rand(30, 3))

prompt = st.chat_input("say something")
if prompt :     # prompt가 존재하면
    with st.chat_message("user") :
        st.write(prompt)