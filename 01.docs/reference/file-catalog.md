# 파일별 설명

**실제 작업은 [1차 인프라 구축](../01-infra-setup.md) → [2차 Sandbox 배포](../02-sandbox-deploy.md) 두 문서를 따라 진행합니다.** 이 페이지는 필요한 파일을 찾을 때만 열어보세요. 아래에서 해당 폴더를 펼치면 **폴더 → 파일명 → 역할 → 수행 순서**를 확인할 수 있습니다.

| 수행 순서 표기 | 읽는 방법 |
|---|---|
| **1차 1~7** | 1차 인프라 문서의 표에 표시된 순서입니다. 1~3은 계정·네트워크·공통 기반, 4~5는 승인·접속 점검, 6~7은 이미지·HTTPS 준비입니다. |
| **2차 1~3** | 2차 배포 문서의 절 번호입니다. **1 승인 요청 확인 → 2 Workflow 제출 → 3 결과·사용자 검증** 순서입니다. |
| **자동** | Cloud Run·Cloud Build·Infrastructure Manager·Notebook이 해당 파일을 사용합니다. 운영자가 파일마다 실행하지 않습니다. |
| **참고 · 선택 · 필요 시** | 설계 확인, 선택 보조 도구, 오류 대응 또는 개발 검증에 사용합니다. |

폴더 번호는 파일 분류입니다. 여러 폴더가 한 수행 단계에 함께 사용됩니다. 파일 간 호출과 참조는 [Mermaid 관계도](file-relationships.md)에서 확인할 수 있습니다.

<details>
<summary>루트 · 시작 안내와 개발 설정 (3개)</summary>

| 폴더 | 파일명 | 역할 | 수행 순서 |
|---|---|---|---|
| `루트` | [`.gitignore`](../../.gitignore) | 로컬 설정·인증서·State·캐시 제외 | 공통 · Git 설정 |
| `루트` | [`README.md`](../../README.md) | 시작 문서 | 시작 · 읽기 |
| `루트` | [`requirements-dev.txt`](../../requirements-dev.txt) | 로컬 검증 의존성 | 개발 검증 · 의존성 |

</details>

<details>
<summary>01.docs · 실행 안내와 참고 문서 (22개)</summary>

| 폴더 | 파일명 | 역할 | 수행 순서 |
|---|---|---|---|
| `01.docs` | [`README.md`](../README.md) | 실제 수행 단계·실행 계정·완료 기준의 시작 안내 | 시작 · 읽기 |
| `01.docs` | [`01-infra-setup.md`](../01-infra-setup.md) | 공통 인프라 구축과 이미지 준비 명령 | 1차 · 실행 |
| `01.docs` | [`02-sandbox-deploy.md`](../02-sandbox-deploy.md) | sbx03 승인 요청 확인·Workflow 제출·검증 명령 | 2차 · 실행 안내 |
| `01.docs/reference` | [`admin-requests.md`](admin-requests.md) | 관리자별 네트워크·데이터·인증 준비 요청 | 1차 준비 · 필요 시 |
| `01.docs/reference` | [`architecture-and-operations.md`](architecture-and-operations.md) | 구조·권한 통합 영향·State 전환 | 참고 · 설계 |
| `01.docs/reference` | [`cloud-identity-group-terraform.md`](cloud-identity-group-terraform.md) | 그룹 관리자 역할·Customer ID·기존 그룹 import 안내 | 1차 4 · 관리자 승인 |
| `01.docs/reference` | [`cloudbuild-private-gke-vpn-design.md`](cloudbuild-private-gke-vpn-design.md) | Private Pool의 GKE DNS 접속 점검과 사설 IP 점검 범위 | 1차 5 · 점검 안내 |
| `01.docs/reference` | [`file-catalog.md`](file-catalog.md) | 이 파일: 전체 파일 설명 | 참고 · 파일 찾기 |
| `01.docs/reference` | [`file-relationships.md`](file-relationships.md) | 폴더와 파일별 Mermaid 실행·참조 관계 | 참고 · Mermaid |
| `01.docs/reference` | [`git-sync-current-environment.md`](git-sync-current-environment.md) | 코드 동기화와 기존 환경에서 재시험 | 재시험 · 동기화 |
| `01.docs/reference` | [`internal-alb-design.md`](internal-alb-design.md) | Shared VPC 내부 ALB 구조와 리소스 | 참고 · ALB 설계 |
| `01.docs/reference` | [`jupyterhub-internal-alb-oauth-runbook.md`](jupyterhub-internal-alb-oauth-runbook.md) | ALB·OAuth 접속 설명 | 참고 · 공통 접속 절차 |
| `01.docs/reference` | [`minimal-ip-design.md`](minimal-ip-design.md) | 공통 기반과 과제 네트워크의 IP 최소화 설계 | 참고 · 대역 설계 |
| `01.docs/reference` | [`network-resource-design.md`](network-resource-design.md) | 프로젝트·서브넷·Pool·자원 매핑 | 참고 · 자원 설계 |
| `01.docs/reference` | [`operator-command-guide.md`](operator-command-guide.md) | 운영자 계정과 실제 개별 명령 | 필요 시 · 상세 명령 |
| `01.docs/reference` | [`runbook-two-stage.md`](runbook-two-stage.md) | 실행 순서 | 필요 시 · 상세 실행 |
| `01.docs/reference` | [`sbx03-google-oauth-runbook.md`](sbx03-google-oauth-runbook.md) | Google OAuth 클라이언트·콜백 등록 및 로그인 점검 | 1차 7 · 설정 / 2차 3 · 검증 |
| `01.docs/reference` | [`sbx03-https-certificate-runbook.md`](sbx03-https-certificate-runbook.md) | 내부 HTTPS ALB, 인증서, Windows 접속 확인 | 1차 7 · 설정 / 2차 3 · 검증 |
| `01.docs/reference` | [`sbx03-new-project-runbook.md`](sbx03-new-project-runbook.md) | 신규 과제 생성과 GKE 복구 후 재시험 | 2차 1 · 사전 준비 / 재시험 |
| `01.docs/reference` | [`tf-manager-project.md`](tf-manager-project.md) | 플랫폼 프로젝트와 배포 서비스 계정의 범위 | 참고 · 계정 설계 |
| `01.docs/reference` | [`work-order.md`](work-order.md) | 운영 단계와 관련 명령 문서 연결 | 참고 · 작업 순서 |
| `01.docs/reference` | [`set-request-release.py`](set-request-release.py) | 수동 시험 요청에 릴리스 메타데이터 반영 | 참고 · 선택 실행 |

</details>

<details>
<summary>03.cloudbuild · 플랫폼 릴리스와 미러링 빌드 (6개)</summary>

| 폴더 | 파일명 | 역할 | 수행 순서 |
|---|---|---|---|
| `03.cloudbuild` | [`check-private-gke.yaml`](../../03.cloudbuild/check-private-gke.yaml) | Private Pool에서 DNS 엔드포인트를 통해 Namespace 조회 | 1차 5 · Build 설정 |
| `03.cloudbuild` | [`mirror-jupyterhub-images.yaml`](../../03.cloudbuild/mirror-jupyterhub-images.yaml) | JupyterHub 이미지 내부 미러링 | 1차 6 · Build 설정 |
| `03.cloudbuild` | [`platform-release.yaml`](../../03.cloudbuild/platform-release.yaml) | Runner/Provisioner 빌드·소스 ZIP 게시·Cloud Run 갱신 | 1차 6 · Build 설정 |
| `03.cloudbuild` | [`notebook-candidate-release.yaml`](../../03.cloudbuild/notebook-candidate-release.yaml) | 의존성 변경 시 Notebook 후보 이미지 빌드 설정 | 운영 릴리스 · 선택 |
| `03.cloudbuild` | [`publish-sandbox-source.sh`](../../03.cloudbuild/publish-sandbox-source.sh) | Terraform 소스 ZIP을 GCS에 게시 | 플랫폼 릴리스 Build가 호출 |
| `03.cloudbuild` | [`bootstrap-build.yaml`](../../03.cloudbuild/bootstrap-build.yaml) | 초기 두 실행 이미지 Build 입력 | 1차 3 · Build 설정 |

</details>

<details>
<summary>04.Jupiter-setup-image · Notebook 이미지와 시작 설정 (7개)</summary>

| 폴더 | 파일명 | 역할 | 수행 순서 |
|---|---|---|---|
| `04.Jupiter-setup-image` | [`Dockerfile`](../../04.Jupiter-setup-image/Dockerfile) | Notebook 표준 이미지에 라이브러리와 시작 스크립트 추가 | 1차 6 · Notebook 이미지 빌드 |
| `04.Jupiter-setup-image` | [`README.md`](../../04.Jupiter-setup-image/README.md) | 해당 기능 설명서 | 1차 6 · 빌드 안내 / 2차 3 · 재적용 |
| `04.Jupiter-setup-image` | [`requirements.txt`](../../04.Jupiter-setup-image/requirements.txt) | 표준 이미지의 공통 Python 패키지 | 관리 VM 빌드 |
| `04.Jupiter-setup-image` | [`.dockerignore`](../../04.Jupiter-setup-image/.dockerignore) | 빌드 입력을 Dockerfile·설치 목록·시작 스크립트·wheel로 제한 | 관리 VM 빌드 |
| `04.Jupiter-setup-image` | [`start-sandbox-notebook.sh`](../../04.Jupiter-setup-image/start-sandbox-notebook.sh) | 사용자별 마운트 경로를 HOME으로 설정하고 Notebook 서버 시작 | 2차 3 · Notebook 시작 시 자동 |
| `04.Jupiter-setup-image` | [`Dockerfile.release`](../../04.Jupiter-setup-image/Dockerfile.release), [`release-image.sh`](../../04.Jupiter-setup-image/release-image.sh) | 후보 이미지 빌드 정의와 승인 digest 운영 태그 등록 | 운영 릴리스 · 필요 시 |

</details>

<details>
<summary>05.sandbox_json · 과제 요청 작성 규칙 (1개)</summary>

| 폴더 | 파일명 | 역할 | 수행 순서 |
|---|---|---|---|
| `05.sandbox_json` | [`README.md`](../../05.sandbox_json/README.md) | 필수 항목·조건·요청 호출 흐름 | 2차 1 · 포털 요청 작성 |

</details>

<details>
<summary>07.sandbox_request_api · Cloud Run 요청 처리 (7개)</summary>

| 폴더 | 파일명 | 역할 | 수행 순서 |
|---|---|---|---|
| `07.sandbox_request_api` | [`Dockerfile`](../../07.sandbox_request_api/Dockerfile) | 요청 API 코드와 런타임 스키마를 Cloud Run 이미지에 포함 | 1차 3·6 · 이미지 빌드 |
| `07.sandbox_request_api` | [`README.md`](../../07.sandbox_request_api/README.md) | 신청 접수 API 역할 설명 | 참고 · API 설명 |
| `07.sandbox_request_api` | [`main.py`](../../07.sandbox_request_api/main.py) | 승인 JSON 검증·배포 ZIP 생성·동적 Build 생성 | 2차 2 · Cloud Run 자동 |
| `07.sandbox_request_api` | [`requirements.txt`](../../07.sandbox_request_api/requirements.txt) | Python 라이브러리 의존성 | 1차 3·6 · 빌드 입력 |
| `07.sandbox_request_api` | [`sandbox-request.schema.json`](../../07.sandbox_request_api/sandbox-request.schema.json) | 실제 런타임 요청 규격 | 2차 2 · Cloud Run 자동 |
| `07.sandbox_request_api` | [`provisioner-env.yaml`](../../07.sandbox_request_api/provisioner-env.yaml) | Cloud Run 환경변수 입력 | 1차 3·6 · Cloud Run 입력 |
| `07.sandbox_request_api` | [`workflow.template.yaml`](../../07.sandbox_request_api/workflow.template.yaml) | Cloud Run 호출용 Workflow 정의 | Workflows 배포 입력 |

</details>

<details>
<summary>08.sandbox_setup_02_terraform · 과제별 Terraform 자동 적용 (16개)</summary>

| 폴더 | 파일명 | 역할 | 수행 순서 |
|---|---|---|---|
| `08.sandbox_setup_02_terraform` | [`README.md`](../../08.sandbox_setup_02_terraform/README.md) | 과제별 Infrastructure Manager 상태 설명 | 참고 · Terraform 상태 |
| `08.sandbox_setup_02_terraform/deployments/05-group` | [`main.tf`](../../08.sandbox_setup_02_terraform/deployments/05-group/main.tf) | 과제 Google Group과 구성원 관리 | 2차 2 · Terraform 자동 05 |
| `08.sandbox_setup_02_terraform/deployments/05-group` | [`variables.tf`](../../08.sandbox_setup_02_terraform/deployments/05-group/variables.tf) | 그룹·구성원 입력 변수 | 2차 2 · Terraform 자동 05 |
| `08.sandbox_setup_02_terraform/deployments/05-group` | [`versions.tf`](../../08.sandbox_setup_02_terraform/deployments/05-group/versions.tf) | 그룹 단계의 Terraform·Provider 버전 | 2차 2 · Terraform 자동 05 |
| `08.sandbox_setup_02_terraform/deployments/10-project` | [`main.tf`](../../08.sandbox_setup_02_terraform/deployments/10-project/main.tf) | 프로젝트·API·자동화 IAM | 2차 2 · Terraform 자동 10 |
| `08.sandbox_setup_02_terraform/deployments/10-project` | [`variables.tf`](../../08.sandbox_setup_02_terraform/deployments/10-project/variables.tf) | 입력 변수 | 2차 2 · Terraform 자동 10 |
| `08.sandbox_setup_02_terraform/deployments/10-project` | [`versions.tf`](../../08.sandbox_setup_02_terraform/deployments/10-project/versions.tf) | Terraform/Provider 버전 | 2차 2 · Terraform 자동 10 |
| `08.sandbox_setup_02_terraform/deployments/20-network` | [`main.tf`](../../08.sandbox_setup_02_terraform/deployments/20-network/main.tf) | 선택적 과제 네트워크 | 2차 2 · Terraform 자동 20 · 선택 |
| `08.sandbox_setup_02_terraform/deployments/20-network` | [`variables.tf`](../../08.sandbox_setup_02_terraform/deployments/20-network/variables.tf) | 입력 변수 | 2차 2 · Terraform 자동 20 · 선택 |
| `08.sandbox_setup_02_terraform/deployments/20-network` | [`versions.tf`](../../08.sandbox_setup_02_terraform/deployments/20-network/versions.tf) | Terraform/Provider 버전 | 2차 2 · Terraform 자동 20 · 선택 |
| `08.sandbox_setup_02_terraform/deployments/30-project-iam` | [`main.tf`](../../08.sandbox_setup_02_terraform/deployments/30-project-iam/main.tf) | 과제 Group IAM | 2차 2 · Terraform 자동 30 |
| `08.sandbox_setup_02_terraform/deployments/30-project-iam` | [`variables.tf`](../../08.sandbox_setup_02_terraform/deployments/30-project-iam/variables.tf) | 입력 변수 | 2차 2 · Terraform 자동 30 |
| `08.sandbox_setup_02_terraform/deployments/30-project-iam` | [`versions.tf`](../../08.sandbox_setup_02_terraform/deployments/30-project-iam/versions.tf) | Terraform/Provider 버전 | 2차 2 · Terraform 자동 30 |
| `08.sandbox_setup_02_terraform/deployments/40-data` | [`main.tf`](../../08.sandbox_setup_02_terraform/deployments/40-data/main.tf) | Dataset·Bucket·Notebook GSA·Workload Identity·승인 데이터레이크 권한 | 2차 2 · Terraform 자동 40 |
| `08.sandbox_setup_02_terraform/deployments/40-data` | [`variables.tf`](../../08.sandbox_setup_02_terraform/deployments/40-data/variables.tf) | 입력 변수 | 2차 2 · Terraform 자동 40 |
| `08.sandbox_setup_02_terraform/deployments/40-data` | [`versions.tf`](../../08.sandbox_setup_02_terraform/deployments/40-data/versions.tf) | Terraform/Provider 버전 | 2차 2 · Terraform 자동 40 |

</details>

<details>
<summary>09.sandbox_gke_deployer · GKE와 내부 ALB 자동 배포 (5개)</summary>

| 폴더 | 파일명 | 역할 | 수행 순서 |
|---|---|---|---|
| `09.sandbox_gke_deployer` | [`Dockerfile`](../../09.sandbox_gke_deployer/Dockerfile) | GKE 배포·ALB 연결 코드를 Runner 이미지에 포함 | 1차 3·6 · 이미지 빌드 |
| `09.sandbox_gke_deployer` | [`README.md`](../../09.sandbox_gke_deployer/README.md) | GKE·Jupyter 배포 도구 역할 설명 | 참고 · Runner 설명 |
| `09.sandbox_gke_deployer` | [`apply_gke_workload.py`](../../09.sandbox_gke_deployer/apply_gke_workload.py) | Namespace·KSA·RBAC·Quota·JupyterHub·NEG | 2차 2 · GKE 배포 자동 |
| `09.sandbox_gke_deployer` | [`reconcile_postdeploy.py`](../../09.sandbox_gke_deployer/reconcile_postdeploy.py) | WI 확인·Backend·Health Check·공통 ALB 경로 연결 | 2차 2 · GKE 배포 후 자동 |
| `09.sandbox_gke_deployer` | [`requirements.txt`](../../09.sandbox_gke_deployer/requirements.txt) | Python 라이브러리 의존성 | 1차 3·6 · 빌드 입력 |

</details>

<details>
<summary>11.tests · 개발 검증 (9개)</summary>

| 폴더 | 파일명 | 역할 | 수행 순서 |
|---|---|---|---|
| `11.tests` | [`README.md`](../../11.tests/README.md) | 검증 흐름·테스트별 역할·실행 명령 | 개발 검증 · 시작 안내 |
| `11.tests` | [`request_fixtures.py`](../../11.tests/request_fixtures.py) | 로컬 테스트용 합성 요청 | 개발 검증 · 테스트 입력 |
| `11.tests/fixtures` | [`group.example.json`](../../11.tests/fixtures/group.example.json) | 그룹 공유 Notebook 점검용 입력 예시 | 개발 검증 · 테스트 입력 |
| `11.tests` | [`test_build_paths.py`](../../11.tests/test_build_paths.py) | 빌드 Context·Docker COPY 경로·삭제 컴포넌트 참조 검사 | 개발 검증 · 필요 시 |
| `11.tests` | [`test_commandbooks.py`](../../11.tests/test_commandbooks.py) | 명령 Bash 구문·변수 치환·Workflow 치환의 오프라인 검증 | 개발 검증 · 필요 시 |
| `11.tests` | [`test_internal_alb.py`](../../11.tests/test_internal_alb.py) | Workload Identity 연결과 내부 ALB 백엔드·호스트 경로 검증 | 개발 검증 · 필요 시 |
| `11.tests` | [`test_provisioning.py`](../../11.tests/test_provisioning.py) | 실제 생성 ZIP·Build 계정·그룹 순서·선택 네트워크 검증 | 개발 검증 · 필요 시 |
| `11.tests` | [`test_release_bootstrap.py`](../../11.tests/test_release_bootstrap.py) | 릴리스 설정 검증과 소스 게시 빌드 구성 검사 | 개발 검증 · 필요 시 |
| `11.tests` | [`test_shared_sandbox.py`](../../11.tests/test_shared_sandbox.py) | 공유 Notebook Pod·PVC·테스트 계정 검증 | 개발 검증 · 필요 시 |

</details>
