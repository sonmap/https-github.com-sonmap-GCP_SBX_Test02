# 과제별 Infrastructure Manager Terraform

> 신규 프로젝트·과제 전용 GSA 생성은 [sbx03 신규 과제 절차](../01.docs/reference/sbx03-new-project-runbook.md)를 우선 적용합니다. 기존 프로젝트 재사용 절차와 구분하세요.

최초 1~3단계는 `02.sandbox_setup_01_gcloud/01-admin.md`·`02-network.md`·`03-foundation.md`의 개별 명령으로 이전했습니다. 여기는 과제별 자원만 남깁니다.

| Root | 기능 | 실행 계정 |
|---|---|---|
| deployments/05-group | Cloud Identity Group·구성원 관리 | tf-manager |
| deployments/10-project | 신규/기존 프로젝트와 API·자동화 IAM | tf-manager |
| deployments/20-network | 선택적 과제 서브넷·Shared VPC 연결 | tf-manager |
| deployments/30-project-iam | 과제 Google Group 프로젝트 권한 | tf-manager |
| deployments/40-data | Dataset·Bucket·중앙 GSA 접근·Workload Identity | tf-manager |

중앙 `sbx-manager`는 data source로 조회합니다. 이 Terraform은 GSA를 생성하지 않습니다. data.adopt_existing_resources는 Dataset/Bucket 편입용입니다. 기존 그룹·멤버는 identity의 별도 import 필드로 편입합니다.

각 Root는 `sbxtest01-<task>-<project-hash>-<stage>` Infrastructure Manager Deployment에서 독립 State로 관리합니다. VM에서 직접 terraform apply하지 않습니다. Kubernetes와 ALB 연결은 Cloud Build Runner가 처리합니다.

## 그룹 생성이 첫 단계입니다

05-group → 10-project → 선택적 20-network → 30-project-iam → 40-data 순서로 Infrastructure Manager가 적용합니다. 모든 단계는 tf-manager로 수행합니다. [권한 및 기존 그룹 편입](../01.docs/reference/cloud-identity-group-terraform.md)을 먼저 확인합니다.

## Host 네트워크 변경은 VPC Admin 수행

현재 API는 Subnet 생성과 Shared VPC 연결 변경을 요청하면 거절합니다. 기본 network.required=false를 사용하며, 별도 승인된 기존 Subnet 조회가 필요한 경우에만 required=true / create_subnet=false / shared_vpc_join=false로 요청합니다. VPC Admin이 먼저 해당 Subnet을 구성·연결하고 사용 권한을 부여해야 합니다. 과거 네트워크 리소스를 소유한 state는 이 변경으로 자동 변경·삭제하지 않습니다.
