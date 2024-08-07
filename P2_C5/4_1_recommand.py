import json
import pandas as pd
import streamlit as st

# Streamlit 앱 레이아웃 설정
st.set_page_config(page_title="오늘의 영어 표현", layout="wide")

# 앱 제목 및 설명
st.title('오늘의 영어 단어 추천',)


# cache되어있기 때문에 같은 데이터가 들어있다면 다시 실행되지 않음
@st.cache_data
def load_data():
    # 엑셀 파일을 불러들임
    df = pd.read_excel("./words_usage.xlsx")
    # 문자열 타입으로 저장되어있는 usage를 json.loads()를 통해서 딕셔너리 형태로 만듬
    df["usage"] = df.apply(lambda row: json.loads(row["usage"]), axis=1)
    return df


# 엑셀 파일에 있는 오늘의 단어 추천 목록을 불러옴
df = load_data()

for i, sample in df.iterrows():
    with st.container(border=True):
        st.subheader(f"{sample['imoj']} {sample['word']}")

        # situation 의 영단어의 뜻 
        st.markdown(sample["meaning"])

        with st.container(border=True):
            """사용법"""

            for i, row in enumerate(sample["usage"]["conversation"]):
                avatar = '🧑' if i % 2 == 0 else '👩🏼'
                with st.chat_message(avatar):
                    st.markdown(row['content'])
