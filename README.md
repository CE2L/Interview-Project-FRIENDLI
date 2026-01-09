AI Interview Analysis Pipeline

프로젝트 개요  
면접 텍스트 데이터를 기반으로 후보자를 자동으로 평가하기 위한 개인 프로젝트입니다.  
AWS S3에 저장된 면접 데이터를 읽어와 LLM을 통해 분석하고, 분석 결과를 Snowflake에 저장한 뒤 Streamlit으로 확인할 수 있도록 구성하였습니다.

LLM은 환경변수 설정을 통해 하나의 모델을 선택하여 실행하는 방식으로 사용하였으며, 동일한 구조에서 환경변수 설정을 변경하여 LLM을 교체 실행할 수 있도록 설계하였습니다.

라이브 데모  
https://your-app.streamlit.app  
테스트용 샘플 면접 데이터를 기준으로 동작합니다.

사용 기술  
Cloud: AWS S3, Snowflake, Streamlit Cloud  
LLM: Google Gemini, OpenAI gpt-4o-mini, Friendli Llama 3.3  
Backend: Python  
Frontend: Streamlit  
Infra: Docker  

프로젝트 구조  
pipeline.py  
AWS S3에서 면접 데이터를 수집하고, LLM으로 분석한 뒤 Snowflake에 저장하는 메인 파이프라인입니다.

dashboard.py  
Snowflake에 저장된 평가 결과를 Streamlit으로 조회할 수 있는 대시보드입니다.

clean_db.py  
Snowflake에 생성된 테이블을 초기화하기 위한 스크립트입니다.

interviews.txt  
테스트용 면접 데이터 파일입니다.

requirements.txt  
프로젝트 실행에 필요한 Python 패키지 목록입니다.

Dockerfile  
프로젝트 실행을 위한 Docker 이미지 빌드 설정 파일입니다.

run.bat  
로컬 환경에서 Docker 컨테이너를 실행하기 위한 스크립트입니다.

.env  
로컬 실행 시 사용하는 환경변수 파일이며, GitHub에는 포함하지 않습니다.

.streamlit/secrets.toml  
Streamlit Cloud 배포 시 사용하는 시크릿 설정 파일이며, GitHub에는 포함하지 않습니다.

로컬 실행 방법  
1. .env 파일에 API 키 및 Snowflake 접속 정보를 설정합니다.  
2. run.bat 파일을 실행합니다.  
3. 브라우저에서 http://localhost:9000 으로 접속합니다.

Streamlit Cloud 배포 방법  
1. GitHub에 코드를 업로드합니다. (.env 및 secrets.toml 파일은 .gitignore 처리합니다.)  
2. Streamlit Cloud에서 해당 저장소를 연동합니다.  
3. Settings 메뉴의 Secrets에 secrets.toml 내용을 등록합니다.

구현 내용  
면접 데이터 수집  
AWS S3에 저장된 텍스트 파일에서 면접 데이터를 읽어옵니다.

LLM 기반 면접 분석  
면접 데이터를 LLM에 전달하여 요약, 장점, 단점, 점수, 판정 정보를 텍스트 형태로 생성합니다.

점수 자동 추출  
LLM 출력 결과에서 점수 값을 정규표현식을 이용해 추출합니다.

분석 결과 저장  
후보자 이름, 분석 결과, 점수, 판정, 응답 시간을 Snowflake 테이블에 저장합니다.

결과 조회  
Streamlit 대시보드를 통해 저장된 평가 결과를 확인할 수 있습니다.

보안  
API 키 및 민감 정보는 환경변수를 통해 관리합니다.  
.env 및 secrets.toml 파일은 GitHub에 업로드하지 않습니다.  
Streamlit Cloud 배포 시 Secrets 기능을 사용합니다.
