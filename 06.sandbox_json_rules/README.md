# Sandbox 신청 JSON 입력 규칙

이 폴더는 **신청서 양식의 검사 규칙**을 보관합니다. 실제 신청값은 `05.sandbox_json/`에 있습니다.

| 내용 | 검사 예 |
|---|---|
| 필수 항목 | request_id, approval, task, project, network, data, gke, source |
| 승인 상태 | approval.status는 APPROVED |
| 계정·그룹 | 허용된 이메일/그룹 이름 형식 |
| 과제 설정 | 과제명·Namespace·프로젝트 ID 형식 |
| 배포 소스 | 릴리스 ID, ZIP 주소, Generation, SHA256 |

`sandbox-request.schema.json`은 JSON Schema 형식의 참고 규격입니다. Cloud Run에서 실제 검사는 `07.sandbox_request_api/sandbox-request.schema.json`을 읽습니다. 두 파일은 동일해야 하며 자동 테스트에서 일치 여부를 확인합니다. 신청 항목을 바꾸면 두 파일과 API 검증 코드도 함께 수정합니다.

입력 규칙 자체는 BQ나 GKE 자원을 생성하지 않습니다.
