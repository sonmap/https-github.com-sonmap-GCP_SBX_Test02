# 실제 실행 구조·계정·관리 범위

실제 명령은 [실행 절차](runbook-two-stage.md), 전체 순서는 [시작 안내](../README.md)를 따릅니다. 이 문서는 현재 코드가 누가 무엇을 실행하는지 정리합니다.

## 사람이 실행하는 작업과 자동 작업

| 구간 | 누가 실행 | 실제 입력/프로그램 | 실제 결과 |
|---|---|---|---|
| 최초 관리자 준비 | 기존 권한 관리자 | 02 폴더의 01-admin.md | API·sbx-manager·tf-manager·IAM |
| 공통 네트워크/기반 | VPC Admin 네트워크·Subnet IAM 후 tf-manager 기반 구축 | 02-network.md → 02-subnet-iam.md → 03-foundation.md | Subnet/PSA/Pool/GKE/Run/Workflow/ALB |
| 로그인/그룹 준비 | 운영자·Workspace/OAuth 관리자 | Secret 등록·OAuth Callback·tf-manager 그룹 관리자 역할 부여 | 로그인·Terraform Group 생성 사전 조건 |
| 플랫폼/사용자 이미지 | tf-manager Build | 04-manual-gcloud.md의 개별 gcloud 빌드 명령 | 버전 이미지·소스 ZIP·Chart |
| 최종 신청/승인 | 승인 담당자·운영자 | 실제 신청 JSON·release.json | .local/request.json |
| 접수 | 운영자 → sbx-manager Workflow/Run | 05-deploy.md의 gcloud workflows run → /provision | 승인 검증·요청별 ZIP·부모 Build 시작 |
| 과제 자원 | tf-manager 부모 Build/IM | Terraform Group → 전파 대기 → Project → Network 선택 → IAM → Data | Google Group·과제 자원·WI Binding |
| Kubernetes/접속 경로 | tf-manager 자식 Private Pool Build | apply_gke_workload.py → reconcile_postdeploy.py | Namespace·JupyterHub·NEG·Backend·ALB 경로 |

폴더 번호를 따라 코드를 수동 실행하지 않습니다. 수동 진입점은 02 폴더의 gcloud 명령, 이미지 준비 명령, 마지막 승인 요청 제출입니다. Terraform Root에서 직접 apply하거나 Cloud Run main.py를 VM에서 실행할 필요가 없습니다.

## 현재 사용하는 프로젝트

| 프로젝트 | 코드에서 쓰는 역할 |
|---|---|
| gcp-sbx-edp-gke01 | SA·AR·Cloud Build·Private Pool·Run·Workflow·승인/Bundle/Source 버킷 |
| gcp-prod-edp-hub-vpchost | Shared VPC·서브넷·PSA·방화벽 |
| gcp-sbx-edp-gke01 | 기존/신규 Main Autopilot GKE·공통 ALB |
| pjt-net-hub-base | 예제의 기존 과제 프로젝트·Dataset·GCS·Query Job |
| pjt-c-admin 등 별도 데이터 프로젝트 | 기존 BQ 데이터; 조회 권한은 해당 관리자가 별도 관리 |

런타임 Schema/YAML/보조 스크립트 일부에는 이 PoC 대상이 고정되어 있습니다. 프로젝트를 바꿀 때는 한 변수만 바꾸지 말고 전체 대상과 권한을 함께 검토합니다.

## 실제 실행 계정

| 계정 | 실행 위치·권한 용도 |
|---|---|
| 기존 관리자/운영자 | 초기 Project/Folder/Billing IAM·승인 JSON 업로드·Workflow 호출 |
| sbx-manager | Run/Workflow Runtime·Notebook GSA |
| tf-manager | 기반 구축·모든 Build/IM·GKE·Helm·ALB |
| Google 서비스 에이전트/노드 기본 SA | API/노드 동작; 두 사용자 관리 SA와 별도 |
| ksa-jupyter-sbx01 등 KSA | 과제 Namespace 안의 Kubernetes 계정; sbx-manager로 WI 연결 |

실제 SA ID는 하이픈, 표시 이름은 sbx_manager/tf_manager입니다. 두 사용자 관리 계정을 합친 PoC이므로 Notebook도 sbx-manager의 Build 제출·tf-manager actAs 권한과 여러 과제의 데이터 권한을 공유합니다. Namespace만으로 과제별 GCP IAM은 격리되지 않습니다. 신뢰 사용자 PoC 범위를 넘어 운영하려면 Notebook GSA 분리가 필요합니다.

## 어떤 자원이 언제 준비되는가

| 시점 | 현재 리소스/이름 |
|---|---|
| 최초 기반 | ar-sbxtest01-platform, pool-sbxtest01, run-sbxtest01-provisioner, workflow-sbxtest01-provision |
| 최초 기반 GCS | <SBX_GKE_PROJECT>-sbxtest01-requests / -sbxtest01-bundles / -sbxtest01-build-source |
| 최초 Build | sbxtest01-automation-runner:bootstrap, run-sbxtest01-provisioner:bootstrap |
| 플랫폼 릴리스 | git-<커밋12자리>의 Runner/API 이미지·platform-releases/<release>/sandbox-source.zip·release.json |
| 요청 접수 | requests/<request_id>/<release_id>/ 단계별 ZIP·manifest·dispatch 기록 |
| 과제 IM | sbxtest01-<task>-<project-hash>-project/network/project-iam/data |
| Jupyter 설치 후 | namespace sbx01, KSA, Hub/Proxy, proxy-public NEG |
| 사용자 로그인 후 | 사용자 Notebook Pod·사용자 PVC |
| 접속 경로 연결 | hc-jupyter-<task>, bes-jupyter-<task>, 공통 URL Map Host 경로 |

공통 ALB는 기반 단계가 한 번 만들고 과제별 Reconciler가 경로를 붙입니다. Worker Pool와 GKE는 준비되어 있어도 승인 요청 배포 전에는 과제 JupyterHub가 없을 수 있고, 사용자 Pod/PVC는 로그인 후에 생성됩니다.

## State와 기존 자원

- 08 폴더의 각 Terraform Root는 독립 Infrastructure Manager Deployment/State입니다.
- create_project=false이면 기존 프로젝트를 사용합니다. network.required=false이면 Network 적용을 생략합니다.
- 현재 40-data는 Dataset/GCS/Workload Identity를 관리하는 필수 단계입니다. 별도 BQ만 조회하며 과제 데이터 자원을 생략하는 설정은 아직 없습니다.
- adopt_existing_resources=true이면 기존 Dataset와 Bucket 두 개를 요청 Bundle의 정적 imports.tf로 편입합니다. 중앙 sbx-manager는 조회하며 생성/import하지 않습니다.
- 기존 Terraform/다른 IM State가 자원을 관리한다면 기존 배포를 중지하고 State 소유권을 정리한 뒤 편입합니다. 무조건 destroy하지 않습니다.

## 자동으로 준비되지 않는 항목

| 항목 | 실제 담당·확인 시점 |
|---|---|
| Private Pool → GKE Private IP 경로 | 네트워크 담당; 실행 절차 5단계의 실제 Pool Build로 확인 |
| Workspace tf-manager 그룹 관리자 역할 부여 | Workspace 관리자; 4단계 |
| OAuth 웹 Client/Callback | OAuth 담당자; 4단계 |
| SSL 인증서·DNS/PoC hosts | 인증서/DNS 담당자; HTTPS 기반 준비·11단계 |
| 기존 별도 BQ Dataset 조회 권한 | 데이터 프로젝트 관리자; Notebook 데이터 조회 전 |

사용자 Jupyter 접속은 Regional Internal ALB의 사설 VIP를 사용합니다. GKE API/노드도 private 설정입니다. 요청 API인 Cloud Run은 기존처럼 IAM 인증과 ingress=all이며 VPC 미연결입니다. 이 변경은 사용자용 ALB를 내부화하는 것이며 모든 Google API를 사설화하는 변경은 아닙니다. [내부 ALB 설계](internal-alb-design.md)를 확인합니다.

## 새 소스 구조의 릴리스 경계

소스 ZIP의 Root는 `08.sandbox_setup_02_terraform/deployments/`입니다. 폴더 변경 후 새 API 이미지와 새 ZIP을 같은 릴리스로 게시합니다. 이전 경로의 ZIP을 새 API와 섞지 않습니다. 릴리스/미러링은 외부 패키지를 받는 완전관리형 Build, 과제 배포와 GKE 접속 점검은 외부 IP 없는 Private Pool을 사용합니다.

별도 데이터레이크 권한 자동화 서비스는 제거되었습니다. 현재 소스 변경만으로 이전에 생성된 GCP 서비스·기존 BQ를 삭제하지 않습니다. 실제 클라우드 배포 여부는 Build/IM/Kubernetes 조회로 확인합니다.

## Host IAM과 ALB 배포 경계

VPC Admin이 네트워크·서브넷·방화벽·PSA와 Private Pool 초기 연결을 준비합니다. tf-manager에는 Host Network Viewer와 지정한 GKE·VIP 서브넷 Network User를 부여하며, Host 전체 Network User·Network Admin·Security Admin·Service Networking Admin은 기본 부여하지 않습니다. ALB·VIP·Backend의 생성 권한은 gcp-sbx-edp-gke01에서 유지합니다. [서브넷 IAM](../../02.sandbox_setup_01_gcloud/02-subnet-iam.md)과 [기존 권한 정리](../../02.sandbox_setup_01_gcloud/06-iam-migration.md)를 확인합니다.
