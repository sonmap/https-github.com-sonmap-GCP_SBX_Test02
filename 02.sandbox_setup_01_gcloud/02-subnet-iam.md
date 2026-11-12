# 2-1. Shared VPC 서브넷별 사용 권한 — VPC Admin 수행

**01-admin → 02-network → 이 문서 → 03-foundation 순서**입니다. Subnet이 실제 존재한 뒤 수행합니다. VPC Admin은 Subnet IAM 수정 권한이 필요하며, Host 프로젝트 역할 변경은 해당 프로젝트 IAM 관리자 권한으로 수행합니다. 권한은 Subnet 소유 프로젝트 gcp-prod-edp-hub-vpchost에 적용하며, 서비스 계정의 프로젝트 번호는 gcp-sbx-edp-gke01에서 조회합니다. 후보 서브넷 이름이 실제와 다르면 아래 값을 맞춥니다.

| Subnet | 주체 | 역할 |
|---|---|---|
| Main GKE Node | tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com | roles/compute.networkUser |
| Main GKE Node | service-NUM@container-engine-robot.iam.gserviceaccount.com | roles/compute.networkUser |
| Main GKE Node | NUM@cloudservices.gserviceaccount.com | roles/compute.networkUser |
| ALB VIP /27 | tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com | roles/compute.networkUser |
| 프록시 전용 /26 | 별도 사용자 Network User 바인딩 없음 | VPC Admin이 생성·관리, Envoy가 사용 |
| GKE Pod Secondary | 별도 IAM 없음 | Main GKE Subnet 정책으로 처리 |
| Private Pool PSA | Subnet IAM 대상 아님 | VPC Admin의 프로젝트·연결 관리 |

NUM은 아래에서 조회하는 gcp-sbx-edp-gke01의 프로젝트 번호입니다. sbx-manager·Cloud Run 서비스 에이전트·Notebook KSA에는 Subnet Network User를 부여하지 않습니다. Cloud Run은 VPC 미연결이며, Notebook은 이미 생성된 GKE 네트워크를 사용합니다.

```bash
export ADMIN_ACCOUNT="son@sonmap.net"
# 실제 VPC Admin 계정으로 변경합니다.
export VPC_ADMIN_ACCOUNT="${VPC_ADMIN_ACCOUNT:-admin@sonmap.net}"
export VPC_HOST_PROJECT="gcp-prod-edp-hub-vpchost"
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export REGION="asia-northeast3"
export MAIN_SUBNET="subnet-prod-sbx-gke-01"
export ILB_VIP_SUBNET="subnet-prod-edp-alb-frontend-an3"
export TF_MANAGER="tf-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"
export SBX_GKE_PROJECT_NUMBER="$(gcloud projects describe "${SBX_GKE_PROJECT}" --account="${VPC_ADMIN_ACCOUNT}" --format='value(projectNumber)')"
# 프로젝트 번호가 숫자인지 확인하고 조회 실패 시 중단합니다.

# 존재 여부와 현재 IAM을 확인합니다.
gcloud compute networks subnets describe "${MAIN_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --account="${VPC_ADMIN_ACCOUNT}"
gcloud compute networks subnets describe "${ILB_VIP_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --account="${VPC_ADMIN_ACCOUNT}"
gcloud compute networks subnets get-iam-policy "${MAIN_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --account="${VPC_ADMIN_ACCOUNT}"
gcloud compute networks subnets get-iam-policy "${ILB_VIP_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --account="${VPC_ADMIN_ACCOUNT}"

# 1. GKE를 구축·사용할 배포 계정
gcloud compute networks subnets add-iam-policy-binding "${MAIN_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --member="serviceAccount:${TF_MANAGER}" --role=roles/compute.networkUser --account="${VPC_ADMIN_ACCOUNT}"

# 2. GKE 서비스 에이전트
gcloud compute networks subnets add-iam-policy-binding "${MAIN_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --member="serviceAccount:service-${SBX_GKE_PROJECT_NUMBER}@container-engine-robot.iam.gserviceaccount.com" --role=roles/compute.networkUser --account="${VPC_ADMIN_ACCOUNT}"

# 3. Google APIs 서비스 에이전트
gcloud compute networks subnets add-iam-policy-binding "${MAIN_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --member="serviceAccount:${SBX_GKE_PROJECT_NUMBER}@cloudservices.gserviceaccount.com" --role=roles/compute.networkUser --account="${VPC_ADMIN_ACCOUNT}"

# 4. 내부 ALB VIP 서브넷 사용자
gcloud compute networks subnets add-iam-policy-binding "${ILB_VIP_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --member="serviceAccount:${TF_MANAGER}" --role=roles/compute.networkUser --account="${VPC_ADMIN_ACCOUNT}"

# 적용 후 다시 조회합니다.
gcloud compute networks subnets get-iam-policy "${MAIN_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --account="${VPC_ADMIN_ACCOUNT}"
gcloud compute networks subnets get-iam-policy "${ILB_VIP_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --account="${VPC_ADMIN_ACCOUNT}"
```

GKE 서비스 에이전트의 roles/container.hostServiceAgentUser는 01-admin.md에서 **Host 프로젝트 범위로 유지**합니다. tf-manager의 Host roles/compute.networkViewer도 네트워크 조회용으로 유지하며, 사용·변경 권한을 대신하지 않습니다. ALB 생성·인증서·Backend 관리 권한은 gcp-sbx-edp-gke01의 roles/compute.loadBalancerAdmin 등으로 처리합니다.

## 기존 권한을 줄이는 경우

기존 Host 전체 Network User가 남아 있으면 Subnet별로 추가해도 사용 범위는 제한되지 않습니다. 새 Subnet 바인딩과 GKE·ALB·Pool 동작 검증 후 [기존 광역 권한 정리](06-iam-migration.md)를 수행합니다. 신규 구축에서는 이 정리 절차가 필요하지 않습니다.

추가 서브넷 생성·Shared VPC 연결 변경을 과제 Deploy에서 요청하지 않습니다. 기본 요청은 network.required=false입니다. 추가 네트워크가 필요하면 VPC Admin이 먼저 구성하고 승인된 범위에 별도 사용 권한을 부여해야 합니다.
