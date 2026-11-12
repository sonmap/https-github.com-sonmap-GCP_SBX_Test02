# 2. 공통 네트워크 — 주석으로 통합한 gcloud 명령

필요한 변수 선언을 아래 코드 블록 맨 앞에 포함했습니다. 별도 문서에서 변수를 설정할 필요 없이, 이 문서의 선언부터 같은 터미널에서 실행합니다. `# 주석`을 보며 순서대로 실행하고, **기존 자원이 있으면 해당 생성 명령을 건너뜁니다.** 403·인증·연결 오류면 중단합니다. 선택 작업은 주석을 해제한 경우에만 실행합니다.

```bash
# ── 이 문서에서 사용하는 변수 선언 ──
# 아래 값을 확인하고 이 블록부터 같은 터미널에서 실행합니다.
unset CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT
export ADMIN_ACCOUNT=admin@sonmap.net
# 실행 프로젝트 작업자는 son, Shared VPC·초기 권한 관리자는 admin으로 구분합니다.
export VPC_ADMIN_ACCOUNT="${VPC_ADMIN_ACCOUNT:-admin@sonmap.net}"
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export VPC_HOST_PROJECT="gcp-prod-edp-hub-vpchost"
export REGION=asia-northeast3
export NETWORK=vpc-prod-edp-hub
# 내부 ALB 대역 후보: VPC Admin의 실제 중복 확인·승인 후 실행합니다.
export ILB_VIP_SUBNET=subnet-prod-edp-alb-frontend-an3
export ILB_VIP_CIDR=172.31.96.0/27
export ILB_VIP_ADDRESS="" # 예약 후 실제 할당 주소 조회
export ILB_PROXY_SUBNET=subnet-prod-sbx-ilb-proxy
export ILB_PROXY_CIDR=172.31.111.64/26
export MAIN_SUBNET=subnet-prod-sbx-gke-01
export MAIN_NODE_CIDR=10.252.0.0/24
export MAIN_POD_RANGE=subnet-prod-sbx-pod-01
export MAIN_POD_CIDR=100.64.128.0/19
export PSA_NAME=psa-prod-edp-cloudbuild
export PSA_ADDRESS="10.250.0.0"
export PSA_PREFIX_LENGTH="24"
# 이 문서는 VPC Admin 계정으로 수행합니다. 초기 Shared VPC 연결·Subnet·방화벽·PSA를 관리할 권한이 필요합니다.
# 완료 후 02-subnet-iam.md를 수행한 뒤 03-foundation.md로 진행합니다.

# 먼저 기존 Primary/Secondary 대역을 확인합니다.
# Node · Pod · Control Plane · PSA 대역이 겹치거나 기존 설정과 다르면 중단합니다.

# ── 기존 대역 먼저 확인 ──
gcloud compute networks subnets list --project="${VPC_HOST_PROJECT}" --format=json --account="${VPC_ADMIN_ACCOUNT}"

# ── 1. compute networks create vpc-prod-edp-hub ──
# 기존 자원 확인
gcloud compute networks describe "${NETWORK}" --project="${VPC_HOST_PROJECT}" --format=json --account="${VPC_ADMIN_ACCOUNT}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
# 기존 자원 확인값: {"autoCreateSubnetworks": false} — 다르면 중단합니다.
gcloud compute networks create "${NETWORK}" --project="${VPC_HOST_PROJECT}" --subnet-mode=custom --account="${VPC_ADMIN_ACCOUNT}"

# ── 2. compute shared-vpc get-host-project gcp-prod-edp-hub-vpchost ──
# 기존 자원 확인
gcloud compute shared-vpc get-host-project "${VPC_HOST_PROJECT}" --format=json --account="${VPC_ADMIN_ACCOUNT}"

# ── 3. compute shared-vpc enable gcp-prod-edp-hub-vpchost ──
# 앞의 조회에서 이미 같은 Host에 연결되어 있으면 아래 명령은 건너뜁니다. 다른 Host면 중단합니다.
gcloud compute shared-vpc enable "${VPC_HOST_PROJECT}" --account="${VPC_ADMIN_ACCOUNT}"

# ── 4. compute shared-vpc get-host-project gcp-sbx-edp-gke01 ──
# 기존 자원 확인
gcloud compute shared-vpc get-host-project "${SBX_GKE_PROJECT}" --format=json --account="${VPC_ADMIN_ACCOUNT}"

# ── 5. compute shared-vpc associated-projects add gcp-sbx-edp-gke01 ──
# 앞의 조회에서 이미 같은 Host에 연결되어 있으면 아래 명령은 건너뜁니다. 다른 Host면 중단합니다.
gcloud compute shared-vpc associated-projects add "${SBX_GKE_PROJECT}" --host-project="${VPC_HOST_PROJECT}" --account="${VPC_ADMIN_ACCOUNT}"

# ── 6. compute networks subnets create subnet-prod-sbx-gke-01 ──
# 기존 자원 확인
gcloud compute networks subnets describe "${MAIN_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --format=json --account="${VPC_ADMIN_ACCOUNT}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
# 기존 자원 확인값: {"ipCidrRange": "10.252.0.0/24", "network": "https://www.googleapis.com/compute/v1/projects/gcp-prod-edp-hub-vpchost/global/networks/vpc-prod-edp-hub"} — 다르면 중단합니다.
gcloud compute networks subnets create "${MAIN_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --network="${NETWORK}" --range="${MAIN_NODE_CIDR}" --enable-private-ip-google-access --secondary-range="${MAIN_POD_RANGE}=${MAIN_POD_CIDR}" --account="${VPC_ADMIN_ACCOUNT}"

# ── 7. compute networks subnets update subnet-prod-sbx-gke-01 ──
gcloud compute networks subnets update "${MAIN_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --enable-private-ip-google-access --account="${VPC_ADMIN_ACCOUNT}"

# IP 최소화: Cloud Run·과제 전용 Subnet을 생성하지 않습니다.
# 과제 Namespace는 기존 Main GKE Pod 대역을 공유합니다.

# ── 8. compute addresses create psa-prod-edp-cloudbuild ──
# 기존 자원 확인
gcloud compute addresses describe "${PSA_NAME}" --project="${VPC_HOST_PROJECT}" --global --format=json --account="${VPC_ADMIN_ACCOUNT}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
# 기존 자원 확인값: {"address": "10.250.0.0", "prefixLength": 24, "purpose": "VPC_PEERING"} — 다르면 중단합니다.
gcloud compute addresses create "${PSA_NAME}" --project="${VPC_HOST_PROJECT}" --global --purpose=VPC_PEERING --addresses="${PSA_ADDRESS}" --prefix-length="${PSA_PREFIX_LENGTH}" --network="projects/${VPC_HOST_PROJECT}/global/networks/${NETWORK}" --account="${VPC_ADMIN_ACCOUNT}"

# ── 9. services vpc-peerings list ──
# 기존 자원 확인
gcloud services vpc-peerings list --project="${VPC_HOST_PROJECT}" --network="${NETWORK}" --service=servicenetworking.googleapis.com --format=json --account="${VPC_ADMIN_ACCOUNT}"

# ── 10. services vpc-peerings connect ──
# 앞의 조회에 PSA Range 연결이 이미 있으면 건너뜁니다. 기존 Range를 덮어쓰지 않습니다.
gcloud services vpc-peerings connect --project="${VPC_HOST_PROJECT}" --network="${NETWORK}" --service=servicenetworking.googleapis.com --ranges="${PSA_NAME}" --account="${VPC_ADMIN_ACCOUNT}"

# ── 11. compute firewall-rules create fw-sbxtest01-alb-hc ──
# 기존 자원 확인
gcloud compute firewall-rules describe fw-sbxtest01-alb-hc --project="${VPC_HOST_PROJECT}" --format=json --account="${VPC_ADMIN_ACCOUNT}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
# 기존 자원 확인값: {"sourceRanges": ["35.191.0.0/16", "130.211.0.0/22"], "destinationRanges": ["100.64.128.0/19"]} — 다르면 중단합니다.
gcloud compute firewall-rules create fw-sbxtest01-alb-hc --project="${VPC_HOST_PROJECT}" --network="${NETWORK}" --direction=INGRESS --allow=tcp:8000 --source-ranges=35.191.0.0/16,130.211.0.0/22 --destination-ranges="${MAIN_POD_CIDR}" --account="${VPC_ADMIN_ACCOUNT}"

# ── 내부 ALB VIP용 일반 Subnet /27 — Shared VPC Host 소유 ──
# 후보 CIDR은 반드시 VPC Admin이 전체 사내망과 중복 여부를 확인합니다.
gcloud compute networks subnets describe "${ILB_VIP_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --format=json --account="${VPC_ADMIN_ACCOUNT}"
# 명시적 Not Found일 때만 생성합니다. 403이면 중단합니다.
gcloud compute networks subnets create "${ILB_VIP_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --network="${NETWORK}" --range="${ILB_VIP_CIDR}" --enable-private-ip-google-access --account="${VPC_ADMIN_ACCOUNT}"

# ── 프록시 전용 Subnet — 같은 VPC·리전에 ACTIVE가 있으면 재사용 ──
# 목록의 network·region·purpose·role을 확인합니다. 기존 ACTIVE가 있으면
# ILB_PROXY_SUBNET·ILB_PROXY_CIDR을 그 값으로 맞추고 아래 create를 건너뜁니다.
gcloud compute networks subnets list --project="${VPC_HOST_PROJECT}" --filter="purpose=REGIONAL_MANAGED_PROXY AND region:${REGION}" --format=json --account="${VPC_ADMIN_ACCOUNT}"
# 호환 ACTIVE가 없고 CIDR 승인이 완료된 경우에만 생성합니다. /28은 사용할 수 없습니다.
gcloud compute networks subnets create "${ILB_PROXY_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --network="${NETWORK}" --range="${ILB_PROXY_CIDR}" --purpose=REGIONAL_MANAGED_PROXY --role=ACTIVE --account="${VPC_ADMIN_ACCOUNT}"

# ── ALB 프록시에서 GKE NEG의 Proxy Pod로 HTTP 전달 ──
gcloud compute firewall-rules describe fw-sbxtest01-ilb-proxy --project="${VPC_HOST_PROJECT}" --format=json --account="${VPC_ADMIN_ACCOUNT}"
# 명시적 Not Found일 때만 생성합니다. 기존 규칙이면 실제 CIDR·포트를 비교합니다.
gcloud compute firewall-rules create fw-sbxtest01-ilb-proxy --project="${VPC_HOST_PROJECT}" --network="${NETWORK}" --direction=INGRESS --allow=tcp:8000 --source-ranges="${ILB_PROXY_CIDR}" --destination-ranges="${MAIN_POD_CIDR}" --account="${VPC_ADMIN_ACCOUNT}"
```
