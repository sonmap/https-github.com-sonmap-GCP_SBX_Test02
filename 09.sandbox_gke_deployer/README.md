# Sandbox GKE·Jupyter 배포 실행 도구

Cloud Build의 Private Pool 컨테이너 안에서 실행하는 도구입니다.

| 파일 | 역할 |
|---|---|
| apply_gke_workload.py | Namespace·KSA·RBAC·Quota·JupyterHub 설치 |
| reconcile_postdeploy.py | Workload Identity 확인·NEG·Backend·공통 ALB 경로 연결 |
| Dockerfile | 위 도구와 gcloud/kubectl/Helm 등을 담는 이미지 |
| requirements.txt | Python 라이브러리 목록 |

신청을 받는 Cloud Run API와 다른 역할입니다. 요청 접수는 `07.sandbox_request_api/`, 사용자 Notebook 실행 이미지는 `04.Jupiter-setup-image/`에 있습니다.
