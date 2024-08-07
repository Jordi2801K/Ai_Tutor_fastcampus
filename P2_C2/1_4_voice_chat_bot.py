import base64
import streamlit as st
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder


# Init
client = OpenAI()

if "messages" not in st.session_state:
    st.session_state.messages = []


# Helpers
# streamlit에서 audio를 자동 재생하기 위한 코드
def autoplay_audio(file_path: str):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio controls autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(
            md,
            unsafe_allow_html=True,
        )

# View
st.title("프리 토킹 서비스")

# container()는 위젯이나 요소들을 그룹화하거나 레이아웃을 나눌 수 있음
con1 = st.container()   # 메시지를 담을 container
con2 = st.container()   # 음성인식을 위한 container
# container를 메시지와 음성인식으로 나눠서 관리하는 이유는 음성인식이 메시지보다 먼저 렌더링되야 하므로 나눠서 관리
# BUT, 코드 순서는 con2, con1 순서이지만 container는 숫자대로 띄워주기 때문에 메시지가 위로 오고 음성인식하는 부분은 아래애 위치함

user_input = ""

# 음성인식 먼저
with con2:
    audio_bytes = audio_recorder("talk", pause_threshold=2.0,)  # pause_threshold 는 설정한 초만큼 무음이 유지되면 자동으로 recording을 종료
    try:
        if audio_bytes:     # 녹음이 완료되면
            with open("./tmp_audio.wav", "wb") as f:    # 해당 녹음을 파일로 저장
                f.write(audio_bytes)

            with open("./tmp_audio.wav", "rb") as f:    # 녹음된 파일을 Whisper API로 전달
                transcript = client.audio.transcriptions.create(    # transcript에 텍스트로 저장됨
                    model="whisper-1",
                    file=f
                )
                user_input = transcript.text    # 변환된 음성 텍스트를 user_input에 저장
    except Exception as e:
        pass

# 메시지 표현
with con1:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input:  # 음성 인식된 user_input이 있으면
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)


        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            for response in client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            ):
                full_response += (response.choices[0].delta.content or "")
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)

            # TTS API를 이용하여 AI의 대답을 음성으로 들려줌
            speech_file_path = "tmp_speak.mp3"
            response = client.audio.speech.create(
              model="tts-1",
              voice="echo", # alloy, echo, fable, onyx, nova, and shimmer
              input=full_response
            )
            response.stream_to_file(speech_file_path)   # 빗금이 왜 쳐져있는지는 모르겠는데 잘 작동함

            autoplay_audio(speech_file_path)

        st.session_state.messages.append({"role": "assistant", "content": full_response})



