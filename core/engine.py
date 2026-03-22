# core/engine.py
import pygame, sys, os, math
from .constants import *
from .utils import *
from .assets import AssetManager
from .models import Fly
from .network import upload_score, flush_pending, login_with_supabase, load_web_token, logout

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Frog Jump Game")
        try:
            icon = pygame.image.load(os.path.join(ASSETS_DIR, "frog.ico"))
            pygame.display.set_icon(icon)
        except: pass
        self.clock = pygame.time.Clock()
        self.assets = AssetManager()
        self.font = self.assets.get_font(36)
        self.big_font = self.assets.get_font(80)
        self.small_font = self.assets.get_font(24)

        # 배경 이미지 로드 (웹페이지랑 같은 배경)
        try:
            bg_path = os.path.join(ASSETS_DIR, "background_mygame2.png")
            self.login_bg = pygame.image.load(bg_path).convert()
            self.login_bg = pygame.transform.scale(self.login_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except:
            self.login_bg = None

        # 로그인 상태 변수
        self.login_id = ""
        self.login_pw = ""
        self.login_active_field = "id"  # "id" or "pw"
        self.login_error = ""
        self.login_loading = False

        # 저장된 토큰 확인
        token = load_web_token()
        if token and token.get("access_token"):
            self.nickname = token.get("nickname", "PLAYER")
            self.state = STATE_PROLOGUE
        else:
            self.state = STATE_LOGIN

        self.reset_round_vars()
        self.fade_alpha, self.fade_speed, self.fade_done_time = 255, 3, None
        self.score_uploaded, self.upload_status, self.upload_status_time = False, "", 0
        try: flush_pending(force=True)
        except Exception as e: print(f"Pending sync failed: {e}")

    def reset_round_vars(self):
        self.score = 0
        self.remaining_time = GAME_TIME
        self.ground_y = (SCREEN_HEIGHT - 170) - self.assets.frog_normal.get_rect().height
        self.flies = [Fly(self.assets.fly_origin, self.ground_y) for _ in range(6)]
        self.frog_rect = self.assets.frog_normal.get_rect()
        self.frog_rect.x, self.frog_rect.y = SCREEN_WIDTH // 2, self.ground_y
        self.start_ticks = pygame.time.get_ticks()
        self.charging = self.jumping = self.falling = False
        self.velocity_y = self.jump_height = 0
        self.target_y = self.ground_y
        self.character_img = self.assets.frog_normal
        self.ranking, self.score_uploaded, self.upload_status = [], False, ""

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if self.state == STATE_LOGIN: self.handle_login_event(event)
            elif self.state == STATE_START and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.state = STATE_GAME; self.reset_round_vars()
            elif self.state == STATE_GAME: self.handle_game_event(event)
            elif self.state == STATE_GAMEOVER and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.state = STATE_GAME; self.reset_round_vars()

    def handle_login_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 필드 클릭 감지
            if LOGIN_ID_BOX.collidepoint(event.pos):
                self.login_active_field = "id"
            elif LOGIN_PW_BOX.collidepoint(event.pos):
                self.login_active_field = "pw"
            elif LOGIN_BTN_RECT.collidepoint(event.pos):
                self.try_login()
            elif LOGIN_EXIT_RECT.collidepoint(event.pos):
                pygame.quit(); sys.exit()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.login_active_field == "id":
                    self.login_active_field = "pw"
                else:
                    self.try_login()
            elif event.key == pygame.K_TAB:
                self.login_active_field = "pw" if self.login_active_field == "id" else "id"
            elif event.key == pygame.K_BACKSPACE:
                if self.login_active_field == "id":
                    self.login_id = self.login_id[:-1]
                else:
                    self.login_pw = self.login_pw[:-1]
            elif event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

        elif event.type == pygame.TEXTINPUT:
            if self.login_active_field == "id" and len(self.login_id) < 20:
                self.login_id += event.text
            elif self.login_active_field == "pw" and len(self.login_pw) < 30:
                self.login_pw += event.text

    def try_login(self):
        if not self.login_id.strip() or not self.login_pw.strip():
            self.login_error = "Please enter ID and Password"
            return
        self.login_error = "Logging in..."
        self.login_loading = True

        result = login_with_supabase(self.login_id.strip(), self.login_pw.strip())

        self.login_loading = False
        if result is None:
            self.login_error = "Invalid ID or Password"
        elif result.get("error") == "deleted":
            self.login_error = "This account has been deleted"
        else:
            self.nickname = result.get("nickname", self.login_id)
            self.login_error = ""
            self.state = STATE_PROLOGUE
            self.fade_alpha = 255
            self.fade_done_time = None

    def handle_game_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and not self.jumping:
            self.charging, self.jump_height, self.character_img = True, 0, self.assets.frog_prepare
        elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE and self.charging:
            self.charging, self.jumping, self.target_y = False, True, self.ground_y - self.jump_height
            self.velocity_y, self.character_img = -JUMP_SPEED, self.assets.frog_jump

    def update(self):
        if self.state == STATE_GAME:
            elapsed = (pygame.time.get_ticks() - self.start_ticks) // 1000
            self.remaining_time = max(0, GAME_TIME - elapsed)
            if self.remaining_time == 0: self.game_over(); return
            for fly in self.flies: fly.update()
            keys = pygame.key.get_pressed()
            move = MOVE_SPEED if not self.jumping else MOVE_SPEED * AIR_CONTROL
            if keys[pygame.K_LEFT]:
                self.frog_rect.x -= move
                if not self.jumping and not self.charging: self.character_img = self.assets.frog_left
            elif keys[pygame.K_RIGHT]:
                self.frog_rect.x += move
                if not self.jumping and not self.charging: self.character_img = self.assets.frog_right
            elif not self.jumping and not self.charging: self.character_img = self.assets.frog_normal
            self.frog_rect.x = max(0, min(self.frog_rect.x, SCREEN_WIDTH - self.frog_rect.width))
            if self.charging:
                ratio = self.jump_height / MAX_JUMP_HEIGHT
                self.jump_height = min(self.jump_height + max(5, int(18 * (1 - ratio)) + 1), MAX_JUMP_HEIGHT)
            if self.jumping:
                self.frog_rect.y += self.velocity_y
                if not self.falling and self.frog_rect.y <= self.target_y: self.frog_rect.y, self.falling = self.target_y, True
                if self.falling: self.velocity_y += GRAVITY
                if self.frog_rect.y >= self.ground_y:
                    self.frog_rect.y, self.jumping, self.falling, self.velocity_y = self.ground_y, False, False, 0
                    self.character_img = self.assets.frog_normal
            for fly in self.flies[:]:
                if self.frog_rect.colliderect(fly.rect):
                    self.score += 2 if fly.big else 1
                    self.flies.remove(fly); self.flies.append(Fly(self.assets.fly_origin, self.ground_y))

    def game_over(self):
        self.ranking = save_score_local(self.score)
        if not self.score_uploaded:
            self.upload_status = "UPLOADED" if upload_score(self.nickname, self.score) else "QUEUED"
            self.upload_status_time, self.score_uploaded = pygame.time.get_ticks(), True
        self.state = STATE_GAMEOVER

    def draw(self):
        if self.state == STATE_LOGIN: self.draw_login()
        elif self.state == STATE_PROLOGUE: self.draw_prologue()
        elif self.state == STATE_START: self.screen.blit(self.assets.start_bg, (0, 0))
        elif self.state in (STATE_GAME, STATE_GAMEOVER): self.draw_game_main()
        pygame.display.update()

    def draw_login(self):
        # 배경
        if self.login_bg:
            self.screen.blit(self.login_bg, (0, 0))
        else:
            self.screen.fill((10, 22, 40))

        # 어두운 오버레이
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        # 개구리 이미지 + 타이틀 (나란히 배치)
        frog_scaled = pygame.transform.scale(self.assets.frog_normal, (90, 90))
        title_surf = self.big_font.render("Frog Jump", True, (245, 200, 66))
        shadow_surf = self.big_font.render("Frog Jump", True, (0, 0, 0))

        total_w = frog_scaled.get_width() + 20 + title_surf.get_width()
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        title_y = Sy(80)

        # 그림자 + 타이틀
        self.screen.blit(shadow_surf, (start_x + frog_scaled.get_width() + 20 + 3, title_y + 3))
        self.screen.blit(title_surf, (start_x + frog_scaled.get_width() + 20, title_y))
        # 개구리 이미지 (세로 중앙 맞춤)
        frog_y = title_y + title_surf.get_height() // 2 - frog_scaled.get_height() // 2
        self.screen.blit(frog_scaled, (start_x, frog_y))

        # 로그인 박스
        box_w, box_h = Sx(440), Sy(340)
        box_x = SCREEN_WIDTH // 2 - box_w // 2
        box_y = SCREEN_HEIGHT // 2 - box_h // 2 + Sy(40)

        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.rect(box_surf, (0, 0, 0, 180), (0, 0, box_w, box_h), border_radius=16)
        pygame.draw.rect(box_surf, (74, 124, 63, 255), (0, 0, box_w, box_h), width=2, border_radius=16)
        self.screen.blit(box_surf, (box_x, box_y))

        # 아이디 라벨 (영문)
        id_label = self.small_font.render("ID", True, (180, 180, 180))
        self.screen.blit(id_label, (LOGIN_ID_BOX.x, LOGIN_ID_BOX.y - Sy(28)))

        # 아이디 입력창
        id_active = self.login_active_field == "id"
        id_border_color = (74, 124, 63) if id_active else (60, 60, 60)
        pygame.draw.rect(self.screen, (30, 30, 30), LOGIN_ID_BOX, border_radius=8)
        pygame.draw.rect(self.screen, id_border_color, LOGIN_ID_BOX, width=2, border_radius=8)
        caret = "|" if id_active and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        id_surf = self.font.render(self.login_id + caret, True, (255, 255, 255))
        # 텍스트가 박스 넘치지 않도록 clip
        clip_rect = pygame.Rect(LOGIN_ID_BOX.x + 12, LOGIN_ID_BOX.y, LOGIN_ID_BOX.w - 20, LOGIN_ID_BOX.h)
        self.screen.set_clip(clip_rect)
        self.screen.blit(id_surf, (LOGIN_ID_BOX.x + 12, LOGIN_ID_BOX.y + LOGIN_ID_BOX.h // 2 - id_surf.get_height() // 2))
        self.screen.set_clip(None)

        # 비밀번호 라벨 (영문)
        pw_label = self.small_font.render("Password", True, (180, 180, 180))
        self.screen.blit(pw_label, (LOGIN_PW_BOX.x, LOGIN_PW_BOX.y - Sy(28)))

        # 비밀번호 입력창
        pw_active = self.login_active_field == "pw"
        pw_border_color = (74, 124, 63) if pw_active else (60, 60, 60)
        pygame.draw.rect(self.screen, (30, 30, 30), LOGIN_PW_BOX, border_radius=8)
        pygame.draw.rect(self.screen, pw_border_color, LOGIN_PW_BOX, width=2, border_radius=8)
        pw_caret = "|" if pw_active and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        pw_display = "*" * len(self.login_pw) + pw_caret
        pw_surf = self.font.render(pw_display, True, (255, 255, 255))
        clip_rect = pygame.Rect(LOGIN_PW_BOX.x + 12, LOGIN_PW_BOX.y, LOGIN_PW_BOX.w - 20, LOGIN_PW_BOX.h)
        self.screen.set_clip(clip_rect)
        self.screen.blit(pw_surf, (LOGIN_PW_BOX.x + 12, LOGIN_PW_BOX.y + LOGIN_PW_BOX.h // 2 - pw_surf.get_height() // 2))
        self.screen.set_clip(None)

        # 에러 메시지
        if self.login_error:
            err_color = (122, 232, 255) if self.login_error == "Logging in..." else (255, 100, 100)
            err_surf = self.small_font.render(self.login_error, True, err_color)
            self.screen.blit(err_surf, err_surf.get_rect(center=(SCREEN_WIDTH // 2, LOGIN_BTN_RECT.y - Sy(18))))

        # 로그인 버튼
        btn_hover = LOGIN_BTN_RECT.collidepoint(pygame.mouse.get_pos())
        btn_color = (90, 156, 79) if btn_hover else (74, 124, 63)
        pygame.draw.rect(self.screen, btn_color, LOGIN_BTN_RECT, border_radius=10)
        pygame.draw.rect(self.screen, (100, 180, 90), LOGIN_BTN_RECT, width=1, border_radius=10)
        btn_surf = self.font.render("Login", True, (255, 255, 255))
        self.screen.blit(btn_surf, btn_surf.get_rect(center=LOGIN_BTN_RECT.center))

        # 종료 버튼
        exit_surf = self.small_font.render("Exit  (ESC)", True, (150, 150, 150))
        self.screen.blit(exit_surf, exit_surf.get_rect(center=LOGIN_EXIT_RECT.center))

        # 안내 문구
        guide_surf = self.small_font.render("Please sign up on the website first", True, (120, 120, 120))
        self.screen.blit(guide_surf, guide_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - Sy(30))))

    def draw_prologue(self):
        self.screen.blit(self.assets.prologue_bg, (0, 0))
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade.fill((0, 0, 0))
        fade.set_alpha(self.fade_alpha)
        self.screen.blit(fade, (0, 0))
        self.fade_alpha = max(0, self.fade_alpha - self.fade_speed)
        if self.fade_alpha == 0:
            if not self.fade_done_time: self.fade_done_time = pygame.time.get_ticks()
            if pygame.time.get_ticks() - self.fade_done_time >= 1000: self.state = STATE_START

    def draw_game_main(self):
        self.screen.blit(self.assets.background, (0, 0))
        for fly in self.flies:
            if fly.glow: self.screen.blit(fly.glow, fly.glow.get_rect(center=fly.rect.center))
            self.screen.blit(fly.image, fly.rect)
        self.screen.blit(self.character_img, self.frog_rect)
        self.draw_hud()
        if self.charging and self.state == STATE_GAME: self.draw_gauge()
        if self.state == STATE_GAMEOVER: self.draw_gameover()

    def draw_text_with_shadow(self, text, font, color, pos, shadow_color=(0, 0, 0), offset=(2, 2)):
        shadow_surf = font.render(text, True, shadow_color)
        self.screen.blit(shadow_surf, (pos[0] + offset[0], pos[1] + offset[1]))
        text_surf = font.render(text, True, color)
        self.screen.blit(text_surf, pos)

    def draw_hud(self):
        hud_bg = pygame.Surface((SCREEN_WIDTH, 60), pygame.SRCALPHA)
        pygame.draw.rect(hud_bg, (0, 0, 0, 80), (0, 0, SCREEN_WIDTH, 60))
        self.screen.blit(hud_bg, (0, 0))
        mini_fly = pygame.transform.scale(self.assets.fly_origin, (30, 30))
        self.screen.blit(mini_fly, (20, 15))
        self.draw_text_with_shadow(f"SCORE : {self.score}", self.font, (255, 230, 100), (60, 16))
        timer_text = f"TIME : {self.remaining_time}"
        if self.state == STATE_GAME and self.remaining_time <= 10:
            pulse = 1.0 + 0.1 * math.sin(pygame.time.get_ticks() * 0.01)
            timer_surf = pygame.transform.rotozoom(self.font.render(timer_text, True, (255, 80, 80)), 0, pulse)
            self.screen.blit(timer_surf, timer_surf.get_rect(midright=(SCREEN_WIDTH - 20, 30)))
        else:
            self.draw_text_with_shadow(timer_text, self.font, (255, 255, 255), (SCREEN_WIDTH - 180, 16))

    def draw_gauge(self):
        w, h, x, y = 120, 14, SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT - 35
        ratio = self.jump_height / MAX_JUMP_HEIGHT
        color = (0, 200, 0) if ratio < 0.6 else (230, 180, 0) if ratio < 0.85 else (230, 50, 50)
        pygame.draw.rect(self.screen, (40, 40, 40), (x, y, w, h))
        pygame.draw.rect(self.screen, color, (x, y, int(w * ratio), h))

    def draw_gameover(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        board_w, board_h = 500, 500
        board_x, board_y = SCREEN_WIDTH // 2 - board_w // 2, 60
        pygame.draw.rect(self.screen, (40, 30, 0, 100), (board_x + 8, board_y + 8, board_w, board_h), border_radius=25)
        pygame.draw.rect(self.screen, (255, 250, 230), (board_x, board_y, board_w, board_h), border_radius=25)
        pygame.draw.rect(self.screen, (100, 80, 40), (board_x, board_y, board_w, board_h), width=5, border_radius=25)
        title_surf = self.big_font.render("TIME OVER!", True, (230, 50, 50))
        self.screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, board_y + 60)))
        rank_y, line_h = board_y + 130, 55
        icons = ["🏆", "🥈", "🥉", "⭐", "⭐"]
        for i, s in enumerate(self.ranking):
            is_cur = (s == self.score)
            bg_color = (255, 220, 100) if is_cur else (245, 240, 210)
            row_rect = pygame.Rect(board_x + 25, rank_y - 10, board_w - 50, 45)
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=12)
            if is_cur: pygame.draw.rect(self.screen, (255, 100, 0), row_rect, width=3, border_radius=12)
            rank_txt = f"{icons[i] if i<5 else '•'}  RANK {i+1} : {s:,}"
            txt_surf = self.font.render(rank_txt, True, (40, 40, 40))
            self.screen.blit(txt_surf, txt_surf.get_rect(midleft=(board_x + 50, rank_y + 12)))
            rank_y += line_h
        replay_surf = self.font.render("Press [ R ] to Replay!", True, (80, 60, 30))
        self.screen.blit(replay_surf, replay_surf.get_rect(center=(SCREEN_WIDTH // 2, board_y + board_h - 65)))
        if self.upload_status and (pygame.time.get_ticks() - self.upload_status_time) < 5000:
            status_surf = self.small_font.render(f"Server: {self.upload_status}", True, (150, 150, 150))
            self.screen.blit(status_surf, status_surf.get_rect(center=(SCREEN_WIDTH // 2, board_y + board_h - 25)))

    def run(self):
        pygame.key.start_text_input()
        while True:
            self.clock.tick(60)
            self.handle_events()
            self.update()
            self.draw()