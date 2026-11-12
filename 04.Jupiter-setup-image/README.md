# 사용자 Notebook 표준 이미지

표준 이미지는 내부 sample 이미지에 gcloud/git/jq와 pandas/pyarrow/BigQuery/GCS 라이브러리를 추가합니다. 빌드 명령은 [공통 기반 준비 7단계](../02.sandbox_setup_01_gcloud/04-manual-gcloud.md)를 참고하세요.

이미지 태그 `4.2.0-r2-home`은 사용자의 PVC를 `/home/{username}`에 마운트하고, 시작 스크립트가 같은 경로를 `HOME`과 작업 디렉터리로 사용합니다. 예를 들어 `user01`은 `/home/user01`에서 시작합니다. 컨테이너의 Linux 실행 계정은 이미지의 `jovyan`을 사용하므로 기존 PVC의 UID와 권한을 유지합니다.

## 기존 sbx03에 적용

관리 VM에서 저장소를 갱신하고 신규 이미지를 빌드합니다.

```bash
gcloud builds submit 04.Jupiter-setup-image \
  --config=04.Jupiter-setup-image/cloudbuild.yaml \
  --project=gcp-sbx-edp-gke01 --region=asia-northeast3 \
  --service-account=projects/gcp-sbx-edp-gke01/serviceAccounts/tf-manager@gcp-sbx-edp-gke01.iam.gserviceaccount.com \
  --gcs-source-staging-dir=gs://gcp-sbx-edp-gke01-sbxtest01-build-source/jupyter-source \
  --account=son@sonmap.net
```

빌드가 성공하면 Helm 레지스트리에 로그인합니다.

```bash
gcloud auth print-access-token --account=son@sonmap.net | helm registry login asia-northeast3-docker.pkg.dev --username oauth2accesstoken --password-stdin
```

기존 Helm 설정을 사용하면서 사용자 이미지와 홈 설정을 적용합니다.

```bash
CLOUDSDK_CORE_ACCOUNT=son@sonmap.net helm upgrade jupyterhub-sbx03 \
  oci://asia-northeast3-docker.pkg.dev/gcp-sbx-edp-gke01/ar-sbxtest01-platform/jupyterhub \
  --version=4.2.0 --namespace=sbx03 \
  --kubeconfig="$HOME/.kube/config-sbx-dns" \
  --reuse-values --atomic --timeout=15m \
  --set-string singleuser.image.tag=4.2.0-r2-home \
  --set-string 'singleuser.storage.homeMountPath=/home/{username}' \
  --set-string 'singleuser.extraEnv.SANDBOX_NOTEBOOK_HOME=/home/{username}' \
  --set-string 'singleuser.cmd[0]=/usr/local/bin/start-sandbox-notebook'
```

사용자는 작업을 저장한 뒤 JupyterHub에서 서버를 중지하고 다시 시작합니다. 새 Pod의 JupyterLab 터미널에서 `printf '%s\n' "$HOME"; pwd`를 실행합니다. user01의 예상 경로는 `/home/user01`입니다. 기존 홈 파일은 동일한 PVC에서 열립니다.

신규 과제 자동 배포에는 이 소스로 빌드한 배포 runner 릴리스가 필요합니다.
