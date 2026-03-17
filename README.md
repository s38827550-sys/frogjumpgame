# 🐸 Frog Jump Game (Client)

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/Library-Pygame-green.svg)

개구리를 점프시켜 하늘을 나는 파리를 잡아 높은 점수를 얻는 아케이드 게임입니다.

## ✨ 주요 기능
- **닉네임 프로필**: 첫 실행 시 입력한 닉네임이 `player_profile.json`에 저장되어 다음 실행부터 자동으로 로그인됩니다.
- **점프 차징 시스템**: Space 키를 누르는 시간에 따라 점프 높이가 조절되는 전략적 플레이.
- **오프라인 점수 보호**: 네트워크 연결이 불안정할 경우 점수를 `pending_scores.json`에 임시 저장하고, 연결이 복구되면 자동으로 서버에 전송합니다.
- **실시간 서버 연동**: 게임 종료 즉시 전역 리더보드 서버로 점수가 전송됩니다.

## 🎮 게임 조작법
- **이동**: 좌우 방향키 (`←`, `→`)
- **점프 차징**: `Space` 키 길게 누르기 (게이지가 찰수록 높게 점프합니다)
- **점프**: `Space` 키 떼기
- **재시작**: 게임 오버 화면에서 `R` 키

## 🚀 시작하기
### 1. 필수 라이브러리 설치
```bash
pip install pygame requests
```
### 2. 게임 실행
```bash
python practice.py
```

## 🛠 설정 (`config.json`)
```json
{
  "api_base": "https://frogjump-leaderboard.onrender.com"
}
```
