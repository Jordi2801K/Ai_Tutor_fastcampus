import os
from typing import List
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser
import langchain_core.pydantic_v1 as pyd1

api_key = os.getenv("OPENAI_API_KEY")

# Streamlit 페이지 설정
st.set_page_config(page_title="AI English Assistant", layout="wide")


# # 문법평가 chain을 만들기 위한 Class
class Grammar(pyd1.BaseModel):
    reason_list: List[str] = pyd1.Field(description="문법적으로 틀린 이유들이 들어있고, 만약 틀린 것이 없으면 빈 리스트로 남아있음. 답변은 한국어로 작성되어있으며, 문법 오류 하나 당 이유는 한개만 설명함.")

# 문법평가를 진행하는 함수
def build_grammar_analysis_chain(model):
    # parser 설정
    parser = JsonOutputParser(pydantic_object=Grammar)
    # 문법검사 후 출력 형식을 parser의 format_instruction을 따라서 출력할 수 있도록 format_instruction 설정
    format_instruction = parser.get_format_instructions()

    human_msg_prompt_template = HumanMessagePromptTemplate.from_template(
        """{input}\n--\n위 영어 텍스트에 문법적으로 틀린 점이 있는지 꼼꼼하게 분석하고 틀린 부분을 찾아서 나열해줘. 문법오류 하나 당 이유는 하나만 설명해줘.\
        틀린 점이 있다면 문법적으로 어떤 부분이 틀린건지 정확하게 표시해주고 자세한 설명을 함께 해줘. 단답식으로 대답하는 것이 아닌 존댓말로 설명해줘.\
        value값은 한국어로 작성해주고, 형식은 아래의 포맷을 따라: {format_instruction}""",
        partial_variables={"format_instruction": format_instruction})
    
    # 최종 prompt template
    prompt_template = ChatPromptTemplate.from_messages([human_msg_prompt_template])

    # Chain 생성
    chain = prompt_template | model | parser
    return chain



# # Proficiency를 검사하는 chain을 만들기 위한 Class
class EnglishProficiencyScore(pyd1.BaseModel):
    vocabulary_score: int = pyd1.Field(description="어휘, 단어의 적절성을 0 ~ 10점 사이의 점수로 표현함")
    coherence_score: int = pyd1.Field(description="일관성을 0 ~ 10점 사이의 점수로 표현함")
    clarity_score: int = pyd1.Field(description="명확성을 0 ~ 10점 사이의 점수로 표현함")
    final_score: int = pyd1.Field(description="총점을 0 ~ 10점 사이의 점수로 표현함")

# Proficiency를 검사하는 함수
def build_proficiency_scoring_chain(model):
    parser = JsonOutputParser(pydantic_object=EnglishProficiencyScore)
    format_instruction = parser.get_format_instructions()

    human_msg_prompt_template = HumanMessagePromptTemplate.from_template(
        # 문법, 어휘, 일관성 등을 고려하여 위 영어 텍스트의 전반적인 영어 능력을 평가해줘. 라는 뜻
        "{input}\n--\nEvaluate the overall English proficiency of the above text. Consider grammar, vocabulary, coherence, etc. Follow the format: {format_instruction}",
        partial_variables={"format_instruction": format_instruction}
    )

    # 최종 prompt template
    prompt_template = ChatPromptTemplate.from_messages([human_msg_prompt_template])

    # Chain 생성
    chain = prompt_template | model | parser
    return chain



# # 맞는 문장을 만들어줄 chain을 만들기 위한 Class
class Correction(pyd1.BaseModel):
    reason: str = pyd1.Field(description="원래의 영어 문장이 어색하거나 잘못된 이유들이 들어있고, 한국어로 작성되어있음.")
    correct_sentence: str = pyd1.Field(description="교정된 문장.")

# 맞는 문장을 만들어주는 함수
def build_correction_chain(model):
    # parser 설정
    parser = JsonOutputParser(pydantic_object=Correction)
    format_instruction = parser.get_format_instructions()

    human_msg_prompt_template = HumanMessagePromptTemplate.from_template(
        """{input}\n--\n위 영어 텍스트에 문법적으로 틀린 점이 있는지 꼼꼼하게 분석하고, 틀린 점이 있다면 문법적으로 어떤 부분이 틀린건지 정확하게 표시해주고 자세한 설명을 함께 해줘.\
        단답식으로 대답하는 것이 아닌 존댓말로 설명해줘. 형식은 아래의 포맷을 따라: {format_instruction}""",
        partial_variables={"format_instruction": format_instruction})
    
    # 최종 prompt template
    prompt_template = ChatPromptTemplate.from_messages([human_msg_prompt_template])

    # Chain 생성
    chain = prompt_template | model | parser
    return chain



# # 위에서 만든 Chain들을 필요할 때 마다 사용할 수 있도록 session_state에 저장
if "model" not in st.session_state:
    model = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
    st.session_state.model = model

if "grammar_analysis_chain" not in st.session_state:
    st.session_state.grammar_analysis_chain = build_grammar_analysis_chain(st.session_state.model)

if "proficiency_scoring_chain" not in st.session_state:
    st.session_state.proficiency_analysis_chain = build_proficiency_scoring_chain(st.session_state.model)

if "correction_chain" not in st.session_state:
    st.session_state.correction_chain = build_correction_chain(st.session_state.model)




# 메인 섹션
st.title("AI 문장 교정 서비스")

# 사용자 입력을 위한 텍스트 에어리어
user_input = st.text_area("Enter your text here:")

grammar_analysis = None
proficiency_analysis = None
proficiency_result = None


start_button = st.button("분석하기")

if start_button :

    # # 문법 분석
    st.subheader("문법")
    # 문법 분석 결과를 띄워줄 Container
    with st.container(border=True):
        with st.spinner('분석중...'):
            # 문법 검사 실행
            grammar_analysis = st.session_state.grammar_analysis_chain.invoke({"input": user_input})
        # 문법검사 결과 표시
        print(grammar_analysis)

        # 문법검사에서 발견된 문제 표시
        reason_list = grammar_analysis["reason_list"]   # 문법검사 시 발견된 문제들
        reasons = "\n".join([f"- {reason}" for reason in reason_list])
        st.markdown(reasons)


    # # 문법 분석 후 문장 교정
    st.subheader("교정")
    # 문장 교정 결과를 띄워줄 Container
    with st.container(border=True):
        with st.spinner('교정중...'):
            # 교정된 문장 받아오기
            correction = st.session_state.correction_chain.invoke({"input": user_input})

        # 문장이 왜 이렇게 교정되었는지에 대한 이유와 교정된 문장 출력
        st.markdown(correction["reason"])
        st.subheader("교정된 문장")
        st.markdown(correction["correct_sentence"])



# 평가 결과를 표시해줄 사이드바
with st.sidebar:

    st.title("AI Assistant")

    # Overall은 맨 밑에서 계산되지만 Overall을 가장 위에 표시해주기 위해 미리 선언한 Container
    overall_con = st.container(border=True)
    
    with st.container(border=True):
        """
        **Correctness**
        """
        if user_input and grammar_analysis:     # 문장이 입력되고 문법 검사 결과가 있으면
            with st.spinner('Analyzing correctness...'):
                n_wrong = len(grammar_analysis['reason_list'])      # 틀린 갯수를 확인

            if n_wrong: # 틀린 부분이 있으면 == n_wrong이 0이 아니면
                st.error(f"{n_wrong} alert")    # 개수 표시해줌
            else:       # 틀린 부분이 없으면 == n_wrong이 1이상이면
                st.success("All correct!")
    

    if user_input and start_button:  # 문장이 입력되면
        with st.spinner("Analyzing..."):
            # Proficiency 검사 실행
            proficiency_analysis = st.session_state.proficiency_analysis_chain.invoke({"input": user_input})

    # # Proficiency 검사 결과 표시
    with st.container(border=True):
        """
        **Coherence**
        """

        if user_input and proficiency_analysis: # 문장이 입력되고 Proficiency 검사 결과가 존재하면
            score = proficiency_analysis["coherence_score"]   # 점수로 표시

            score_text = f"{score}/10"  # 0 ~ 10점 사이로 점수를 매김
            # 점수 간격마다 색깔을 다르게 표시함
            if score >= 8:
                st.success(score_text)
            elif 4<= score < 8:
                st.warning(score_text)
            else:
                st.error(score_text)


    # # Clarity 검사 결과 표시
    with st.container(border=True):
        """
        **Clarity**
        """

        if user_input and proficiency_analysis: # 문장이 입력되고 Proficiency 검사 결과가 존재하면
            score = proficiency_analysis["clarity_score"] # 점수로 표시
            
            # score의 최대, 최솟값 설정
            score = min(score, 3)
            score = max(score, 0)

            # 0 ~ 3까지 4가지 점수에서 해당하는 Clarity를 표시
            score_to_text_map = {
                0: "unclear",
                1: "Somewhat unclear",
                2: "clear",
                3: "very clear"
            }
            text = score_to_text_map[score]

            # 점수 간격마다 색깔을 다르게 표시함
            if score == 3:
                st.success(text)
            elif score == 2:
                st.info(text)
            elif score == 1:
                st.warning(text)
            elif score == 0:
                st.error(text)


    # # Vocabulary 검사 결과 표시
    with st.container(border=True):
        """
        **Vocabulary**
        """

        if user_input and proficiency_analysis: # 문장이 입력되고 Proficiency 검사 결과가 존재하면
            score = proficiency_analysis["vocabulary_score"]  # 점수로 표시하고

            score_text = f"{score}/10"  # 0 ~ 10점 사이로 점수를 매기고
            # 점수 간격마다 색깔을 다르게 표시함
            if score >= 8:
                st.success(score_text)
            elif 4<= score < 8:
                st.warning(score_text)
            else:
                st.error(score_text)


    # # 가장 나중에 검사하지만 가장 위에 표시될 Overall 검사 결과
    with overall_con:
        """
        **Overall score**
        """

        if user_input and proficiency_analysis: # 문장이 입력되고 Proficiency 검사 결과가 존재하면
            score = proficiency_analysis["final_score"]   # 점수로 표시하고

            score_text = f"{score}/10"  # 0 ~ 10점 사이로 점수를 매기고
            # 점수 간격마다 색깔을 다르게 표시함
            if score >= 8:
                st.success(score_text)
            elif 4<= score < 8:
                st.warning(score_text)
            else:
                st.error(score_text)