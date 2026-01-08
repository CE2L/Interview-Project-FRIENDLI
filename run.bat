@echo off
chcp 65001 >nul
color 0A

echo   AI Interview Analysis Pipeline
echo.

REM 기존 컨테이너 정리
docker stop interview-system 2>nul
docker rm interview-system 2>nul

REM Docker 이미지 빌드
echo 이미지 빌드 중...
docker build --no-cache -t interview-analysis .
if errorlevel 1 (
    echo 빌드 실패!
    pause
    exit /b 1
)
echo 빌드 완료

REM 파이프라인 실행
echo [PIPELINE] 데이터 분석 중...
docker run --rm --env-file .env interview-analysis python pipeline.py
if errorlevel 1 (
    echo 파이프라인 실패!
    pause
    exit /b 1
)
echo Pipeline 완료

REM 대시보드 실행
echo [DASHBOARD] 웹 시작 중...
docker run -d --name interview-system --env-file .env -p 9000:8501 interview-analysis streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true

REM 대시보드 준비 대기
timeout /t 5 >nul
start http://localhost:9000

echo.
echo 대시보드: http://localhost:9000
echo 종료: docker stop interview-system
pause
docker logs -f interview-system