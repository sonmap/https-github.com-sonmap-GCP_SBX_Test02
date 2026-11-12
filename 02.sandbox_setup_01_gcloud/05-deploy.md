# 과제 Deploy — 작업자가 배포 명령 실행

> **담당 구분:** Private Pool → GKE 사설 경로와 기존 BigQuery 데이터 조회 권한은 **VPC Admin 요청사항**입니다. 인증서·DNS는 **별도 진행**합니다. tf-manager의 그룹 관리자 역할은 과제 Google Group 관리용, Jupyter OAuth는 사용자 로그인용입니다. [담당자 요청서·인증 설명](../01.docs/reference/admin-requests.md)을 확인하세요.

현재 운영 방식은 **인프라를 개별 gcloud 명령으로 구축한 뒤, 작업자가 과제 Deploy 명령을 실행**하는 것입니다. GCS 이벤트 자동 시작·포털 결과 전달 자동화는 이후에 적용합니다. 기존 배포 코드를 사용하므로 Deploy 시작 이후의 그룹·Terraform·GKE 설치 순서는 Cloud Build가 수행합니다.

## 1. 최초 한 번 — 인프라 준비

관리 VM에서 저장소 루트 GCP_SBX_Test01을 기준으로 아래 문서의 gcloud 명령을 한 줄씩 실행합니다. 각 단계가 성공한 뒤 다음 단계로 진행합니다. 기존 자원은 조회 후 필요한 create/update 명령만 실행합니다. .sh 실행이나 전체 명령 일괄 붙여넣기는 필요하지 않습니다.

| 순서 | 직접 실행할 문서 | 수행 내용 |
|---|---|---|
| 0 | [공통 변수](00-variables.md) | 프로젝트·계정·대역 확인 |
| 1 | [관리자 준비](01-admin.md) | API·서비스 계정·IAM |
| 2 | [네트워크](02-network.md) | Shared VPC·Subnet·PSA·방화벽 |
| 2-1 | [서브넷별 IAM](02-subnet-iam.md) | GKE·ALB VIP 사용 계정 부여 |
| 3 | [공통 실행 기반](03-foundation.md) | GCS·AR·Private Pool·GKE·Cloud Run·Workflow·ALB |
| 4 | [관리자 개별 명령](04-manual-gcloud.md) 및 [인증 안내](../01.docs/reference/jupyterhub-internal-alb-oauth-runbook.md) | OAuth 등록·그룹 관리자 역할 직접 부여·인증서·DNS 준비 |
| 5 | [Private Pool 접속 점검](../01.docs/reference/runbook-two-stage.md#5-private-pool에서-gke-사설-api-연결-확인) | GKE 사설 API 조회 Build 성공 확인 |
| 6 | [관리자 개별 명령 5~7절](04-manual-gcloud.md) | 플랫폼 릴리스·기본 이미지 미러링·Notebook 이미지 빌드 |

tf-manager 그룹 관리자 역할 준비·DNS·인증서와 기존 BQ 데이터 조회 권한은 각 담당자가 준비합니다. 인증서는 공통 ALB의 HTTPS 연결 명령 전에 필요합니다. 이 준비 작업을 과제 Deploy마다 반복하지 않습니다.

## 2. 과제마다 — 배포할 요청 지정

포털이 GCS에 저장한 **승인된** request.json을 사용합니다. 포털 파일은 [요청 Schema](../06.sandbox_json_rules/sandbox-request.schema.json)를 만족하고 source의 릴리스·generation·SHA256이 실제 게시값이어야 합니다. 파일 저장만으로 배포가 시작되지 않습니다.

아래 REQUEST_ID와 REQUEST_URI를 실제 포털 파일로 바꿉니다. 실행 계정에는 요청 객체 읽기와 Workflow 호출 권한이 필요합니다. 폴더 이름의 번호는 실행 순서가 아니며 07/08/09에서 프로그램을 직접 실행하지 않습니다.

```bash
# 저장소 루트에서 한 줄씩 실행합니다.
export ADMIN_ACCOUNT="son@sonmap.net"
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export SBX_NAME="sbx01"
export VPC_HOST_PROJECT="gcp-prod-edp-hub-vpchost"
export SBX_PROJECT="pjt-net-hub-base"
export REGION="asia-northeast3"
export WORKFLOW_NAME="workflow-sbxtest01-provision"
export REQUEST_ID="REQ-20261105-001"
export REQUEST_URI="gs://${SBX_GKE_PROJECT}-sbxtest01-requests/approved/${REQUEST_ID}/request.json"
unset CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT
mkdir -p .local

# 1. 포털이 저장한 객체의 특정 버전을 고정합니다.
gcloud storage objects describe "${REQUEST_URI}" --account="${ADMIN_ACCOUNT}" --format='yaml(name,generation,size)'
export REQUEST_GENERATION="$(gcloud storage objects describe "${REQUEST_URI}" --account="${ADMIN_ACCOUNT}" --format='value(generation)')"

# 2. 해당 버전을 읽어 무결성 확인값을 계산합니다. 오류 시 중단합니다.
gcloud storage cp "${REQUEST_URI}#${REQUEST_GENERATION}" .local/deploy-request.json --account="${ADMIN_ACCOUNT}"
export REQUEST_SHA256="$(sha256sum .local/deploy-request.json | cut -d ' ' -f1)"

# 3. Request ID와 대상 과제를 확인합니다. false 또는 오류이면 배포하지 않습니다.
jq -e --arg id "${REQUEST_ID}" --arg name "${SBX_NAME}" --arg gke "${SBX_GKE_PROJECT}" --arg project "${SBX_PROJECT}" '.request_id == $id and .task.name == $name and .gke.project_id == $gke and .project.project_id == $project' .local/deploy-request.json

# 4. 배포 입력 파일을 만듭니다. jq는 JSON 작성 도구이며 GCP 자원을 생성하지 않습니다.
jq -n --arg id "${REQUEST_ID}" --arg uri "${REQUEST_URI}" --arg gen "${REQUEST_GENERATION}" --arg sha "${REQUEST_SHA256}" '{request_id:$id,approved_json_uri:$uri,generation:($gen|tonumber),sha256:$sha}' > .local/deploy-input.json
```

위 준비 명령들이 모두 성공하고 요청 대상이 맞는지 확인한 뒤 아래 Deploy 명령만 실행합니다. 같은 요청을 반복 제출하기 전에 기존 Build 결과를 확인합니다.

## 3. Deploy 시작 — gcloud 명령 하나

```bash
gcloud workflows run "${WORKFLOW_NAME}" --project="${SBX_GKE_PROJECT}" --location="${REGION}" --account="${ADMIN_ACCOUNT}" --data="$(cat .local/deploy-input.json)"
```

이 명령은 기존 Workflow → Cloud Run → Cloud Build 배포 경로를 시작합니다. **ACCEPTED 또는 Workflow 성공은 배포 접수 결과**입니다. GKE 생성·공통 네트워크 재구축·이미지 빌드는 이 명령에서 반복하지 않습니다. 과제 요청에 따른 그룹·Project/IAM/Data·선택 Network 구성과 GKE 워크로드 배포는 수행됩니다.

## 4. Deploy 결과 확인

```bash
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export TF_MANAGER="tf-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"

# 이번 요청의 실행 시각과 결과를 확인합니다.
gcloud workflows executions list "${WORKFLOW_NAME}" --project="${SBX_GKE_PROJECT}" --location="${REGION}" --account="${ADMIN_ACCOUNT}" --limit=5
gcloud builds list --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --limit=10 --sort-by='~createTime' --format='table(id,status,createTime)'

# 위 목록과 요청 로그로 이번 부모·자식 Build를 식별한 후 실제 ID를 입력합니다.
# export BUILD_ID="실제_BUILD_ID"
# gcloud builds describe "${BUILD_ID}" --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --format='yaml(id,status,steps)'
# gcloud builds log "${BUILD_ID}" --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
```

완료 기준은 부모·자식 Build SUCCESS와 [GKE·ALB·로그인·BQ 확인](../01.docs/reference/runbook-two-stage.md#11-최종-배포와-사용자-동작-확인)입니다. 최신 Build 하나만 보고 다른 과제의 성공을 이번 요청의 성공으로 판단하지 않습니다.

## 나중에 적용할 자동화

현재 작업 순서에 Eventarc 설치·GCS 이벤트 연동 구현을 필수 단계로 넣지 않습니다. 추후 GCS 파일 저장 이벤트가 요청 버전 고정·입력 생성·Deploy 시작을 대신하고, Build 완료 추적과 포털 결과 전달을 연결합니다. 지금은 작업자가 Deploy 시작과 결과 확인을 수행합니다.
