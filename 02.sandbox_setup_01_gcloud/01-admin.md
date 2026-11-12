# 1. 관리자 권한 — 주석으로 통합한 gcloud 명령

필요한 변수 선언을 아래 코드 블록 맨 앞에 포함했습니다. 별도 문서에서 변수를 설정할 필요 없이, 이 문서의 선언부터 같은 터미널에서 실행합니다. 아래 한 개의 코드 블록에서 `# 주석`을 보며 순서대로 실행합니다. **계정이 이미 있으면 해당 create 명령을 건너뜁니다.** Billing은 필요한 경우에만 주석을 해제합니다.

```bash
# ── 이 문서에서 사용하는 변수 선언 ──
# 아래 값을 확인하고 이 블록부터 같은 터미널에서 실행합니다.
unset CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT
export ADMIN_ACCOUNT=son@sonmap.net
# 실행 프로젝트 작업자는 son, Shared VPC·초기 권한 관리자는 admin으로 구분합니다.
export VPC_ADMIN_ACCOUNT="${VPC_ADMIN_ACCOUNT:-admin@sonmap.net}"
export OPERATOR_MEMBER=user:son@sonmap.net
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export VPC_HOST_PROJECT="gcp-prod-edp-hub-vpchost"
export SBX_PROJECT="pjt-net-hub-base"
export FOLDER_ID=154455658682
export BILLING_ACCOUNT=""
export TF_MANAGER="tf-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"
export SBX_MANAGER="sbx-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"
export SBX_GKE_PROJECT_NUMBER="$(gcloud projects describe "${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}" --format='value(projectNumber)')"
# 프로젝트 번호는 자동 조회합니다. 조회 실패 또는 숫자가 아닌 결과이면 이후 명령을 중단합니다.

# ── 1. 필요한 API 활성화 — CI/CD · Shared VPC Host · GKE 프로젝트 ──
gcloud services enable servicenetworking.googleapis.com serviceusage.googleapis.com iam.googleapis.com iamcredentials.googleapis.com compute.googleapis.com container.googleapis.com cloudbuild.googleapis.com config.googleapis.com run.googleapis.com workflows.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com storage.googleapis.com logging.googleapis.com cloudresourcemanager.googleapis.com cloudbilling.googleapis.com cloudidentity.googleapis.com --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
gcloud services enable compute.googleapis.com container.googleapis.com servicenetworking.googleapis.com --project="${VPC_HOST_PROJECT}" --account="${VPC_ADMIN_ACCOUNT}"
gcloud services enable container.googleapis.com compute.googleapis.com iam.googleapis.com iamcredentials.googleapis.com cloudresourcemanager.googleapis.com orgpolicy.googleapis.com --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"

# ── 2. Google 서비스 에이전트 준비 — API별로 필요한 시스템 계정 ──
gcloud beta services identity create --service=cloudbuild.googleapis.com --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
gcloud beta services identity create --service=servicenetworking.googleapis.com --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
gcloud beta services identity create --service=config.googleapis.com --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
gcloud beta services identity create --service=run.googleapis.com --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
gcloud beta services identity create --service=workflows.googleapis.com --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
gcloud beta services identity create --service=container.googleapis.com --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
gcloud beta services identity create --service=container.googleapis.com --project="${VPC_HOST_PROJECT}" --account="${VPC_ADMIN_ACCOUNT}"
# 호스트 PSA 조회 오류 시 Service Networking 에이전트 역할도 확인합니다.
gcloud beta services identity create --service=servicenetworking.googleapis.com --project="${VPC_HOST_PROJECT}" --account="${VPC_ADMIN_ACCOUNT}"
export VPC_HOST_PROJECT_NUMBER="$(gcloud projects describe "${VPC_HOST_PROJECT}" --account="${VPC_ADMIN_ACCOUNT}" --format='value(projectNumber)')"
gcloud projects add-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:service-${VPC_HOST_PROJECT_NUMBER}@service-networking.iam.gserviceaccount.com" --role=roles/servicenetworking.serviceAgent --condition=None --account="${VPC_ADMIN_ACCOUNT}"

# Service Networking 시스템 계정의 역할은 사용자 계정에 부여하지 않습니다.
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:service-${SBX_GKE_PROJECT_NUMBER}@service-networking.iam.gserviceaccount.com" --role=roles/servicenetworking.serviceAgent --condition=None --account="${ADMIN_ACCOUNT}"

# ── 3. 사용자 관리 서비스 계정 — sbx-manager · tf-manager ──

# sbx-manager: 조회 성공(이미 존재)이면 바로 다음 create 한 줄은 건너뜁니다.
# 명시적 Not Found일 때만 create를 실행합니다. 403·인증·연결 오류면 중단합니다.
gcloud iam service-accounts describe "${SBX_MANAGER}" --project="${SBX_GKE_PROJECT}" --format=json --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts create sbx-manager --project="${SBX_GKE_PROJECT}" --display-name=sbx_manager --account="${ADMIN_ACCOUNT}"

# tf-manager: 조회 성공(이미 존재)이면 바로 다음 create 한 줄은 건너뜁니다.
# 명시적 Not Found일 때만 create를 실행합니다. 403·인증·연결 오류면 중단합니다.
gcloud iam service-accounts describe "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --format=json --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts create tf-manager --project="${SBX_GKE_PROJECT}" --display-name=tf_manager --account="${ADMIN_ACCOUNT}"

# ── 4. tf-manager 권한 — CI/CD 기반 구축 · Build · Infrastructure Manager ──
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/serviceusage.serviceUsageAdmin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/iam.serviceAccountAdmin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/resourcemanager.projectIamAdmin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/storage.admin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/secretmanager.admin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/artifactregistry.admin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/cloudbuild.builds.editor --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/cloudbuild.workerPoolUser --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/config.admin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/config.agent --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/run.admin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/workflows.admin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/container.admin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/compute.viewer --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/logging.logWriter --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/serviceusage.serviceUsageConsumer --condition=None --account="${ADMIN_ACCOUNT}"

# ── 5. sbx-manager 권한 — 요청 처리 · Workflow · Build 제출 ──
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${SBX_MANAGER}" --role=roles/cloudbuild.builds.editor --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${SBX_MANAGER}" --role=roles/cloudbuild.workerPoolUser --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${SBX_MANAGER}" --role=roles/workflows.invoker --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${SBX_MANAGER}" --role=roles/logging.logWriter --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${SBX_MANAGER}" --role=roles/serviceusage.serviceUsageConsumer --condition=None --account="${ADMIN_ACCOUNT}"

# ── 6. Shared VPC 조회와 VPC Admin의 Pool 초기 구성 권한 ──
# tf-manager에는 Host 전체 Network User/Network Admin/Security Admin을 부여하지 않습니다.
# 서브넷 사용 권한은 서브넷 생성 후 02-subnet-iam.md에서 부여합니다.
gcloud projects add-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/compute.networkViewer --condition=None --account="${VPC_ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/serviceusage.serviceUsageConsumer --condition=None --account="${VPC_ADMIN_ACCOUNT}"
# VPC Admin은 Host 네트워크 관리 권한을 이미 보유한 계정입니다.
# Pool 자원은 gcp-sbx-edp-gke01에 생성하므로 해당 프로젝트의 초기 Pool 관리 권한을 부여합니다.
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="user:${VPC_ADMIN_ACCOUNT}" --role=roles/cloudbuild.workerPoolOwner --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="user:${VPC_ADMIN_ACCOUNT}" --role=roles/serviceusage.serviceUsageConsumer --condition=None --account="${ADMIN_ACCOUNT}"

# ── 7. tf-manager 권한 — GKE · 공통 로드밸런서 ──
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/compute.loadBalancerAdmin --condition=None --account="${ADMIN_ACCOUNT}"

# ── 8. 서비스 계정 사용·위임 권한 — 운영자 · 두 계정 · 서비스 에이전트 ──
gcloud iam service-accounts add-iam-policy-binding "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --member="${OPERATOR_MEMBER}" --role=roles/iam.serviceAccountTokenCreator --condition=None --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts add-iam-policy-binding "${SBX_MANAGER}" --project="${SBX_GKE_PROJECT}" --member="${OPERATOR_MEMBER}" --role=roles/iam.serviceAccountTokenCreator --condition=None --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts add-iam-policy-binding "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --member="${OPERATOR_MEMBER}" --role=roles/iam.serviceAccountUser --condition=None --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts add-iam-policy-binding "${SBX_MANAGER}" --project="${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/iam.serviceAccountUser --condition=None --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts add-iam-policy-binding "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --member="serviceAccount:${SBX_MANAGER}" --role=roles/iam.serviceAccountUser --condition=None --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts add-iam-policy-binding "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/iam.serviceAccountUser --condition=None --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts add-iam-policy-binding "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/iam.serviceAccountTokenCreator --condition=None --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts add-iam-policy-binding "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --member="serviceAccount:service-${SBX_GKE_PROJECT_NUMBER}@gcp-sa-config.iam.gserviceaccount.com" --role=roles/iam.serviceAccountUser --condition=None --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts add-iam-policy-binding "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --member="serviceAccount:service-${SBX_GKE_PROJECT_NUMBER}@gcp-sa-cloudbuild.iam.gserviceaccount.com" --role=roles/iam.serviceAccountTokenCreator --condition=None --account="${ADMIN_ACCOUNT}"

# ── 9. tf-manager 권한 — 기존 과제 프로젝트의 IAM · BigQuery · GCS ──
gcloud projects add-iam-policy-binding "${SBX_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/browser --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/resourcemanager.projectIamAdmin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/serviceusage.serviceUsageAdmin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/bigquery.admin --condition=None --account="${ADMIN_ACCOUNT}"
gcloud projects add-iam-policy-binding "${SBX_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/storage.admin --condition=None --account="${ADMIN_ACCOUNT}"

# ── 10. tf-manager 권한 — 지정 Folder의 프로젝트 생성 · IAM ──
gcloud resource-manager folders add-iam-policy-binding "${FOLDER_ID}" --member="serviceAccount:${TF_MANAGER}" --role=roles/resourcemanager.projectCreator --condition=None --account="${VPC_ADMIN_ACCOUNT}"
gcloud resource-manager folders add-iam-policy-binding "${FOLDER_ID}" --member="serviceAccount:${TF_MANAGER}" --role=roles/resourcemanager.projectIamAdmin --condition=None --account="${VPC_ADMIN_ACCOUNT}"

# ── 11. GCP 서비스 에이전트 권한 — Shared VPC 사용 ──
gcloud projects add-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:service-${SBX_GKE_PROJECT_NUMBER}@container-engine-robot.iam.gserviceaccount.com" --role=roles/container.hostServiceAgentUser --condition=None --account="${VPC_ADMIN_ACCOUNT}"

# ── 12. GKE 노드 기본 계정 권한 — 노드 실행 · tf-manager의 계정 사용 ──
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${SBX_GKE_PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role=roles/container.defaultNodeServiceAccount --condition=None --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts add-iam-policy-binding "${SBX_GKE_PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --project="${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/iam.serviceAccountUser --condition=None --account="${ADMIN_ACCOUNT}"

# ── 선택: 신규 과제 프로젝트의 Billing 연결 권한 ──
# BILLING_ACCOUNT에 실제 ID를 입력하고 신규 프로젝트를 사용할 때만 아래 주석을 해제합니다.
# gcloud billing accounts add-iam-policy-binding "${BILLING_ACCOUNT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/billing.user --account="${ADMIN_ACCOUNT}"

# ── Cloud Identity 그룹 관리자 역할 직접 부여에 사용할 서비스 계정 Unique ID ──
# Workspace 최고 관리자는 tf-manager에 Groups Administrator 역할을 직접 부여합니다.
# GCP IAM 역할과 별개이며 사용자 대신 실행하는 Domain-wide Delegation은 사용하지 않습니다.
gcloud iam service-accounts describe "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}" --format='value(uniqueId)'
```
