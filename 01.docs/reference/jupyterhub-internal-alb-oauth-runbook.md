# 내부 ALB Jupyter OAuth·HTTPS 수행과 확인

> 실제 sbx03 접속 설정은 [내부 HTTPS ALB와 인증서](sbx03-https-certificate-runbook.md), [Google OAuth 로그인](sbx03-google-oauth-runbook.md)으로 나누어 정리했습니다. 아래 공통 설정 예시는 기존 과제의 참고용입니다.

전체 단계는 [실행 절차](runbook-two-stage.md)의 4단계와 11단계입니다. 아래 명령은 저장소 루트에서 실행합니다.

## 1. OAuth 담당자 준비

| 항목 | 현재 예제 |
|---|---|
| 웹 OAuth Client | Jupyter 로그인용 Client ID/Secret |
| Callback URL | https://jupyter-sbx01.sonmap.net/hub/oauth_callback |
| 허용 도메인 | sonmap.net |
| 허용 사용자 | 최종 승인 JSON의 identity.members |

OAuth Client 등록·정책은 담당자가 설정합니다. Google Group 관리는 tf-manager의 Cloud Identity 그룹 관리자 역할로 수행하며, Jupyter OAuth Client Secret과 별개입니다.

```bash
export ADMIN_ACCOUNT="son@sonmap.net"
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export REGION="asia-northeast3"
export SBX_NAME="sbx01"
export TF_MANAGER="tf-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"
export CLOUDSDK_CORE_ACCOUNT="${ADMIN_ACCOUNT}"

# 03-foundation에서 Secret 이름을 만든 후 실제 값을 입력합니다.
# 입력값은 화면에 표시하지 않습니다. set -x를 사용하지 않습니다.
read -r -s -p "OAuth Client ID: " OAUTH_CLIENT_ID
printf '\n'
read -r -s -p "OAuth Client Secret: " OAUTH_CLIENT_SECRET
printf '\n'
# 둘 다 입력했는지 확인한 뒤 아래 명령을 실행합니다.
test -n "${OAUTH_CLIENT_ID}" && test -n "${OAUTH_CLIENT_SECRET}"

# 입력이 비어 있으면 중단합니다. 값은 표준입력으로만 전달합니다.
if [ -n "${OAUTH_CLIENT_ID}" ] && [ -n "${OAUTH_CLIENT_SECRET}" ]; then
  printf '%s' "${OAUTH_CLIENT_ID}" | gcloud secrets versions add jupyter-oauth-client-id --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --data-file=-
  printf '%s' "${OAUTH_CLIENT_SECRET}" | gcloud secrets versions add jupyter-oauth-client-secret --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --data-file=-
fi
unset OAUTH_CLIENT_ID OAUTH_CLIENT_SECRET

# 값 자체를 출력하지 않고 버전 상태만 확인합니다.
gcloud secrets versions describe latest --secret=jupyter-oauth-client-id --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --format='value(state)'
gcloud secrets versions describe latest --secret=jupyter-oauth-client-secret --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --format='value(state)'
```

성공 기준: 두 latest 버전 ENABLED. Runner는 JupyterHub 설치 전에 이 값을 읽습니다.

## 2. 인증서 준비와 공통 ALB

Regional Internal ALB용 인증서는 asia-northeast3 리전 자원으로 준비합니다. 기존 Global 인증서를 그대로 연결하지 않습니다. 03-foundation의 인증서 조회 명령으로 `cert-jupyter-sbx01-self` 존재를 먼저 확인합니다. 인증서 담당자가 실제 도메인에 맞는 인증서를 별도 등록한 뒤 HTTPS Proxy/443 구성을 진행합니다. PEM/개인키는 저장소에 넣지 않습니다.

```bash
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
gcloud compute ssl-certificates describe cert-jupyter-sbx01-self --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
gcloud compute addresses describe ip-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --format='value(address)'
```

VPC Admin의 사설 경로 준비 후 내부 DNS 담당자가 Jupyter 도메인의 A 레코드를 위 사설 VIP로 연결합니다. 사용자 PC는 사내망 또는 승인된 VPN/Interconnect 경로에 있어야 합니다. PoC hosts 파일을 사용해도 동일한 도메인과 인증서를 사용합니다. self-managed 인증서의 클라이언트 신뢰 등록은 해당 PoC 정책에 따라 처리합니다.

## 3. 과제 배포 후 Backend 확인

```bash
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
gcloud compute backend-services get-health "bes-jupyter-${SBX_NAME}" --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
gcloud compute url-maps describe urlmap-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --format='yaml(hostRules,pathMatchers)'
```

성공 기준: Backend HEALTHY, 요청 도메인이 해당 과제 Backend로 연결됩니다. 공통 ALB는 기반 단계가 준비하고, 과제 배포 후 Reconciler가 Health Check/Backend/NEG/Host 경로를 연결합니다. GKE Service는 ClusterIP이며 사용자 접속은 Regional Internal ALB 경로입니다.

## 4. 사용자 브라우저 확인

승인된 계정으로 `https://jupyter-sbx01.sonmap.net`에 접속 → Google 로그인 → Notebook 서버 시작을 수행합니다. 사용자 Pod/PVC는 이 시점에 생성될 수 있습니다.

| 증상 | 확인 |
|---|---|
| 이름을 찾을 수 없음 | DNS/hosts의 IP |
| 인증서 오류 | 실제 도메인·인증서 SAN·유효기간·신뢰 |
| 502/503 | Backend health·Proxy Pod·NEG endpoint |
| redirect_uri_mismatch | OAuth Client의 Callback URL과 실제 도메인 |
| 사용자 로그인 거부 | 승인 JSON identity.members·hosted_domain·OAuth 정책 |
| 로그인 후 서버 시작 실패 | Pod 이벤트·이미지 Pull·Quota·PVC·KSA 연결 |

Secret 변경은 등록 즉시 기존 JupyterHub 설정을 자동 갱신하지 않습니다. 재배포할 경우 새 최종 승인 요청/Request ID로 설치 단계가 다시 실행되도록 하거나, 승인된 운영 절차로 해당 Helm 설정을 갱신합니다. 기존 사용자 PVC를 삭제하여 해결하지 않습니다.

기존 테스트용 외부 Global ALB는 이 소스 변경으로 자동 비활성화되지 않습니다. 내부 ALB 접속과 DNS 전환을 확인한 뒤 외부 Forwarding Rule·Proxy·Backend 등 의존성을 조회해 담당자가 별도 폐기합니다. [전환 확인 목록](internal-alb-design.md)을 따릅니다.
