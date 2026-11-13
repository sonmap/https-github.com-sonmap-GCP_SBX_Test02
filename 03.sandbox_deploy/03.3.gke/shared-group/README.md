# GKE 공유 샌드박스 배포

Test02의 그룹 공유 배포는 2차 Sandbox 구축 업무입니다. 포털이 그룹 구성을 승인한 뒤 [그룹 공유 배포 Workflow](../../README.md#그룹-공유-sandbox-자동-배포)를 호출하면 Private Pool에서 Hub·Proxy, 과제 Notebook과 내부 ALB를 적용합니다. 기존 과제별 Workflow와는 별도입니다. 과제 Namespace는 한 배포 경로에서 관리합니다.

| 범위 | 구성 |
| --- | --- |
| 그룹 | 그룹당 JupyterHub 1개와 Configurable HTTP Proxy 1개, 내부 ALB 호스트 경로 1개 |
| 과제 | Namespace·KSA·GSA 각 1개, Notebook Deployment 1개, PVC 1개, 멤버 5명 |
| Notebook | 과제당 Pod 1개 안에서 5개 멤버 서버를 각각 별도 컨테이너와 포트로 실행. 합계 요청과 제한은 8 vCPU·64 GiB. 컨테이너별 CPU·메모리 한도를 적용하며 전체 자원을 한 사용자가 사용할 수 있는 방식은 아님 |
| 데이터 | 모든 멤버가 과제 PVC의 `/home/jupyter`를 공유. 시작 경로의 기본값은 `/home/jupyter/<GW 이메일>`. 이 디렉터리 구분은 사용자 간 파일 접근 제어 경계가 아님 |
| 인증 | PoC용 Hub 로컬 로그인. 승인된 GW 이메일을 로그인 ID로 사용하고 별도로 설정한 테스트 비밀번호를 확인합니다. Hub는 named server 요청도 과제 승인 명단과 대조합니다. |
| 이미지 | 과제별 승인된 AR digest를 지정. 기존 Ubuntu VM의 `systemctl`, Docker 종료 훅, 호스트 계정 동기화는 GKE 실행 경로에 의존하지 않음 |

표준 이미지 빌드와 개발자 추가 패키지 설치 흐름은 [Mermaid와 GCS 반입 명령](../notebook-image/README.md#개발자-추가-패키지-gcs-경유)을 참고합니다.

## 파일별 용도와 필요 여부

| 파일 | 용도 | 누가 언제 사용하나요? | 필요 여부 |
|---|---|---|---|
| [README.md](README.md) | 그룹·과제 배포, 로컬 로그인, PVC, 중지·재개 명령 | 운영자가 배포 순서와 확인 항목을 확인할 때 | 운영 안내 |
| [shared_sandbox.py](shared_sandbox.py) | Helm 값·과제 리소스 생성, ALB 연결, 과제 시작·중지 | 운영자가 관리 VM에서 해당 작업을 실행할 때 | 그룹 공유 배포 실행 파일 |
| [prepare_test_accounts.py](prepare_test_accounts.py) | 테스트 계정 비밀번호 해시 파일 작성 | 운영자가 로컬 계정을 처음 등록하거나 비밀번호를 바꿀 때 | 로컬 로그인 초기 설정·변경 시 |
| [test_passwords.py](test_passwords.py) | 테스트 계정 비밀번호 해시 생성·검증 | 계정 준비 도구와 Hub 설정이 호출 | 로컬 로그인 실행 의존성 |
| [hub_spawner.py](hub_spawner.py) | 그룹 Hub 로그인과 승인 멤버의 과제 서버 연결 | Helm 설정에 포함되어 Hub가 실행할 때 | 그룹 공유 배포 실행 의존성 |
| [notebook_slot.py](notebook_slot.py) | 과제 Pod에서 멤버별 Jupyter 서버 실행 | 과제 매니페스트에 포함되어 Notebook 컨테이너가 시작할 때 | 그룹 공유 배포 실행 의존성 |

운영 이관용 이미지 태그·후보 빌드 파일은 [Notebook 이미지 운영 릴리스](../notebook-image/README.md#notebook-이미지-운영-릴리스)에서 관리합니다.

## 수동 점검과 복구

아래 명령은 운영자가 단계별로 직접 적용해야 하는 점검·복구에 사용합니다. 자동 배포의 계정 Secret Manager 등록 방법은 [2차 배포 문서](../../README.md#그룹-공유-sandbox-자동-배포)에 있습니다.

### 1. 공통 인프라와 그룹 준비

- VPC·GKE·내부 ALB·DNS·인증서는 기존 Foundation 절차로 준비합니다. 동일 ALB에 그룹 DNS 세 개를 등록하고 인증서가 세 이름을 포함하도록 구성합니다. 사내 DNS에서 각 이름은 내부 ALB VIP를 가리킵니다.
- 관리 VM `infra-son01`에서 [Helm 차트 4.2.0 수동 반입 명령](../../../02.infra-setup/infra-setup-commend.md#infra-son01에서-helm-차트-수동-반입)을 실행합니다. Hub·Proxy 컨테이너 이미지는 같은 문서의 기본 이미지 복사 절차에서 준비합니다. 이후 배포 환경에서 AR, 사설 GKE API, Filestore에 접근할 수 있어야 합니다.
- 세 그룹마다 [점검용 그룹 JSON 예시](../../../04.tests/fixtures/group.example.json)을 복사해 승인된 테스트 계정 이메일, 고유 과제명, GSA, AR 이미지 digest, PVC 이름을 입력합니다. 예제의 digest는 자리표시자입니다. 그룹 전체에서 과제명과 GSA가 중복되지 않도록 포털 또는 운영자가 관리합니다.
- 그룹별로 승인된 계정의 테스트 비밀번호를 준비합니다. 실제 GW 비밀번호 대신 테스트 전용 비밀번호를 사용하세요. 준비 도구는 비밀번호를 화면에 표시하지 않고 해시만 파일에 기록합니다. 이 파일은 Git에 올리지 않고 Hub 네임스페이스의 Secret으로 등록합니다. Jupyter 사용자는 GKE 관리 권한을 받지 않습니다.

```bash
GROUP_CONFIG=/secure/approved-group.json
GROUP=sandbox-group-01
CTX=approved-gke-context
TEST_ACCOUNTS_SECRET=shared-test-accounts
TEST_ACCOUNT_HASHES=/secure/shared-test-accounts.json
CHART=oci://asia-northeast3-docker.pkg.dev/gcp-sbx-edp-gke01/ar-sbxtest01-platform/jupyterhub

kubectl --context "$CTX" create namespace "$GROUP" --dry-run=client -o yaml |
  kubectl --context "$CTX" apply -f -
python3 03.sandbox_deploy/03.3.gke/shared-group/prepare_test_accounts.py "$GROUP_CONFIG" "$TEST_ACCOUNT_HASHES"
kubectl --context "$CTX" -n "$GROUP" create secret generic "$TEST_ACCOUNTS_SECRET" \
  --from-file=accounts.json="$TEST_ACCOUNT_HASHES" --dry-run=client -o yaml |
  kubectl --context "$CTX" apply --server-side --field-manager=sandbox-test-accounts -f -

python3 03.sandbox_deploy/03.3.gke/shared-group/shared_sandbox.py "$GROUP_CONFIG" hub-values > /tmp/sbx-hub-values.json
helm upgrade --install shared-hub "$CHART" --version 4.2.0 \
  --kube-context "$CTX" --namespace "$GROUP" --values /tmp/sbx-hub-values.json --atomic --timeout 15m
```

기존 구성 JSON을 사용 중이면 `okta_issuer`, `okta_secret`을 삭제하고 `test_accounts_secret`을 지정합니다. 이 PoC 모드에서는 Okta 앱, Client ID·Secret, 콜백 등록 없이 내부 ALB 주소에서 JupyterHub 로그인 화면을 열 수 있습니다. 비밀번호를 바꾸려면 준비 명령에 `--rotate <이메일>`을 추가하고 Secret 등록 명령을 다시 실행합니다.

포털 링크 예시는 `https://<그룹-DNS>/hub/spawn/<URL 인코딩한 GW 이메일>/<과제명>`입니다. 한 계정이 여러 과제에 속하면 각각 다른 named server를 사용합니다. 그룹 Hub의 구성 파일과 과제 명단을 같이 갱신합니다. 기존 멤버를 바꾸기 전에는 해당 과제 세션을 종료하고 Pod를 중지한 뒤 변경합니다.

그룹 Proxy의 standalone NEG를 기존 내부 ALB에 연결합니다. ALB와 GKE가 같은 서비스 프로젝트에 있는 기존 배치 기준입니다.

```bash
python3 03.sandbox_deploy/03.3.gke/shared-group/shared_sandbox.py "$GROUP_CONFIG" alb \
  --context "$CTX" --project "$GKE_PROJECT" --region asia-northeast3 --url-map "$SHARED_URL_MAP"
```

### 2. 과제와 데이터 배포

1. 신규 구성에서는 과제별 Filestore 볼륨과 RWX PVC를 준비하고 PV의 reclaim policy를 `Retain`으로 설정합니다. 기존 공유 Filestore를 사용할 경우 과제별 PVC와 전용 디렉터리를 준비하고 `sub_path`로 지정합니다. `sub_path`는 사전에 만들어야 하며, 같은 디렉터리를 여러 과제에 할당하면 안 됩니다. 여러 PVC에서 같은 Filestore 공유를 참조하면 PVC에 표시되는 `100Gi`는 공유 내 디렉터리별 용량 제한을 만들지 않습니다. 실제 공유 총사용량을 운영자가 모니터링합니다.
2. 동적 생성이 필요하면 `storage.storage_class`에 사전에 검증한 Filestore CSI RWX StorageClass를 지정합니다. 이 모드의 기본 요청값은 `100Gi`이고 선택한 Filestore 티어의 최소 용량을 충족해야 합니다. 기존 PVC를 참조할 때는 `storage_class`를 생략합니다.
3. 최초 이관 시 VM의 실제 `/home/jupyter` 데이터와 권한을 복사합니다. 기존 디렉터리명으로 홈을 열려면 과제의 `home_dirs`에 `{"member01@example.com": "member01"}`처럼 GW 이메일과 기존 디렉터리명을 매핑합니다. 이 설정을 생략하면 해당 사용자의 기존 파일을 `/home/jupyter/<GW 이메일>` 아래로 이관합니다. Pod UID/GID가 이 경로와 멤버 디렉터리에 쓸 수 있는지 확인합니다. 과제별 GSA에 필요한 데이터 IAM을 부여한 뒤 아래와 같이 KSA를 연결합니다. 기존 레거시 Pod를 덮어쓰기 전에 별도 PoC 과제에서 시험합니다.

```bash
TASK=sbx01
KSA="ksa-jupyter-${TASK}"
gcloud iam service-accounts add-iam-policy-binding "$GSA_EMAIL" \
  --project="$GSA_PROJECT" --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:${GKE_PROJECT}.svc.id.goog[${TASK}/${KSA}]"

python3 03.sandbox_deploy/03.3.gke/shared-group/shared_sandbox.py "$GROUP_CONFIG" task-manifest "$TASK" > /tmp/sbx-task.json
kubectl --context "$CTX" apply --dry-run=server -f /tmp/sbx-task.json
kubectl --context "$CTX" apply -f /tmp/sbx-task.json
```

신규 Namespace에서 서버 dry-run을 하려면 해당 Namespace를 먼저 생성하세요. 기존 PVC 모드에서도 PVC는 해당 Namespace에 미리 생성합니다. 내부 ALB 접근, GKE Workload Identity, AR pull 주체의 Reader 권한은 인프라 준비 범위입니다. Notebook은 Autopilot의 Balanced compute class를 선택합니다. 실제 허용 리소스와 Pod IP 여유는 GKE에서 확인합니다.

### 3. 중지·재개와 운영 릴리스

```bash
python3 03.sandbox_deploy/03.3.gke/shared-group/shared_sandbox.py "$GROUP_CONFIG" stop "$TASK" --context "$CTX"
python3 03.sandbox_deploy/03.3.gke/shared-group/shared_sandbox.py "$GROUP_CONFIG" start "$TASK" --context "$CTX"
```

`stop`은 Deployment를 0으로 조정하고 멤버 세션 데이터를 지웁니다. `start`는 Deployment를 다시 1로 조정합니다. PVC는 두 명령의 대상이 아니며 사용자가 다시 로그인해 서버를 열면 같은 파일을 읽습니다. Hub idle culler는 60분 후 유휴 멤버 서버를 종료합니다. 과제 Pod 자체의 운영시간 종료는 포털 또는 승인된 스케줄러가 `stop`을 호출해야 합니다.

승인된 이미지 digest에 운영 태그를 붙이거나 라이브러리 변경으로 후보 이미지를 빌드할 때는 [Notebook 이미지 운영 릴리스](../notebook-image/README.md#notebook-이미지-운영-릴리스)를 따릅니다. Git에 있는 Python 소스는 기존 승인 절차에서 배치 Filestore로 이관합니다. 운영 릴리스 기록에는 소스 리비전, Filestore 배치 경로, AR digest와 버전 태그를 함께 기록합니다. 배치 호출은 기존 Central-1 `run-gke.sh` → `client-gke` → GKE #3 경로에서 수행합니다.

### 4. 전환 확인 항목

1. 기존 AR 이미지를 digest로 지정하고 `python`과 `jupyterhub-singleuser`가 배포 UID에서 실행되는지 확인합니다. 이미지의 JupyterHub single-user 패키지 호환성도 확인합니다. 이미지의 VM용 시작 명령은 이 배포에서 재정의합니다.
2. 승인된 5개 이메일과 각 테스트 비밀번호로 동시에 로그인하여 동일한 과제 Pod에 연결되고, 각 홈 디렉터리가 표시되는지 확인합니다. 타 과제의 named server는 거부되어야 합니다.
3. 파일을 저장하고 과제 Pod를 중지·재개한 뒤 파일을 다시 엽니다. 재기동 뒤 다시 로그인해 새 세션을 시작하고 커널을 실행합니다.
4. 배치용 Python 코드와 이미지 digest를 운영 이관한 뒤 Central-1에서 기존 배치 흐름을 수행합니다.
