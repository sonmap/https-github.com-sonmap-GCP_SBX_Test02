# 통합 프로젝트 — gcp-sbx-edp-gke01

GKE와 자동화 자원을 **SBX_GKE_PROJECT=gcp-sbx-edp-gke01**에 함께 구성합니다. 별도의 CI/CD 프로젝트 변수는 제거했습니다.

| 자원 | 대상 |
|---|---|
| GKE·Cloud Run·Cloud Build·Private Pool | gcp-sbx-edp-gke01 |
| Workflows·Infrastructure Manager·Secret Manager | gcp-sbx-edp-gke01 |
| Artifact Registry | asia-northeast3-docker.pkg.dev/gcp-sbx-edp-gke01/ar-sbxtest01-platform |
| 요청·번들·빌드 소스 GCS | gcp-sbx-edp-gke01-sbxtest01-requests / -bundles / -build-source |
| Terraform·Build 실행 계정 | tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com |
| API·Workflow·Notebook 계정 | sbx-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com |
| Shared VPC Host | VPC_HOST_PROJECT=gcp-prod-edp-hub-vpchost |
| 과제 자원·Query Job | SBX_PROJECT=pjt-net-hub-base |
| 기존 데이터레이크 | pjt-c-admin — 기존 별도 데이터 프로젝트 |

## 작업 순서

1. [공통 변수](../../02.sandbox_setup_01_gcloud/00-variables.md)에서 SBX_GKE_PROJECT=gcp-sbx-edp-gke01을 설정합니다.
2. [01-admin](../../02.sandbox_setup_01_gcloud/01-admin.md)의 개별 gcloud 명령으로 API와 두 서비스 계정·권한을 준비합니다. 자동화와 서비스 계정 소속이 같으므로 프로젝트 간 SA 사용을 위한 조직 정책 예외 명령은 제거했습니다.
3. VPC Admin이 [02-network](../../02.sandbox_setup_01_gcloud/02-network.md)에서 gcp-sbx-edp-gke01의 Shared VPC 연결·Subnet·PSA·방화벽을 준비합니다. GKE와 자동화가 같은 프로젝트이므로 같은 연결·권한은 중복 실행하지 않습니다.
4. VPC Admin이 [서브넷별 IAM](../../02.sandbox_setup_01_gcloud/02-subnet-iam.md)을 적용한 후 [03-foundation](../../02.sandbox_setup_01_gcloud/03-foundation.md)에서 버킷·AR·Private Pool·Run·Workflow 등 공통 기반을 준비합니다. 기존 GKE는 조회해 설정이 맞으면 생성을 건너뜁니다.
5. 실제 Customer ID를 provisioner-env.yaml에 설정합니다. tf-manager의 Cloud Identity 그룹 관리자 역할을 확인하고, 새 Secret Manager에 Jupyter OAuth 값을 등록합니다. 인증서·DNS는 별도 진행합니다.
6. [04-manual-gcloud](../../02.sandbox_setup_01_gcloud/04-manual-gcloud.md)의 명령으로 플랫폼 릴리스·기본 이미지 미러링·Notebook 이미지 빌드를 수행합니다. [Private Pool 접속 점검](cloudbuild-private-gke-vpn-design.md)을 통과해야 합니다.
7. 포털 JSON에 새 버킷·이미지와 새 release.json의 소스 주소·generation·SHA256을 반영한 뒤 [Deploy](../../02.sandbox_setup_01_gcloud/05-deploy.md)를 수행합니다.

## 기존 운영 자원이 있는 경우

이 변경은 새 통합 프로젝트를 사용하는 소스·명령 변경입니다. 기존 프로젝트의 자원·데이터·Secret 값·이미지·Infrastructure Manager state는 자동 이동하지 않습니다. 실제 GCP 자원을 생성·이전·삭제한 것은 아닙니다.

기존 배포를 새 IM Deployment로 이어받을 경우 기존 state의 관리 대상과 새 배포의 소유권을 먼저 확인합니다. 같은 그룹·Dataset·Bucket 등을 두 state가 동시에 관리하지 않게 기존 실행을 중지하고 이전 절차를 정해야 합니다. [그룹·멤버 import](cloud-identity-group-terraform.md)와 data.adopt_existing_resources는 편입 수단이며 전체 state 이전을 대신하지 않습니다. 사용자 PVC나 기존 데이터를 삭제해서 충돌을 해결하지 않습니다.

VPC Admin은 새 Private Pool 경로와 **sbx-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com**의 기존 BQ Dataset 조회 권한을 확인해야 합니다. 이전 서비스 계정에 준 권한이 새 계정으로 자동 이전되지는 않습니다. 기존 프로젝트의 폐기·삭제는 이 작업에 포함하지 않습니다.

```bash
export ADMIN_ACCOUNT="son@sonmap.net"
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export TF_MANAGER="tf-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"
export SBX_MANAGER="sbx-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"
gcloud iam service-accounts describe "${TF_MANAGER}" --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
gcloud iam service-accounts describe "${SBX_MANAGER}" --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
```
