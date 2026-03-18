# core/engine.py (Final Polished Version)
import pygame, sys, os, math
from .constants import *
from .utils import *
from .assets import AssetManager
from .models import Fly
from .network import upload_score, flush_pending

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
        self.profile = load_profile()
        self.nickname = self.profile.get("nickname", "PLAYER").strip() if self.profile else "PLAYER"
        self.state = STATE_PROLOGUE if self.profile else STATE_NAME_ENTRY
        self.reset_round_vars()
        self.init_name_entry()
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

    def init_name_entry(self):
        self.name_text = ""
        if self.state == STATE_NAME_ENTRY:
            pygame.key.start_text_input(); pygame.key.set_text_input_rect(NAME_BOX_RECT)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if self.state == STATE_NAME_ENTRY: self.handle_name_entry_event(event)
            elif self.state == STATE_START and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.state = STATE_GAME; self.reset_round_vars()
            elif self.state == STATE_GAME: self.handle_game_event(event)
            elif self.state == STATE_GAMEOVER and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.state = STATE_GAME; self.reset_round_vars()

    def handle_name_entry_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if OK_BTN_RECT.collidepoint(event.pos) or EXIT_BTN_RECT.collidepoint(event.pos): self.confirm_nickname()
        elif event.type == pygame.TEXTINPUT:
            if len(self.name_text) < 16: self.name_text += event.text
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE: self.name_text = self.name_text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE): self.confirm_nickname()

    def confirm_nickname(self):
        self.nickname = self.name_text.strip() or "PLAYER"
        save_profile(self.nickname); pygame.key.stop_text_input(); self.state = STATE_PROLOGUE

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
        if self.state == STATE_NAME_ENTRY: self.draw_name_entry()
        elif self.state == STATE_PROLOGUE: self.draw_prologue()
        elif self.state == STATE_START: self.screen.blit(self.assets.start_bg, (0, 0))
        elif self.state in (STATE_GAME, STATE_GAMEOVER): self.draw_game_main()
        pygame.display.update()

    def draw_name_entry(self):
        self.screen.blit(self.assets.name_entry_bg, (0, 0))
        caret = "|" if (pygame.time.get_ticks() // 350) % 2 == 0 else ""
        show_text = (self.name_text + caret) if self.name_text else ("Enter Name..." + caret)
        txt_surf = self.font.render(show_text, True, (255, 255, 255) if self.name_text else (220, 220, 220))
        self.screen.blit(txt_surf, txt_surf.get_rect(midleft=(NAME_BOX_RECT.left + 20, NAME_BOX_RECT.centery)))

    def draw_prologue(self):
        self.screen.blit(self.assets.prologue_bg, (0, 0))
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); fade.fill((0,0,0)); fade.set_alpha(self.fade_alpha)
        self.screen.blit(fade, (0,0))
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
        hud_bg = pygame.Surface((SCREEN_WIDTH, 60), pygame.SRCALPHA); pygame.draw.rect(hud_bg, (0, 0, 0, 80), (0, 0, SCREEN_WIDTH, 60))
        self.screen.blit(hud_bg, (0, 0))
        mini_fly = pygame.transform.scale(self.assets.fly_origin, (30, 30))
        self.screen.blit(mini_fly, (20, 15))
        self.draw_text_with_shadow(f"SCORE : {self.score}", self.font, (255, 230, 100), (60, 16))
        timer_text = f"TIME : {self.remaining_time}"
        if self.state == STATE_GAME and self.remaining_time <= 10:
            pulse = 1.0 + 0.1 * math.sin(pygame.time.get_ticks() * 0.01)
            timer_surf = pygame.transform.rotozoom(self.font.render(timer_text, True, (255, 80, 80)), 0, pulse)
            self.screen.blit(timer_surf, timer_surf.get_rect(midright=(SCREEN_WIDTH - 20, 30)))
        else: self.draw_text_with_shadow(timer_text, self.font, (255, 255, 255), (SCREEN_WIDTH - 180, 16))

    def draw_gauge(self):
        w, h, x, y = 120, 14, SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT - 35
        ratio = self.jump_height / MAX_JUMP_HEIGHT
        color = (0, 200, 0) if ratio < 0.6 else (230, 180, 0) if ratio < 0.85 else (230, 50, 50)
        pygame.draw.rect(self.screen, (40, 40, 40), (x, y, w, h)); pygame.draw.rect(self.screen, color, (x, y, int(w * ratio), h))

    def draw_gameover(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 160)); self.screen.blit(overlay, (0, 0))
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
        while True:
            self.clock.tick(60); self.handle_events(); self.update(); self.draw()
