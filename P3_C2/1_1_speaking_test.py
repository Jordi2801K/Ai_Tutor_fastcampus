from typing import List
import random
import io
import base64
import time
import pandas as pd
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.schema import StrOutputParser, AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
import os


# # 기본 설정
# 화면 레이아웃 wide로 설정
st.set_page_config(layout="wide")

# 현재 페이지 초기화
if "curr_page" not in st.session_state:
    st.session_state["curr_page"] = "home"
    st.session_state["curr_topic"] = "home"

# 오디오 자동 플레이 함수에서 이이전 오디오 제거를 위한 작업
if "prev_audio_bytes" not in st.session_state:
    st.session_state.prev_audio_bytes = None

# session_state.exam_context 은 각 시험에 대해 필요한 정보들을 담아놓은 session_state. 기본은 빈 딕셔너리
if "exam_context" not in st.session_state:
    st.session_state.exam_context = {}

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


# # 오디오 자동 재생 함수
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


# # 유저 음성 인식하는 함수
def recognize_speech():
    user_input = ""
    # 질문에 답하기
    audio_bytes = audio_recorder("talk", pause_threshold=2.0,)
    if audio_bytes == st.session_state.prev_audio_bytes:
        audio_bytes = None
    st.session_state.prev_audio_bytes = audio_bytes

    try:
        if audio_bytes:
            with st.spinner("음성 인식중..."):
                with open("./tmp_audio.wav", "wb") as f:
                    f.write(audio_bytes)

                with open("./tmp_audio.wav", "rb") as f: 
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        language="en"
                    )
                    user_input = transcript.text
    except Exception as e:
        print(e)
        pass
    return user_input


# speaking 유형에 맞춰 매핑해주기 위한 딕셔너리
speaking_topic_to_topic_info_map = {
    'speaking__listen_and_answer': {'display_name': '듣고 질문에 답하기', 'emoji': '💭'},
    'speaking__express_an_opinion': {'display_name': '의견 말하기', 'emoji': '🗣️'},
    'speaking__debate': {'display_name': '토론하기', 'emoji': '👩‍'},
    'speaking__describe_img': {'display_name': '사진 묘사하기', 'emoji': '🏞️'},
    'speaking__describe_charts': {'display_name': '도표 보고 설명하기', 'emoji': '📊'},
}

# wrting 유형에 맞춰 매핑해주기 위한 딕셔너리
writing_topic_to_topic_info_map = {
    'writing__dictation': {'display_name': '받아쓰기 시험', 'emoji': '✏️'},
    'writing__responding_to_an_email': {'display_name': '이메일 답장하기', 'emoji': '✉️'},
    'writing__summarization': {'display_name': '제시문 내용을 요약하기', 'emoji': '✍️'},
    'writing__writing_opinion': {'display_name': '자신의 의견쓰기', 'emoji': '📝'},
}


# session_state의 curr_page와 curr_topic을 현재 topic으로 바꿔주는 함수
def go_to_topic(topic):
    st.session_state["curr_page"] = topic
    st.session_state["curr_topic"] = topic

# session_state의 curr_page를 'result'로 바꿔주는 함수
def go_to_result():
    st.session_state["curr_page"] = "result"

# 메인화면에 topic들을 띄워주는 함수
def display_topic(topic, topic_info, key):
    with st.container(border=True):
        st.write(f"{topic_info['emoji']} **{topic_info['display_name']}**")
        st.button("시작", key=f"start_{topic}_{key}", on_click=go_to_topic, kwargs=dict(topic=topic))



#### 메인 페이지 ####
# # home 페이지
con = st.container()
if st.session_state["curr_page"] == "home":
    with con:
        st.title("Speaking & Writing 어학 시험")
        tab1, tab2 = st.tabs(["Speaking 시험", "Writing 시험"])

        with tab1:
            cols = st.columns(2)
            for i, (topic, topic_info) in enumerate(speaking_topic_to_topic_info_map.items()):
                with cols[i % 2]:  # This will alternate between the two columns
                    display_topic(topic, topic_info, i)
        
        with tab2:
            cols = st.columns(2)
            for i, (topic, topic_info) in enumerate(writing_topic_to_topic_info_map.items()):
                with cols[i % 2]:  # This will alternate between the two columns
                    display_topic(topic, topic_info, i)


# speaking_and_answer 페이지
elif st.session_state["curr_page"] == "speaking__listen_and_answer":
    topic_info = speaking_topic_to_topic_info_map[st.session_state.curr_topic]  # 현재 topic에 맞는 정보들을 가져옴
    st.title(topic_info['display_name'])

    # csv에 저장된 질문 가져오기
    @st.cache_data
    def load_listen_and_answer_data():
        df = pd.read_csv("./data/1_speaking__listen_and_answer/question_and_audio.csv")
        return df

    # 질문 가져옴
    df = load_listen_and_answer_data()

    # session_state.exam_context에 'question'이 없으면
    if "question" not in st.session_state.exam_context:
        sample = df.sample(n=1).iloc[0]     # 질문 중 하나를 랜덤하게 가져옴

        question = sample["question"]
        audio_file_path = sample["audio_file_path"]

        # 각종 필요한 정보들을 exam_context에 추가
        st.session_state.exam_context["sample"] = sample
        st.session_state.exam_context["question"] = question
        st.session_state.exam_context["audio_file_path"] = audio_file_path


    if st.button("시험 시작"):  # 시험 시작 버튼을 누르면
        st.session_state.exam_context["exam_start"] = True
        st.session_state.exam_context["do_speech"] = True

    # session_state의 exam_context.exam_start 에서 .get()을 사용하여 True or False값을 받아오는데, 기본은 False로 설정되어있음
    if st.session_state.exam_context.get("exam_start", False):  # 기본은 False이나, exam_context.exam_start가 True이면
        if st.session_state.exam_context["do_speech"]:  # exam_context.do_speech가 True이면
            autoplay_audio(st.session_state.exam_context["audio_file_path"])    # 오디오 자동 재생
            st.session_state.exam_context["do_speech"] = False  # exam_context.do_speech를 False로 설정

        if not st.session_state.exam_context["do_speech"]:  # exam_context.do_speech가 False이면
            recognized_text = recognize_speech()    # 유저의 응답을 받음
            st.session_state.exam_context["user_answer"] = recognized_text  # 유저의 응답을 session_state에 추가

        if st.session_state.exam_context.get("user_answer"):    # 유저의 응답이 있으면
            
            # 질문과 유저의 응답을 표시
            with st.container(border=True):
                answer_text = f"""
                - Question: {st.session_state.exam_context["question"]}
                - Your Answer: {st.session_state.exam_context.get("user_answer")}
                """

                st.markdown(answer_text)
            

            # 유저의 응답에 대해 점수를 매기고 평가 결과를 만들어주는 함수
            def get_speaking__listen_and_answer_result(answer_text):
                model = ChatOpenAI(model="gpt-4o-mini")
                class Score(BaseModel):
                    reason: str = Field(description="Question에 대해 Your Answer가 적절한지에 대해 추론하라. 한국어로.")
                    score: int = Field(description="Question에 대해 Your Answer가 적절한지에 대해 0~10점 사이의 점수를 부여하라")
                parser = JsonOutputParser(pydantic_object=Score)
                format_instruction = parser.get_format_instructions()

                human_msg_prompt_template = HumanMessagePromptTemplate.from_template(
                    "{input}\n---\nQuestion에 대해 Your Answer가 적절한지에 대해 추론해서 0~10점 사이의 점수를 부여해줘. 답은 한국어로, 존댓말로 작성해줘. 다음의 포맷에 맞춰 응답해줘.  : {format_instruction}",
                    partial_variables={"format_instruction": format_instruction})

                prompt_template = ChatPromptTemplate.from_messages([human_msg_prompt_template],)
                
                chain = prompt_template | model | parser
                return chain.invoke({"input": answer_text})

            
            # 평가 결과와 점수를 출력
            with st.container(border=True):
                """
                ### 평가 결과
                """

                with st.spinner("채점중..."):
                    result = get_speaking__listen_and_answer_result(answer_text)

                f"""
                {result['reason']}

                #### 점수: {result['score']} / 10

                """


# # express_an_opinion 페이지
elif st.session_state["curr_page"] == "speaking__express_an_opinion":
    topic_info = speaking_topic_to_topic_info_map[st.session_state.curr_topic]  # 현재 topic에 맞는 정보들을 가져옴
    st.title(topic_info['display_name'])

    # csv에 저장된 질문 가져오는 함수
    @st.cache_data
    def load_speaking__express_an_opinion_data():
        df = pd.read_csv("./data/2_speaking__express_an_opinion/question_and_audio.csv")
        return df

    # 질문 가져오기
    df = load_speaking__express_an_opinion_data()

    # session_state.exam_context에 'question'이 없으면
    if "question" not in st.session_state.exam_context:
        sample = df.sample(n=1).iloc[0]     # 질문 중 하나를 랜덤하게 가져옴

        question = sample["question"]
        audio_file_path = sample["audio_file_path"]

        # 각종 필요한 정보들을 exam_context에 추가
        st.session_state.exam_context["sample"] = sample
        st.session_state.exam_context["question"] = question
        st.session_state.exam_context["audio_file_path"] = audio_file_path


    if st.button("시험 시작"):  # 시험 시작 버튼을 누르면
        st.session_state.exam_context["exam_start"] = True
        st.session_state.exam_context["do_speech"] = True

    if st.session_state.exam_context.get("exam_start", False):  # exam_context.exam_start가 True이면
        if st.session_state.exam_context["do_speech"]:
            autoplay_audio(st.session_state.exam_context["audio_file_path"])
            st.session_state.exam_context["do_speech"] = False

        if not st.session_state.exam_context["do_speech"]:  # exam_context.do_speech가 False이면
            recognized_text = recognize_speech()    # 유저의 응답을 받음
            st.session_state.exam_context["user_answer"] = recognized_text  # 유저의 응답을 session_state에 추가

        if st.session_state.exam_context.get("user_answer"):    # 유저의 응답이 있으면

            # 질문과 유저의 응답을 표시
            with st.container(border=True):
                answer_text = f"""
                - Question: {st.session_state.exam_context["question"]}
                - Your Answer: {st.session_state.exam_context.get("user_answer")}
                """

                st.markdown(answer_text)
                
            with st.container(border=True):
                # 유저의 응답에 대해 점수를 매기고 평가 결과를 만들어주는 함수
                def get_speaking__express_opinion_result(answer_text):
                    model = ChatOpenAI(model="gpt-4o-mini")
                    class Score(BaseModel):
                        reason: str = Field(description="Question에 대해 의견을 말하는 시험이다. 의견을 적절히 구조적으로 응답했는지 추론하라. 한국어로.")
                        score: int = Field(description="Question에 대해 Your Answer가 충분히 논리적으로 의견을 표현했는지에 대해 0~10점 사이의 점수를 부여하라.")
                    parser = JsonOutputParser(pydantic_object=Score)
                    format_instruction = parser.get_format_instructions()

                    human_msg_prompt_template = HumanMessagePromptTemplate.from_template(
                        "{input}\n---\nQuestion에 대해 Your Answer가 충분히 논리적으로 의견을 표현했는지에 대해 0~10점 사이의 점수를 부여해줘. 답은 한국어로, 존댓말로 작성해줘. 다음의 포맷에 맞춰 응답해줘.  : {format_instruction}",
                        partial_variables={"format_instruction": format_instruction})

                    prompt_template = ChatPromptTemplate.from_messages([human_msg_prompt_template],)
                    
                    chain = prompt_template | model | parser
                    return chain.invoke({"input": answer_text})

                # 평가 결과와 점수를 출력
                """
                ### 평가 결과
                """

                with st.spinner("채점중..."):
                    result = get_speaking__express_opinion_result(answer_text)

                f"""
                {result['reason']}

                #### 점수: {result['score']} / 10

                """


# # debate 페이지
elif st.session_state["curr_page"] == "speaking__debate":
    topic_info = speaking_topic_to_topic_info_map[st.session_state.curr_topic]
    st.title(topic_info['display_name'])

    con1 = st.container()
    con2 = st.container()

    user_input = ""

    # session_state.exam_context에 'model'이 없으면
    if "model" not in st.session_state.exam_context:
        st.session_state.exam_context["model"] = ChatOpenAI(model="gpt-4o-mini")

    # session_state.exam_context에 'messages'가 없으면
    if "messages" not in st.session_state.exam_context:
        system_prompt = """\
            - 너는 AI 시험 감독이다.
            - user의 영어 실력을 위해 어떠한 주제에 대해 서로 질문과 답을하며 토론한다."""

        # 모델 설정
        model = st.session_state.exam_context["model"]
        # 논란이 될만한 질문(토론 주제) 생성
        question = model.invoke("Create a controversial question for me.").content

        # session_state.exam_context.messages에 System message와 AI message 추가
        st.session_state.exam_context["messages"] = [SystemMessage(content=system_prompt), AIMessage(content=question),]

        # 토론 주제 음성 생성
        speech_file_path = "tmp_speak.mp3"
        response = client.audio.speech.create(
            model="tts-1",
            voice="echo", # alloy, echo, fable, onyx, nova, and shimmer
            input=question
        )
        response.stream_to_file(speech_file_path)
        autoplay_audio(speech_file_path)    # 자동재생

    # messages를 표시하는 Container
    with con1:
        for message in st.session_state.exam_context['messages']:
            # isinstance()는 어떠한 변수가 해당 타입인지 확인하는 함수
            if isinstance(message, SystemMessage):  # message가 System message이면
                continue    # 건너뜀 (표시하지 않음)
            role = 'user' if message.type == 'human' else 'assistant'   # message의 타입이 human이면 role을 user로, 아니면 assatant로 설정
            with st.chat_message(role):     # role에 따라 아이콘을 다르게하여
                st.markdown(message.content)    # message를 출력

    # # 음성 인식을 위한 Container
    # with con2:
    #     user_input = recognize_speech()
    

    # 음성 인식을 위한 Container
    with con2:
        # 화면 크기에 따라 오디오 녹음기 버튼을 중앙에 배치
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.write("")  # 왼쪽 공백
        with col2:
            user_input = recognize_speech()
        with col3:
            st.write("")  # 오른쪽 공백

    # 다시 messages의 Container로 와서
    with con1:
    
        # 대화의 턴이 4번 되면 종료시키기 위해 session_state.exam_context.messages의 길이를 측정
        turn_len = len(st.session_state.exam_context['messages'])
        max_turn_len = 5    # 총 대화의 턴수 4번이지만 session_state.exam_context.messages 안에 System message가 들어있으므로 5로 설정

        if user_input and turn_len < max_turn_len:  # 유저의 입력이 존재하고 대화의 턴이 5번보다 작으면 계속 입력을 받고 대답을 함
            st.session_state.exam_context['messages'].append(HumanMessage(content=user_input))  # 유저의 입력을 session_state에 추가

            # user의 message를 출력
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # assistant의 message를 stream의 형태로 출력
            with st.chat_message("assistant"):
                message_placeholder = st.empty()    # stream 하기 위한 placeholder
                full_response = ""

                model = st.session_state.exam_context["model"]  # 모델 설정

                # session_state.exam_context.messages를 순회하면서 message 출력
                for chunk in model.stream(st.session_state.exam_context['messages']):
                    full_response += (chunk.content or "")
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)

                # 음성 생성
                speech_file_path = "tmp_speak.mp3"
                response = client.audio.speech.create(
                model="tts-1",
                voice="echo", # alloy, echo, fable, onyx, nova, and shimmer
                input=full_response
                )
                response.stream_to_file(speech_file_path)

                autoplay_audio(speech_file_path)    # 자동 재생

            # session_state에 AI message 추가
            st.session_state.exam_context['messages'].append(AIMessage(content=full_response))


        if turn_len >= max_turn_len:    # 대화의 턴이 5번(4번 대화 자체는 4번) 이상 되었으면 입력을 그만 받고 토론에 대한 평가를 진행
            # 유저의 응답에 대해 점수를 매기고 평가 결과를 만들어주는 함수
            def get_speaking__debate_result(conversation):
                model = ChatOpenAI(model="gpt-4o-mini")
                class Score(BaseModel):
                    reason: str = Field(description="주어진 대화에 대해 User가 얼마나 논리적이고 유창하게 영어로 응답하였는지 추론하라. 한국어로.")
                    score: int = Field(description="주어진 대화에서 User의 응답에 대해 유창성과 논리성을 고려하여 0~10점 사이의 점수를 부여하라.")
                parser = JsonOutputParser(pydantic_object=Score)
                format_instruction = parser.get_format_instructions()

                human_msg_prompt_template = HumanMessagePromptTemplate.from_template(
                    "{input}\n---\n주어진 대화에서 User의 응답에 대해 유창성과 논리성을 고려하여 0~10점 사이의 점수를 부여해줘. 답은 한국어로, 존댓말로 작성해줘. 다음의 포맷에 맞춰 응답해줘.  : {format_instruction}",
                    partial_variables={"format_instruction": format_instruction})

                prompt_template = ChatPromptTemplate.from_messages([human_msg_prompt_template],)
                
                chain = prompt_template | model | parser
                return chain.invoke({"input": conversation})

                
            with st.container(border=True):
                """
                ### 평가 결과
                """

                with st.spinner("채점중..."):

                    conversation = ""
                    # session_state.exam_context.messages에 role을 부여하고 채점을 진행
                    for msg in st.session_state.exam_context["messages"]:
                        role = 'User' if msg.type == 'human' else 'AI'
                        conversation += f"{role}: {msg.content}"

                    result = get_speaking__debate_result(conversation)

                # 등급 부여
                grade = ""
                if result['score'] >= 8:
                    grade = "Advanced"
                elif 4 < result['score'] < 8:
                    grade = "Intermediate"
                elif result['score'] <= 4:
                    grade = "Novice"

                grade = f"{grade}, {result['score']} / 10"

                f"""
                {result['reason']}

                #### 등급, 점수: {grade}
                """


# # describe_image 페이지
elif  st.session_state["curr_page"] == "speaking__describe_img":
    topic_info = speaking_topic_to_topic_info_map[st.session_state.curr_topic]
    st.title(topic_info['display_name'])

    # csv에 저장된 이미지와 설명 가져오는 함수
    @st.cache_data
    def load_speaking__describe_img():
        df = pd.read_csv("./data/3_speaking__describe_img/desc_img.csv")
        return df

    # 질문 가져오기
    df = load_speaking__describe_img()

    # session_state.exam_context에 'img_path'가 없으면
    if "img_path" not in st.session_state.exam_context:
        sample = df.sample(n=1).iloc[0]     # 랜덤하게 이미지 하나 가져옴

        img_path = sample["img_path"]   # 이미지 경로 변수로 저장
        desc = sample["desc"]   # 설명 변수로 저장

        # session_state.exam_context에 각 정보들 저장
        st.session_state.exam_context["img_path"] = img_path
        st.session_state.exam_context["desc"] = desc
        st.session_state.exam_context["recognized_text"] = ""

    
    # 화면에 이미지 표시
    st.image(st.session_state.exam_context['img_path'])
    
    # 유저에게 이미지에 대한 묘사(설명)을 응답받음
    with st.container(border=True):
        recognized_text = recognize_speech()
        if recognized_text:     # 음답이 있으면
            st.session_state.exam_context["recognized_text"] = recognized_text  # session_state.exam_context.recognized_text에 추가
        st.write(st.session_state.exam_context["recognized_text"])  # 응답을 화면에 표시

    if st.button("제출하기"):   # 버튼을 누르면
        # 유저의 응답과 정답을 비교하는 함수
        def get_speaking__describe_img(user_input, ref):
            model = ChatOpenAI(model="gpt-4o-mini", temperature=0.8) # CoT 는 다양한 샘플을 만들어야하기 때문에 temperature를 올려야함
            
            class Evaluation(BaseModel):
                score: int = Field(description="사진 묘사하기 표현 표현 점수. 0~10점")
                feedback: str = Field(description="사진 묘사하기를 더 잘 할 수 있도록하는 자세한 피드백. Markdown형식, 한국어로.")
            
            parser = JsonOutputParser(pydantic_object=Evaluation)
            format_instructions = parser.get_format_instructions()

            human_prompt_template = HumanMessagePromptTemplate.from_template(
                            "사진 묘사하기 영어 시험이야. 사용자의 응답을 Reference와 비교하여 묘사에서 부족한 점이 있는지 평가해줘. 부족한 점이 많거나 응답이 너무 짧거나 단순하면 확실하게 낮은 점수를 부여하고 평가도 그에 맞게 해줘. 부족한 점이 있다면 어떤점이 부족한지, 설명에 추가되면 좋을만한 것들을 설명해줘. 평가와 설명은 존댓말, 한국어로 해줘.\n사용자의 응답: {input}\Reference: {ref}\n다음 포멧에 맞춰서 응답해줘 : {format_instructions}",
                                        partial_variables={"format_instructions": format_instructions})

            prompt = ChatPromptTemplate.from_messages([human_prompt_template,])
            eval_chain = prompt | model | parser

            result = eval_chain.invoke({"input": user_input, "ref": ref})
            return result


        st.title("결과 & 피드백- 사진 묘사하기")

        with st.spinner("결과 & 피드백 생성중..."):
            # 유저의 응답과 정답을 비교하여 평가 진행
            result = get_speaking__describe_img(user_input=recognized_text,
                                                ref=st.session_state.exam_context['desc'])

            grade = ""
            if result['score'] >= 8:
                grade = "고급"
            elif 4 < result['score'] < 8:
                grade = "중급"
            elif result['score'] <= 4:
                grade = "초급"

            grade = f"{grade} ({result['score']} / 10)"

            f"""
            당신이 제공한 답변은 스피킹 사진 묘사 시험에서 `{grade}` 수준으로 시작하기 좋은 접근입니다.
            
            여기 몇가지 피드백을 드립니다.

            {result['feedback']}
            """


# # describe_charts 페이지
elif  st.session_state["curr_page"] == "speaking__describe_charts":
    topic_info = speaking_topic_to_topic_info_map[st.session_state.curr_topic]
    st.title(topic_info['display_name'])

    # csv에 저장된 도표와 설명 가져오는 함수
    @st.cache_data
    def load_speaking__describe_charts():
        df = pd.read_csv("./data/4_speaking__describe_charts/desc_charts.csv")
        return df

    # 질문 가져오기
    df = load_speaking__describe_charts()

    # session_state.exam_context에 'img_path'가 없으면
    if "img_path" not in st.session_state.exam_context:
        sample = df.sample(n=1).iloc[0]     # 도표 랜덤하게 하나 가져옴

        img_path = sample["img_path"]   # 도표 경로
        desc = sample["desc"]   # 도표에 대한 설명

        # session_state.exam_context에 각 정보들 저장
        st.session_state.exam_context["img_path"] = img_path
        st.session_state.exam_context["desc"] = desc
        st.session_state.exam_context["recognized_text"] = ""

    # 화면에 도표 출력
    st.image(st.session_state.exam_context['img_path'])
    
    # 유저에게 도표에 대한 설명을 응답받음
    with st.container(border=True):
        recognized_text = recognize_speech()
        if recognized_text:     # 응답이 있으면
            st.session_state.exam_context["recognized_text"] = recognized_text  # session_state.exam_context.recognized_text에 추가
        st.write(st.session_state.exam_context["recognized_text"])  # 응답을 하면에 표시

    if st.button("제출하기"):   # 버튼 누르면
        # 유저의 응답과 정답을 비교하는 함수
        def get_speaking__describe_img(user_input, ref):
            model = ChatOpenAI(model="gpt-4o-mini", temperature=0.8) # CoT 는 다양한 샘플을 만들어야하기 때문에 temperature를 올려야함
            class Evaluation(BaseModel):
                score: int = Field(description="도표 보고 발표하기 점수. 0~10점")
                feedback: str = Field(description="도표 보고 발표하기 점수. Markdown형식, 한국어로.")
            parser = JsonOutputParser(pydantic_object=Evaluation)
            format_instructions = parser.get_format_instructions()

            human_prompt_template = HumanMessagePromptTemplate.from_template(
                            "도표보고 설명하기 영어 시험이야. 사용자의 응답을 Reference와 비교하여 올바르게 도표를 설명했는지 평가해줘. 정확하지 않거나 응답이 너무 짧거나 단순하면 확실하게 낮은 점수를 부여하고 평가도 그에 맞게 해줘. 정확하지 않다면 어떤점이 정확하지 않은지, 추가로 설명하면 좋을만한 것들을 설명해줘. 평가와 설명은 존댓맛, 한국어로 해줘.\n사용자의 응답: {input}\Reference: {ref}\n다음 포맷에 맞춰서 응답해줘 : {format_instructions}",
                                        partial_variables={"format_instructions": format_instructions})

            prompt = ChatPromptTemplate.from_messages([human_prompt_template,])
            eval_chain = prompt | model | parser

            result = eval_chain.invoke({"input": user_input, "ref": ref})
            return result


        st.title("결과 & 피드백- 도표 보고 설명하기")

        with st.spinner("결과 & 피드백 생성중..."):

            result = get_speaking__describe_img(user_input=recognized_text,
                                                ref=st.session_state.exam_context['desc'])
        
            grade = ""
            if result['score'] >= 8:
                grade = "고급"
            elif 4 < result['score'] < 8:
                grade = "중급"
            elif result['score'] <= 4:
                grade = "초급"

            grade = f"{grade} ({result['score']} / 10)"

            f"""
            당신이 제공한 답변은 스피킹 사진 묘사 시험에서 `{grade}` 수준으로 시작하기 좋은 접근입니다.
            
            여기 몇가지 피드백을 드립니다.

            {result['feedback']}
            """


# # writing_dictation 페이지
elif  st.session_state["curr_page"] == "writing__dictation":
    topic_info = writing_topic_to_topic_info_map[st.session_state.curr_topic]
    st.title(topic_info['display_name'])

    # csv에 저장된 문장과 음성 가져오는 함수
    @st.cache_data
    def load_writing__dictation():
        df = pd.read_csv("./data/5_writing__dictation/sent_and_audio.csv")
        return df

    # 문장, 음성 가져오기
    df = load_writing__dictation()

    # session_state.exam_context에 'sentence'가 없으면
    if "sentence" not in st.session_state.exam_context:
        sample = df.sample(n=1).iloc[0]     # 문장과 음성을 랜덤하게 가져오고

        sentence = sample["sentence"]
        audio_file_path = sample["audio_file_path"]

        # session_state.exam_context에 각 정보들 저장
        st.session_state.exam_context["sample"] = sample
        st.session_state.exam_context["sentence"] = sentence
        st.session_state.exam_context["audio_file_path"] = audio_file_path


    if st.button("시험 시작"):  # 버튼 누르면
        st.session_state.exam_context["exam_start"] = True
        st.session_state.exam_context["do_speech"] = True

    if st.session_state.exam_context.get("exam_start", False):  # 기본은 False이지만, exam_start가 True이면
        if st.session_state.exam_context["do_speech"]:  # do_speech가 True이면
            autoplay_audio(st.session_state.exam_context["audio_file_path"])    # 문장의 음성 재생
            st.session_state.exam_context["do_speech"] = False  # do_speech를 False로 설정


        # 유저의 받아쓰기 입력을 받음
        user_answer = st.text_input("user answer")
        if user_answer: # 유저의 입력이 있으면
            st.session_state.exam_context["user_answer"] = user_answer  # session_state.exam_context.user_answer에 추가

        # session_state.exam_context.user_answer가 있으면 == 유저의 받아쓰기 입력이 있으면
        if st.session_state.exam_context.get("user_answer"):
            # 받아쓰기의 정답과 유저의 입력을 출력
            with st.container(border=True):
                answer_text = f"""
                - Original sentence: {st.session_state.exam_context["sentence"]}
                - Your Answer: {st.session_state.exam_context.get("user_answer")}
                """
                st.markdown(answer_text)
                
            # 유저의 입력과 정답을 비교하는 함수
            def get_writing__dictation_result(answer_text, ref):
                model = ChatOpenAI(model="gpt-4o-mini")
                class Evaluation(BaseModel):
                    reason: str = Field(description="받아쓰기 평가를 위한 추론")
                    score: int = Field(description="받아쓰기 점수. 0~10점")
                parser = JsonOutputParser(pydantic_object=Evaluation)
                format_instruction = parser.get_format_instructions()

                human_prompt_template = HumanMessagePromptTemplate.from_template(
                                            "영어 받아쓰기 시험이야. 사용자의 응답을 Reference와 비교하여 얼마나 정확한지 분석하고 평가해줘. 설명은 존댓말, 한국어로 작성해줘.\n사용자의 응답: {input}\Reference: {ref}\n다음 포맷에 맞춰서 응답해줘 : {format_instructions}",
                                            partial_variables={"format_instructions": format_instruction})

                prompt_template = ChatPromptTemplate.from_messages([human_prompt_template,])

                chain = prompt_template | model | parser
                return chain.invoke({"input": answer_text, "ref": ref})
                
            with st.container(border=True):
                """
                ### 평가 결과
                """

                with st.spinner("채점중..."):
                    # AI가 채점한 결과
                    model_result = get_writing__dictation_result(answer_text, st.session_state.exam_context['sentence'])
                    model_score = model_result['score']

                f"""
                ### 평가 결과
                {model_result['reason']}
                점수: {model_score} / 10
                """