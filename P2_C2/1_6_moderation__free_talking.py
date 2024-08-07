import base64
import streamlit as st
from openai import OpenAI
from audio_recorder_streamlit import audio_recorder


# Init
client = OpenAI()

# # Moderation API를 활용한 입력된 문장의 위험도(문제) 측정
def get_policy_violated(text):
    response = client.moderations.create(input=text)    # Moderation API로 검사
    output = response.results[0]    # 검사된 결과
    output_dict = output.model_dump()   # 결과를 Dictionary 형태로 변경
    flagged_list = []   # Moderation API의 category가 True인 항목들(문제가 있는 항목)을 담아둘 리스트
    for k, v in output_dict['categories'].items():
        if v:   # categories안에 True인 항목이 있으면
            score = output_dict['category_scores'][k]   # 위험도 점수를 받아오고
            flagged_list.append((k, score))     # category와 위험도를 flagged_list에 추가
    return flagged_list

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
# session_state는 화면이 새로고침 되더라도 이전 내용을 유지함
# chat_input() 으로 입력받을 때 새로운 입력을 받으면 이전 내용을 지우고 같은 message block에 덮어씌우지만
# session_state를 사용하면 이전 입력을 유지하고 밑에 추가로 입력할 수 있다
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

        # # 입력된 문장의 위험도 확인
        flag_list = get_policy_violated(user_input)

        with st.chat_message("user"):
            if flag_list :  # flag_list가 비어있지 않으면 == 문제가 있으면
                st.markdown("그런말 하면 안돼요~")  # User의 메시지를 보여주지 않고
                st.warning(flag_list)   # 위험도를 표시해준다
            else :  # 문제가 없으면
                st.markdown(user_input)     # 정상적으로 User의 메시지를 표시해줌
            
            if flag_list :  #문제가 있으면
                st.session_state.messages.append({"role": "user", "content": "그런말 하면 안돼요~"})    # session_state에 입력된 문장을 추가하지 않음
            else :  # 문제가 없는 경우에는
                st.session_state.messages.append({"role": "user", "content": user_input})   # 정상적으로 session_state에 추가함


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

            # TTS API를 이용하여 AI의 대답을 음성으로 들려줌
            speech_file_path = "tmp_speak.mp3"
            response = client.audio.speech.create(
              model="tts-1",
              voice="echo", # alloy, echo, fable, onyx, nova, and shimmer
              input=full_response
            )
            response.stream_to_file(speech_file_path)   # client.audio.speech.create()에서 stream_to_file 메소드가 더이상 사용되지 않음 / reponse객체 생성할 때 client.audio.speech.with_streaming_response.create() 사용
                                                        # 그냥 사용해도 작동은 함

            autoplay_audio(speech_file_path)

        st.session_state.messages.append({"role": "assistant", "content": full_response})   # session_state에 추가



