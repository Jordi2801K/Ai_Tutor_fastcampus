# # 입력한 말을 따라하는 Echo Bot

import streamlit as st

st.title("Echo Bot")

# Initialize chat history
# session_state는 화면이 새로고침 되더라도 이전 내용을 유지함
# chat_input() 으로 입력받을 때 새로운 입력을 받으면 이전 내용을 지우고 같은 message block에 덮어씌우지만
# session_state를 사용하면 이전 입력을 유지하고 밑에 추가로 입력할 수 있다
if "messages" not in st.session_state:  # 이전 내용이 없으면
    st.session_state.messages = []      # messages를 빈 리스트로 초기화

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):  # ex) {"role": "assistant", "content": "hello"}
        st.markdown(message["content"])

# React to user input

# := 이건 뭐냐?
#> prompt = st.chat_input("What is up?")
#> if prompt :
# 위 아래 코드는 같은 코드. 한 줄로 줄일 수 있음
#> if prompt := st.chat_input("What is up?"):

prompt = st.chat_input("What is up?")   # Chat 입력받기
if prompt :     # prompt가 있으면 == 입력되면
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)    # markdown 형식으로 그 메시지를 띄워줌
    # Add user message to chat history
    # user role로 입력된 데이터를 messages에 저장
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Bot의 응답
    response = f"Echo: {prompt}"
    # Display assistant response in chat message container
    with st.chat_message("assistant"):  # assistant role의 message block을 만들어서 
        st.markdown(response)   # markdown형식으로 reponse를 출력
    # Add assistant response to chat history
    # 동일하게 assistant role로 입력된 데이터를 messages에 저장
    st.session_state.messages.append({"role": "assistant", "content": response})