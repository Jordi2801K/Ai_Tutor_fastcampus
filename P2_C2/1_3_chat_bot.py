
import streamlit as st
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder

# Init
client = OpenAI()

if "messages" not in st.session_state:
    st.session_state.messages = []


# View
st.title("대화하기")


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


user_input = st.chat_input("What is up?")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()    # stream을 설정했기 때문에 조각조각 나뉘어서 들어오는 ChatGPT API의 응답을 placeholder로 한번에 모아주어 실시간으로 보여주기 위함
        full_response = ""  # 단순 최종 응답을 출력하기 위함
        for response in client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages  # session_state안에 있는 모든 messages를 넘겨줌
            ],
            stream=True,    # stream 활성화
        ):
            full_response += (response.choices[0].delta.content or "")  # stream을 활성화 했을 때 받는 조각조각의 응답은 구조체로 이루어져있음
                                                                        # 그 구조체의 choices[0]의 delta 안의 content에 조각조각 응답이 들어있음
            message_placeholder.markdown(full_response + "▌")   # placeholder에 markdown형식으로 커서 문자를 추가하여 보기 좋게 띄워줌
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})   # session_state에 추가
