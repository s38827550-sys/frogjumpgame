import os
import json
import random
import pygame
import sys

def get_base_dir() -> str:
    # PyInstaller로 빌드된 exe 실행 시: exe가 있는 폴더
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # 파이썬 실행 시: 현재 파일 폴더
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

from leaderboard_client import upload_score, flush_pending, fetch_leaderboard  # fetch_leaderboard는 현재 코드에서 미사용

pygame.init()

# =============================
# 디버그 플래그
# =============================
DEBUG_UI = False

# =============================
# 프로필(닉네임) 저장
# =============================
PROFILE_FILE = os.path.join(BASE_DIR, "player_profile.json")


def load_profile():
    if not os.path.exists(PROFILE_FILE):
        return None
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_profile(nickname: str):
    data = {"nickname": nickname}
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =============================
# 에셋 로드 헬퍼
# =============================
def load_img(name: str):
    return pygame.image.load(os.path.join(ASSETS_DIR, name)).convert_alpha()


def create_glow_surface(radius, color, alpha=120):
    size = radius * 2
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surface, (*color, alpha), (radius, radius), radius)
    return surface

DESIGN_W, DESIGN_H = 1200, 673
screen_width, screen_height = 1400, 680

SX = screen_width / DESIGN_W
SY = screen_height / DESIGN_H

def Sx(x): return int(round(x * SX))
def Sy(y): return int(round(y * SY))

def scale_rect(x, y, w, h):
    return pygame.Rect(Sx(x), Sy(y), Sx(w), Sy(h))


# =============================
# 화면 설정
# =============================
screen_width = 1400
screen_height = 680
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Frog Jump Game")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)
big_font = pygame.font.SysFont(None, 72)

# =============================
# NAME_ENTRY UI 좌표
# =============================
NAME_BOX_RECT = scale_rect(333, 316, 532, 50)
OK_BTN_RECT   = scale_rect(288, 432, 262, 60)
EXIT_BTN_RECT = scale_rect(621, 433, 273, 57)

# =============================
# 배경
# =============================
background = load_img("background_mygame2.png")
prologue_background = load_img("background_mygame_Prologue.png")
start_background = load_img("background_mygame_start.PNG")
name_entry_background = load_img("name_entry.png")
name_entry_background = pygame.transform.smoothscale(name_entry_background, (screen_width, screen_height))

def scale_img_to_screen(img, smooth=True):
    # 픽셀감 유지가 목표면 smooth=False 권장(=scale)
    if smooth:
        return pygame.transform.smoothscale(img, (screen_width, screen_height))
    return pygame.transform.scale(img, (screen_width, screen_height))

prologue_background = scale_img_to_screen(prologue_background, smooth=True)
start_background = scale_img_to_screen(start_background, smooth=True)
name_entry_background = scale_img_to_screen(name_entry_background, smooth=True)

# =============================
# 캐릭터 이미지
# =============================
frog_normal = load_img("frog_normal.png")
frog_jump = load_img("frog_jump.png")
frog_prepare = load_img("frog_prepare_jump.png")
frog_left = load_img("frog_left.png")
frog_right = load_img("frog_right.png")

character_img = frog_normal
rect = frog_normal.get_rect()

GROUND_Y = (screen_height - 170) - rect.height
MAX_JUMP_HEIGHT = 220

rect.x = screen_width // 2
rect.y = GROUND_Y

# =============================
# 이동 & 점프 파라미터
# =============================
move_speed = 4.2
air_control = 0.6
gravity = 1.2
jump_speed = 16

jump_height = 0
velocity_y = 0
target_y = GROUND_Y

charging = False
jumping = False
falling = False

# =============================
# 파리
# =============================
fly_origin = load_img("fly.png")


class Fly:
    def __init__(self):
        self.big = random.random() < 0.15
        self.size = 70 if self.big else random.randint(35, 50)

        self.image = pygame.transform.scale(fly_origin, (self.size, self.size)).convert_alpha()
        self.rect = self.image.get_rect()

        self.rect.x = random.randint(0, screen_width - self.size)

        min_y = GROUND_Y - MAX_JUMP_HEIGHT
        max_y = GROUND_Y - self.rect.height - 10
        self.rect.y = random.randint(min_y, max_y)

        # 부드러운 이동용 float 누적
        self.fx = float(self.rect.x)
        self.fy = float(self.rect.y)

        speed = 0.8 if self.big else 1.2
        self.vx = random.uniform(-speed, speed)
        self.vy = random.uniform(-speed, speed)

        if self.big:
            glow_radius = self.size // 2 + 12
            self.glow = create_glow_surface(glow_radius, color=(255, 220, 100), alpha=130)
        else:
            self.glow = None

    def update(self):
        min_y = GROUND_Y - MAX_JUMP_HEIGHT
        max_y = GROUND_Y - self.rect.height - 10

        self.fx += self.vx
        self.fy += self.vy

        if self.fx < 0:
            self.fx = 0
            self.vx *= -1
        elif self.fx > screen_width - self.rect.width:
            self.fx = screen_width - self.rect.width
            self.vx *= -1

        if self.fy < min_y:
            self.fy = min_y
            self.vy *= -1
        elif self.fy > max_y:
            self.fy = max_y
            self.vy *= -1

        self.rect.x = int(self.fx)
        self.rect.y = int(self.fy)


flies = [Fly() for _ in range(6)]

# =============================
# 점수 / 시간
# =============================
score = 0
GAME_TIME = 60
start_ticks = None
remaining_time = GAME_TIME

# =============================
# 로컬 랭킹
# =============================
RANK_FILE = os.path.join(BASE_DIR, "ranking.txt")


def load_ranking():
    if not os.path.exists(RANK_FILE):
        return []
    with open(RANK_FILE, "r", encoding="utf-8") as f:
        ranks = []
        for line in f.readlines():
            line = line.strip()
            if line.isdigit():
                ranks.append(int(line))
        return ranks


def save_score_local(new_score: int):
    ranks = load_ranking()
    ranks.append(int(new_score))
    ranks = sorted(ranks, reverse=True)[:5]
    with open(RANK_FILE, "w", encoding="utf-8") as f:
        for r in ranks:
            f.write(str(r) + "\n")
    return ranks


ranking = []

# =============================
# 점프 게이지
# =============================
def draw_jump_gauge():
    gauge_w = 120
    gauge_h = 14
    x = screen_width // 2 - gauge_w // 2
    y = screen_height - 35

    ratio = jump_height / MAX_JUMP_HEIGHT if MAX_JUMP_HEIGHT else 0.0
    color = (0, 200, 0) if ratio < 0.6 else (230, 180, 0) if ratio < 0.85 else (230, 50, 50)

    pygame.draw.rect(screen, (40, 40, 40), (x, y, gauge_w, gauge_h))
    pygame.draw.rect(screen, color, (x, y, int(gauge_w * ratio), gauge_h))


# =============================
# 게임 상태
# =============================
STATE_NAME_ENTRY = "name_entry"
STATE_PROLOGUE = "prologue"
STATE_START = "start"
STATE_GAME = "game"
STATE_GAMEOVER = "gameover"

# 프로필 로드
profile = load_profile()
if profile and profile.get("nickname", "").strip():
    nickname = profile["nickname"].strip()
    game_state = STATE_PROLOGUE
else:
    nickname = "PLAYER"
    game_state = STATE_NAME_ENTRY

# 닉네임 입력
name_text = ""
name_max_len = 16

# 텍스트 입력 활성화(IME)
if game_state == STATE_NAME_ENTRY:
    pygame.key.start_text_input()
    pygame.key.set_text_input_rect(NAME_BOX_RECT)
else:
    pygame.key.stop_text_input()

# =============================
# 프롤로그 페이드
# =============================
fade_alpha = 255
fade_speed = 3
fade_done_time = None


def reset_prologue_fade():
    global fade_alpha, fade_done_time
    fade_alpha = 255
    fade_done_time = None


# =============================
# 네트워크/업로드 큐 정리 (1회만)
# =============================
try:
    flush_pending(force=True)
except Exception:
    pass

# 업로드 중복 방지 (한 판에서 1회)
score_uploaded = False
upload_status = ""        # "UPLOADED" / "QUEUED" / "FAILED"
upload_status_time = 0    # 표시 시작 시각(ms)

# =============================
# 유틸: 게임 한 판 초기화
# =============================
def reset_round():
    global score, flies, rect, start_ticks
    global charging, jumping, falling, velocity_y, jump_height, character_img
    global ranking, score_uploaded

    score = 0
    flies = [Fly() for _ in range(6)]
    rect.x = screen_width // 2
    rect.y = GROUND_Y
    start_ticks = pygame.time.get_ticks()

    charging = False
    jumping = False
    falling = False
    velocity_y = 0
    jump_height = 0
    character_img = frog_normal

    ranking = []
    score_uploaded = False
    
    upload_status = ""
    upload_status_time = 0


# =============================
# 메인 루프
# =============================
running = True
restart_pending = False

while running:
    clock.tick(60)

    # 남은 시간 계산
    if game_state == STATE_GAME and start_ticks is not None:
        elapsed = (pygame.time.get_ticks() - start_ticks) // 1000
        remaining_time = max(0, GAME_TIME - elapsed)
    else:
        remaining_time = GAME_TIME

    # -------------------------
    # 이벤트 처리
    # -------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            continue

        # =========================
        # NAME_ENTRY
        # =========================
        if game_state == STATE_NAME_ENTRY:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if OK_BTN_RECT.collidepoint(mx, my):
                    nickname = name_text.strip() or "PLAYER"
                    save_profile(nickname)

                    pygame.key.stop_text_input()
                    reset_prologue_fade()
                    game_state = STATE_PROLOGUE

                elif EXIT_BTN_RECT.collidepoint(mx, my):
                    nickname = "PLAYER"
                    save_profile(nickname)

                    pygame.key.stop_text_input()
                    reset_prologue_fade()
                    game_state = STATE_PROLOGUE

            elif event.type == pygame.TEXTINPUT:
                if event.text and len(name_text) < name_max_len:
                    remain = name_max_len - len(name_text)
                    name_text += event.text[:remain]

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    name_text = name_text[:-1]

                elif event.key == pygame.K_RETURN:
                    nickname = name_text.strip() or "PLAYER"
                    save_profile(nickname)

                    pygame.key.stop_text_input()
                    reset_prologue_fade()
                    game_state = STATE_PROLOGUE

                elif event.key == pygame.K_ESCAPE:
                    nickname = "PLAYER"
                    save_profile(nickname)

                    pygame.key.stop_text_input()
                    reset_prologue_fade()
                    game_state = STATE_PROLOGUE

            continue  # NAME_ENTRY는 여기서 종료

        # =========================
        # START
        # =========================
        if game_state == STATE_START:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                pygame.event.clear(pygame.KEYDOWN)
                game_state = STATE_GAME
                reset_round()

        # =========================
        # GAME
        # =========================
        if game_state == STATE_GAME:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not jumping:
                    charging = True
                    jump_height = 0
                    character_img = frog_prepare

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE and charging:
                    charging = False
                    jumping = True
                    falling = False
                    target_y = GROUND_Y - jump_height
                    velocity_y = -jump_speed
                    character_img = frog_jump

        # =========================
        # GAMEOVER
        # =========================
        if game_state == STATE_GAMEOVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                restart_pending = True

    # -------------------------
    # 프레임 로직
    # -------------------------
    if game_state == STATE_GAME:
        # 파리 자동 이동
        for fly in flies:
            fly.update()

        # 좌우 이동
        keys = pygame.key.get_pressed()
        move = move_speed if not jumping else move_speed * air_control

        if keys[pygame.K_LEFT]:
            rect.x -= move
            if not jumping and not charging:
                character_img = frog_left
        elif keys[pygame.K_RIGHT]:
            rect.x += move
            if not jumping and not charging:
                character_img = frog_right
        elif not jumping and not charging:
            character_img = frog_normal

        rect.x = max(0, min(rect.x, screen_width - rect.width))

        # 점프 차징
        if charging:
            ratio = jump_height / MAX_JUMP_HEIGHT
            jump_height += max(5, int(18 * (1 - ratio)) + 1)
            jump_height = min(jump_height, MAX_JUMP_HEIGHT)

        # 점프/낙하
        if jumping:
            rect.y += velocity_y

            if not falling and rect.y <= target_y:
                rect.y = target_y
                falling = True

            if falling:
                velocity_y += gravity

            if rect.y >= GROUND_Y:
                rect.y = GROUND_Y
                jumping = False
                falling = False
                velocity_y = 0
                character_img = frog_normal

        # 충돌 처리
        for fly in flies[:]:
            if rect.colliderect(fly.rect):
                score += 2 if fly.big else 1
                flies.remove(fly)
                flies.append(Fly())

        # 타임오버 처리 -> 상태 전환
        if remaining_time == 0:
            # 로컬 랭킹 갱신 + 이번 판 랭킹 보관
            prev_ranks = load_ranking()
            prev_best = prev_ranks[0] if prev_ranks else -1

            ranking = save_score_local(score)

           # GAMEOVER로 전환되기 직전(점수가 확정된 순간)
            if not score_uploaded:
                try:
                    upload_score(nickname, score)
                    try:
                        flush_pending(force=True)
                        upload_status = "UPLOADED"
                    except Exception:
                        # 업로드는 큐에 들어갔을 수 있으니 queued로 처리
                        upload_status = "QUEUED"
                except Exception:
                    upload_status = "FAILED"

                upload_status_time = pygame.time.get_ticks()
                score_uploaded = True

            game_state = STATE_GAMEOVER


    # -------------------------
    # 렌더링
    # -------------------------
    if game_state == STATE_NAME_ENTRY:
        screen.blit(name_entry_background, (0, 0))

        caret = "|" if (pygame.time.get_ticks() // 350) % 2 == 0 else ""
        show_text = (name_text + caret) if name_text else ("Enter Name..." + caret)
        color = (255, 255, 255) if name_text else (220, 220, 220)

        text_surf = font.render(show_text, True, color)
        text_rect = text_surf.get_rect(midleft=(NAME_BOX_RECT.left + 20, NAME_BOX_RECT.centery))
        screen.blit(text_surf, text_rect)

        if DEBUG_UI:
            pygame.draw.rect(screen, (0, 200, 255), NAME_BOX_RECT, 2)

    elif game_state == STATE_PROLOGUE:
        screen.blit(prologue_background, (0, 0))

        fade_surface = pygame.Surface((screen_width, screen_height))
        fade_surface.fill((0, 0, 0))
        fade_surface.set_alpha(fade_alpha)
        screen.blit(fade_surface, (0, 0))

        fade_alpha -= fade_speed
        if fade_alpha <= 0:
            fade_alpha = 0

            if fade_done_time is None:
                fade_done_time = pygame.time.get_ticks()

            if pygame.time.get_ticks() - fade_done_time >= 1000:
                game_state = STATE_START

    elif game_state == STATE_START:
        screen.blit(start_background, (0, 0))

    elif game_state in (STATE_GAME, STATE_GAMEOVER):
        # 기본 게임 화면 렌더
        screen.blit(background, (0, 0))

        for fly in flies:
            if fly.glow:
                glow_rect = fly.glow.get_rect(center=fly.rect.center)
                screen.blit(fly.glow, glow_rect)
            screen.blit(fly.image, fly.rect)

        screen.blit(character_img, rect)

        if charging and game_state == STATE_GAME:
            draw_jump_gauge()

        timer_color = (
            (255, 80, 80)
            if (game_state == STATE_GAME and remaining_time <= 10 and (pygame.time.get_ticks() // 300) % 2 == 0)
            else (255, 255, 255)
        )

        screen.blit(font.render(f"Time : {remaining_time}", True, timer_color), (screen_width - 150, 20))
        screen.blit(font.render(f"Score : {score}", True, (255, 255, 255)), (20, 20))

        # GAMEOVER 오버레이
        if game_state == STATE_GAMEOVER:
            overlay = pygame.Surface((screen_width, screen_height))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))

            screen.blit(big_font.render("TIME OVER", True, (255, 80, 80)),
                        (screen_width // 2 - 180, 80))

            screen.blit(font.render("RANKING", True, (255, 255, 255)),
                        (screen_width // 2 - 50, 140))

            rank_start_y = 180
            line_gap = 35

            highlighted = False
            for idx, s in enumerate(ranking):
                rank = idx + 1
                if (not highlighted) and (s == score):
                    color = (255, 200, 0)
                    highlighted = True
                else:
                    color = (255, 255, 255)

                screen.blit(font.render(f"{rank} : {s}", True, color),
                            (screen_width // 2 - 70, rank_start_y))
                rank_start_y += line_gap

            screen.blit(font.render("Press R : REPLAY", True, (200, 200, 200)),
                        (screen_width // 2 - 110, rank_start_y + 30))
                # 업로드 상태 표시(5초만)
            if upload_status and (pygame.time.get_ticks() - upload_status_time) < 5000:
                screen.blit(font.render(f"SERVER: {upload_status}", True, (180, 180, 180)),
                            (screen_width // 2 - 90, rank_start_y + 70))

    pygame.display.update()

    # -------------------------
    # 재시작 처리 (프레임 종료 후)
    # -------------------------
    if restart_pending:
        # GAME으로 복귀 + 라운드 리셋
        game_state = STATE_GAME
        reset_round()
        restart_pending = False

pygame.quit()
