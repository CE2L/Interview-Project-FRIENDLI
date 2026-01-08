import streamlit as st
import snowflake.connector
import pandas as pd
import altair as alt
import re

import os

SNOWFLAKE_CONFIG={
    "user":os.environ.get("SNOWFLAKE_USER"),
    "password":os.environ.get("SNOWFLAKE_PASSWORD"),
    "account":os.environ.get("SNOWFLAKE_ACCOUNT"),
    "warehouse":os.environ.get("SNOWFLAKE_WAREHOUSE"),
    "database":os.environ.get("SNOWFLAKE_DATABASE"),
    "schema":os.environ.get("SNOWFLAKE_SCHEMA"),
}


def load_metrics():
    conn=snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cursor=conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ANALYSIS_METRICS (
                CANDIDATE_NAME STRING, AI_MODEL STRING, AI_SUMMARY STRING,
                HUMAN_NOTE STRING, QUALITY_SCORE FLOAT, LATENCY_SEC FLOAT,
                INTERVIEW_SCORE INT, HIRING_DECISION STRING, CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            )
            """
        )
        cursor.execute("SELECT * FROM ANALYSIS_METRICS ORDER BY CREATED_AT DESC")
        cols=[col[0] for col in cursor.description]
        return pd.DataFrame(cursor.fetchall(),columns=cols)
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()

def clean_text(text):
    if not text:
        return ""
    t=str(text)
    t=t.replace("\r\n","\n").replace("\r","\n")
    t=re.sub(r"\*\*", "", t)
    t=re.sub(r"^[\-\*\u2022]\s*", "", t, flags=re.MULTILINE)
    t=re.sub(r"\n[\-\*\u2022]\s*", "\n", t)
    t=re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def parse_ai_summary(text):
    t=clean_text(text)
    if not t:
        return {"요약":"","장점":"","단점":""}

    m1=re.search(r"1\.\s*요약\s*:\s*(.*?)(?=\n2\.\s*장점\s*:|\Z)", t, re.DOTALL)
    m2=re.search(r"2\.\s*장점\s*:\s*(.*?)(?=\n3\.\s*단점\s*:|\Z)", t, re.DOTALL)
    m3=re.search(r"3\.\s*단점\s*:\s*(.*?)(?=\n4\.\s*점수\s*:|\Z)", t, re.DOTALL)

    summary=(m1.group(1).strip() if m1 else "").strip()
    pros=(m2.group(1).strip() if m2 else "").strip()
    cons=(m3.group(1).strip() if m3 else "").strip()

    return {"요약":summary,"장점":pros,"단점":cons}

def build_korean_report(df,primary_model="GEMINI"):
    base=df[df["AI_MODEL"]==primary_model].copy()
    if base.empty:
        base=df.copy()

    base=base.sort_values("INTERVIEW_SCORE",ascending=False)
    top_row=base.iloc[0]
    top_name=str(top_row["CANDIDATE_NAME"])
    top_score=int(top_row["INTERVIEW_SCORE"])
    top_decision=str(top_row["HIRING_DECISION"])

    top_sections=parse_ai_summary(top_row.get("AI_SUMMARY",""))

    others=base[base["CANDIDATE_NAME"]!=top_name].copy()

    intro=(
        f"후보자 평가 결과를 요약한 최종 결과입니다. "
        f"평가 기준에 따라 후보자들의 강점과 리스크를 비교했으며, "
        f"가장 높은 점수를 받은 {top_name}을(를) 최종 채용 추천 대상으로 선정했습니다. "
        f"다른 후보들은 역량이 충분함에도 불구하고, 현재 포지션에서 요구하는 핵심 역량 대비 "
        f"상대적으로 보완이 필요한 영역이 확인되어 보류/불합격으로 정리했습니다."
    )

    hire_title=f"{top_name} ({top_score}점): {top_decision}"
    hire_body=(
        f"{top_name}은(는) 이번 포지션의 핵심 요구사항과 가장 직접적으로 맞닿아 있습니다.\n\n"
        f"요약:\n{top_sections['요약'] or '주요 문제를 구조적으로 정의하고 해결 방향을 제시하는 역량이 돋보였습니다.'}\n\n"
        f"장점:\n{top_sections['장점'] or '업무 임팩트를 만드는 실행력과 문제 해결력이 확인되었습니다.'}\n\n"
        f"단점:\n{top_sections['단점'] or '실무 적용 과정에서 추가 검증이 필요한 영역이 일부 존재합니다.'}\n\n"
        f"그럼에도 불구하고, 강점이 직무 성공에 더 결정적으로 기여하며 "
        f"단점은 온보딩/협업 프로세스로 충분히 보완 가능한 범위라고 판단됩니다."
    )

    rej_blocks=[]
    for _,row in others.iterrows():
        name=str(row["CANDIDATE_NAME"])
        score=int(row["INTERVIEW_SCORE"])
        sections=parse_ai_summary(row.get("AI_SUMMARY",""))

        block=(
            f"{name} ({score}점): REJECT\n\n"
            f"{name}은(는) 기본 역량이 탄탄하고 실무 기여 가능성이 있으나, "
            f"이번 포지션에서 가장 중요한 핵심 역량 대비 우선순위가 낮게 평가되었습니다.\n\n"
            f"요약:\n{sections['요약'] or '역량은 충분하지만 포지션 핏에서 차이가 있었습니다.'}\n\n"
            f"강점:\n{sections['장점'] or '일정 수준 이상의 강점이 확인되었습니다.'}\n\n"
            f"보완 필요:\n{sections['단점'] or '핵심 요구사항과의 간극이 존재합니다.'}\n\n"
            f"종합적으로, {top_name} 대비 직무 적합성과 즉시 전력감에서 차이가 확인되어 "
            f"이번 라운드에서는 불합격으로 결정합니다."
        )
        rej_blocks.append(block)

    return intro,hire_title,hire_body,rej_blocks

st.set_page_config(page_title="AI 채용 관리자", layout="wide")
st.title("AI 채용 관리자")
st.markdown("자동 후보 평가 & 채용 결정")

try:
    df=load_metrics()

    st.subheader("최종 채용 보고서")

    if df.empty:
        st.warning("분석 데이터 없음. docker run --rm interview-analysis python pipeline.py 실행")
    else:
        intro,hire_title,hire_body,rej_blocks=build_korean_report(df,primary_model="GEMINI")

        st.markdown("## Interview Result Summary")
        st.write(intro)

        st.markdown("## Hire Recommendation")
        st.markdown(hire_title)
        st.write(hire_body)

        st.markdown("## Rejection Reasons")
        for b in rej_blocks:
            st.write(b)

        st.subheader("후보자 랭킹")
        ranking_df=df[df["AI_MODEL"]=="GEMINI"].sort_values("INTERVIEW_SCORE",ascending=False)
        if ranking_df.empty:
            ranking_df=df.sort_values("INTERVIEW_SCORE",ascending=False)

        for idx,(_,row) in enumerate(ranking_df.iterrows()):
            st.metric(
                f"순위 {idx+1}",
                f"{int(row['INTERVIEW_SCORE'])}/100",
                row["HIRING_DECISION"],
            )

        st.subheader("모델 비교")
        col1,col2=st.columns(2)
        with col1:
            df_chart=df.pivot(index="CANDIDATE_NAME",columns="AI_MODEL",values="INTERVIEW_SCORE")
            st.bar_chart(df_chart)

        with col2:
            avg=df.groupby("AI_MODEL")[["INTERVIEW_SCORE","LATENCY_SEC"]].mean()
            st.dataframe(avg)

        st.subheader("상세 평가")
        candidates=sorted(df["CANDIDATE_NAME"].unique())
        selected=st.selectbox("선택",candidates)
        comp_df=df[df["CANDIDATE_NAME"]==selected].sort_values("INTERVIEW_SCORE",ascending=False)

        for _,row in comp_df.iterrows():
            with st.expander(f"{row['AI_MODEL']} - {int(row['INTERVIEW_SCORE'])}점 - {row['HIRING_DECISION']}"):
                st.write(clean_text(row.get("AI_SUMMARY","")))
                if "QUALITY_SCORE" in row and pd.notna(row["QUALITY_SCORE"]):
                    st.caption(f"{row['LATENCY_SEC']}초 | 유사도 {float(row['QUALITY_SCORE']):.1f}%")
                else:
                    st.caption(f"{row['LATENCY_SEC']}초")

except Exception as e:
    st.error(f"시스템 오류: {str(e)}")
