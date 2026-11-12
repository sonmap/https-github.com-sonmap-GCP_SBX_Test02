# IP 최소화 구성

중앙 GKE와 Private Pool 배포 자동화는 유지하고 불필요한 별도 대역을 만들지 않습니다. 기존 운영 자원을 삭제하거나 GKE 대역을 임의로 축소하지 않습니다.

| 항목 | IP 최소화 처리 | 추가 예약 |
|---|---|---|
| Cloud Run 요청 API | VPC 연결 해제, Google API로 GCS·Cloud Build 호출 | 전용 Subnet 0 |
| Workflows·AR·GCS·Secret Manager | 전용 Subnet 없이 관리형 API 사용 | 전용 Subnet 0 |
| 과제 프로젝트 | 기존 프로젝트 사용, network.required=false | 과제별 Subnet 0 |
| 과제 JupyterHub·Notebook | 중앙 GKE Namespace와 기존 Pod 대역 사용 | 과제별 Pod CIDR 별도 예약 0, 실제 Pod IP는 소비 |
| Main GKE | Node 10.252.0.0/24·Pod 100.64.128.0/19·제어 영역 10.253.3.0/28 유지·재사용 | 기존 사용이면 새 대역 추가 없음 |
| 내부 ALB | 기존 VIP 서브넷 172.31.96.0/27 재사용, 기존 프록시 전용 Subnet 재사용 우선 | VIP용 신규 대역 예약 없음, 프록시 신규 시 /26 64주소 추가 |
| Private Pool | 기존 호환 PSA 할당에 여유가 있으면 재사용, 없으면 현재 10.250.0.0/24 설계 검증 | 신규 PSA는 최소 /24 단위 |

## 유지하는 대역을 줄이지 않은 이유

- GKE Node/Pod 대역은 실제 동시 Pod·자원·증설 여유를 확인한 뒤 별도 용량 설계해야 합니다. 기존 클러스터의 대역을 소스에서 바꾸는 것으로 IP가 회수되지는 않습니다.
- Google 서비스 PSA 예약 범위의 최소 크기는 /24입니다. Private Pool의 작업자 범위 자체는 더 작게 지정할 수 있지만, 이것이 PSA /24 예약을 /29로 줄여 주는 것은 아닙니다. 기존 PSA를 재사용할 수 있는지는 VPC Admin이 서비스별 배정 현황을 확인합니다. 공유 가능한 기존 할당을 사용한다면 PSA_NAME·Pool의 peered-network-ip-range 등을 실제 값에 맞춰 일관되게 조정합니다.
- IP 최소화 후에도 Private Pool → GKE 사설 API 통신 경로는 필요합니다. VPN/BGP 등 추가 경로 주소는 VPC Admin이 확정합니다.

[PSA 최소 할당 크기](https://docs.cloud.google.com/vpc/docs/configure-private-services-access) / [Private Pool 범위 설정](https://docs.cloud.google.com/build/docs/private-pools/private-pool-config-file-schema)

## 적용 순서

1. [02-network](../../02.sandbox_setup_01_gcloud/02-network.md)는 Main GKE·PSA·기본 방화벽만 준비합니다.
2. [03-foundation](../../02.sandbox_setup_01_gcloud/03-foundation.md)의 Cloud Run deploy와 플랫폼 릴리스 update에는 --clear-network가 포함되어 있습니다. 새 서비스는 Direct VPC 없이 구성되고, 기존 서비스는 다음 적용 시 VPC 연결을 해제합니다.
3. [승인 요청 샘플](../../05.sandbox_json/sbx01-approved-request.json)은 기존 SBX 프로젝트를 사용하고 과제 Network 단계를 생략합니다. 포털 요청에도 동일한 기준을 반영합니다. 별도 승인 시에만 선택적 20-network 모듈을 사용할 수 있습니다.
4. API의 요청 검증·GCS 다운로드·Build 시작이 성공하는지 확인한 후 Private Pool·GKE Deploy 및 사용자 접속을 확인합니다.
5. 이미 만들어진 Cloud Run Subnet·과제 Subnet이 있다면 실제 사용과 이전 Revision 등 의존성을 조회합니다. 다른 사용자가 없다는 확인 후 VPC Admin이 별도 IP 회수 여부를 결정합니다. 이 변경에는 실제 자원 삭제 명령이 없습니다.

현재 API가 사설 내부 서비스에 직접 접속하지 않는다는 기준입니다. Google API 접근을 반드시 특정 VPC 경로로 제한하는 기존 조직 정책이 있다면 해당 정책과 연결 해제의 적합성을 적용 전에 확인합니다.

## 기존 서비스에서 직접 확인할 명령

아래는 작업자가 실행할 명령입니다. 소스 수정 과정에서 실제 GCP에 실행하지 않았습니다. 조회 후 현재 서비스가 요청 API인지 확인하고 연결 해제 명령을 실행합니다.

```bash
export ADMIN_ACCOUNT="son@sonmap.net"
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export REGION="asia-northeast3"
export TF_MANAGER="tf-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"

gcloud run services describe run-sbxtest01-provisioner --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --format=export

gcloud run services update run-sbxtest01-provisioner --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --clear-network
```

기존 Subnet 예약이 자동 해제되는 것은 아닙니다. 위 표의 0은 새 구성의 추가 예약 기준이며 실제 현재 IP 확보량을 의미하지 않습니다.

## 내부 ALB 추가 요구 반영

사용자 사설 접속의 VIP는 기존 172.31.96.0/27 서브넷에서 할당합니다. 프록시 전용 Subnet은 /28로 만들 수 없으며 최소 /26입니다. 같은 VPC·리전에 이미 있다면 공유하여 추가 /26 예약을 피합니다. 후보 CIDR·소유 프로젝트는 [내부 ALB 설계](internal-alb-design.md)에서 확인합니다.
