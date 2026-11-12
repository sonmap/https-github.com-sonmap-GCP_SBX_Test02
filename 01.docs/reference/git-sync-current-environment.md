# Git 설정 동기화 후 현재 작업 재개

기준일: 2026-11-07. 프로젝트명 치환용 `sed` 없이 저장소 파일을 직접 사용합니다. 이미 생성한 GCP 자원과 게시한 Terraform ZIP은 Git pull만으로 변경되지 않습니다.

| 항목 | 저장소 기본값 |
|---|---|
| 실행 프로젝트 / 작업자 | gcp-sbx-edp-gke01 / son@sonmap.net |
| 호스트 프로젝트 / 관리자 | gcp-prod-edp-hub-vpchost / admin@sonmap.net |
| Shared VPC | vpc-prod-edp-hub |
| GKE | gke-sbx-main-an3 / asia-northeast3 |
| 노드 / Pod / 제어 영역 | 10.252.0.0/24 / 100.64.128.0/19 / 10.253.3.0/28 |
| 노드 서브넷 / Pod 범위 | subnet-prod-sbx-gke-01 / subnet-prod-sbx-pod-01 |
| PSA | psa-prod-edp-cloudbuild / 10.250.0.0/24 |
| ALB 프런트엔드 | 기존 subnet-prod-edp-alb-frontend-an3 / 172.31.96.0/27 |
| proxy-only | subnet-prod-sbx-ilb-proxy / 172.31.111.64/26 |

## 1. 관리 VM의 로컬 설정 보존

실행 위치: infra-son01. Git 명령은 GCP 계정과 별개입니다. 다음 명령은 로컬 변경을 삭제하지 않습니다. Customer ID를 넣은 파일을 먼저 별도로 보관합니다. Secret 값은 이 파일이나 Git에 넣지 않습니다.

```bash
cd "$HOME/GCP_SBX_Test01"
```

```bash
cp -p 02.sandbox_setup_01_gcloud/configs/provisioner-env.yaml "$HOME/provisioner-env.before-sbx-sync.yaml"
```

```bash
git status --short
```

## 2. 수정·미추적 파일을 로컬 stash에 보관하고 최신 main 받기

미추적 파일에 비밀값이 없는지 확인합니다. stash는 로컬 보관이며 원격으로 push하지 않습니다. 개인 브랜치·별도 커밋으로 작업 중이면 자동 병합하지 말고 현재 상태를 먼저 확인합니다.

```bash
git stash push -u -m "before-sbx-environment-sync-20261107"
```

```bash
git pull --ff-only origin main
```

```bash
git log -1 --oneline
```

`--ff-only`가 실패하면 중단하고 분기된 커밋을 확인합니다. `reset --hard`, `clean -fd`로 작업을 삭제하지 않습니다. 기존 파일을 통째로 덮어쓸 수 있으므로 바로 `stash pop`하지 않습니다. 필요한 변경만 `git stash show -p`로 확인하여 다시 반영합니다.

## 3. 실제 Customer ID만 복원

저장소는 `CLOUD_IDENTITY_CUSTOMER_ID: __SET_CUSTOMER_ID__`를 유지합니다. 백업 파일에서 실제 값을 확인합니다. Customer ID는 프로젝트 번호가 아닙니다.

```bash
awk '/^CLOUD_IDENTITY_CUSTOMER_ID:/ {print}' "$HOME/provisioner-env.before-sbx-sync.yaml"
```

아래 `실제_CUSTOMER_ID`를 백업의 C... 값으로 바꾼 뒤 실행합니다. 기존 프로젝트·버킷·Pool 경로를 백업 파일 전체에서 복원하지 않습니다.

```bash
sed -i 's/__SET_CUSTOMER_ID__/실제_CUSTOMER_ID/' 02.sandbox_setup_01_gcloud/configs/provisioner-env.yaml
```

```bash
cat 02.sandbox_setup_01_gcloud/configs/provisioner-env.yaml
```

## 4. 현재 단계 — Private Pool에서 GKE API 조회

YAML 자체가 현재 프로젝트를 가리킵니다. `/tmp/check-private-gke-sbx.yaml` 생성이나 프로젝트명 치환은 필요 없습니다.

**수행·실행 계정: son@sonmap.net — Pool 상태 확인**

```bash
gcloud builds worker-pools describe pool-sbxtest01 --project=gcp-sbx-edp-gke01 --region=asia-northeast3 --account=son@sonmap.net --format="yaml(state,privatePoolV1Config)"
```

**로컬 설정 확인**

```bash
cat 03.cloudbuild/check-private-gke.yaml
```

**제출 계정: son@sonmap.net / 빌드 실행: tf-manager / 실행 풀: pool-sbxtest01**

```bash
gcloud builds submit --no-source --project=gcp-sbx-edp-gke01 --region=asia-northeast3 --account=son@sonmap.net --service-account=projects/gcp-sbx-edp-gke01/serviceAccounts/tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com --config=03.cloudbuild/check-private-gke.yaml
```

Pool이 RUNNING이고 이 Build가 SUCCESS여야 합니다. 조회만 수행하며 Pod를 생성하지 않습니다. 관리 VM의 kubectl 성공을 Pool 접속 성공으로 대신하지 않습니다. 최신 커밋이 바뀌어도 이번 점검은 기존 runner:bootstrap을 사용하므로 이미지를 먼저 전부 다시 만들 필요는 없습니다.

## 5. 과제 Deploy 전에 API 이미지의 새 Schema 반영

요청 검증 Schema의 고정 프로젝트·VPC도 동기화했습니다. **Git pull은 이미 배포된 Cloud Run 컨테이너의 Schema를 바꾸지 않습니다.** 기존 이미지 bootstrap에는 이전 검증값이 남아 있으므로 요청 제출 전에 새 API 이미지로 갱신합니다. Customer ID가 실제 값인지 확인한 후 수행합니다.

**제출: son@sonmap.net / Build 실행: tf-manager / 기본 Build 풀**

```bash
gcloud builds submit 07.sandbox_request_api --project=gcp-sbx-edp-gke01 --region=asia-northeast3 --account=son@sonmap.net --service-account=projects/gcp-sbx-edp-gke01/serviceAccounts/tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com --tag=asia-northeast3-docker.pkg.dev/gcp-sbx-edp-gke01/ar-sbxtest01-platform/run-sbxtest01-provisioner:env-sync-20261107 --gcs-source-staging-dir=gs://gcp-sbx-edp-gke01-sbxtest01-build-source/source --gcs-log-dir=gs://gcp-sbx-edp-gke01-sbxtest01-build-source/logs
```

**배포: son@sonmap.net / Run 실행: sbx-manager — 위 Build SUCCESS 후**

```bash
gcloud run services update run-sbxtest01-provisioner --project=gcp-sbx-edp-gke01 --region=asia-northeast3 --account=son@sonmap.net --image=asia-northeast3-docker.pkg.dev/gcp-sbx-edp-gke01/ar-sbxtest01-platform/run-sbxtest01-provisioner:env-sync-20261107 --env-vars-file=02.sandbox_setup_01_gcloud/configs/provisioner-env.yaml
```

**확인: son@sonmap.net**

```bash
gcloud run services describe run-sbxtest01-provisioner --project=gcp-sbx-edp-gke01 --region=asia-northeast3 --account=son@sonmap.net --format="yaml(status.latestReadyRevisionName,status.conditions)"
```

이번 작업은 설정·Schema 동기화이며 과제 Deploy를 시작하지 않습니다. 기존 ZIP을 변경하지 않았다면 해당 generation·SHA-256은 같은 객체에 계속 사용할 수 있습니다. 새 ZIP을 게시하면 새 release_id·generation·SHA-256을 준비합니다. source.release_id와 runner 이미지 태그의 일치, 그룹 권한, ALB·인증서·DNS·데이터 권한은 별도로 확인합니다.

[전체 개별 명령 가이드](operator-command-guide.md)에서 미확인 항목을 확인하세요.
