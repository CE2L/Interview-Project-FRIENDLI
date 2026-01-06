import os
import boto3
import snowflake.connector
import google.genai as genai
import time
import re
import warnings

warnings.filterwarnings("ignore")

SYSTEM_PROMPT="""후보자 면접 평가. 한글로만 작성.

채용 기준:
90+ 뛰어남=HIRE (1명만)
85-89 우수=CONSIDER
85미만=REJECT

형식:
1. 요약:
2. 장점:
3. 단점:
4. 점수: 숫자만 (0-100)
5. 판정: HIRE 또는 REJECT

최고 후보 무조건 HIRE."""

GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY")

SNOWFLAKE_CONFIG={
    "user":os.environ.get("SNOWFLAKE_USER"),
    "password":os.environ.get("SNOWFLAKE_PASSWORD"),
    "account":os.environ.get("SNOWFLAKE_ACCOUNT"),
    "warehouse":os.environ.get("SNOWFLAKE_WAREHOUSE"),
    "database":os.environ.get("SNOWFLAKE_DATABASE"),
    "schema":os.environ.get("SNOWFLAKE_SCHEMA"),
}

AWS_ACCESS_KEY=os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY=os.environ.get("AWS_SECRET_KEY")
AWS_REGION=os.environ.get("AWS_REGION")
BUCKET_NAME=os.environ.get("S3_BUCKET_NAME")
FILE_KEY=os.environ.get("S3_FILE_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

def get_data_from_s3():
    print(f"S3에서 파일 읽는 중: {BUCKET_NAME}/{FILE_KEY}")
    try:
        s3=boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION,
        )
        resp=s3.get_object(Bucket=BUCKET_NAME,Key=FILE_KEY)
        return resp["Body"].read().decode("utf-8")
    except Exception as e:
        print(f"S3에서 못 가져옴: {e}")
        return None

def extract_score(text):
    text=re.sub(r"[*_`]", "", text)

    m=re.search(r"점수\s*[:：]\s*(\d{1,3})", text)
    if m:
        v=int(m.group(1))
        if 0<=v<=100:
            return v

    m=re.search(r"(\d{1,3})\s*점", text)
    if m:
        v=int(m.group(1))
        if 0<=v<=100:
            return v

    m=re.search(r"(\d{1,3})\s*/\s*100", text)
    if m:
        v=int(m.group(1))
        if 0<=v<=100:
            return v

    return 0

def extract_decision(text):
    t=text.upper()
    if "HIRE" in t or "채용" in t or "합격" in t:
        return "HIRE"
    if "REJECT" in t or "불합격" in t or "탈락" in t:
        return "REJECT"
    return "PENDING"

def analyze(transcript):
    start_t=time.time()
    try:
        model=genai.GenerativeModel("gemini-2.0-flash-exp")
        full_prompt=f"{SYSTEM_PROMPT}\n\n[면접 내용]\n{transcript}"
        response=model.generate_content(full_prompt)
        latency=round(time.time()-start_t,3)
        return (response.text or "").strip(),latency
    except Exception as e:
        print(f"Gemini 호출 실패: {e}")
        return "",0.0

def run():
    print("Interview Analysis Pipeline Start")

    raw_txt=get_data_from_s3()
    if not raw_txt:
        print("입력 데이터 없음")
        return

    candidate_list=[]
    for line in raw_txt.splitlines():
        line=line.strip()
        if not line:
            continue
        if ":" not in line:
            continue
        name,content=line.split(":",1)
        name=name.strip()
        content=content.strip()
        if name and content:
            candidate_list.append((name,content))

    if not candidate_list:
        print("후보 데이터 파싱 실패")
        return

    print(f"후보 {len(candidate_list)}명")

    conn=snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cur=conn.cursor()

    try:
        cur.execute("DROP TABLE IF EXISTS ANALYSIS_METRICS")
        cur.execute(
            """
            CREATE TABLE ANALYSIS_METRICS (
                CANDIDATE_NAME STRING,
                AI_MODEL STRING,
                AI_SUMMARY STRING,
                INTERVIEW_SCORE INT,
                HIRING_DECISION STRING,
                LATENCY_SEC FLOAT,
                CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            )
            """
        )

        for name,text in candidate_list:
            print(f"{name} 평가 중...",end=" ")

            result_text,dt=analyze(text)

            score=extract_score(result_text)
            decision=extract_decision(result_text)

            cur.execute(
                """
                INSERT INTO ANALYSIS_METRICS
                (CANDIDATE_NAME, AI_MODEL, AI_SUMMARY, INTERVIEW_SCORE, HIRING_DECISION, LATENCY_SEC)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (name,"GEMINI",result_text,score,decision,dt),
            )

            print(f"{score}점 {decision}")

        conn.commit()
        print("끝")

    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

if __name__=="__main__":
    run()