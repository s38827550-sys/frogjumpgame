# 🐸 Frog Jump Game (Final Polished Version)

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Pygame](https://img.shields.io/badge/Library-Pygame-green.svg)

개구리를 점프시켜 하늘을 나는 파리를 잡아 전 세계 사용자들과 경쟁하는 아케이드 게임입니다. 

## ✨ 최신 업데이트 (v2.2)
- **네트워크 동기화 강화**: 실시간 리더보드 연동 및 전송 실패 시 로컬 큐(Pending Scores) 저장 기능 추가.
- **고급 게임 엔진**: 물리 엔진 최적화 및 세련된 UI 애니메이션 (충전 게이지, 타이머 펄스 등).
- **구조적 리팩토링**: `pathlib` 기반의 견고한 경로 처리 및 `core/` 패키지 모듈화 완성.
- **안정성 개선**: 네트워크 타임아웃 처리 및 사용자 프로필 관리 시스템 고도화.

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
