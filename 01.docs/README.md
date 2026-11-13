# GKE Sandbox 시작하기

## 1차 공통 인프라 준비

관리 VM의 Test02 저장소 루트에서 작업합니다. 터미널을 바꿀 때는 `gcloud auth list --filter=status:ACTIVE --format='value(account)'`로 계정을 확인합니다. 기존 자원은 조회하고 필요한 명령만 실행합니다.

| 순서 | 작업 | 담당 |
|---|---|---|
| 1 | [공통 변수](../02.sandbox_setup_01_gcloud/00-variables.md)와 [API·서비스 계정·IAM](../02.sandbox_setup_01_gcloud/01-admin.md) | 플랫폼 프로젝트 관리자와 인프라 관리자 |
| 2 | [Shared VPC·네트워크](../02.sandbox_setup_01_gcloud/02-network.md)와 [서브넷 IAM](../02.sandbox_setup_01_gcloud/02-subnet-iam.md) | VPC 관리자 |
| 3 | [GKE·AR·내부 ALB 등 공통 기반](../02.sandbox_setup_01_gcloud/03-foundation.md) | 플랫폼 운영자. Private Pool 초기 생성은 VPC 관리자 |
| 4 | [Helm 차트·기본 이미지 반입과 Notebook 이미지 준비](../02.sandbox_setup_01_gcloud/04-manual-gcloud.md#6-chart와-기본-이미지-미러링) | 플랫폼 운영자 |
| 5 | [GKE 접속 확인](reference/sbx03-new-project-runbook.md#62-gke-복구와-private-pool-점검)과 [내부 HTTPS·DNS 확인](reference/sbx03-https-certificate-runbook.md) | 플랫폼 운영자와 DNS·인증서 담당자 |

기존 Workflows 자동 배포를 구성할 때는 [Cloud Identity 그룹 권한](reference/cloud-identity-group-terraform.md), [OAuth 설정과 플랫폼 릴리스](../02.sandbox_setup_01_gcloud/04-manual-gcloud.md#4-oauth-값-등록), [Private Pool의 GKE 접속 점검](reference/cloudbuild-private-gke-vpn-design.md)을 함께 확인합니다.

## 2차 Sandbox 배포

- [그룹 공유 PoC](../12.sandbox_shared/README.md)에서 Helm·kubectl 배포와 로컬 테스트 로그인을 진행합니다.
- [기존 Workflows 과제 배포](02-sandbox-deploy.md)에서 승인 요청으로 배포하는 절차를 확인합니다.

공통 자원이 준비된 환경은 2차부터 진행합니다. 설계와 오류 대응은 [참고 문서](reference)에서 확인합니다.
