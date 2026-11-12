# 기존 Host 전체 권한 정리 — 이미 광역 권한을 적용한 환경만

신규 설치의 필수 단계가 아닙니다. 이전 저장소의 명령으로 부여한 **동일한 무조건부 바인딩**만 정리합니다. 현재 권한이 다른 시스템에도 사용되는지, 조직·Folder·그룹 상속이나 조건부 정책이 있는지 먼저 확인합니다. 서브넷별 권한을 먼저 추가하고 VPC Admin이 네트워크·PSA·Pool 준비를 맡은 뒤 실제 GKE·내부 ALB·배포가 정상인지 확인해야 합니다. 실제 IAM을 이 소스 수정 과정에서 변경하지 않았습니다.

```bash
export ADMIN_ACCOUNT="son@sonmap.net"
export VPC_ADMIN_ACCOUNT="${VPC_ADMIN_ACCOUNT:-admin@sonmap.net}"
export VPC_HOST_PROJECT="gcp-prod-edp-hub-vpchost"
export SBX_GKE_PROJECT="gcp-sbx-edp-gke01"
export FOLDER_ID="154455658682"
export TF_MANAGER="tf-manager@${SBX_GKE_PROJECT}.iam.gserviceaccount.com"
export SBX_GKE_PROJECT_NUMBER="$(gcloud projects describe "${SBX_GKE_PROJECT}" --account="${VPC_ADMIN_ACCOUNT}" --format='value(projectNumber)')"

# 조회·권한 출처 확인 후 아래 정리 명령을 개별 실행합니다.
gcloud projects get-iam-policy "${VPC_HOST_PROJECT}" --account="${VPC_ADMIN_ACCOUNT}" --format=json

# 새 Subnet별 Network User 바인딩이 실제 적용된 경우에만 기존 Host 전체 바인딩을 제거합니다.
gcloud projects remove-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/compute.networkUser --condition=None --account="${VPC_ADMIN_ACCOUNT}"
gcloud projects remove-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:service-${SBX_GKE_PROJECT_NUMBER}@container-engine-robot.iam.gserviceaccount.com" --role=roles/compute.networkUser --condition=None --account="${VPC_ADMIN_ACCOUNT}"
gcloud projects remove-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:${SBX_GKE_PROJECT_NUMBER}@cloudservices.gserviceaccount.com" --role=roles/compute.networkUser --condition=None --account="${VPC_ADMIN_ACCOUNT}"

# Host 관리 작업을 VPC Admin으로 이전하고, tf-manager의 기존 관리 권한을 정리합니다.
gcloud projects remove-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/compute.networkAdmin --condition=None --account="${VPC_ADMIN_ACCOUNT}"
gcloud projects remove-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/compute.securityAdmin --condition=None --account="${VPC_ADMIN_ACCOUNT}"
gcloud projects remove-iam-policy-binding "${VPC_HOST_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/servicenetworking.networksAdmin --condition=None --account="${VPC_ADMIN_ACCOUNT}"

# Pool 초기 관리 권한을 VPC Admin에게 이전한 뒤 기존 tf-manager의 Pool Owner를 정리합니다.
gcloud projects remove-iam-policy-binding "${SBX_GKE_PROJECT}" --member="serviceAccount:${TF_MANAGER}" --role=roles/cloudbuild.workerPoolOwner --condition=None --account="${ADMIN_ACCOUNT}"

# 이전 단계에서 tf-manager에 아래 Folder 역할도 부여했다면, 다른 업무 의존성 확인 후에만 정리합니다.
gcloud resource-manager folders get-iam-policy "${FOLDER_ID}" --account="${ADMIN_ACCOUNT}" --format=json
gcloud resource-manager folders remove-iam-policy-binding "${FOLDER_ID}" --member="serviceAccount:${TF_MANAGER}" --role=roles/compute.xpnAdmin --condition=None --account="${ADMIN_ACCOUNT}"
```

Host Service Agent User·Network Viewer·서비스 에이전트 본래 역할은 삭제 대상이 아닙니다. 바인딩이 없으면 실패를 무시해 일괄 실행하지 말고 실제 정책과 조건을 확인합니다. 남은 상위 상속·다른 역할까지 자동 제거하거나 최소 권한이 완성되었다고 간주하지 않습니다. 정리 후 GKE 접속·ALB 생성/Backend health·과제 Deploy를 다시 확인합니다.
