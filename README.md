# 🐸 Frog Jump Game (Client)

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/Library-Pygame-green.svg)

개구리를 점프시켜 하늘을 나는 파리를 잡아 높은 점수를 얻는 아케이드 게임입니다.

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

## 🛠 주요 설정 (`config.json`)
서버와 연동하기 위해 `config.json` 파일에 서버 주소를 설정할 수 있습니다.
```json
{
  "api_base": "http://your-server-address:8000"
}
```

## 📁 주요 파일 구성
- `practice.py`: 게임의 메인 로직 및 렌더링.
- `leaderboard_client.py`: 서버와 통신하여 점수 업로드 및 큐잉 담당.
- `assets/`: 게임에 필요한 이미지 리소스.
- `player_profile.json`: 사용자의 닉네임 정보 저장.
