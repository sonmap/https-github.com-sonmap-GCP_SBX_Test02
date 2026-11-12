# 3. 공통 기반 — 주석으로 통합한 gcloud 명령

필요한 변수 선언을 아래 코드 블록 맨 앞에 포함했습니다. 별도 문서에서 변수를 설정할 필요 없이, 이 문서의 선언부터 같은 터미널에서 실행합니다. `# 주석`을 보며 순서대로 실행하고, **기존 자원이 있으면 해당 생성 명령을 건너뜁니다.** 403·인증·연결 오류면 중단합니다. 선택 작업은 주석을 해제한 경우에만 실행합니다.

```bash
# ── 이 문서에서 사용하는 변수 선언 ──
# 아래 값을 확인하고 이 블록부터 같은 터미널에서 실행합니다.
unset CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT
export ADMIN_ACCOUNT=son@sonmap.net
# 실행 프로젝트 작업자는 son, Shared VPC·초기 권한 관리자는 admin으로 구분합니다.
export VPC_ADMIN_ACCOUNT="${VPC_ADMIN_ACCOUNT:-admin@sonmap.net}"
export OPERATOR_MEMBER=user:son@sonmap.net
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export VPC_HOST_PROJECT="gcp-prod-edp-hub-vpchost"
export REGION=asia-northeast3
export NETWORK=vpc-prod-edp-hub
# 내부 ALB 대역 후보: VPC Admin의 실제 중복 확인·승인 후 실행합니다.
export ILB_VIP_SUBNET=subnet-prod-edp-alb-frontend-an3
export ILB_VIP_CIDR=172.31.96.0/27
export ILB_VIP_ADDRESS="" # 예약 후 실제 할당 주소 조회
export ILB_PROXY_SUBNET=subnet-prod-sbx-ilb-proxy
export ILB_PROXY_CIDR=172.31.111.64/26
export MAIN_CLUSTER=gke-sbx-main-an3
export MAIN_SUBNET=subnet-prod-sbx-gke-01
export MAIN_POD_RANGE=subnet-prod-sbx-pod-01
export MAIN_CP_CIDR=10.253.3.0/28
export PSA_CIDR=10.250.0.0/24
export ADMIN_CIDR=172.31.10.0/24
export SSL_CERTIFICATE=cert-jupyter-sbx01-self
export TF_MANAGER="tf-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"
export SBX_MANAGER="sbx-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"
export SBX_GKE_PROJECT_NUMBER="$(gcloud projects describe "${SBX_GKE_PROJECT}" --account="${ADMIN_ACCOUNT}" --format='value(projectNumber)')"
# 프로젝트 번호는 자동 조회합니다. 조회 실패 또는 숫자가 아닌 결과이면 이후 명령을 중단합니다.

# 02-network.md와 02-subnet-iam.md 완료 후 저장소 루트에서 실행합니다.
# 기존 GKE는 Autopilot · Private Nodes/Endpoint · Subnet · Pod Range를 확인합니다.
# Private Pool → GKE 사설 경로는 별도로 준비합니다.

# ── 1. storage buckets create gs://gcp-sbx-edp-gke01-sbxtest01-requests ──
# 기존 자원 확인
gcloud storage buckets describe "gs://${SBX_GKE_PROJECT}-sbxtest01-requests" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
gcloud storage buckets create "gs://${SBX_GKE_PROJECT}-sbxtest01-requests" --project="${SBX_GKE_PROJECT}" --location="${REGION}" --uniform-bucket-level-access --public-access-prevention --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 2. storage buckets update gs://gcp-sbx-edp-gke01-sbxtest01-requests ──
gcloud storage buckets update "gs://${SBX_GKE_PROJECT}-sbxtest01-requests" --versioning --public-access-prevention --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 3. storage buckets create gs://gcp-sbx-edp-gke01-sbxtest01-bundles ──
# 기존 자원 확인
gcloud storage buckets describe "gs://${SBX_GKE_PROJECT}-sbxtest01-bundles" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
gcloud storage buckets create "gs://${SBX_GKE_PROJECT}-sbxtest01-bundles" --project="${SBX_GKE_PROJECT}" --location="${REGION}" --uniform-bucket-level-access --public-access-prevention --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 4. storage buckets update gs://gcp-sbx-edp-gke01-sbxtest01-bundles ──
gcloud storage buckets update "gs://${SBX_GKE_PROJECT}-sbxtest01-bundles" --versioning --public-access-prevention --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 5. storage buckets create gs://gcp-sbx-edp-gke01-sbxtest01-build-source ──
# 기존 자원 확인
gcloud storage buckets describe "gs://${SBX_GKE_PROJECT}-sbxtest01-build-source" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
gcloud storage buckets create "gs://${SBX_GKE_PROJECT}-sbxtest01-build-source" --project="${SBX_GKE_PROJECT}" --location="${REGION}" --uniform-bucket-level-access --public-access-prevention --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 6. storage buckets update gs://gcp-sbx-edp-gke01-sbxtest01-build-source ──
gcloud storage buckets update "gs://${SBX_GKE_PROJECT}-sbxtest01-build-source" --versioning --public-access-prevention --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 7. storage buckets add-iam-policy-binding gs://gcp-sbx-edp-gke01-sbxtest01-requests · roles/storage.objectAdmin ──
gcloud storage buckets add-iam-policy-binding "gs://${SBX_GKE_PROJECT}-sbxtest01-requests" --member="serviceAccount:${SBX_MANAGER}" --role=roles/storage.objectAdmin --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 8. storage buckets add-iam-policy-binding gs://gcp-sbx-edp-gke01-sbxtest01-bundles · roles/storage.objectAdmin ──
gcloud storage buckets add-iam-policy-binding "gs://${SBX_GKE_PROJECT}-sbxtest01-bundles" --member="serviceAccount:${SBX_MANAGER}" --role=roles/storage.objectAdmin --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 9. storage buckets add-iam-policy-binding gs://gcp-sbx-edp-gke01-sbxtest01-bundles · roles/storage.objectViewer ──
gcloud storage buckets add-iam-policy-binding "gs://${SBX_GKE_PROJECT}-sbxtest01-bundles" --member="serviceAccount:service-${SBX_GKE_PROJECT_NUMBER}@gcp-sa-config.iam.gserviceaccount.com" --role=roles/storage.objectViewer --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 10. artifacts repositories create ar-sbxtest01-platform ──
# 기존 자원 확인
gcloud artifacts repositories describe ar-sbxtest01-platform --project="${SBX_GKE_PROJECT}" --location="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
gcloud artifacts repositories create ar-sbxtest01-platform --project="${SBX_GKE_PROJECT}" --location="${REGION}" --repository-format=docker --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 11. artifacts repositories add-iam-policy-binding ar-sbxtest01-platform · roles/artifactregistry.reader ──
gcloud artifacts repositories add-iam-policy-binding ar-sbxtest01-platform --project="${SBX_GKE_PROJECT}" --location="${REGION}" --member="serviceAccount:${SBX_GKE_PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role=roles/artifactregistry.reader --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 12. artifacts repositories add-iam-policy-binding ar-sbxtest01-platform · roles/artifactregistry.reader ──

# ── 13. secrets create jupyter-oauth-client-id ──
# 기존 자원 확인
gcloud secrets describe jupyter-oauth-client-id --project="${SBX_GKE_PROJECT}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
gcloud secrets create jupyter-oauth-client-id --project="${SBX_GKE_PROJECT}" --replication-policy=user-managed --locations="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 14. secrets add-iam-policy-binding jupyter-oauth-client-id · roles/secretmanager.secretAccessor ──
gcloud secrets add-iam-policy-binding jupyter-oauth-client-id --project="${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/secretmanager.secretAccessor --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 15. secrets create jupyter-oauth-client-secret ──
# 기존 자원 확인
gcloud secrets describe jupyter-oauth-client-secret --project="${SBX_GKE_PROJECT}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
gcloud secrets create jupyter-oauth-client-secret --project="${SBX_GKE_PROJECT}" --replication-policy=user-managed --locations="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 16. secrets add-iam-policy-binding jupyter-oauth-client-secret · roles/secretmanager.secretAccessor ──
gcloud secrets add-iam-policy-binding jupyter-oauth-client-secret --project="${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/secretmanager.secretAccessor --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 17. VPC Admin: Private Pool 초기 구성 ──
# 이 절만 VPC_ADMIN_ACCOUNT로 실행합니다. 이후 GKE·ALB 등은 tf-manager 위임입니다.
# 기존 자원 확인
gcloud builds worker-pools describe pool-sbxtest01 --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${VPC_ADMIN_ACCOUNT}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
gcloud builds worker-pools create pool-sbxtest01 --project="${SBX_GKE_PROJECT}" --region="${REGION}" --worker-machine-type=e2-standard-4 --worker-disk-size=100GB --no-public-egress --peered-network="projects/${VPC_HOST_PROJECT}/global/networks/${NETWORK}" --peered-network-ip-range="${PSA_CIDR}" --account="${VPC_ADMIN_ACCOUNT}"

# ── 18. container clusters create-auto gke-sbx-main-an3 ──
# 기존 자원 확인
gcloud container clusters describe "${MAIN_CLUSTER}" --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
# 기존 자원 확인값: {"autopilot.enabled": true, "privateClusterConfig.enablePrivateNodes": true, "privateClusterConfig.enablePrivateEndpoint": true, "ipAllocationPolicy.clusterSecondaryRangeName": "subnet-prod-sbx-pod-01"} — 다르면 중단합니다.
gcloud container clusters create-auto "${MAIN_CLUSTER}" --project="${SBX_GKE_PROJECT}" --region="${REGION}" --network="projects/${VPC_HOST_PROJECT}/global/networks/${NETWORK}" --subnetwork="projects/${VPC_HOST_PROJECT}/regions/${REGION}/subnetworks/${MAIN_SUBNET}" --cluster-secondary-range-name="${MAIN_POD_RANGE}" --enable-private-nodes --enable-private-endpoint --master-ipv4-cidr="${MAIN_CP_CIDR}" --enable-master-authorized-networks --master-authorized-networks="${ADMIN_CIDR},${PSA_CIDR}" --enable-master-global-access --release-channel=regular --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 19. builds submit . ──
gcloud builds submit . --project="${SBX_GKE_PROJECT}" --region="${REGION}" --service-account="projects/${SBX_GKE_PROJECT}/serviceAccounts/${TF_MANAGER}" --gcs-source-staging-dir="gs://${SBX_GKE_PROJECT}-sbxtest01-build-source/source" --config=02.sandbox_setup_01_gcloud/configs/bootstrap-build.yaml --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 20. run deploy run-sbxtest01-provisioner ──
gcloud run deploy run-sbxtest01-provisioner --project="${SBX_GKE_PROJECT}" --region="${REGION}" --image="${REGION}-docker.pkg.dev/${SBX_GKE_PROJECT}/ar-sbxtest01-platform/run-sbxtest01-provisioner:bootstrap" --service-account="${SBX_MANAGER}" --no-allow-unauthenticated --ingress=all --timeout=300 --max-instances=2 --env-vars-file=02.sandbox_setup_01_gcloud/configs/provisioner-env.yaml --clear-network --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 21. run services add-iam-policy-binding run-sbxtest01-provisioner · roles/run.invoker ──
gcloud run services add-iam-policy-binding run-sbxtest01-provisioner --project="${SBX_GKE_PROJECT}" --region="${REGION}" --member="serviceAccount:${SBX_MANAGER}" --role=roles/run.invoker --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 22. run services describe run-sbxtest01-provisioner ──
gcloud run services describe run-sbxtest01-provisioner --project="${SBX_GKE_PROJECT}" --region="${REGION}" '--format=value(status.url)' --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── Workflow 입력 파일 준비 ──
# Cloud Run URL 조회가 성공했고 값이 비어 있지 않은지 확인합니다.
# URL만 치환합니다. Workflows의 ${args}, ${response.body}는 그대로 유지합니다.
export PROVISIONER_URL="$(gcloud run services describe run-sbxtest01-provisioner --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --format='value(status.url)')"
mkdir -p .local
sed "s|__PROVISIONER_URL__|${PROVISIONER_URL}|g" 02.sandbox_setup_01_gcloud/configs/workflow.template.yaml > .local/workflow.yaml

# ── 23. workflows deploy workflow-sbxtest01-provision ──
gcloud workflows deploy workflow-sbxtest01-provision --project="${SBX_GKE_PROJECT}" --location="${REGION}" --service-account="${SBX_MANAGER}" --source=.local/workflow.yaml --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 24. projects add-iam-policy-binding gcp-sbx-edp-gke01 · roles/workflows.invoker ──
gcloud projects add-iam-policy-binding "${SBX_GKE_PROJECT}" --member="${OPERATOR_MEMBER}" --role=roles/workflows.invoker --condition=None --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 25. storage buckets add-iam-policy-binding gs://gcp-sbx-edp-gke01-sbxtest01-requests · roles/storage.objectAdmin ──
gcloud storage buckets add-iam-policy-binding "gs://${SBX_GKE_PROJECT}-sbxtest01-requests" --member="${OPERATOR_MEMBER}" --role=roles/storage.objectAdmin --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 26. storage buckets add-iam-policy-binding gs://gcp-sbx-edp-gke01-sbxtest01-bundles · roles/storage.objectViewer ──
gcloud storage buckets add-iam-policy-binding "gs://${SBX_GKE_PROJECT}-sbxtest01-bundles" --member="${OPERATOR_MEMBER}" --role=roles/storage.objectViewer --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── ALB 사전 확인: tf-manager로 VIP Subnet 조회 ──
gcloud compute networks subnets describe "${ILB_VIP_SUBNET}" --project="${VPC_HOST_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 조회는 Network Viewer로도 성공할 수 있습니다. 실제 사용 권한은 02-subnet-iam.md의 바인딩을 확인합니다.
# 조회 실패 또는 바인딩 미확인 상태에서는 VPC Admin에게 요청하고 ALB 생성을 중단합니다.

# ── 27. Regional Internal ALB: 사설 VIP 예약 ──
# 서브넷·프록시 전용 Subnet·방화벽 준비가 완료된 뒤 실행합니다.
# 기존 Global 외부 ALB를 제자리 변환하지 않습니다. Regional 자원을 별도로 생성합니다.
gcloud compute addresses describe ip-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 명시적 Not Found일 때만 생성합니다.
gcloud compute addresses create ip-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --subnet="projects/${VPC_HOST_PROJECT}/regions/${REGION}/subnetworks/${ILB_VIP_SUBNET}" --purpose=SHARED_LOADBALANCER_VIP --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 자동 예약된 실제 VIP를 이후 프런트엔드 구성에 사용합니다.
export ILB_VIP_ADDRESS="$(gcloud compute addresses describe ip-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}" --format='value(address)')"

# ── 28. 기본 Regional Health Check·Backend ──
gcloud compute health-checks describe hc-alb-sbxtest01-shared-default --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 명시적 Not Found일 때만 생성합니다.
gcloud compute health-checks create http hc-alb-sbxtest01-shared-default --project="${SBX_GKE_PROJECT}" --region="${REGION}" --port=8000 --request-path=/_chp_healthz --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
gcloud compute backend-services describe bes-alb-sbxtest01-shared-default --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 명시적 Not Found일 때만 생성합니다. 기존 scheme은 INTERNAL_MANAGED여야 합니다.
gcloud compute backend-services create bes-alb-sbxtest01-shared-default --project="${SBX_GKE_PROJECT}" --region="${REGION}" --protocol=HTTP --load-balancing-scheme=INTERNAL_MANAGED --health-checks=hc-alb-sbxtest01-shared-default --health-checks-region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 29. Regional URL Map ──
gcloud compute url-maps describe urlmap-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 명시적 Not Found일 때만 생성합니다.
gcloud compute url-maps create urlmap-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --default-service="projects/${SBX_GKE_PROJECT}/regions/${REGION}/backendServices/bes-alb-sbxtest01-shared-default" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 30. Regional HTTP Proxy ──
gcloud compute target-http-proxies describe http-proxy-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 명시적 Not Found일 때만 생성합니다.
gcloud compute target-http-proxies create http-proxy-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --url-map="projects/${SBX_GKE_PROJECT}/regions/${REGION}/urlMaps/urlmap-alb-sbxtest01-shared" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 31. 내부 HTTP Forwarding Rule ──
gcloud compute forwarding-rules describe fr-alb-sbxtest01-shared-http --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 명시적 Not Found일 때만 생성합니다. global-access는 사설 연결의 리전 제한만 해제합니다.
gcloud compute forwarding-rules create fr-alb-sbxtest01-shared-http --project="${SBX_GKE_PROJECT}" --region="${REGION}" --load-balancing-scheme=INTERNAL_MANAGED --network="projects/${VPC_HOST_PROJECT}/global/networks/${NETWORK}" --subnet="projects/${VPC_HOST_PROJECT}/regions/${REGION}/subnetworks/${ILB_VIP_SUBNET}" --address=ip-alb-sbxtest01-shared --ports=80 --target-http-proxy=http-proxy-alb-sbxtest01-shared --target-http-proxy-region="${REGION}" --allow-global-access --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 32. Regional SSL 인증서 별도 준비 확인 ──
# Global 인증서는 재사용할 수 없습니다. 아래 Regional 인증서가 없으면 HTTPS 생성을 중단합니다.
gcloud compute ssl-certificates describe "${SSL_CERTIFICATE}" --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 33. Regional HTTPS Proxy ──
gcloud compute target-https-proxies describe https-proxy-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 명시적 Not Found이고 Regional 인증서가 준비된 경우에만 생성합니다.
gcloud compute target-https-proxies create https-proxy-alb-sbxtest01-shared --project="${SBX_GKE_PROJECT}" --region="${REGION}" --url-map="projects/${SBX_GKE_PROJECT}/regions/${REGION}/urlMaps/urlmap-alb-sbxtest01-shared" --ssl-certificates="${SSL_CERTIFICATE}" --ssl-certificates-region="${REGION}" --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 34. 내부 HTTPS Forwarding Rule ──
gcloud compute forwarding-rules describe fr-alb-sbxtest01-shared-https --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 명시적 Not Found일 때만 생성합니다.
gcloud compute forwarding-rules create fr-alb-sbxtest01-shared-https --project="${SBX_GKE_PROJECT}" --region="${REGION}" --load-balancing-scheme=INTERNAL_MANAGED --network="projects/${VPC_HOST_PROJECT}/global/networks/${NETWORK}" --subnet="projects/${VPC_HOST_PROJECT}/regions/${REGION}/subnetworks/${ILB_VIP_SUBNET}" --address=ip-alb-sbxtest01-shared --ports=443 --target-https-proxy=https-proxy-alb-sbxtest01-shared --target-https-proxy-region="${REGION}" --allow-global-access --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# ── 35. 선택 · builds triggers create github ──
# 선택 작업: 필요한 경우에만 아래 명령의 주석을 해제합니다.
# 기존 자원 확인
# gcloud builds triggers describe trigger-sbxtest01-platform-release --project="${SBX_GKE_PROJECT}" --region="${REGION}" --format=json --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"
# 조회 결과가 명시적 Not Found일 때만 아래 생성 명령을 실행합니다.
# gcloud builds triggers create github --name=trigger-sbxtest01-platform-release --project="${SBX_GKE_PROJECT}" --region="${REGION}" --repo-owner=sonmap --repo-name=GCP_SBX_Test01 --branch-pattern="^main$" --build-config=03.cloudbuild/platform-release.yaml --service-account="projects/${SBX_GKE_PROJECT}/serviceAccounts/${TF_MANAGER}" '--substitutions=_RELEASE_ID=git-$SHORT_SHA,_COMMIT_SHA=$COMMIT_SHA' --account="${ADMIN_ACCOUNT}" --impersonate-service-account="${TF_MANAGER}"

# 다음: OAuth Secret 값 등록 → Workspace tf-manager 그룹 관리자 역할 부여 → 릴리스 → 이미지 미러링 → 과제 요청
# Build/Run/Workflow 입력: 02.sandbox_setup_01_gcloud/configs/의 YAML 파일을 사용합니다. Python 실행기는 없습니다.
```
