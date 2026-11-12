# Sandbox 자동 배포 기반 설계서 — 프로젝트·서브넷·GCP 자원

> **IP 최소화 적용:** Cloud Run 전용 Subnet·과제별 새 Subnet을 기본 구축에서 제외했습니다. 기존 GKE 대역과 Private Pool PSA는 유지·재사용합니다. [최소 IP 구성 및 기존 자원 확인](minimal-ip-design.md)

작성 기준: 현재 저장소 소스, 리전 asia-northeast3. **실제 GCP 인벤토리 조회 결과가 아니라 소스 기반 설계값**입니다. 기존 자원은 조회·비교 후 재사용하고, 새 CIDR은 VPC Admin의 전체 사내망 중복 검증 후 확정합니다.

과제용 SBX 프로젝트는 별도로 존재하는 기존 프로젝트를 사용하며 신규 프로젝트 생성을 기본 작업에 포함하지 않습니다. 현재 샘플은 pjt-net-hub-base이고 실제 운영 SBX 프로젝트가 다르면 승인 JSON의 project와 해당 권한을 맞춥니다.

## 1. 프로젝트 배치

| 변수 / 범위 | 프로젝트 | 역할 | 구축 구분 |
|---|---|---|---|
| SBX_GKE_PROJECT | gcp-sbx-edp-gke01 | GKE·Cloud Build·Private Pool·Run·Workflow·IM·AR·Secret·공통 GCS·두 SA | 공통 실행 기반 구성 / 기존 GKE 재사용 가능 |
| VPC_HOST_PROJECT | gcp-prod-edp-hub-vpchost | Shared VPC·Subnet·Secondary Range·PSA·방화벽·라우팅 | VPC Admin 확인·구성 |
| SBX_PROJECT | pjt-net-hub-base — 현재 샘플 | 기존 과제 Dataset·과제 GCS·BQ Query Job | **기존 프로젝트 사용**, create_project=false |
| 기존 데이터레이크 | pjt-c-admin — 현재 예시 | 기존 BigQuery 데이터 | 기존 사용·승인 범위 조회 권한 |

공통 VPC는 vpc-prod-edp-hub입니다. GKE는 gcp-sbx-edp-gke01의 서비스 자원이며 사용하는 Shared VPC 서브넷은 gcp-prod-edp-hub-vpchost 소유입니다. Cloud Run은 VPC에 연결하지 않고 Google API를 호출합니다. Private Pool 작업자는 Google 관리 서비스 제공자 네트워크에서 실행되며 사용자 VPC와 PSA/Peering으로 연결합니다.

## 2. 필수·기존 네트워크 대역

주소 수는 CIDR의 전체 주소 수이며 실제 할당 가능한 수·Pod 수·동시 Build 수가 아닙니다.

| No. | 용도 | 이름 / 설정 변수 | CIDR | 전체 주소 | 종류 / 소유·관리 | 사용 자원 / 처리 |
|---|---|---|---|---:|---|---|
| N1 | Main GKE Node | subnet-prod-sbx-gke-01 / MAIN_NODE_CIDR | 10.252.0.0/24 | 256 | Shared VPC 일반 Subnet Primary / VPC Host | gke-sbx-main-an3, 기존 설정 확인 후 재사용 또는 생성 |
| N2 | Main GKE Pod | subnet-prod-sbx-pod-01 / MAIN_POD_CIDR | 100.64.128.0/19 | 4,096 | N1의 Secondary Range / VPC Host | Hub·Proxy·Notebook·시스템 Pod |
| N3 | Main GKE 제어 영역 | MAIN_CP_CIDR | 10.253.3.0/28 | 16 | 관리형 제어 영역 대역, 일반 사용자 Subnet 아님 | 소스의 master-ipv4-cidr 값, 기존 클러스터 설정과 대조 |
| N4 | Cloud Run 전용 Subnet | 기본 구성에서 제거 | 예약 없음 | 0 | Direct VPC 연결 없음 | Google API 호출만 수행, GKE 배포는 Private Pool 담당 |
| N5 | Private Pool PSA 할당 | psa-prod-edp-cloudbuild / PSA_CIDR | 10.250.0.0/24 | 256 | VPC_PEERING 전용 할당 범위, 일반 Subnet 아님 | Pool 작업자 통신용, 다른 PSA 서비스와 중복 사용 검토 |
| N6 | 과제 전용 Subnet | 기본 구성에서 제외 | 신규 예약 없음 | 0 추가 | 기존 자원이 있으면 그대로 유지 | 샘플 network.required=false, 과제 Namespace는 N2 공유 |
| N7 | 기존 관리자망 | ADMIN_CIDR, Subnet 이름 미지정 | 172.31.10.0/24 | 256 | 기존 관리자 접속 대역 | 관리 PC/VM 위치는 실제 환경 확인 |
| N8 | GKE Service ClusterIP | 명시적 Service CIDR 설정 없음 | 실제 클러스터 조회 후 기록 | 미확정 | GKE 관리 Service 범위 | 사용자 Subnet 추가 생성 대상으로 보지 않음 |
| N9 | ALB 사설 VIP | ip-alb-sbxtest01-shared | 실제 할당 VIP 후보 | 1 VIP | Regional Internal ALB / gcp-sbx-edp-gke01 | VIP는 N10에서 예약, DNS·Regional 인증서 별도 |
| N10 | ALB VIP용 Subnet | subnet-prod-edp-alb-frontend-an3 | 172.31.96.0/27 기존 재사용 | 32 | 일반 Subnet / Shared VPC Host | gcp-sbx-edp-gke01의 ALB에서 사용 |
| N11 | ALB 프록시 전용 Subnet | subnet-prod-sbx-ilb-proxy | 172.31.111.64/26 후보 | 64 | REGIONAL_MANAGED_PROXY / Shared VPC Host | 같은 VPC·리전의 기존 ACTIVE 우선 재사용 |

Private Pool의 peered-network-ip-range도 N5의 10.250.0.0/24를 참조합니다. 이는 N5와 별개의 256주소 서브넷을 추가하는 의미가 아닙니다. 실제 Pool이 배정받은 IP와 예약 범위 사용 현황은 생성 후 확인합니다. Cloud Run의 기존 /26 예약·생성 명령은 제거했습니다. Workflows 전용 Subnet은 생성하지 않습니다.

과제별 Jupyter 환경은 중앙 GKE의 Namespace와 N2의 Pod IP를 사용합니다. **기존 과제 프로젝트가 있다는 이유만으로 과제마다 새 Subnet을 만들 필요는 없습니다.** 과제에서 VPC 자원이 불필요하면 승인 요청의 network.required=false / shared_vpc_join=false로 선택적 Network 단계를 생략할 수 있습니다. 현재 샘플은 network.required=false / shared_vpc_join=false / create_subnet=false이며 과제 전용 서브넷을 사용하지 않습니다.

## 3. 기본 구성에서 제외한 대역

| 제외 대상 | 종전 설계값 | 현재 처리 |
|---|---|---|
| Cloud Run Direct VPC | 10.251.0.0/26 | Subnet 생성·VPC 연결 제거 |
| 과제별 Subnet | 172.31.110.0/24 샘플 | 기본 예약·생성 제외, 기존 자원 삭제 아님 |

기존 운영 자원이 위 대역을 사용하고 있다면 소스 변경만으로 IP가 회수되지 않습니다. 실사용·이전 Revision·연결·의존성을 확인한 뒤 VPC Admin이 별도 회수 여부를 판단합니다.

## 4. GCP 자원 설계

| 자원 | 이름 / 기준 | 프로젝트 | Subnet 필요 여부 | 실행·관리 |
|---|---|---|---|---|
| GKE Autopilot | gke-sbx-main-an3 | gcp-sbx-edp-gke01 | N1·N2, N3 제어 영역 설정 | 공통 기반 최초 구성·기존 재사용 |
| Cloud Build 기본 Pool | 이미지 빌드·릴리스·외부 Chart/이미지 미러링 | gcp-sbx-edp-gke01 | 사용자 Subnet 불필요 | tf-manager, 작업자가 빌드 명령 실행 |
| Cloud Build Private Pool | pool-sbxtest01 | gcp-sbx-edp-gke01 | N5 PSA 연결 사용, 일반 Subnet 생성 아님 | e2-standard-4 / disk 100GB / no-public-egress |
| Infrastructure Manager | 과제별 group/project/network/project-iam/data Deployment | gcp-sbx-edp-gke01 | 자체 전용 Subnet 없음, 현재 Terraform 실행에 Private Pool 사용 | tf-manager |
| Cloud Run | run-sbxtest01-provisioner | gcp-sbx-edp-gke01 | 전용 Subnet 없음 | sbx-manager, 요청 검증·Build 시작 |
| Workflows | workflow-sbxtest01-provision | gcp-sbx-edp-gke01 | 전용 Subnet 없음 | sbx-manager, OIDC로 API 호출 |
| Artifact Registry | ar-sbxtest01-platform | gcp-sbx-edp-gke01 | 전용 Subnet 없음, API 접근 경로 필요 | Docker 이미지·Helm Chart 보관 |
| 요청 GCS | gcp-sbx-edp-gke01-sbxtest01-requests | gcp-sbx-edp-gke01 | 전용 Subnet 없음 | 포털 승인 JSON 저장 |
| 배포 번들 GCS | gcp-sbx-edp-gke01-sbxtest01-bundles | gcp-sbx-edp-gke01 | 전용 Subnet 없음 | 릴리스·요청별 Terraform ZIP |
| Build 소스 GCS | gcp-sbx-edp-gke01-sbxtest01-build-source | gcp-sbx-edp-gke01 | 전용 Subnet 없음 | Build 입력 소스 |
| Secret Manager | jupyter-oauth-client-id / jupyter-oauth-client-secret | gcp-sbx-edp-gke01 | 전용 Subnet 없음 | Jupyter 로그인용 OAuth 값 |
| 공통 ALB | alb-sbxtest01-shared, URL Map·HTTP/HTTPS Proxy·VIP | gcp-sbx-edp-gke01 | N10 VIP용 /27과 N11 프록시 전용 /26 사용 | tf-manager, 인증서·DNS 별도 |
| 과제 Backend·NEG·Health Check | bes-jupyter-sbx01 / hc-jupyter-sbx01 / proxy-public NEG | gcp-sbx-edp-gke01 | Backend는 N2 Pod IP에 연결 | 과제 Deploy에서 구성 |
| Namespace·KSA·Hub·Proxy | sbx01 / ksa-jupyter-sbx01 | gcp-sbx-edp-gke01의 GKE | N2 | 자동 Deploy |
| 사용자 Notebook·PVC | 로그인·서버 시작 시 생성 | gcp-sbx-edp-gke01의 GKE | Pod는 N2, PVC는 별도 디스크 자원 | JupyterHub |
| 과제 Dataset·GCS | sbx01_main / pjt-net-hub-base-sbx01-data | 기존 SBX_PROJECT | 전용 Subnet 없음 | 기존 자원 편입 또는 승인 범위 구성 |
| 기존 BQ 데이터 | 승인 Dataset·Table | pjt-c-admin 등 | 전용 Subnet 없음 | 데이터 관리자 / VPC Admin 요청 |
| Cloud Identity Group | pgrp-gcp-dev-sbx01@sonmap.net | Workspace/Cloud Identity 조직 자원 | Subnet 없음 | tf-manager의 Terraform 05-group |

## 5. 통신·담당 요청사항

| 출발 | 목적지 | 포트 / 방식 | 담당 / 완료 기준 |
|---|---|---|---|
| Private Pool 작업자 N5 | GKE Private API N3의 실제 endpoint | TCP 443 | **VPC Admin**: 왕복 경로·방화벽·GKE 접근 허용 범위 확인, 점검 Build 성공 |
| 관리 PC/VM N7 | GKE Private API | TCP 443 | VPC Admin / 운영자: 관리 경로·IAM·Kubernetes 권한 확인 |
| Workflow | Cloud Run API | HTTPS 443 + OIDC | 플랫폼 관리자: sbx-manager의 Run Invoker |
| API·Build·Notebook | GCS·AR·IAM·BQ 등 Google API | HTTPS 443 | VPC Admin·플랫폼 관리자: DNS·Private Google Access/승인된 API 접근 경로 |
| ALB 프록시 N11 | GKE Proxy Pod N2 | TCP 8000 | VPC Admin: 프록시 전용 CIDR 허용 |
| Google Health Check | GKE Proxy Pod N2 | TCP 8000 | VPC Admin: 소스 35.191.0.0/16·130.211.0.0/22 허용 |
| 사내 사용자 / 승인된 사설 연결 | Jupyter 내부 ALB 도메인 | HTTPS 443 | 사설 경로·내부 DNS·Regional 인증서 별도 진행 |
| Notebook GSA | 기존 BQ Dataset | IAM·Dataset 조회 권한 | **VPC Admin 요청·완료 확인**, 데이터 IAM 권한 보유자가 실제 부여 |
| 기본 Cloud Build | 외부 이미지·패키지 저장소 | HTTPS 443 등 | 플랫폼 관리자: 외부 다운로드가 필요한 이미지 빌드·미러링 |

Private Pool과 GKE가 같은 프로젝트라도 N5에서 GKE Private API로의 라우팅이 자동 완성되는 것은 아닙니다. Peering 경유 제한을 고려해 VPN/BGP 등 실제 연결 방식과 추가 주소는 VPC Admin이 확정합니다. 해당 VPN 터널·BGP 주소는 현재 소스에서 정의하지 않으므로 임의 CIDR을 기재하지 않았습니다.

no-public-egress는 Pool의 공용 인터넷 egress를 제한하는 설정입니다. API·AR·GCS·Terraform Provider 다운로드까지 자동으로 해결하는 설정이 아니므로, 각 목적지의 사설/승인된 접근 경로를 실제 Build에서 검증해야 합니다.

## 6. 서비스 계정·초기 준비

| 주체 | 소속 / 값 | 용도 | 사전 준비 |
|---|---|---|---|
| tf-manager | tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com | 공통 구축·Build·IM·그룹·GKE·ALB | 프로젝트·VPC·과제 IAM 및 Cloud Identity Groups Administrator 역할 |
| sbx-manager | sbx-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com | Workflow·Run·Notebook의 Google API 접근 | KSA Workload Identity, 과제·기존 BQ 승인 권한 |
| KSA | sbx01 / ksa-jupyter-sbx01 | Notebook Pod의 Kubernetes 계정 | sbx-manager 연결 |
| Google 서비스 에이전트·노드 SA | 실제 gcp-sbx-edp-gke01 프로젝트 번호로 결정 | 관리형 서비스·노드 실행 | 사용자 관리 SA 두 개와 별도 |

현재는 포털이 승인 JSON을 저장한 뒤 작업자가 Deploy 명령을 실행하면 이후 배포 작업이 자동 처리됩니다. GCS 이벤트 자동 시작과 포털 완료 전달은 향후 작업입니다. 실행 계정 두 개를 공유하는 현재 PoC 구조에서는 Namespace만으로 과제별 GCP IAM이 격리되지 않습니다.

## 7. 실행·확정 순서

| 순서 | 수행 내용 | 담당 |
|---|---|---|
| 1 | 기존 SBX 프로젝트·기존 자원·실제 CIDR 인벤토리 확정 | 운영자·VPC Admin |
| 2 | 유지하는 GKE 대역·PSA·공통 Shared VPC 연결 검증 | VPC Admin |
| 3 | API·SA·권한 → 네트워크 → 공통 서비스 gcloud 개별 실행 | 프로젝트 작업자·VPC Admin 분담 |
| 4 | tf-manager 그룹 관리자 역할·실제 Customer ID·OAuth 준비 | Workspace/OAuth 담당자 |
| 5 | 이미지·Chart·소스 릴리스 준비, Private Pool 사설 접속 확인 | 작업자·VPC Admin |
| 6 | 기존 그룹·Dataset·GCS/state 편입 검토 후 Deploy | 작업자 |
| 7 | Build·IM·GKE·ALB·로그인·기존 BQ 실제 조회 검증 | 운영자·사용자 |

[실행 순서·명령 링크](work-order.md) / [개별 gcloud](../../02.sandbox_setup_01_gcloud/04-manual-gcloud.md) / [Deploy](../../02.sandbox_setup_01_gcloud/05-deploy.md)

## 공식 기준

- [Private Pool 네트워크](https://docs.cloud.google.com/build/docs/private-pools/set-up-private-pool-to-use-in-vpc-network)
- [Private Pool IP 범위 설정](https://docs.cloud.google.com/build/docs/private-pools/private-pool-config-file-schema)
- [Private GKE 접속](https://docs.cloud.google.com/build/docs/private-pools/accessing-private-gke-clusters-with-cloud-build-private-pools)
- [Cloud Run Direct VPC](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc)
- [GKE IP 범위](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/alias-ips)

## 내부 ALB 추가 기준

N10·N11·VIP 값은 신규 후보이며 실제 VPC·온프레미스 IPAM 조회 없이 확정한 값이 아닙니다. 기존 프록시 전용 Subnet이 있으면 N11을 추가 생성하지 않고 해당 이름·CIDR을 방화벽과 변수에 반영합니다. 기존 /27은 VIP용이고 프록시 전용은 최소 /26입니다. ALB·VIP 자원은 gcp-sbx-edp-gke01, Subnet은 Shared VPC Host gcp-prod-edp-hub-vpchost에 생성합니다. [전환·구축 절차](internal-alb-design.md)를 따릅니다.

## 서브넷 사용 계정과 관리 담당

Main GKE Subnet은 tf-manager·GKE 서비스 에이전트·Google APIs 서비스 에이전트에, ALB VIP Subnet은 tf-manager에만 Network User를 부여합니다. 프록시 Subnet·PSA·방화벽은 VPC Admin이 관리하고, tf-manager는 Host에서 Network Viewer를 사용해 조회합니다. [정확한 계정·gcloud 명령](../../02.sandbox_setup_01_gcloud/02-subnet-iam.md)을 따릅니다.
