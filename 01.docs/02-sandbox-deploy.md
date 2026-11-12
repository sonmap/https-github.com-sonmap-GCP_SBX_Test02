# 2차 Sandbox 배포 · sbx03

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
