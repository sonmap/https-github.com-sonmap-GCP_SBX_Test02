# Sandbox JupyterHub 내부 ALB — Google 관리 인증서

Sandbox JupyterHub 3개를 사내 사용자가 HTTPS로 접속하도록 리전 내부 ALB와 Certificate Manager 관리 인증서를 구성합니다. 운영 `alb-prod-l2comn-01`과 같은 방식이며 자체 서명 인증서를 사용하지 않습니다. 사내 PC가 이미 신뢰하는 체인이므로 클라이언트에 인증서를 따로 설치하지 않습니다.

기존 [자체 서명 인증서 절차](sbx03-https-certificate-runbook.md)는 이 문서로 대체합니다.

## 허브와 도메인

| 용도 | 약자 | FQDN |
|---|---|---|
| 일반 | `com` | `jupyter-com.dlk.lguplus.co.kr` |
| 보안 | `sec` | `jupyter-sec.dlk.lguplus.co.kr` |
| System Analysis | `sa` | `jupyter-sa.dlk.lguplus.co.kr` |

약자는 FQDN과 자원 이름 전체에 같게 적용합니다. 용도별 자원은 `bes-jupyter-<약자>`, `hc-jupyter-<약자>`, `neg-jupyter-<약자>`, `dnsauth-jupyter-<약자>`, 네임스페이스 `jhub-<약자>`를 사용합니다.

## 공용 자원과 용도별 자원

VIP·전달 규칙·HTTPS 프록시·URL 맵·인증서는 하나씩만 만들고, URL 맵의 호스트 규칙으로 세 허브에 분기합니다. ALB를 세 벌 만들지 않습니다. 운영 인증서도 `gitssm`과 `git.gitssm` 두 도메인을 한 장에 담았으며 같은 방식입니다.

| 구분 | 자원 | 수량 |
|---|---|---|
| 공용 | 사설 VIP `ip-alb-sbxtest01-shared` | 1 |
| 공용 | 전달 규칙 `fr-alb-sbxtest01-shared-https` | 1 |
| 공용 | HTTPS 프록시 `https-proxy-alb-sbxtest01-shared` | 1 |
| 공용 | URL 맵 `urlmap-alb-sbxtest01-shared` | 1 |
| 공용 | 인증서 `cert-jupyter-sbx` — 도메인 3개 | 1 |
| 공용 | SSL 정책 `sslpolicy-sbx01` | 1 |
| 용도별 | DNS 인증 | 3 |
| 용도별 | 백엔드 서비스·상태 점검·NEG | 각 3 |
| 용도별 | 외부DNS CNAME·내부DNS A | 각 3 |

내부 A 레코드 3건은 모두 같은 VIP를 가리킵니다.

## 기준 값

| 항목 | 값 |
|---|---|
| ALB 프로젝트 / 리전 | `gcp-sbx-edp-gke01` / `asia-northeast3` |
| Shared VPC / VIP 서브넷 | `gcp-prod-edp-hub-vpchost`의 `vpc-prod-edp-hub` / `subnet-prod-edp-alb-frontend-an3` |
| 인증서 | `cert-jupyter-sbx` — Regional, Google 관리 |
| SSL 정책 | `sslpolicy-sbx01` — TLS 1.2 Compatible |
| 백엔드 | GKE NEG · JupyterHub 프록시 TCP 8000 |
| 백엔드 타임아웃 | 1,800초 |

## 운영과의 차이

| 항목 | 운영 `alb-prod-l2comn-01` | Sandbox | 사유 |
|---|---|---|---|
| 인증서 방식 | Certificate Manager 관리 인증서 | 동일 | 사내 신뢰 체인 사용 |
| SSL 정책 | TLS 1.2 Compatible | 동일 | 운영 기준 일치 |
| 백엔드 타임아웃 | 1,800초 | 동일 | Notebook WebSocket 유지 |
| 인증서 도메인 수 | 2 | 3 | 허브 3개 |
| 백엔드 유형 | PSC NEG → Secure Source Manager | GKE NEG | 서비스 대상이 다름 |
| 상태 점검 | 없음 — PSC는 구성 불가 | HTTP 8000 `/_chp_healthz` | GKE NEG는 필수 |

## 두 DNS 레코드의 역할

검증용 CNAME과 서비스용 A 레코드는 등록 위치와 목적이 다릅니다.

| 레코드 | 등록 위치 | 역할 |
|---|---|---|
| `_acme-challenge_<발급값>.<FQDN>` CNAME | 외부DNS | 인증서 발급·갱신 검증 |
| `<FQDN>` A | 내부DNS | 사용자 접속 |

검증 CNAME은 Google 검증 서버가 인터넷에서 조회하므로 외부DNS에 있어야 합니다. 서비스 A 레코드는 내부 VIP를 가리키므로 내부DNS에만 등록합니다. 운영의 `gitssm.dlk.lguplus.co.kr`도 같은 구조입니다.

검증 CNAME은 인증서 자동 갱신 때마다 재검증에 사용하므로 발급 완료 후에도 삭제하지 않습니다. DNS 요청서의 기타 항목에 이 내용을 적어 정리 대상으로 오인되지 않게 합니다.

도메인마다 DNS 인증을 따로 만들며 각 인증이 CNAME 한 쌍을 발급합니다. 운영 요청서에서 두 도메인의 접두 라벨이 같아 보였지만 대상값은 서로 달랐습니다. 값을 추측하지 말고 조회 출력을 그대로 옮깁니다.

## 작업 순서

VIP 예약과 DNS 인증 생성은 서로 의존하지 않습니다. 둘을 먼저 끝내면 외부DNS·내부DNS 요청을 동시에 제출할 수 있어 대기가 한 번으로 줄어듭니다. 운영에서는 두 요청이 4주 떨어져 있었습니다.

| 단계 | 담당 | 선행 조건 |
|---|---|---|
| 1. VIP 예약 | 인프라 작업자 | 프록시 전용 Subnet ACTIVE |
| 2. DNS 인증 3건 생성 | 인프라 작업자 | FQDN 확정 |
| 3. 외부DNS CNAME 3건 등록 | DNS 담당자 | 2의 출력값 |
| 4. 내부DNS A 3건 등록 | DNS 담당자 | 1의 VIP 값 |
| 5. 인증서 생성·ACTIVE 확인 | 인프라 작업자 | 3 완료 |
| 6. SSL 정책·HTTPS 프록시·전달 규칙 | 인프라 작업자 | 5 ACTIVE |
| 7. URL 맵 호스트 규칙 3개 | 인프라 작업자 | 백엔드 3개 생성 |
| 8. 접속 검증 | 인프라 작업자 | 4·6·7 완료, 백엔드 HEALTHY |

## 1. API 활성화와 DNS 인증 생성

[03-foundation](../../02.sandbox_setup_01_gcloud/03-foundation.md) 27단계의 VIP 예약을 마친 뒤 수행합니다.

```bash
export JUPYTER_DOMAIN_SUFFIX="dlk.lguplus.co.kr"
export JUPYTER_HUBS="com sec sa"

gcloud services enable certificatemanager.googleapis.com \
  --project="${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}"
```

```bash
for H in ${JUPYTER_HUBS}; do
  gcloud certificate-manager dns-authorizations create "dnsauth-jupyter-${H}" \
    --project="${SBX_GKE_PROJECT}" --location="${REGION}" \
    --domain="jupyter-${H}.${JUPYTER_DOMAIN_SUFFIX}" --account="${ADMIN_ACCOUNT}"
done
```

DNS 담당자에게 전달할 CNAME 3건을 한 번에 조회합니다. 세 번째·네 번째 칸이 요청서의 도메인명과 IP 정보입니다.

```bash
gcloud certificate-manager dns-authorizations list \
  --project="${SBX_GKE_PROJECT}" --location="${REGION}" --account="${ADMIN_ACCOUNT}" \
  --format="table(name,domain,dnsResourceRecord.name,dnsResourceRecord.data)"
```

콘솔에서는 Network Services → Certificate Manager → DNS authorizations에서 같은 값을 확인합니다.

VIP 예약값도 조회해 내부DNS 요청에 사용합니다. 세 도메인 모두 이 한 주소를 사용합니다.

```bash
gcloud compute addresses describe ip-alb-sbxtest01-shared \
  --project="${SBX_GKE_PROJECT}" --region="${REGION}" \
  --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" \
  --format='value(address)'
```

## 2. DNS 요청서

두 건을 동시에 제출합니다. `<발급값>`과 `<VIP 예약값>`은 위 조회 결과로 대체합니다. 도메인마다 대상값이 다르므로 한 줄씩 그대로 옮깁니다.

외부DNS — 인증서 검증용

```text
1.작업대상(외부DNS or 내부DNS) :
외부DNS

2.작업내용
[등록]
도메인명 : _acme-challenge_<발급값>.jupyter-com.dlk.lguplus.co.kr
IP 정보 : <발급값>.asia-northeast3.authorize.certificatemanager.goog
TYPE : CNAME

[등록]
도메인명 : _acme-challenge_<발급값>.jupyter-sec.dlk.lguplus.co.kr
IP 정보 : <발급값>.asia-northeast3.authorize.certificatemanager.goog
TYPE : CNAME

[등록]
도메인명 : _acme-challenge_<발급값>.jupyter-sa.dlk.lguplus.co.kr
IP 정보 : <발급값>.asia-northeast3.authorize.certificatemanager.goog
TYPE : CNAME

3.등록/변경/삭제 목적(주요 서비스 대상(사용자) 및 주요 서비스 내용)
Sandbox JupyterHub 내부 ALB의 SSL 인증서 프로비저닝을 위해 DNS 승인이 필요하여 CNAME 등록이 필요합니다.

5.기타((상단 요청 항목 외 작업자에게 공유할 내용 or 고려사항을 기재하여 주십시오))
해당 CNAME은 인증서 자동 갱신 시 재검증에 사용되므로 발급 완료 후에도 유지되어야 합니다.
```

내부DNS — 서비스 접속용

```text
1.작업대상(외부DNS or 내부DNS) :
내부DNS

2.작업내용
[등록]
도메인명 : jupyter-com.dlk.lguplus.co.kr
IP 정보 : <VIP 예약값>
TYPE : A

[등록]
도메인명 : jupyter-sec.dlk.lguplus.co.kr
IP 정보 : <VIP 예약값>
TYPE : A

[등록]
도메인명 : jupyter-sa.dlk.lguplus.co.kr
IP 정보 : <VIP 예약값>
TYPE : A

3.등록/변경/삭제 목적(주요 서비스 대상(사용자) 및 주요 서비스 내용)
Sandbox JupyterHub 내부 ALB 접속을 위해 내부도메인 등록이 필요합니다.
```

## 3. 인증서 생성

외부DNS에 CNAME 3건이 모두 반영된 뒤 수행합니다. 반영 전에 생성하면 검증에 실패하고 재시도를 기다려야 합니다. 세 도메인을 한 장에 담습니다.

```bash
gcloud certificate-manager certificates create cert-jupyter-sbx \
  --project="${SBX_GKE_PROJECT}" --location="${REGION}" \
  --domains="jupyter-com.${JUPYTER_DOMAIN_SUFFIX},jupyter-sec.${JUPYTER_DOMAIN_SUFFIX},jupyter-sa.${JUPYTER_DOMAIN_SUFFIX}" \
  --dns-authorizations="dnsauth-jupyter-com,dnsauth-jupyter-sec,dnsauth-jupyter-sa" \
  --account="${ADMIN_ACCOUNT}"
```

ACTIVE가 될 때까지 상태를 확인합니다. 보통 수 분에서 수십 분이 걸립니다.

```bash
gcloud certificate-manager certificates describe cert-jupyter-sbx \
  --project="${SBX_GKE_PROJECT}" --location="${REGION}" \
  --account="${ADMIN_ACCOUNT}" \
  --format="value(managed.state,managed.authorizationAttemptInfo)"
```

`FAILED`이면 `authorizationAttemptInfo`에서 어느 도메인이 실패했는지 확인합니다. 대부분 CNAME 미반영이거나 대상값 오기입니다. 도메인 하나라도 실패하면 인증서 전체가 발급되지 않습니다.

## 4. SSL 정책과 HTTPS 프런트엔드

운영과 같은 TLS 1.2 하한을 적용합니다. 정책을 지정하지 않으면 기본값인 TLS 1.0으로 생성되어 운영과 동작이 달라집니다.

```bash
gcloud compute ssl-policies create sslpolicy-sbx01 \
  --project="${SBX_GKE_PROJECT}" --region="${REGION}" \
  --profile=COMPATIBLE --min-tls-version=1.2 \
  --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
```

```bash
gcloud compute target-https-proxies create https-proxy-alb-sbxtest01-shared \
  --project="${SBX_GKE_PROJECT}" --region="${REGION}" \
  --url-map=urlmap-alb-sbxtest01-shared --url-map-region="${REGION}" \
  --certificate-manager-certificates="projects/${SBX_GKE_PROJECT}/locations/${REGION}/certificates/cert-jupyter-sbx" \
  --ssl-policy=sslpolicy-sbx01 --ssl-policy-region="${REGION}" \
  --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
```

```bash
gcloud compute forwarding-rules create fr-alb-sbxtest01-shared-https \
  --project="${SBX_GKE_PROJECT}" --region="${REGION}" \
  --load-balancing-scheme=INTERNAL_MANAGED \
  --network="projects/${VPC_HOST_PROJECT}/global/networks/${NETWORK}" \
  --subnet="projects/${VPC_HOST_PROJECT}/regions/${REGION}/subnetworks/${ILB_VIP_SUBNET}" \
  --address=ip-alb-sbxtest01-shared --ports=443 \
  --target-https-proxy=https-proxy-alb-sbxtest01-shared \
  --target-https-proxy-region="${REGION}" --allow-global-access \
  --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
```

## 5. URL 맵 호스트 규칙

허브별 백엔드가 생성된 뒤 호스트 규칙을 추가합니다. 기본 백엔드는 어느 호스트에도 해당하지 않는 요청을 받습니다.

```bash
for H in ${JUPYTER_HUBS}; do
  gcloud compute url-maps add-path-matcher urlmap-alb-sbxtest01-shared \
    --project="${SBX_GKE_PROJECT}" --region="${REGION}" \
    --path-matcher-name="pm-${H}" \
    --new-hosts="jupyter-${H}.${JUPYTER_DOMAIN_SUFFIX}" \
    --default-service="projects/${SBX_GKE_PROJECT}/regions/${REGION}/backendServices/bes-jupyter-${H}" \
    --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
done
```

백엔드 타임아웃은 운영과 같은 1,800초로 둡니다. 기본값 30초에서는 Notebook 터미널과 WebSocket 세션이 끊깁니다.

```bash
for H in ${JUPYTER_HUBS}; do
  gcloud compute backend-services update "bes-jupyter-${H}" \
    --project="${SBX_GKE_PROJECT}" --region="${REGION}" --timeout=1800 \
    --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
done
```

## 6. 접속 검증

사내 VM에서 세 도메인을 각각 확인합니다. 셋 모두 같은 VIP로 해석되어야 하며 응답은 허브마다 달라야 합니다.

```bash
for H in com sec sa; do
  echo "== ${H}"
  getent ahostsv4 "jupyter-${H}.dlk.lguplus.co.kr"
  curl -sS --connect-timeout 5 -o /dev/null \
    -w 'remote_ip=%{remote_ip} http=%{http_code} redirect=%{redirect_url}\n' \
    "https://jupyter-${H}.dlk.lguplus.co.kr/hub/login"
done
```

| 결과 | 확인할 부분 |
|---|---|
| 이름 조회 실패 | 내부DNS A 레코드 |
| 연결 타임아웃 | 전달 규칙, VIP, Shared VPC 경로, 방화벽 |
| TLS 오류 | 인증서 ACTIVE 상태, 해당 도메인이 인증서에 포함되었는지 |
| 세 도메인이 같은 허브로 감 | URL 맵 호스트 규칙 |
| `502`·`503` | 백엔드 HEALTHY, GKE NEG |
| 로그인 화면 | [Google OAuth 설정](sbx03-google-oauth-runbook.md)으로 이동 |

백엔드 상태는 허브별로 확인합니다. GKE NEG는 상태 점검이 필수이므로 `UNHEALTHY`이면 방화벽과 Pod 포트를 먼저 봅니다.

```bash
for H in ${JUPYTER_HUBS}; do
  gcloud compute backend-services get-health "bes-jupyter-${H}" \
    --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}"
done
```

## 용량 검토 — 사용자 약 500명

두 대역이 제약이 됩니다. 적용 전에 확인해야 합니다.

| 항목 | 현재 설계 | 제약 | 대응 |
|---|---|---|---|
| Pod 대역 `100.64.128.0/19` | 8,192개 | 노드당 기본 `/24` 할당 시 최대 32노드 | 클러스터 생성 시 `--max-pods-per-node`를 낮춰 노드당 할당 대역을 줄입니다. IP 추가가 필요 없습니다 |
| 프록시 전용 `/26` | 64개 | Envoy 작업자 IP | 장시간 WebSocket 연결이 많으므로 가능하면 확대하고, 유지 시 사용량을 관찰합니다 |

노드당 Pod 수는 클러스터 생성 시에만 지정할 수 있으므로 GKE 생성 전에 정해야 합니다. 등록 사용자 500명과 동시 접속 500명은 필요한 노드 수가 크게 다르므로 기준을 확인한 뒤 노드 풀을 설계합니다.

## 검증 범위

이 문서는 인증서와 HTTPS 프런트엔드 구성 절차입니다. 실제 CIDR 가용성, 사내 라우팅, GKE NEG 상태, 내부 DNS 반영, 사용자 로그인은 적용 환경에서 확인해야 합니다. Notebook에서 사내 Git 서버로 접속하는 경로는 Pod 기준으로 별도 검증이 필요하며 사내 VM 기준 확인 결과로 대체할 수 없습니다.

[Certificate Manager DNS 인증](https://cloud.google.com/certificate-manager/docs/dns-authorizations) / [리전 내부 ALB 구성](https://cloud.google.com/load-balancing/docs/l7-internal/setting-up-l7-internal)
