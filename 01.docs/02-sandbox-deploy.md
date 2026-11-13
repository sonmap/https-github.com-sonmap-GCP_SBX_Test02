# 2차 Sandbox 배포

- 그룹당 Hub·Proxy 한 세트와 과제당 공유 Notebook Pod를 배포할 때는 [그룹 공유 Sandbox 자동 배포](#그룹-공유-sandbox-자동-배포)를 사용합니다.
- 기존 과제별 Hub 방식의 예시는 [기존 과제별 Sandbox 배포](#기존-과제별-sandbox-배포-sbx03)에 있습니다.

## 기존 과제별 Sandbox 배포 · sbx03

[1차 공통 인프라](01-infra-setup.md)가 준비되면, 포털에서 승인된 요청으로 과제별 자원을 추가합니다. 아래는 신규 과제 `sbx03` 기준입니다.

| 구분 | 배포를 시작하는 주체 | 그 뒤에 실행되는 작업 |
|---|---|---|
| 포털 연동 목표 | 포털에서 승인 → GCS에 JSON 저장 → 저장 이벤트로 Workflows 호출 | Cloud Run 검증 → Cloud Build → Terraform → GKE·ALB |
| 현재 반자동 시험 | 운영자 `son@sonmap.net`이 관리 VM에서 승인 JSON을 읽고 `gcloud workflows run` 실행 | 같은 Cloud Run·Cloud Build·Terraform·GKE 흐름 |

```mermaid
flowchart TD
    P["포털 서버 · Sandbox 요청 승인"] --> S["GCS · approved 경로에 요청 JSON 저장"]
    S -.->|목표 · 저장 이벤트 연동 필요| W["workflow-sbxtest01-provision"]
    S -->|현재 시험 · 운영자가 읽기| M["관리 VM · gcloud workflows run"]
    M --> W
```

현재 저장소의 시험 절차에서는 **승인 JSON을 저장한 뒤 1~2절의 명령으로 시작**합니다. 목표 흐름에서 자동으로 시작하려면 GCS 객체 생성 이벤트를 Workflows 입력 형식으로 연결하고, `approved/` 경로와 객체 세대 번호·SHA256을 처리하는 연동이 필요합니다.

## 1. 승인 요청 읽기

```mermaid
flowchart TD
    subgraph P["플랫폼 프로젝트 · gcp-sbx-edp-gke01"]
      B["요청 버킷 · gcp-sbx-edp-gke01-sbxtest01-requests"]
      B --> R["approved / 요청 ID / request.json"]
    end
    R -->|지정한 객체 버전 다운로드| V["관리 VM · 운영자 son@sonmap.net"]
    V --> C["승인 상태와 과제 확인 · SHA256 계산"]
    C --> I["sbx03-workflow-input.json"]
```

포털이 GCS에 저장한 **승인된 요청 ID**를 입력합니다. 신규 프로젝트 사전 권한과 승인 JSON이 아직 준비되지 않았다면 [sbx03 신규 과제 절차 1~3절](reference/sbx03-new-project-runbook.md)을 먼저 따릅니다. 같은 `sbx03`을 재배포할 때는 포털에서 새 요청 ID를 발급받습니다.

아래 블록을 같은 Bash 셸에서 실행합니다. 성공하면 검증된 입력 파일을 만듭니다. 다운로드나 검증이 실패하면 파일을 새로 만들지 않습니다.

```bash
read -r -p '승인된 sbx03 요청 ID: ' REQUEST_ID
REQUEST_URI="gs://gcp-sbx-edp-gke01-sbxtest01-requests/approved/${REQUEST_ID}/request.json"
mkdir -p .local &&
  rm -f .local/sbx03-workflow-input.json &&
  REQUEST_GENERATION="$(gcloud storage objects describe "$REQUEST_URI" --account=son@sonmap.net --format='value(generation)')" &&
  gcloud storage cp "${REQUEST_URI}#${REQUEST_GENERATION}" .local/sbx03-request.json --account=son@sonmap.net &&
  jq -e --arg id "$REQUEST_ID" '
    .request_id == $id and .approval.status == "APPROVED"
    and .task.name == "sbx03"
    and .project.project_id == "gcp-sbx-edp-sbx03"
    and .gke.project_id == "gcp-sbx-edp-gke01"
  ' .local/sbx03-request.json &&
  REQUEST_SHA256="$(sha256sum .local/sbx03-request.json | cut -d ' ' -f1)" &&
  jq -n --arg id "$REQUEST_ID" --arg uri "$REQUEST_URI" --arg gen "$REQUEST_GENERATION" --arg sha "$REQUEST_SHA256" \
    '{request_id:$id,approved_json_uri:$uri,generation:($gen|tonumber),sha256:$sha}' \
    > .local/sbx03-workflow-input.json
```

## 2. 배포 시작

```mermaid
flowchart TD
    O["관리 VM · son@sonmap.net"] -->|gcloud workflows run| W
    subgraph P["플랫폼 프로젝트 · gcp-sbx-edp-gke01"]
      W["workflow-sbxtest01-provision"] -->|인증된 요청| R["Cloud Run · run-sbxtest01-provisioner"]
      R -->|sbx-manager · 원본 검증과 ZIP 생성| B["GCS · sbxtest01-bundles"]
      R -->|sbx-manager · 빌드 제출| C["상위 Cloud Build · pool-sbxtest01"]
      B -.->|단계별 Terraform ZIP| C
    end
```

1절에서 `true`와 입력 파일 생성을 확인한 뒤 실행합니다.

```bash
test -s .local/sbx03-workflow-input.json &&
  gcloud workflows run workflow-sbxtest01-provision \
    --project=gcp-sbx-edp-gke01 --location=asia-northeast3 \
    --account=son@sonmap.net --data="$(cat .local/sbx03-workflow-input.json)"
```

Workflow의 `SUCCEEDED`와 응답의 `ACCEPTED`는 **배포 접수**입니다. 과제 배포 완료는 다음 단계의 빌드 결과에서 확인합니다.

### 2-1. Terraform이 과제 자원 추가

```mermaid
flowchart TD
    subgraph P["플랫폼 프로젝트 · gcp-sbx-edp-gke01"]
      C["상위 Cloud Build · tf-manager"] -->|단계별 apply 호출| I["Infrastructure Manager · pool-sbxtest01"]
    end
    subgraph W["Google Workspace 조직"]
      G["05-group · 과제 그룹과 구성원"]
    end
    subgraph S["과제 프로젝트 · gcp-sbx-edp-sbx03"]
      P1["10-project · 프로젝트 생성과 API 활성화"]
      N["20-network · 필요할 때만"]
      M["30-project-iam · 과제 그룹 권한"]
      D["40-data · BigQuery · GCS · Notebook GSA"]
    end
    I --> G --> P1
    P1 -->|네트워크 요청 있음| N --> M
    P1 -->|sbx03 · 네트워크 생략| M
    M --> D
    D -->|승인된 Dataset 조회 권한| L["데이터레이크 · pjt-c-admin"]
```

| 자동 작업 | sbx03에서 확인할 결과 |
|---|---|
| 그룹 | `pgrp-gcp-dev-sbx03@sonmap.net`과 승인된 구성원 |
| 프로젝트와 IAM | `gcp-sbx-edp-sbx03` 프로젝트, 필요한 API와 과제 그룹 권한 |
| 데이터와 실행 계정 | `sbx03_main`, `gcp-sbx-edp-sbx03-sbx03-data`, `gsa-jupyter-sbx03`과 Workload Identity 권한 |
| 데이터레이크 연결 | 승인된 경우 `pjt-c-admin:dlk_sample` 조회 권한 |

Infrastructure Manager가 ZIP별로 Terraform을 적용합니다. 시험 운영자가 직접 실행하는 시작 명령은 위의 `gcloud workflows run`입니다. [Terraform 파일과 실행 관계](reference/file-relationships.md#4-terraform-자동-적용--zip과-실제-원본-파일)

### 2-2. 후속 빌드가 GKE와 내부 ALB 연결

```mermaid
flowchart TD
    T["Terraform 단계 완료"] --> C
    subgraph P["플랫폼 프로젝트 · gcp-sbx-edp-gke01"]
      C["후속 Cloud Build · pool-sbxtest01 · tf-manager"]
      A["Artifact Registry · Runner와 Helm Chart"]
      A -.-> C
      C -->|apply_gke_workload.py| G["gke-sbx-main-an3 · sbx03 · KSA · JupyterHub · NEG"]
      G -->|reconcile_postdeploy.py| L["공통 내부 ALB · 과제 백엔드와 호스트 경로"]
    end
    G -->|Workload Identity| S["과제 프로젝트 · gsa-jupyter-sbx03"]
```

기존 GKE에 `sbx03` Namespace와 JupyterHub를 추가하고, 공통 내부 ALB에 `jupyter-sbx03.sonmap.net` 경로를 연결합니다. 사용자가 로그인하고 서버를 시작하면 Notebook Pod를 확인할 수 있습니다.

## 3. 배포 결과와 접속 확인

```mermaid
flowchart TD
    O["운영자 · son@sonmap.net"] --> B["Cloud Build · 이번 요청의 상위 및 하위 빌드"]
    O --> K["GKE · sbx03 Pod와 PVC"]
    O --> A["내부 ALB · bes-jupyter-sbx03"]
    U["승인된 사용자"] --> J["JupyterHub 로그인 · Notebook 시작"]
    J --> Q["과제 GSA로 승인된 BigQuery 데이터 조회"]
```

```bash
gcloud builds list --project=gcp-sbx-edp-gke01 --region=asia-northeast3 --account=son@sonmap.net --limit=10 --format='table(id,status,createTime)'

CLOUDSDK_CORE_ACCOUNT=son@sonmap.net kubectl --kubeconfig="$HOME/.kube/config-sbx-dns" -n sbx03 get pods,pvc

gcloud compute backend-services get-health bes-jupyter-sbx03 --project=gcp-sbx-edp-gke01 --region=asia-northeast3 --account=son@sonmap.net
```

이번 요청의 상위·하위 빌드가 `SUCCESS`이고 ALB 백엔드가 `HEALTHY`면 [JupyterHub](https://jupyter-sbx03.sonmap.net/hub/home)에서 Google 로그인과 Notebook 서버 시작을 시험합니다. Notebook에서 `echo "$HOME"`이 `/home/user01`을 표시하는지, 승인된 BigQuery 데이터셋을 조회할 수 있는지 확인합니다.

| 막힌 지점 | 열어야 할 문서 |
|---|---|
| Workflow 이후 빌드 실패 또는 대기 | [sbx03 실제 시험 기록](reference/sbx03-new-project-runbook.md#6-실제-작업-기록과-다음-테스트-순서) |
| 이름 해석·443·인증서 오류 | [내부 HTTPS와 인증서](reference/sbx03-https-certificate-runbook.md) |
| `redirect_uri_mismatch` 또는 로그인 거부 | [Google OAuth 로그인](reference/sbx03-google-oauth-runbook.md) |
| 이전 Notebook 이미지 또는 홈 경로 | [Notebook 이미지와 Helm 적용](../04.Jupiter-setup-image/README.md) |

## 공통 Workflows 배포 명령

> **담당 구분:** Private Pool → GKE 사설 경로와 기존 BigQuery 데이터 조회 권한은 **VPC Admin 요청사항**입니다. 인증서·DNS는 **별도 진행**합니다. tf-manager의 그룹 관리자 역할은 과제 Google Group 관리용, Jupyter OAuth는 사용자 로그인용입니다. [담당자 요청서·인증 설명](reference/admin-requests.md)을 확인하세요.

현재 운영 방식은 **인프라를 개별 gcloud 명령으로 구축한 뒤, 작업자가 과제 Deploy 명령을 실행**하는 것입니다. GCS 이벤트 자동 시작·포털 결과 전달 자동화는 이후에 적용합니다. 기존 배포 코드를 사용하므로 Deploy 시작 이후의 그룹·Terraform·GKE 설치 순서는 Cloud Build가 수행합니다.

### 최초 한 번 — 인프라 준비

관리 VM에서 저장소 루트 GCP_SBX_Test01을 기준으로 아래 문서의 gcloud 명령을 한 줄씩 실행합니다. 각 단계가 성공한 뒤 다음 단계로 진행합니다. 기존 자원은 조회 후 필요한 create/update 명령만 실행합니다. .sh 실행이나 전체 명령 일괄 붙여넣기는 필요하지 않습니다.

| 순서 | 직접 실행할 문서 | 수행 내용 |
|---|---|---|
| 0 | [공통 변수](01-infra-setup.md#0-공통-변수) | 프로젝트·계정·대역 확인 |
| 1 | [관리자 준비](01-infra-setup.md#1-api와-관리자-권한) | API·서비스 계정·IAM |
| 2 | [네트워크](01-infra-setup.md#2-shared-vpc와-네트워크) | Shared VPC·Subnet·PSA·방화벽 |
| 2-1 | [서브넷별 IAM](01-infra-setup.md#2-1-서브넷별-iam) | GKE·ALB VIP 사용 계정 부여 |
| 3 | [공통 실행 기반](01-infra-setup.md#3-공통-기반) | GCS·AR·Private Pool·GKE·Cloud Run·Workflow·ALB |
| 4 | [관리자 개별 명령](01-infra-setup.md#4-oauth-값-등록) 및 [인증 안내](reference/jupyterhub-internal-alb-oauth-runbook.md) | OAuth 등록·그룹 관리자 역할 직접 부여·인증서·DNS 준비 |
| 5 | [Private Pool 접속 점검](reference/runbook-two-stage.md#5-private-pool에서-gke-사설-api-연결-확인) | GKE 사설 API 조회 Build 성공 확인 |
| 6 | [관리자 개별 명령 5~7절](01-infra-setup.md#4-oauth-값-등록) | 플랫폼 릴리스·기본 이미지 미러링·Notebook 이미지 빌드 |

tf-manager 그룹 관리자 역할 준비·DNS·인증서와 기존 BQ 데이터 조회 권한은 각 담당자가 준비합니다. 인증서는 공통 ALB의 HTTPS 연결 명령 전에 필요합니다. 이 준비 작업을 과제 Deploy마다 반복하지 않습니다.

### 과제마다 — 배포할 요청 지정

포털이 GCS에 저장한 **승인된** request.json을 사용합니다. 포털 파일은 [요청 작성 규칙](../05.sandbox_json/README.md)과 [실행용 스키마](../07.sandbox_request_api/sandbox-request.schema.json)를 만족하고 source의 릴리스·generation·SHA256이 실제 게시값이어야 합니다. 파일 저장만으로 배포가 시작되지 않습니다.

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

### Deploy 시작 — gcloud 명령 하나

```bash
gcloud workflows run "${WORKFLOW_NAME}" --project="${SBX_GKE_PROJECT}" --location="${REGION}" --account="${ADMIN_ACCOUNT}" --data="$(cat .local/deploy-input.json)"
```

이 명령은 기존 Workflow → Cloud Run → Cloud Build 배포 경로를 시작합니다. **ACCEPTED 또는 Workflow 성공은 배포 접수 결과**입니다. GKE 생성·공통 네트워크 재구축·이미지 빌드는 이 명령에서 반복하지 않습니다. 과제 요청에 따른 그룹·Project/IAM/Data·선택 Network 구성과 GKE 워크로드 배포는 수행됩니다.

### 배포 결과 확인

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

완료 기준은 부모·자식 Build SUCCESS와 [GKE·ALB·로그인·BQ 확인](reference/runbook-two-stage.md#11-최종-배포와-사용자-동작-확인)입니다. 최신 Build 하나만 보고 다른 과제의 성공을 이번 요청의 성공으로 판단하지 않습니다.

### 나중에 적용할 자동화

현재 작업 순서에 Eventarc 설치·GCS 이벤트 연동 구현을 필수 단계로 넣지 않습니다. 추후 GCS 파일 저장 이벤트가 요청 버전 고정·입력 생성·Deploy 시작을 대신하고, Build 완료 추적과 포털 결과 전달을 연결합니다. 지금은 작업자가 Deploy 시작과 결과 확인을 수행합니다.

## 그룹 공유 Sandbox 자동 배포

```mermaid
flowchart TD
    P["포털 · 그룹 구성 승인"] --> G["GCS · 승인된 그룹 JSON"]
    P -->|"그룹명 · GCS generation · SHA256"| W["Workflows · workflow-sbx-shared-group"]
    W --> B["Cloud Build Private Pool · Runner"]
    G --> B
    S["Secret Manager · PoC 계정 해시"] --> B
    B --> H["GKE · 그룹 Hub와 Proxy"]
    B --> T["GKE · 과제 Notebook · KSA · PVC"]
    H --> L["공통 내부 ALB · 그룹 DNS 연결"]
```

### 1. 플랫폼 운영자 · Workflow 최초 등록

1차에서 GKE, Private Pool의 GKE 접근, 내부 ALB, 그룹 DNS·리전 인증서, 내부 AR의 Helm 차트와 실행 이미지를 준비합니다. Runner에는 그룹 배포 코드가 포함된 버전을 사용합니다. 기존 Runner만 있으면 관리 VM에서 아래와 같이 전용 버전을 게시합니다. 1차 플랫폼 릴리스로 새 Runner를 이미 게시했다면 해당 태그를 사용할 수 있습니다.

```bash
# 1차 문서의 프로젝트, 리전, 계정, 서비스 계정 변수를 설정하고 저장소 루트에서 실행
export BUILD_STAGING_BUCKET="${SBX_GKE_PROJECT}-sbxtest01-build-source"
export TF_MANAGER_RESOURCE="projects/${SBX_GKE_PROJECT}/serviceAccounts/${TF_MANAGER}"
export AR_REPO="${REGION}-docker.pkg.dev/${SBX_GKE_PROJECT}/ar-sbxtest01-platform"
export RUNNER_IMAGE="${AR_REPO}/sbxtest01-automation-runner:shared-$(git rev-parse --short=12 HEAD)"
export WORKER_POOL="projects/${SBX_GKE_PROJECT}/locations/${REGION}/workerPools/pool-sbxtest01"

# 아래 config는 Runner만 빌드합니다.
gcloud builds submit . --project="$SBX_GKE_PROJECT" --region="$REGION" \
  --account="$ADMIN_ACCOUNT" --impersonate-service-account="$TF_MANAGER" \
  --service-account="$TF_MANAGER_RESOURCE" --gcs-source-staging-dir="gs://${BUILD_STAGING_BUCKET}/source" \
  --config=03.cloudbuild/shared-group-runner.yaml --substitutions="_RUNNER_IMAGE=$RUNNER_IMAGE"

gcloud workflows deploy workflow-sbx-shared-group --project="$SBX_GKE_PROJECT" \
  --location="$REGION" --account="$ADMIN_ACCOUNT" --impersonate-service-account="$TF_MANAGER" \
  --service-account="$SBX_MANAGER" --source=07.sandbox_request_api/shared-group-workflow.yaml \
  --set-env-vars="SBX_REGION=$REGION,SBX_RUNNER_SA=$TF_MANAGER_RESOURCE,SBX_RUNNER_IMAGE=$RUNNER_IMAGE,SBX_WORKER_POOL=$WORKER_POOL,SBX_GKE_CLUSTER=gke-sbx-main-an3,SBX_GKE_ENDPOINT_MODE=dns,SBX_REQUEST_BUCKET=${SBX_GKE_PROJECT}-sbxtest01-requests,SBX_CHART_URI=oci://$AR_REPO/jupyterhub,SBX_CHART_VERSION=4.2.0,SBX_URL_MAP=urlmap-alb-sbxtest01-shared"
```

Workflow 실행 계정 `sbx-manager`에는 Build 제출·조회, Private Pool 사용, `tf-manager` 사용 권한이 필요합니다. Runner의 `tf-manager`에는 GKE·ALB 권한, 요청 버킷의 객체 읽기·잠금 객체 생성 및 삭제 권한, 그룹 Secret 접근 권한, 과제 GSA에 Workload Identity 바인딩을 추가할 권한이 필요합니다. 포털 서비스 계정에 승인 JSON 게시 및 이 Workflow 호출 권한을 부여합니다.

### 2. 플랫폼 운영자 · 그룹 계정과 데이터 준비

그룹별 `shared-test-accounts-<그룹명>` Secret Manager 리소스에 `prepare_test_accounts.py`가 생성한 해시 JSON을 등록하고 Runner 계정에 해당 Secret의 `roles/secretmanager.secretAccessor`를 부여합니다. 새 멤버 등록 또는 비밀번호 변경 때 Secret 버전을 갱신합니다. 승인 JSON과 Git에는 해시나 비밀번호를 넣지 않습니다.

과제별 GSA와 BigQuery·GCS 접근 권한을 준비합니다. 기존 Filestore를 사용할 경우 과제 Namespace에 `sandbox-group=<그룹명>` 라벨과 기존 RWX PVC, 필요한 전용 디렉터리를 미리 준비합니다. 신규 PVC를 자동 생성하려면 승인 JSON에 검증된 `storage_class`를 넣습니다. 기존 그룹에 과제를 추가할 때는 JSON에 기존 과제와 신규 과제를 함께 넣습니다. 멤버 교체 전에는 기존 `stop` 절차로 과제를 중지하고 세션을 정리합니다.

### 3. 포털 · 승인할 때마다 실행

1. [그룹 JSON 예시](../11.tests/fixtures/group.example.json)를 바탕으로 전체 그룹 구성을 작성합니다. 실제 내부 AR digest, 그룹 DNS와 과제 PVC 정보를 넣습니다.
2. 승인한 바이트를 `gs://<요청 버킷>/approved-groups/<그룹명>/group.json`에 게시합니다. 그룹별 최신 승인본만 적용합니다. 동시에 승인하는 경우 GCS 업로드의 generation 조건을 사용해 이전 승인본을 덮어쓰는 충돌을 방지합니다.
3. 같은 바이트의 SHA256과 업로드에서 반환된 generation을 사용해 포털이 Workflows Executions API를 호출합니다. 운영자는 연동 시험 시 아래 예시를 실행할 수 있습니다.

```bash
gcloud workflows run workflow-sbx-shared-group --project="$SBX_GKE_PROJECT" --location="$REGION" \
  --data='{"group":"sandbox-group-01","generation":"<GCS generation>","sha256":"<SHA256>"}'
```

Workflow는 Build 완료를 기다립니다. 실행 ID로 결과를 조회하고 Build에서 Helm, 과제 Deployment, NEG·ALB 적용 결과를 확인합니다. 공통 ALB 갱신은 GCS 잠금으로 직렬화됩니다. 빌드 강제 종료로 잠금이 남으면 운영자는 객체에 기록된 Build ID가 종료된 것을 확인하고, 해당 객체 generation을 조건으로 잠금을 제거한 뒤 최신 승인본을 다시 제출합니다.
