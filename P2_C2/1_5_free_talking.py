import base64
import streamlit as st
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder


# Init
client = OpenAI()

level_1_prompt = """\
- You are an English teacher.
- The user's English proficiency is at a beginner level.
- Respond in a way that is easy for the user to understand.
- You must answer in English only.
"""

level_2_prompt = """\
- You are an English teacher.
- The user's English level is intermediate.
- Respond according to the user's English proficiency.
- You must answer in English only.
"""

level_3_prompt = """\
- You are an English teacher.
- The user's English proficiency is advanced.
- Respond accordingly to the user's level of English.
- You must answer in English only.
"""

# 레벨과 프롬프트를 매핑
level_to_prompt_map = {
    "초급": level_1_prompt,
    "중급": level_2_prompt,
    "고급": level_3_prompt
}

# # 기본 세팅
# 기본 설정을 초급으로
if "level" not in st.session_state :
    st.session_state.level = "초급"

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": level_to_prompt_map[st.session_state.level]}]     # 기본 설정된 초급 level로 ststem prompt 설정

# 대화를 초기화할 때 audio_bytes에 남아있는 cache를 비워주기 위해 우선 비어있는 prev_audio_bytes를 생성
if "prev_audio_bytes" not in st.session_state:
    st.session_state.prev_audio_bytes = None


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

# 대화 초기화 버튼 만들기(새로운 대화 만들기)
if st.button("대화 초기화") :
    st.session_state.messages = [{"role": "system", "content": level_to_prompt_map[st.session_state.level]}]

# # Level 설정 select box 만들기
option = st.selectbox("프리 토이 난이도 설정", ["초급", "중급", "고급"])
if option != st.session_state.level :   # 기본 설정된 초급과 다르면
    st.session_state.level = option     # 해당 level로 설정
    st.session_state.messages = [{"role": "system", "content": level_to_prompt_map[st.session_state.level]}]    # 해당 level로 system prompt 설정

# container()는 위젯이나 요소들을 그룹화하거나 레이아웃을 나눌 수 있음
con1 = st.container()   # 메시지를 담을 container
con2 = st.container()   # 음성인식을 위한 container
# container를 메시지와 음성인식으로 나눠서 관리하는 이유는 음성인식이 메시지보다 먼저 렌더링되야 하므로 나눠서 관리
# BUT, 코드 순서는 con2, con1 순서이지만 container는 숫자대로 띄워주기 때문에 메시지가 위로 오고 음성인식하는 부분은 아래애 위치함

user_input = ""

# 음성인식 먼저
with con2:
    audio_bytes = audio_recorder("talk", pause_threshold=2.0,)  # pause_threshold 는 설정한 초만큼 무음이 유지되면 자동으로 recording을 종료
    
    if audio_bytes == st.session_state.prev_audio_bytes :   # 현재 cache와 이전 cache가 동일하면 == 이전 cache가 남아있으면
        audio_bytes = None      # 현재 cache를 비워줌
    st.session_state.prev_audio_bytes = audio_bytes     # (맨 처음에는 비어있던)prev_audio_bytes에 현재 cache를 덮어 씌워줌

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



