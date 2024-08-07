from typing import List
from fastapi import FastAPI, UploadFile, File
from openai.resources.beta.threads import messages
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import langchain_core.pydantic_v1 as pyd1   # py1은 langchain의 pydantic
import pydantic as pyd2     # py2는 FastAPI의 pydantic
from openai import OpenAI


client = OpenAI()
model = ChatOpenAI(model="gpt-4o-mini")
app = FastAPI()


# # FastAPI에서 입력과 출력의 프로토콜을 지정함
# Turn의 구조
class Turn(pyd2.BaseModel):
    role: str = pyd2.Field(description="role")
    content: str = pyd2.Field(description="content")

# 메시지를 받을 형식
class Messages(pyd2.BaseModel):     # json 파일같은 형태
    messages: List[Turn] = pyd2.Field(description="message", default=[])
    # messages라는 key가 있고 그 안에 Turn이라는 구조로 들어있음

# # 위의 내용을 시각화하면...
# {"messages": [{"role": role, "content": content}]}
# 이러한 내용으로 메시지가 저장됨


# parser에 사용할 Field를 정의
class Goal(pyd1.BaseModel):
    goal: str = pyd1.Field(description="goal.")
    goal_number: int = pyd1.Field(description="goal number.")
    accomplished: bool = pyd1.Field(description="true if goal is accomplished else false.")

# Goal 클래스에서 정의된 Field를 리스트타입으로 변경
class Goals(pyd1.BaseModel):
    goal_list: List[Goal] = pyd1.Field(default=[])
    # {"goal_list": [{"goal": "치즈버거 주문하기", "goal_number": 0, "accomplished": True}, ]}    goal_list 변수는 이런 식으로 작성됨


parser = JsonOutputParser(pydantic_object=Goals)
format_instruction = parser.get_format_instructions()


# # Goal을 달성했는지 확인하는 API
def detect_goal_completion(messages, roleplay):
    global parser, format_instruction

    # messages를 Conversation형식으로 바꿔줌
    conversation ="\n".join([ f"{msg['role']}: {msg['content']}" for msg in messages])
    # "user": "~~~"
    # "assisatant": "~~~"   이런 형식으로

    # Roleplay마다 각기 다른 Goals들이 존재하기에 해당 Roleplay에 맞는 Goal을 들고옴
    goal_list = roleplay_to_goal_map[roleplay]
    goals = "\n".join([f"- Goal Number {i}: {goal} " for i, goal in enumerate(goal_list)])
    # - Goal Number 0: 치즈버거 주문하기
    # - Goal Number 1: 코카콜라 주문하기    # 이런 형식으로

    # langchain의 prompt template 만들기
    prompt_template = """
        # 대화
        {conversation}
        ---
        # 유저의 목표
        {goals}
        ---
        위 대화를 보고 유저가 goal들을 달성했는지 확인해서 아래 포맷으로 응답해.
        {format_instruction}
    """

    chat_prompt_template = ChatPromptTemplate.from_messages([("user", prompt_template)])
    goal_check_chain = chat_prompt_template | model | parser

    # langchain을 통해 Goal달성했는지 확인
    outputs = goal_check_chain.invoke({"conversation": conversation,
                                       "goals": goals,
                                       "format_instruction": format_instruction})
    return outputs



# role에 따라 langchain에 각기 다른 메시지를 쓰도록 맞는 class를 매핑
type_to_msg_class_map = {
        "system":  SystemMessage,
        "user":  HumanMessage,
        "assistant":  AIMessage,
        }

# # OpenAI API를 사용하여 실질적으로 AI와 대화를 하는 기능
def chat(messages):
    messages_lc = []
    for msg in messages:    # {"messages": [{"role": role, "content": content}]}
        msg_class = type_to_msg_class_map[msg["role"]]
        msg_lc = msg_class(content=msg["content"])

        messages_lc.append(msg_lc)  # 순회를 하면서 messages_lc에 메시지들을 담고
        
    resp = model.invoke(messages_lc)    # 메시지에대한 응답을 받아서
    return {"role": "assistant", "content": resp.content}   # return해줌




# role에 따라 각기 다른 system prompt를 매핑하는 딕셔너리
roleplay_to_system_prompt_map = {
        "hamburger": """\
- 너는 햄버거 가게의 직원이다.
- 너는 영어로 응답한다.
- 아래의 단계로 질문을 한다.
1. 주문 할 메뉴 묻기
2. 더 주문 할 것이 없는지 묻기
3. 여기서 먹을지 가져가서 먹을지 질문한다.
4. 카드로 계산할지 현금으로 계산할지 질문한다.
5. 주문이 완료되면 인사를 하고 [END] 라고 이야기한다.\
""",
        "immigration": """\
- 너는 출입국 사무소의 직원이다.
- 너는 영어로 응답한다.
- 아래의 단계로 질문을 한다.
1. 이름 묻기
2. 여행의 목적 묻기
3. 몇일간 체류하는지 묻기
4. 어떤 호텔에서 체류하는지 묻기
5. 모든 질문에 답이 끝났으면 [END] 라고 이야기한다.\
"""
        }

# role에 따라 각기 다른 goal들을 매핑
roleplay_to_goal_map = {
        "hamburger": ["치즈버거 주문하기",
                      "코카콜라 주문하기"],
        "immigration": ["NBA 경기 보러 왔다고 말하기",
                        "5일 동안 체류한다고 말하기"]
        }

# # Chat기능을 동작시키는 API
# Chat을 시작하면 Chat기능을 실행
@app.post("/chat", response_model=Turn)
def post_chat(messages: Messages):  # messages: Messages는 pydantic으로 정해진 프로토콜을 따라 형식을 맞춰줌
    messages_dict = messages.model_dump()   # {"messages": [{"role": role, "content": content}]}
    print(messages_dict)
    resp = chat(messages=messages_dict['messages'])     # "role"과 "content"를 인자로 갖는 chat()함수 실행

    return resp


# # Roleplay기능을 동작시키는 API
@app.post("/chat/{roleplay}", response_model=Turn)
def post_chat_role_play(messages: Messages, roleplay: str):
    messages_dict = messages.model_dump()

    # 해당 롤플레이를 위한 system prompt 가져오기
    system_prompt = roleplay_to_system_prompt_map[roleplay]
    msgs = messages_dict['messages']

    # system prompt를 추가하여 Chat을 동작시킴
    msgs = [{"role": "system", "content": system_prompt}] + msgs 
    resp = chat(messages=msgs)

    return resp


# Goal 목록을 전달해주는 API
@app.get("/{roleplay}/goals")
def get_roleplay_goals(roleplay: str):
    return roleplay_to_goal_map[roleplay]


# Goal의 달성여부를 확인해주는 API
@app.post("/{roleplay}/check_goals")
def post_roleplay_check_goal(messages: Messages, roleplay: str):
    messages_dict = messages.model_dump()
    messages = messages_dict['messages']
    goal_completion = detect_goal_completion(messages, roleplay)
    return goal_completion

# # Streamlit에서 업로드된 유저의 음성 파일을 텍스트로 바꿔줌
@app.post("/transcribe")
def transcribe_audio(audio_file: UploadFile = File(...)):
    try:
        # Streamlit에서 받아온 파일을 저장한 후
        file_name = "tmp_audio_file.wav"
        with open(file_name, "wb") as f:
            f.write(audio_file.file.read())
        
        # 해당 파일을 읽어들이면서 Whisper API를 통해 텍스트로 바꿈
        with open(file_name, "rb") as f:
            transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="en",
                )
        text = transcript.text  # Whisper를 통해 얻은 텍스트
    except Exception as e:
        print(e)
        text = f"음성인식에서 실패했습니다. {e}"
        return {"status": "fail", "text": text}
    print(f"input: {text}")

    return {"status": "ok", "text": text}

