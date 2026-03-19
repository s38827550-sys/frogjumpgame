# 🐸 Frog Jump Game (Final Polished Version)

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/Library-Pygame-green.svg)

개구리를 점프시켜 하늘을 나는 파리를 잡아 전 세계 사용자들과 경쟁하는 아케이드 게임입니다. 

## ✨ 최신 업데이트 (v2.0)
- **귀여운 테마 적용**: 게임 감성에 어울리는 동글동글한 폰트와 아기자기한 디자인.
- **세련된 랭킹 보드**: 게임 오버 시 나타나는 고급스러운 순위표와 메달 시스템(🏆, 🥈, 🥉).
- **HUD 애니메이션**: 시간이 10초 이하일 때 두근거리는 타이머 효과 적용.
- **완전한 모듈화**: `core/` 패키지를 통한 견고한 소프트웨어 아키텍처.

## 🎮 게임 조작법
- **이동**: 좌우 방향키 (`←`, `→`)
- **점프 차징**: `Space` 키 길게 누르기
- **점프**: `Space` 키 떼기
- **재시작**: 게임 오버 화면에서 `R` 키

## 🚀 시작하기
> **Status**: **2026-03-18 Supabase(PostgreSQL) 최적화 및 안정화 완료.** 
> - **네트워크 강화**: SSL 보안 연결(`sslmode=require`) 및 타임아웃 최적화로 Supabase DB와의 연결 안정성 극대화.
> - **버전 호환성**: Python 3.12+ 및 Pydantic v2 환경 완벽 지원.
> - **데이터 무결성**: 로컬 데이터 부재 시에도 오류 없이 실행되는 방어적 설계 적용.

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
- **`core/engine.py`**: UI 애니메이션 및 게임 루프 제어 엔진.
- **`core/network.py`**: 전 세계 리더보드와 실시간 점수 동기화.
- **`core/assets.py`**: 귀여운 폰트 및 이미지 리소스 로더.

## 📊 실시간 월드 랭킹 확인
웹에서도 실시간 순위를 확인할 수 있습니다!
[https://frogjump-leaderboard-web.vercel.app/](https://frogjump-leaderboard-web.vercel.app/)
