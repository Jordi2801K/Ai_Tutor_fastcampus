import io
import base64
from openai import OpenAI, audio
import requests
from openai.types.audio import transcription
import streamlit as st
from audio_recorder_streamlit import audio_recorder

# Set page configuration for wide layout
st.set_page_config(page_title="롤플레이", layout="wide")

host_url = "http://localhost:8000"
chat_url = f"{host_url}/chat"
transcribe_url = f"{host_url}/transcribe"


if "curr_page" not in st.session_state:
    st.session_state["curr_page"] = "home"


if "messages" not in st.session_state:
    st.session_state.messages = []


if "prev_audio_bytes" not in st.session_state:
    st.session_state.prev_audio_bytes = None


# Assuming you have a dictionary that holds your data like below:
roleplays = {
    'hamburger': {"display_name":'햄버거 주문하기', 'emoji': '🍔', 'difficulty': '⭐️'},
    'immigration': {'display_name':'입국 심사하기', 'emoji': '🏦', 'difficulty': '⭐️'},

    'bank': {'display_name':'은행에서 대출하기', 'emoji': '🏦', 'difficulty': '⭐️⭐️⭐️'},
    'school': {'display_name': '새학기 교실', 'emoji': '🏫', 'difficulty': '⭐️⭐️'},
    'caffe': {'display_name': '커피 주문하기', 'emoji': '☕️', 'difficulty': '⭐️'},
    'massage': {'display_name': '마사지 예약하기', 'emoji': '📞', 'difficulty': '⭐️⭐️'},
}


def go_to_chat():
    st.session_state["curr_page"] = "chat"

def go_to_home():
    st.session_state["curr_page"] = "home"
    st.session_state["roleplay"] = None
    st.session_state["roleplay_info"] = None
    st.session_state.messages = []


def roleplay_start(roleplay):
    st.session_state["roleplay"] = roleplay     # session_state.roleplay에 선택한 roleplay를 저장
    st.session_state["roleplay_info"] = roleplays[roleplay]     # 동일하게 session_state.roleplay_info에 정보들(이름, 이모지, 난이도)저장

    go_to_chat()    # Chat 시작


# Create a function to display each roleplay in the grid
def display_roleplay(roleplay, roleplay_info, key):
    with st.container(border=True):
        st.write(f"**{roleplay_info['display_name']}**")
        st.write(roleplay_info['emoji'])
        # st.progress(int(roleplay_info['progress'].replace('%', '')), "진도")
        st.write(f"난이도 {roleplay_info['difficulty']}")
        st.button("시작", key=f"btn_start_roleplay_{key}", on_click=roleplay_start, kwargs=dict(roleplay=roleplay))     # 버튼 클릭 시 roleplay_start()함수가 실행되고 parameter로 딕셔녀리 형태의 roleplay를 넘긴다



# # 메인 페이지 설정
# session_state의 "curr_page"가 "home"인지 "chat"인지에 따라 다른 페이지를 보여줌

if  st.session_state["curr_page"] == "home":

    st.title("롤플레이")
    cols = st.columns(2)
    for i, (roleplay, roleplay_info) in enumerate(roleplays.items()):   # enumerate()는 iterable 객체를 인자로 받으면 인덱스와 함께 뱉어주는 함수
        with cols[i % 2]: 
            display_roleplay(roleplay, roleplay_info, i)


elif  st.session_state["curr_page"] == "chat":
    client = OpenAI()
    roleplay = st.session_state["roleplay"]
    roleplay_info = roleplays[roleplay]
    st.title(roleplay_info['display_name'])


    ###############################################
    # # Helpers
    # stt기능 백엔드에 요청
    def stt(audio_bytes):
        # audio Bytes로 들어온 음성을 file의 형태로 바꿔줌
        audio_file = io.BytesIO(audio_bytes)
        files = {"audio_file": ("audio.wav", audio_file, "audio/wav")}

        # 백엔드에 Whisper를 이용해 텍스트를 받아오도록 요청
        response = requests.post(transcribe_url, files=files)
        return response.json()

    # Chat기능 백엔드에 요청
    def chat(text, roleplay = None):
        user_turn = {"role": "user", "content": text}
        messages = st.session_state.messages + [user_turn]

        # 백엔드에 Chat와 Roleplay기능을 실행하도록 API 요청
        resp = requests.post(chat_url + f"/{roleplay}", json={"messages": messages})
        assistant_turn = resp.json()
        return assistant_turn['content']


    # 백엔드에서 Goal 목록를 가져오는 API 요청
    @st.cache_data      # cache_data이기 때문에 roleplay가 바뀌지 않는 한 데이터는 유지됨
    def get_goals(roleplay):
        resp = requests.get(f"{host_url}/{roleplay}/goals")
        goals = resp.json()

        return goals


    # 백엔드에서 Goal이 달성되었는지 확인하는 API 요청
    @st.cache_data      # cache_data이기 때문에 roleplay가 바뀌지 않는 한 데이터는 유지됨
    def check_goals(messages, roleplay):
        resp = requests.post(f"{host_url}/{roleplay}/check_goals",
                             json={"messages": messages})
        goals = resp.json()

        return goals


    # Moderation API로 민감한 대화 차단
    def get_policy_viloated(text):
        response = client.moderations.create(input=text)
        output = response.results[0]
        output_dict = output.model_dump()
        flagged_list = []
        for k, v in output_dict['categories'].items():
            if v:
                score = output_dict['category_scores'][k]
                flagged_list.append((k, score))
        return flagged_list
    

    # 오디오 자동 재생
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
   
    ###############################################
    # Conversation
    # Whisper 사용을 위한 임시 파일 생성
    speech_file_path = "tmp_speak.mp3"

    # Goal을 확인하기위해 session_state.goal_list에 Goal 목록을 추가
    if "goal_list" not in st.session_state:
        st.session_state.goal_list = get_goals(roleplay)

    # Goal의 달성 여부를 화면에 표시해주기 위해 session_state.goal_list의 형식을 텍스트 타입으로 변경
    goal_text = "\n".join([f"- {goal}" for goal in st.session_state.goal_list])
    # - 치즈버거 주문하기
    # - 코카콜라 주문하기       이런 식으로
    goal_result = ""


    with st.container(border=True):
        con1 = st.container()   # Chat 기능을 구현할 컨테이너
        con2 = st.container()   # 음성인식 기능을 구현할 컨테이너
    

    user_input = ""
    
    
    # 음성인식 기능 Container
    with con2:
        audio_bytes = audio_recorder("talk", pause_threshold=3.0)
        if audio_bytes == st.session_state.prev_audio_bytes:
            audio_bytes = None
        st.session_state.prev_audio_bytes = audio_bytes
    
        try:
            if audio_bytes:
                with st.spinner("음성 인식중..."):
                    resp_stt = stt(audio_bytes)
                    status = resp_stt['status']
                    if status == 'ok':
                        user_input = resp_stt['text']
        except Exception as e:
            print(e)
            pass
    
    
    # Chat 기능 Container
    with con1:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # 유저의 보이스 입력이 있으면
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
    
            # Moderation API
            flag_list = get_policy_viloated(user_input)
            with st.chat_message("user"):
    
                st.markdown(user_input)
                if flag_list:
                    st.warning(flag_list)

            # AI 메시지 출력
            with st.chat_message("assistant"):

                with st.spinner("생각중..."):
                    bot_output = chat(user_input, roleplay)
    
                with st.spinner("음성 생성중..."):
                    response = client.audio.speech.create(
                      model="tts-1",
                      voice="echo", # alloy, echo, fable, onyx, nova, and shimmer
                      input=bot_output
                    )
                    response.stream_to_file(speech_file_path)
                
                # 달성한 Goal이 있는지 확인
                with st.spinner("목표 체크중..."):
                    goal_result = check_goals(st.session_state.messages, roleplay)

                st.markdown(bot_output)
                autoplay_audio(speech_file_path)

                # 롤플레이 시나리오가 종료되면 '[END]' 라는 글자를 마지막에 넣도록 prompt engineering을 함
                # 즉, 롤플레이가 끝나면
                if "[END]" in bot_output:
                    st.balloons()   # 풍선 날려주고
                    go_to_home()    # home 페이지로 이동

            # session_state.messages에 AI의 응답 추가
            st.session_state.messages.append({"role": "assistant", "content": bot_output})


    # # Goal 목록을 출력해줄 Container
    with st.container(border=True):
        st.markdown("### Goal")
        if goal_result:     # 달성한 Goal이 있으면
            st.markdown("\n".join([f"- {st.session_state.goal_list[g['goal_number']]}: {'✅' if g['accomplished'] else '❌'} " for g in goal_result["goal_list"]]))
            # - 치즈버거 주문하기: ✅
            # - 코카콜라 주문하기: ❌       이런 식으로
        else:
            st.markdown(goal_text)

