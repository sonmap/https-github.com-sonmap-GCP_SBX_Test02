# 외부 담당자 요청사항과 인증 준비

인증서·DNS는 별도 진행합니다. Private Pool → GKE 사설 통신 경로와 기존 BigQuery 데이터 조회 권한은 **VPC Admin 요청·완료 확인 항목**으로 구분합니다. 이 문서는 실제 권한 부여나 네트워크 작업을 수행한 기록이 아닙니다.

## 담당 구분

| 항목 | 담당 / 요청 창구 | 준비 내용 | 완료 기준 |
|---|---|---|---|
| Private Pool → GKE 사설 통신 | **VPC Admin** | 경로·왕복 라우팅·필요 방화벽 및 GKE 접근 허용 범위 확인·구성 | Private Pool 점검 Build에서 kubectl get namespaces 성공 |
| 기존 BigQuery 데이터 조회 | **VPC Admin** | 데이터 관리자와 협의해 sbx-manager에 승인 Dataset 조회 권한 요청·적용 확인 | Notebook에서 승인된 실제 Table 조회 성공 |
| 인증서·DNS | **별도 진행** | Jupyter 도메인·인증서·ALB 주소 연결 | HTTPS 접속·도메인 일치 |
| 그룹 관리자 역할 직접 부여 | **Workspace 최고 관리자** | tf-manager 서비스 계정에 Groups Administrator 역할 부여 | Terraform Group 배포 성공 |
| Jupyter OAuth 발급 | **OAuth 설정 담당자** | Google 로그인 Client ID·Secret·Callback URL 준비 | 승인 사용자 Jupyter 로그인 성공 |

VPC Admin은 BigQuery 조회 권한의 요청 창구입니다. 네트워크 관리자 권한 자체로 Dataset IAM을 변경할 수 있는 것은 아니므로, 실제 부여는 데이터 프로젝트/Dataset IAM 권한 보유자가 수행하거나 VPC Admin에게 필요한 권한을 위임해야 합니다.

## VPC Admin 요청 1 — Private Pool → GKE

- 자동화 실행 프로젝트: SBX_GKE_PROJECT = gcp-sbx-edp-gke01
- Private Pool: pool-sbxtest01, 리전 asia-northeast3
- VPC Host: VPC_HOST_PROJECT = gcp-prod-edp-hub-vpchost
- VPC: vpc-prod-edp-hub
- GKE 대상: SBX_GKE_PROJECT = gcp-sbx-edp-gke01 / gke-sbx-main-an3
- 요청: Private Pool에서 GKE 내부 API endpoint까지 TCP 443 왕복 통신이 가능하도록 경로와 방화벽을 구성·검증합니다. 실제 출발 대역과 endpoint는 현행 자원 조회값으로 확정합니다.
- PSA Peering만으로 사설 접속이 보장되지 않으므로 필요한 VPN/BGP 등 경로는 VPC Admin이 설계·적용합니다.
- 완료 확인: [Private Pool 접속 점검](runbook-two-stage.md#5-private-pool에서-gke-사설-api-연결-확인). 인증·Kubernetes 권한 오류는 GKE/IAM 담당자와 분리해 해결합니다.

## VPC Admin 요청 2 — 기존 BigQuery 데이터 조회

- 조회 주체: sbx-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com
- 데이터 프로젝트: pjt-c-admin. 실제 승인 Dataset·Table 범위를 데이터 담당자와 확정합니다.
- 요청 권한: 승인 Dataset 범위의 roles/bigquery.dataViewer 등 필요한 최소 조회 권한. 특수한 뷰·정책 태그·행 수준 접근 제한은 데이터 관리자와 별도 확인합니다.
- Query Job 프로젝트: SBX_PROJECT = pjt-net-hub-base. 데이터 조회 권한과 Query Job 실행 권한은 별개입니다.
- 완료 확인: SELECT 1만으로 끝내지 않고 승인된 실제 Table을 Notebook에서 조회합니다.
- 현재 중앙 sbx-manager를 공유하므로 이 계정에 부여한 데이터 접근 범위가 여러 과제에 영향을 줄 수 있습니다. 승인 범위는 과제 운영 정책과 함께 확인합니다.

## 그룹 관리자 역할 직접 부여

그룹 생성·구성원 관리는 tf-manager가 Cloud Identity Groups API를 사용하는 Terraform 05-group에서 수행합니다. Workspace 최고 관리자는 tf-manager 서비스 계정의 Unique ID에 Groups Administrator 역할을 직접 부여합니다. GCP 조직·Folder·프로젝트 생성 및 IAM 권한도 같은 실행 계정에 사전 부여합니다. 이는 최초 한 번 준비하는 권한 작업이며 배포 때마다 사람이 승인하지 않습니다.

사용자 대신 호출하는 Domain-wide Delegation, Directory API Scope 승인, WORKSPACE_ADMIN_SUBJECT 및 sbx-manager 서명은 제거했습니다. 실제 Cloud Identity Customer ID는 provisioner-env.yaml에 설정합니다. [권한·설정·기존 그룹 편입](cloud-identity-group-terraform.md)을 확인하세요.

## OAuth 발급은 무엇인가

사용자가 JupyterHub에서 Google 계정으로 로그인하도록 웹 애플리케이션의 **Client ID와 Client Secret**을 준비하는 작업입니다.

- 로그인 대상 예시: https://jupyter-sbx01.sonmap.net
- Callback URL 예시: https://jupyter-sbx01.sonmap.net/hub/oauth_callback
- 발급값은 Secret Manager의 jupyter-oauth-client-id / jupyter-oauth-client-secret에 등록합니다.
- [등록 명령](../../02.sandbox_setup_01_gcloud/04-manual-gcloud.md#4-oauth-값-등록)을 사용합니다.

그룹 관리자 역할 부여에는 tf-manager의 Unique ID를 사용하며, Jupyter OAuth Client ID/Secret은 사용자 로그인용입니다. 두 가지는 서로 다른 설정이며 인증서·DNS 준비를 대신하지 않습니다.

## 작업 순서

VPC Admin 요청과 인증서·DNS 별도 준비를 먼저 착수합니다. 작업자는 인프라 gcloud 명령을 수행하고, 해당 외부 준비가 완료된 뒤 Private Pool 접속·사용자 인증을 확인합니다. 이후 [Deploy 명령](../../02.sandbox_setup_01_gcloud/05-deploy.md)을 실행합니다.

## VPC Admin 요청 3 — 내부 ALB

VIP용 172.31.96.0/27과 VIP 실제 할당 VIP는 중복 확인 전 후보입니다. 같은 VPC·리전의 ACTIVE REGIONAL_MANAGED_PROXY가 있으면 재사용하고, 없으면 172.31.111.64/26 후보를 검증합니다. Subnet 소유는 gcp-prod-edp-hub-vpchost, ALB·VIP 소유는 gcp-sbx-edp-gke01입니다. 프록시 CIDR → GKE Pod CIDR TCP 8000과 Google Health Check 소스 → Pod TCP 8000을 허용하고 사내망·VPN/Interconnect에서 VIP로의 경로를 확인합니다. [내부 ALB 설계](internal-alb-design.md)

## VPC Admin 요청 4 — 서브넷 IAM·Pool 초기 준비

[02-network](../../02.sandbox_setup_01_gcloud/02-network.md)로 생성·재사용 범위를 확정한 뒤 [02-subnet-iam](../../02.sandbox_setup_01_gcloud/02-subnet-iam.md)의 네 개 바인딩을 적용합니다. 프록시 전용 Subnet의 사용자 Network User는 만들지 않습니다. Host Service Agent User는 프로젝트 범위로 유지합니다. 03-foundation의 Private Pool 초기 생성 절은 VPC_ADMIN_ACCOUNT로 수행하며 배포 계정 tf-manager는 준비된 Pool을 사용합니다. VPC Admin은 Host 네트워크·방화벽·PSA·Shared VPC·Subnet IAM 관리 권한을 사전에 보유해야 하며, 해당 권한을 tf-manager에 일괄 위임하지 않습니다.
