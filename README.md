# 🐸 Frog Jump Game (Final Polished Version)

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Pygame](https://img.shields.io/badge/Library-Pygame-green.svg)

개구리를 점프시켜 하늘을 나는 파리를 잡아 전 세계 사용자들과 경쟁하는 아케이드 게임입니다. 

## ✨ 최신 업데이트 (v1.1 / Stable Release)
- **빌드 안정성 확보**: PyInstaller 단일 파일(`.exe`) 빌드 시 자산 경로(sys._MEIPASS) 및 확장자 대소문자 호환성 완벽 지원.
- **배포 최적화**: 사용자 데이터가 없는 깨끗한 초기 상태의 배포판(`frogjumpgame.v1.1.exe`) 제작 및 배포 프로세스 수립.
- **네트워크 동기화 강화**: 실시간 리더보드 연동 및 서버 전송 실패 시 로컬 큐(Pending Scores)에 점수를 안전하게 저장하는 기능 최적화.
- **고급 게임 엔진**: 물리 엔진 최적화 및 세련된 UI 애니메이션 (충전 게이지, 타이머 펄스 등) 적용.
- **Pathlib 리팩토링**: 모든 파일 경로 관리를 `pathlib`으로 전환하여 유지보수성 향상.


## 📦 실행 파일 배포 (Deployment)
본 게임은 `PyInstaller`를 통해 단일 실행 파일로 배포할 수 있습니다.
```powershell
# 단일 파일 빌드 (아이콘 및 자산 포함)
pyinstaller --onefile --noconsole --add-data "assets;assets" --add-data "config.json;." --icon "assets/frog.ico" --name "frogjumpgame.v1.1" main.py
```
*주의: 빌드 전 `core/constants.py`와 `core/assets.py`의 경로 로직이 배포용으로 설정되어 있는지 확인하세요.*

## 🎮 게임 조작법
- **이동**: 좌우 방향키 (`←`, `→`)
- **점프 차징**: `Space` 키 길게 누르기
- **점프**: `Space` 키 떼기 (높이는 차징 시간에 비례)
- **재시작**: 게임 오버 화면에서 `R` 키

## 🚀 시작하기

### 1. 필수 라이브러리 설치
```bash
pip install pygame
```

### 2. 게임 실행
```bash
python main.py
```

## 📁 프로젝트 구조
- **`main.py`**: 게임 실행 진입점.
- **`core/engine.py`**: UI 애니메이션 및 메인 게임 루프.
- **`core/network.py`**: 서버 연동 및 펜딩 점수 처리.
- **`core/assets.py`**: 리소스(이미지, 폰트) 관리자.
- **`core/constants.py`**: 전역 설정 및 경로 상수.

## 📊 실시간 월드 랭킹 확인
웹에서도 실시간 순위를 확인할 수 있습니다!
[https://frogjump-leaderboard-web.vercel.app/](https://frogjump-leaderboard-web.vercel.app/)
