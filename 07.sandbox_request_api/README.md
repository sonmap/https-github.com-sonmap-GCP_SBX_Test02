# Sandbox 신청 접수 API

Cloud Run에서 승인된 Sandbox 신청 JSON을 받아 처리합니다.

1. GCS Generation/SHA256, 승인 상태, 입력 규칙을 검사합니다.
2. 승인된 소스 ZIP의 `08.sandbox_setup_02_terraform/deployments/`에서 단계별 배포 ZIP을 만들고 Cloud Build를 시작합니다.

`main.py`는 요청 처리, `sandbox-request.schema.json`은 실제 런타임 입력 규칙, `Dockerfile`은 Cloud Run 실행 이미지, `requirements.txt`는 Python 라이브러리 목록입니다. GKE 안에서 Jupyter를 설치하는 코드는 `09.sandbox_gke_deployer/`에 있습니다.
