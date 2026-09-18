# Scale the Depths 비공식 한국어 패치 설치기

Windows 정식판 **Scale the Depths**용 비공식 한국어 패치의 설치·복구 도구 소스입니다.

> 이 프로젝트는 Glass Gecko Games 및 게임 배급사와 관련 없는 사용자 제작 패치입니다.
> 게임 원본 파일은 포함하거나 배포하지 않습니다.

## 사용자 설치 방법

1. 이 저장소의 **Releases**에서 `ScaleTheDepths-Korean-1.0.0.zip`을 받습니다.
2. ZIP 전체를 새 폴더에 풉니다. EXE만 따로 꺼내면 설치할 수 없습니다.
3. Steam에서 게임을 완전히 종료합니다.
4. `한국어패치.exe`를 실행합니다. Windows 관리자 권한 확인이 표시될 수 있습니다.
5. `Scale The Depths.exe`가 있는 정식 게임 폴더를 선택합니다.
6. `한국어 패치 설치`를 누릅니다.
7. 게임에서 언어를 **한국어(패치)**로 선택합니다. 패치가 기존 English 로케일을 교체하므로 언어 목록에 이 이름으로 표시됩니다.

v1.0.0 배포 ZIP의 SHA-256:

```text
0c9c17f4a7107a8ac815a622fea4b22f6f81aa9c27b9d2a1015beffe146e503c
```

기본 Steam 경로 예시:

```text
C:\Program Files (x86)\Steam\steamapps\common\Scale the Depths
```

다른 Steam 라이브러리를 사용하는 경우 실제 설치 폴더를 선택하세요.

## 원본 복구

1. 게임을 종료합니다.
2. 설치할 때 사용한 폴더의 `한국어패치.exe`를 실행합니다.
3. 같은 게임 폴더를 선택하고 `원본 복구`를 누릅니다.

최초 설치 때 게임 폴더에 만들어진 `KoreanPatch_Backup`은 복구가 끝날 때까지 삭제하지 마세요.
저장 파일은 설치·복구 대상이 아닙니다.

## 지원 범위

- Windows 정식판의 지원 해시와 일치하는 파일만 변경합니다.
- 영어 문자열 테이블 3,711개를 한국어로 교체합니다. 원래 빈 항목 1개는 유지합니다.
- Galmuri11 Regular/Bold 픽셀 폰트를 포함합니다.
- Steam 상점 페이지, 도전 과제 웹페이지, 이미지 로고는 번역 대상이 아닙니다.
- 기존 중국어 폰트 리소스를 재사용하므로 중국어 선택 시 글꼴 모양도 바뀔 수 있습니다.

게임 업데이트로 원본 파일 해시가 달라지면 설치기는 아무 파일도 바꾸지 않고 중단합니다.

## 자주 발생하는 문제

### 지원하지 않는 버전 또는 수정된 파일

Steam 업데이트 또는 다른 모드로 파일이 달라진 상태입니다. Steam의 파일 무결성 검사를 실행한 뒤 대응 패치 버전을 확인하세요.

### 게임이 실행 중이라는 메시지

게임 창과 프로세스를 완전히 종료한 뒤 다시 시도하세요.

### 패치는 적용됐지만 원본 백업이 없음

`KoreanPatch_Backup`이 없거나 이동된 상태입니다. Steam 파일 무결성 검사로 원본을 복구한 뒤 다시 설치하세요.

### EXE만 실행했더니 실패함

ZIP 안의 `manifest.json`과 `payload` 폴더가 EXE 옆에 있어야 합니다. ZIP 전체를 다시 풀어 실행하세요.

## 설치기의 안전 장치

- 지원 원본과 패치 결과를 SHA-256으로 검증
- bsdiff payload 자체의 SHA-256 검증
- 패키지 및 게임 경로 이탈 차단
- 게임 실행 중 설치·복구 차단
- 원본 백업 손상 및 누락 감지
- 모든 결과를 미리 재구성한 뒤 파일 교체 시작
- 임시 파일과 원자적 교체 사용
- 중간 교체 실패 시 이번 작업에서 변경한 파일 자동 롤백
- 설치·복구 반복 실행 지원

## 저장소 구성

```text
scripts/
  installer.py          독립 설치·복구 도구와 GUI
  test_installer.py     설치기 단위 테스트
  package_release.py    bsdiff payload, EXE, ZIP 패키징
  build_patch.py        문자열·폰트·카탈로그 번들 빌드
  pipeline.py           원문 추출 및 번역 형식 검증
  test_install.py       개발용 로컬 설치·복구
  export_public_translations.py  안정 ID 기반 공개 번역 생성
  validate_translations.py      공개 번역 데이터 검증
locales/ko/              27개 테이블의 한국어 번역 3,712항목
docs/
  manifest.example.json 배포 manifest 형식 예시
  GLOSSARY.ko.md         고정 용어와 고유명사
  STYLE_GUIDE.ko.md      문체와 형식 지침
```

한국어 번역 데이터는 table:id 안정 식별자와 함께 전부 공개합니다. 원문 변경을 감지할 수 있도록 SHA-256 지문과 플레이스홀더 정보도 제공하지만 영어 원문 자체는 포함하지 않습니다.

게임 원본, 추출한 영어 원문, 개인 백업과 완성된 payload는 Git 이력에 넣지 않습니다. 사용자가 설치하는 완성 패키지는 GitHub Releases의 ZIP으로 제공합니다. ZIP에는 원본 게임 전체가 아닌 바이너리 변경분만 포함됩니다.

## 번역 기여

번역 개선은 [locales/ko](locales/ko)의 테이블별 JSON에서 target을 수정하는 방식으로 받습니다.

    python .\scripts\validate_translations.py

PR을 보내기 전에 위 검사를 통과해야 합니다. 자세한 과정은 [기여 안내](CONTRIBUTING.md), [용어집](docs/GLOSSARY.ko.md), [문체 지침](docs/STYLE_GUIDE.ko.md)을 참고하세요.

번역 데이터와 한국어 용어집·문체 지침은 [CC BY 4.0](TRANSLATIONS-LICENSE.md), 설치기와 빌드 코드는 MIT로 배포합니다.

## 개발 및 테스트

Python 3.12 x64 기준입니다.

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe .\scripts\test_installer.py
```

설치기 EXE 빌드 예시:

```powershell
& .\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm --clean --onefile --windowed --uac-admin `
  --name 한국어패치 .\scripts\installer.py
```

`package_release.py`와 `build_patch.py`는 게임을 합법적으로 보유한 로컬 작업 환경의 원본 번들, 번역 데이터와 폰트 파일을 입력으로 사용합니다. 패치된 게임에서 `pipeline.py extract`를 실행하면 원문 원장이 오염될 수 있으므로 실행하지 마세요.

## 배포 패키지 구조

```text
한국어패치.exe
manifest.json
payload/
  00.bsdiff
  01.bsdiff
  02.bsdiff
  03.bsdiff
사용안내.md
Galmuri-OFL.txt
```

`manifest.json`은 각 파일의 지원 원본 해시, 설치 후 해시, 결과 크기, payload 경로와 payload 해시를 기록합니다.

## 라이선스

- 이 저장소의 설치기·빌드·테스트 코드는 [MIT License](LICENSE)로 배포합니다.
- locales/ko의 한국어 번역 데이터와 한국어 번역 문서는 [CC BY 4.0](TRANSLATIONS-LICENSE.md)으로 배포합니다.
- Galmuri 폰트는 SIL Open Font License 1.1이며 완성 ZIP에 라이선스 전문을 포함합니다.
- Python 의존성과 게임 자체에는 각 저작권자 및 라이선스가 적용됩니다.
