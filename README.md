# auto

로컬 자동화 스크립트 모음입니다.

## 빠른 시작

- `.env`는 커밋하지 않습니다(로컬 전용).
- 최초 세팅은 `.env.example`을 참고해서 `.env`를 채우세요.

## Git 사용 (PC → 노트북 이어서 작업)

### 1) 이 PC에서 Git 저장소 만들기 + 첫 커밋

```powershell
cd "$env:USERPROFILE\Desktop\auto"
git init -b main
git add .
git commit -m "Initial commit"
```

### 2) GitHub에 원격 저장소 만들고(push)

GitHub에서 빈 저장소를 하나 만든 뒤(보통 `auto`, private 권장) 그 URL을 `origin`으로 등록하고 푸시합니다.

```powershell
cd "$env:USERPROFILE\Desktop\auto"
git remote add origin <GITHUB_REPO_URL>
git push -u origin main
```

### 3) 노트북에서 clone

```powershell
git clone <GITHUB_REPO_URL>
cd auto
copy .env.example .env
```

## 주의

- `output/`, `logs/`, `tmp/`는 용량/환경 의존도가 커서 Git에서 제외되어 있습니다.
