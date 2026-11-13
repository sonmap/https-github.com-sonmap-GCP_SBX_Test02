# Sandbox JupyterHub DNS 요청서

Sandbox JupyterHub 3개의 내부 ALB 접속을 위해 DNS 요청 2건을 제출합니다. 외부DNS는 인증서 검증용 CNAME, 내부DNS는 서비스 접속용 A 레코드입니다. 두 건은 서로 의존하지 않으므로 같은 날 함께 제출합니다.

전체 구성 절차는 [관리 인증서 런북](sbx01-managed-certificate-runbook.md)을 따릅니다.

## 대상 도메인

| 번호 | 용도 | 토큰 | FQDN |
|---|---|---|---|
| 1 | 일반 | `com` | `jupyter-com.dlk.lguplus.co.kr` |
| 2 | 보안 | `sec` | `jupyter-sec.dlk.lguplus.co.kr` |
| 3 | System Analysis | `sa` | `jupyter-sa.dlk.lguplus.co.kr` |

## 제출 전 채울 값

| 자리 | 조회 방법 | 비고 |
|---|---|---|
| `<CNAME 이름>` `<CNAME 대상>` | 아래 1번 명령 | 도메인마다 값이 다릅니다 |
| `<VIP>` | 아래 2번 명령 | 세 도메인이 같은 값을 사용합니다 |
| `<완료희망일자>` | 담당자와 협의 | 형식 `yyyy-mm-dd hh:mm` |

### 1. CNAME 값 조회

DNS 인증 3건을 만든 뒤 한 번에 조회합니다. 세 번째 칸이 도메인명, 네 번째 칸이 IP 정보입니다.

```bash
gcloud certificate-manager dns-authorizations list \
  --project="${SBX_GKE_PROJECT}" --location="${REGION}" --account="${ADMIN_ACCOUNT}" \
  --format="table(name,domain,dnsResourceRecord.name,dnsResourceRecord.data)"
```

콘솔에서는 Network Services → Certificate Manager → DNS authorizations에서 같은 값을 봅니다.

도메인마다 대상값이 다릅니다. 운영 요청서에서 두 도메인의 접두 라벨이 같아 보였지만 대상은 서로 달랐습니다. 한 줄을 복사해 도메인만 바꾸면 해당 도메인은 검증에 실패하므로, 출력된 행을 그대로 옮깁니다.

### 2. VIP 값 조회

```bash
gcloud compute addresses describe ip-alb-sbxtest01-shared \
  --project="${SBX_GKE_PROJECT}" --region="${REGION}" \
  --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" \
  --format='value(address)'
```

---

## 요청서 1 — 외부DNS · 인증서 검증용 CNAME

```text
1.작업대상(외부DNS or 내부DNS) :
외부DNS

2.작업내용
[등록]
도메인명 : <CNAME 이름 · jupyter-com>
IP 정보 : <CNAME 대상 · jupyter-com>
TYPE : CNAME

[등록]
도메인명 : <CNAME 이름 · jupyter-sec>
IP 정보 : <CNAME 대상 · jupyter-sec>
TYPE : CNAME

[등록]
도메인명 : <CNAME 이름 · jupyter-sa>
IP 정보 : <CNAME 대상 · jupyter-sa>
TYPE : CNAME

3.등록/변경/삭제 목적(주요 서비스 대상(사용자) 및 주요 서비스 내용)
Sandbox JupyterHub 내부 ALB의 SSL 인증서 프로비저닝을 위해 DNS 승인이 필요하여 CNAME 등록이 필요합니다.
대상 서비스는 사내 분석 사용자용 JupyterHub 3종(일반·보안·System Analysis)입니다.

4.완료희망일자 (yyyy/mm/dd hh:mm) :
<완료희망일자>

5.기타((상단 요청 항목 외 작업자에게 공유할 내용 or 고려사항을 기재하여 주십시오))
해당 CNAME은 인증서 자동 갱신 시 재검증에 사용되므로 발급 완료 후에도 유지되어야 합니다.
도메인별로 대상값이 다르므로 3건을 각각 등록 부탁드립니다.
```

작성 예시입니다. 실제 값은 조회 결과로 대체합니다.

```text
[등록]
도메인명 : _acme-challenge_a1b2c3d4e5f6g7h8.jupyter-com.dlk.lguplus.co.kr
IP 정보 : 11111111-2222-3333-4444-555555555555.0.asia-northeast3.authorize.certificatemanager.goog
TYPE : CNAME
```

---

## 요청서 2 — 내부DNS · 서비스 접속용 A

```text
1.작업대상(외부DNS or 내부DNS) :
내부DNS

2.작업내용
[등록]
도메인명 : jupyter-com.dlk.lguplus.co.kr
IP 정보 : <VIP>
TYPE : A

[등록]
도메인명 : jupyter-sec.dlk.lguplus.co.kr
IP 정보 : <VIP>
TYPE : A

[등록]
도메인명 : jupyter-sa.dlk.lguplus.co.kr
IP 정보 : <VIP>
TYPE : A

3.등록/변경/삭제 목적(주요 서비스 대상(사용자) 및 주요 서비스 내용)
Sandbox JupyterHub 내부 ALB 접속을 위해 내부도메인 등록이 필요합니다.
대상 서비스는 사내 분석 사용자용 JupyterHub 3종(일반·보안·System Analysis)입니다.

4.완료희망일자 (yyyy/mm/dd hh:mm) :
<완료희망일자>

5.기타((상단 요청 항목 외 작업자에게 공유할 내용 or 고려사항을 기재하여 주십시오))
3건 모두 같은 내부 VIP를 가리킵니다. 내부 전용 주소이며 외부 공개 대상이 아닙니다.
```

## 제출 후 확인

| 요청 | 반영 확인 | 다음 단계 |
|---|---|---|
| 외부DNS CNAME | `dig +short <CNAME 이름> CNAME` | 인증서 생성 후 ACTIVE 확인 |
| 내부DNS A | 사내 VM에서 `getent ahostsv4 jupyter-com.dlk.lguplus.co.kr` | HTTPS 접속 검증 |

외부 CNAME이 반영되기 전에 인증서를 생성하면 검증에 실패하고 재시도를 기다려야 합니다. 반영을 확인한 뒤 인증서를 만듭니다.

세 도메인 중 하나라도 검증에 실패하면 인증서 전체가 발급되지 않습니다. `certificates describe`의 `authorizationAttemptInfo`에서 실패한 도메인을 확인합니다.
