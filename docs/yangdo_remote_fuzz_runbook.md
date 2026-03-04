# Yangdo Remote Fuzz Runbook

로컬 PC 자원 대신 GitHub Actions 러너에서 내부 퍼징을 실행합니다.

## 1) GitHub Secrets 설정
- `GOOGLE_SERVICE_ACCOUNT_JSON`: 서비스계정 JSON 전체 문자열
- `SHEET_NAME` (옵션): 기본 시트명. 미설정 시 `26양도매물` 사용

## 2) 워크플로우 실행
- GitHub > `Actions` > `Yangdo Internal Fuzz (Remote)` > `Run workflow`
- 입력값 권장:
  - `cycles`: `2`
  - `iterations_per_cycle`: `6000`
  - `sleep_sec`: `0.1`
  - `seed`: `20260304`

CLI로 트리거할 수도 있습니다.
- `powershell -ExecutionPolicy Bypass -File scripts/trigger_remote_yangdo_fuzz.ps1 -Repo owner/repo -Cycles 2 -IterationsPerCycle 6000`

## 3) 결과 확인
- 실행 완료 후 `Summary`에서 요약 지표 확인
- `Artifacts`에서 내려받기:
  - `logs/yangdo_internal_fuzz_latest.json`
  - `logs/yangdo_internal_fuzz_cycles.jsonl`

## 4) 스케줄 실행(옵션)
- 워크플로우는 3시간 간격 크론이 포함되어 있으나 기본 비활성 가드가 있습니다.
- Repository Variable `ENABLE_REMOTE_FUZZ_SCHEDULE=true` 설정 시에만 스케줄이 동작합니다.

## 5) 주의사항
- 이 워크플로우는 `scripts/run_yangdo_internal_fuzz_loop.py`만 실행하며, KR/CO 게시 반영 명령을 호출하지 않습니다.
- 퍼징 입력은 의도적으로 극단값/희소값을 포함하므로 `not_ok: 유사 매물 부족`은 일부 발생할 수 있습니다.
