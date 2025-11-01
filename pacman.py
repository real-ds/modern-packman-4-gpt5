import pygame
import pygame.freetype as freetype
import sys
import random
import math

# -----------------------------
# Config & Level
# -----------------------------
TILE = 24
FPS = 60
NUM_GHOSTS = 4           # number of ghosts to spawn (use 3 or 4)
SPAWN_FREEZE = 1.5       # seconds ghosts are frozen after each spawn/reset

# Movement smoothing
TURN_THRESHOLD = max(6, TILE // 4)  # pixels from tile center to allow turning
SNAP_ON_BUMP = True                 # snap to center axis when bumping a wall

# Make corridors "feel" wider by using a smaller hitbox than the drawn sprite
PACMAN_HITBOX_SHRINK = max(4, TILE // 6)   # shrink on each side (visual size unchanged)

# Evolution System
CLIP_DURATION = 2.0       # Wall Clip: pass through maze walls
STUN_DURATION = 5.0       # Ghost Stun: ghosts freeze
SHIFT_DURATION = 4.0      # Dimension Shift: invulnerability + phasing
SPECIAL_SPAWN_COUNT = 3   # how many special pellets to spawn when Tier 2 unlocks

# Side HUDs
SIDE_HUD_W = 200          # width of left/right HUD panels
HUD_PADDING = 10
HUD_LINE_GAP = 6

LEVEL_MAP = [
    "XXXXXXXXXXXXXXXXXXXXX",
    "Xo........X........oX",
    "X.XXX.XXX.X.XXX.XXX.X",
    "X...................X",
    "X.XXX.X.XXXXX.X.XXX.X",
    "X.....X...X...X.....X",
    "XXXXX.XXX.X.X.XXX.XXX",
    "X.........X.........X",
    "X.XXX.XXXXX.XXXXX.XXX",
    "X.........P.........X",
    "X...................X",  # cleaned (was GGG); pellets everywhere now
    "X.XXX.XXXXX.XXXXX.XXX",
    "X.XXX.XXX.X.XXX.XXX.X",
    "X.....X...X...X.....X",
    "X.XXX.X.XXXXX.X.XXX.X",
    "X...................X",
    "X.XXX.XXX.X.XXX.XXX.X",
    "X.....X...X...X.....X",
    "X.XXX.X.XXXXX.X.XXX.X",
    "Xo........X........oX",
    "XXXXXXXXXXXXXXXXXXXXX",
]

COLS = len(LEVEL_MAP[0])
ROWS = len(LEVEL_MAP)
WIDTH = COLS * TILE      # playfield width (maze only)
HEIGHT = ROWS * TILE     # playfield height (maze only)

# Colors
BLACK  = (0, 0, 0)
DARK   = (10, 12, 18)        # screen background
BLUE   = (0, 80, 200)
YELLOW = (255, 210, 0)
WHITE  = (255, 255, 255)
PINK   = (255, 105, 180)
RED    = (255, 60, 60)
CYAN   = (0, 255, 255)
ORANGE = (255, 165, 0)
GREY   = (100, 100, 100)
VIOLET = (185, 120, 255)     # special pellet color
GOLD   = (255, 200, 0)       # UI highlight

# HUD colors
PANEL_BG = (18, 22, 32)
PANEL_ACCENT = (40, 60, 110)
BAR_BG = (40, 44, 58)
BAR_FILL = (90, 180, 255)
BAR_FILL_GOLD = (255, 190, 60)

# Directions (dx, dy)
DIRS = {
    "STOP": (0, 0),
    "UP":   (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}
OPPOSITE = {
    DIRS["UP"]: DIRS["DOWN"],
    DIRS["DOWN"]: DIRS["UP"],
    DIRS["LEFT"]: DIRS["RIGHT"],
    DIRS["RIGHT"]: DIRS["LEFT"],
    DIRS["STOP"]: DIRS["STOP"],
}

# -----------------------------
# Helpers
# -----------------------------
def cell_to_center(c, r):
    return (c * TILE + TILE // 2, r * TILE + TILE // 2)

def pos_to_cell(x, y):
    return (int(x // TILE), int(y // TILE))

def rect_from_center(x, y, size):
    r = pygame.Rect(0, 0, size, size)
    r.center = (x, y)
    return r

def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

# -----------------------------
# Level Build
# -----------------------------
class Level:
    def __init__(self, level_map):
        self.map = [list(row) for row in level_map]
        self.walls = []
        self.pellets = set()
        self.power = set()
        self.special = set()     # special pellets for Ghost Stun
        self.pacman_spawn = None
        self.ghost_spawns = []
        # parse
        for r, row in enumerate(self.map):
            if len(row) != COLS:
                raise ValueError("Inconsistent row length in map")
            for c, ch in enumerate(row):
                if ch == 'X':
                    self.walls.append(pygame.Rect(c*TILE, r*TILE, TILE, TILE))
                elif ch == '.':
                    self.pellets.add((c, r))
                elif ch == 'o':
                    self.power.add((c, r))
                elif ch == 'P':
                    self.pacman_spawn = (c, r)
                elif ch == 'G':
                    self.ghost_spawns.append((c, r))
        if self.pacman_spawn is None:
            self.pacman_spawn = (1, 1)
        if not self.ghost_spawns:
            self.ghost_spawns = [(COLS//2, ROWS//2)]

    def is_wall(self, c, r):
        if c < 0 or r < 0 or c >= COLS or r >= ROWS:
            return True
        return self.map[r][c] == 'X'

    def passable(self, c, r):
        return not self.is_wall(c, r)

    def reset_collectibles(self, base_map):
        # rebuild pellets/power based on base map (do not reset spawns)
        self.pellets.clear()
        self.power.clear()
        self.special.clear()
        for r, row in enumerate(base_map):
            for c, ch in enumerate(row):
                if ch == '.':
                    self.pellets.add((c, r))
                elif ch == 'o':
                    self.power.add((c, r))

    # ------ Corner spawn helpers ------
    def nearest_open(self, start_c, start_r):
        # Find the nearest non-wall tile from (start_c, start_r)
        if self.passable(start_c, start_r):
            return (start_c, start_r)
        from collections import deque
        q = deque([(start_c, start_r)])
        seen = {(start_c, start_r)}
        while q:
            c, r = q.popleft()
            if self.passable(c, r):
                return (c, r)
            for dc, dr in ((1,0), (-1,0), (0,1), (0,-1)):
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS and (nc, nr) not in seen:
                    seen.add((nc, nr))
                    q.append((nc, nr))
        return (start_c, start_r)

    def corner_spawns(self):
        # Top-left, top-right, bottom-right, bottom-left
        corners = [
            (1, 1),
            (COLS - 2, 1),
            (COLS - 2, ROWS - 2),
            (1, ROWS - 2),
        ]
        spawns = []
        for c, r in corners:
            s = self.nearest_open(c, r)
            if s == self.pacman_spawn:
                s = self.nearest_open(s[0] + 1, s[1])
            spawns.append(s)
        return spawns

    # ------ Special pellet helpers ------
    def spawn_special(self, count=SPECIAL_SPAWN_COUNT):
        # Convert random normal pellets into special pellets
        available = list(self.pellets)
        random.shuffle(available)
        n = min(count, len(available))
        for i in range(n):
            cell = available[i]
            if cell in self.pellets:
                self.pellets.remove(cell)
                self.special.add(cell)

# -----------------------------
# Entities
# -----------------------------
class Pacman:
    def __init__(self, level):
        self.level = level
        sx, sy = cell_to_center(*level.pacman_spawn)
        self.x = float(sx)
        self.y = float(sy)
        self.size = int(TILE * 0.8)  # visual size
        self.hit_size = max(10, self.size - 2 * PACMAN_HITBOX_SHRINK)  # collision size
        self.speed = 125.0  # px/s
        self.dir = DIRS["LEFT"]
        self.desired_dir = DIRS["LEFT"]
        self.alive = True
        self.mouth_timer = 0.0
        self.mouth_open = True

    def rect(self):
        # collision rect (smaller than drawn sprite)
        return rect_from_center(self.x, self.y, self.hit_size)

    def _cell(self):
        return pos_to_cell(self.x, self.y)

    def _center(self):
        c, r = self._cell()
        return cell_to_center(c, r)

    def _near_center_for_turn(self, d):
        # Allow turn when close to tile center along the perpendicular axis
        cx, cy = self._center()
        if d[0] != 0:  # turning horizontal: must align vertically
            return abs(self.y - cy) <= TURN_THRESHOLD
        if d[1] != 0:  # turning vertical: must align horizontally
            return abs(self.x - cx) <= TURN_THRESHOLD
        return False

    def _can_enter_dir(self, d):
        c, r = self._cell()
        nc, nr = c + d[0], r + d[1]
        return self.level.passable(nc, nr)

    def update(self, dt, level, phasing=False):
        # Immediate reverse allowed
        if self.desired_dir == OPPOSITE.get(self.dir):
            self.dir = self.desired_dir

        # Turn early if near center and path is open
        if self.desired_dir != self.dir and self._can_enter_dir(self.desired_dir) and self._near_center_for_turn(self.desired_dir):
            cx, cy = self._center()
            if self.desired_dir[0] != 0:
                self.y = cy
            else:
                self.x = cx
            self.dir = self.desired_dir

        vx = self.dir[0] * self.speed * dt
        vy = self.dir[1] * self.speed * dt

        if phasing:
            self.x += vx
            self.y += vy
        else:
            collided_h = False
            collided_v = False

            # Horizontal
            self.x += vx
            r = self.rect()
            for w in level.walls:
                if r.colliderect(w):
                    collided_h = True
                    if vx > 0:
                        self.x = w.left - self.hit_size / 2
                    elif vx < 0:
                        self.x = w.right + self.hit_size / 2
                    r.centerx = int(self.x)

            # Vertical
            self.y += vy
            r = self.rect()
            for w in level.walls:
                if r.colliderect(w):
                    collided_v = True
                    if vy > 0:
                        self.y = w.top - self.hit_size / 2
                    elif vy < 0:
                        self.y = w.bottom + self.hit_size / 2
                    r.centery = int(self.y)

            # Cornering assist on bump
            if (collided_h or collided_v) and self.desired_dir != self.dir and self._can_enter_dir(self.desired_dir):
                cx, cy = self._center()
                if SNAP_ON_BUMP:
                    if collided_h:
                        self.y = cy
                    if collided_v:
                        self.x = cx
                self.dir = self.desired_dir

        # Mouth animation
        self.mouth_timer += dt
        if self.mouth_timer > 0.08:
            self.mouth_open = not self.mouth_open
            self.mouth_timer = 0.0

    def draw(self, surf, shift_active=False, clip_active=False):
        center = (int(self.x), int(self.y))
        radius = self.size // 2
        angle = 0.35 if self.mouth_open else 0.05
        # Determine facing angle
        dx, dy = self.dir
        facing = 0
        if dx == 1:   facing = 0
        elif dx == -1:facing = math.pi
        elif dy == -1:facing = -math.pi/2
        elif dy == 1: facing = math.pi/2

        start_angle = facing + angle
        end_angle = facing - angle
        pygame.draw.circle(surf, YELLOW, center, radius)
        # Mouth "cut" by drawing a filled triangle in black
        mouth_pts = [center,
                     (int(center[0] + math.cos(start_angle)*radius),
                      int(center[1] + math.sin(start_angle)*radius)),
                     (int(center[0] + math.cos(end_angle)*radius),
                      int(center[1] + math.sin(end_angle)*radius))]
        pygame.draw.polygon(surf, BLACK, mouth_pts)

        # Ability aura
        if shift_active:
            pygame.draw.circle(surf, GOLD, center, radius+4, width=2)
        elif clip_active:
            pygame.draw.circle(surf, CYAN, center, radius+3, width=2)

class Ghost:
    def __init__(self, level, spawn_cell, color, name="ghost"):
        self.level = level
        sx, sy = cell_to_center(*spawn_cell)
        self.spawn = spawn_cell
        self.x = float(sx)
        self.y = float(sy)
        self.size = int(TILE * 0.8)
        self.base_speed = 100.0
        self.frightened_speed = 70.0
        self.eyes_speed = 140.0
        self.dir = random.choice([DIRS["LEFT"], DIRS["RIGHT"], DIRS["UP"], DIRS["DOWN"]])
        self.state = "chase"  # chase | frightened | eyes
        self.color = color
        self.name = name
        self.frozen = False   # for stun

    def rect(self):
        return rect_from_center(self.x, self.y, self.size)

    def at_tile_center(self):
        c, r = pos_to_cell(self.x, self.y)
        cx, cy = cell_to_center(c, r)
        return abs(self.x - cx) < 2 and abs(self.y - cy) < 2

    def available_dirs(self, exclude_back=True):
        c, r = pos_to_cell(self.x, self.y)
        options = []
        for d in [DIRS["UP"], DIRS["DOWN"], DIRS["LEFT"], DIRS["RIGHT"]]:
            nc, nr = c + d[0], r + d[1]
            if self.level.passable(nc, nr):
                if exclude_back and d == OPPOSITE.get(self.dir, DIRS["STOP"]):
                    continue
                options.append(d)
        return options

    def choose_dir(self, target_pos):
        options = self.available_dirs(exclude_back=True)
        if not options:
            options = self.available_dirs(exclude_back=False)
        if not options:
            return self.dir

        if self.state == "frightened":
            return random.choice(options)

        best = None
        best_dist = 1e9
        cx, cy = self.x, self.y
        for d in options:
            nx = cx + d[0] * TILE
            ny = cy + d[1] * TILE
            dist = distance((nx, ny), target_pos)
            if dist < best_dist:
                best_dist = dist
                best = d
        return best if best else self.dir

    def update(self, dt, pacman, frightened_timer):
        if self.frozen:
            return

        if self.state != "eyes":
            if frightened_timer > 0:
                self.state = "frightened"
            else:
                self.state = "chase"

        if self.state == "eyes":
            tx, ty = cell_to_center(*self.spawn)
            speed = self.eyes_speed
        elif self.state == "frightened":
            tx, ty = random.randint(0, WIDTH), random.randint(0, HEIGHT)
            speed = self.frightened_speed
        else:
            tx, ty = pacman.x, pacman.y
            speed = self.base_speed

        if self.at_tile_center():
            self.dir = self.choose_dir((tx, ty))

        vx = self.dir[0] * speed * dt
        vy = self.dir[1] * speed * dt

        self.x += vx
        r = self.rect()
        for w in self.level.walls:
            if r.colliderect(w):
                if vx > 0:
                    self.x = w.left - self.size / 2
                elif vx < 0:
                    self.x = w.right + self.size / 2
                r.centerx = int(self.x)

        self.y += vy
        r = self.rect()
        for w in self.level.walls:
            if r.colliderect(w):
                if vy > 0:
                    self.y = w.top - self.size / 2
                elif vy < 0:
                    self.y = w.bottom + self.size / 2
                r.centery = int(self.y)

        if self.state == "eyes":
            sx, sy = cell_to_center(*self.spawn)
            if distance((self.x, self.y), (sx, sy)) < 4:
                self.state = "chase"
                self.dir = random.choice([DIRS["LEFT"], DIRS["RIGHT"], DIRS["UP"], DIRS["DOWN"]])

    def draw(self, surf, frightened_blink=False):
        cx, cy = int(self.x), int(self.y)
        w = self.size
        h = self.size
        body_color = self.color
        if self.frozen:
            body_color = (160, 200, 255)  # icy tint
        elif self.state == "frightened":
            body_color = CYAN if not frightened_blink else WHITE
        if self.state == "eyes":
            body_color = GREY

        rect = pygame.Rect(0, 0, w, h)
        rect.center = (cx, cy)
        top_rect = pygame.Rect(rect.left, rect.top, w, h // 2 + 4)
        pygame.draw.ellipse(surf, body_color, top_rect)
        bottom_rect = pygame.Rect(rect.left, rect.top + h // 3, w, h // 2)
        pygame.draw.rect(surf, body_color, bottom_rect)

        feet = 4
        foot_w = w // feet
        for i in range(feet):
            center = (rect.left + foot_w * i + foot_w // 2, rect.bottom)
            pygame.draw.circle(surf, body_color, center, foot_w // 2)

        eye_offset = 4
        eye_w = w // 5
        ex1 = cx - eye_offset
        ex2 = cx + eye_offset
        ey = cy - 2
        pygame.draw.circle(surf, WHITE, (ex1, ey), eye_w // 2)
        pygame.draw.circle(surf, WHITE, (ex2, ey), eye_w // 2)
        pygame.draw.circle(surf, BLACK, (ex1, ey), eye_w // 4)
        pygame.draw.circle(surf, BLACK, (ex2, ey), eye_w // 4)

# -----------------------------
# Game
# -----------------------------
class Game:
    def __init__(self):
        pygame.init()

        # Fonts (high-quality AA via freetype)
        self.font_path = self._choose_font_path()
        self.font_title = freetype.Font(self.font_path, 22)
        self.font_body  = freetype.Font(self.font_path, 18)
        self.font_small = freetype.Font(self.font_path, 16)
        for f in (self.font_title, self.font_body, self.font_small):
            f.pad = True  # improves glyph spacing on some platforms

        # Screen with side HUD panels
        self.screen_w = WIDTH + SIDE_HUD_W * 2
        self.screen_h = HEIGHT
        pygame.display.set_caption("Pac-Man (Pygame)")
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))
        self.clock = pygame.time.Clock()

        # Separate playfield surface (centered)
        self.field = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()

        self.level = Level(LEVEL_MAP)
        self.base_map = LEVEL_MAP  # for resetting pellets between levels
        self.reset(run_full=True)

    # ---------- Font helpers ----------
    def _choose_font_path(self):
        # Try some clean, modern fonts; fall back to default
        candidates = [
            "Segoe UI", "Poppins", "Montserrat", "Rubik",
            "Open Sans", "Arial Rounded MT Bold", "Verdana", "Arial"
        ]
        path = pygame.font.match_font(candidates, bold=False, italic=False)
        return path or None

    def _render_text(self, font, text, color, outline=0, outline_color=BLACK):
        # Render text to a temporary surface with optional 1px outline
        if not text:
            return None
        # freetype can render directly to target, but we want outline -> render onto a temp
        surf = pygame.Surface((self.screen_w, 50), pygame.SRCALPHA)  # big enough line surf
        x, y = 0, 0
        if outline > 0:
            for dx, dy in ((-outline,0),(outline,0),(0,-outline),(0,outline)):
                font.render_to(surf, (x+dx, y+dy), text, outline_color)
        font.render_to(surf, (x, y), text, color)
        # Crop tight to text
        rect = surf.get_bounding_rect()
        if rect.width == 0 or rect.height == 0:
            rect = pygame.Rect(0,0,1,1)
        cropped = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        cropped.blit(surf, (0,0), rect)
        return cropped

    def _blit_text(self, target, font, text, x, y, color, align="left", outline=0, outline_color=BLACK):
        img = self._render_text(font, text, color, outline, outline_color)
        if img is None:
            return
        if align == "center":
            x -= img.get_width() // 2
        elif align == "right":
            x -= img.get_width()
        target.blit(img, (x, y))

    # Helpers for Evolution
    def tier(self):
        # 0: 0-29, 1: 30-59, 2: 60-89, 3: 90+
        if self.pellets_eaten >= 90: return 3
        if self.pellets_eaten >= 60: return 2
        if self.pellets_eaten >= 30: return 1
        return 0

    def tier_name(self):
        return ["Standard", "Wall Clip", "Ghost Stun", "Dimension Shift"][self.tier()]

    def reset(self, run_full=False):
        # Full reset (new game) or partial reset (after death)
        if run_full:
            self.score = 0
            self.lives = 3
            self.level.reset_collectibles(self.base_map)
            self.level_over = False
            self.game_over = False
            self.level_num = 1
            self.pellets_eaten = 0

        # Total pellets for progress bar
        self.total_pellets = len(self.level.pellets) + len(self.level.power)

        # Spawns
        self.pacman = Pacman(self.level)

        # Ghosts start in the corners (ignore 'G' from the map)
        corner_cells = self.level.corner_spawns()
        ghost_colors = [RED, PINK, CYAN, ORANGE]
        self.ghosts = []
        for i in range(NUM_GHOSTS):
            cell = corner_cells[i % len(corner_cells)]
            self.ghosts.append(Ghost(self.level, cell, ghost_colors[i % len(ghost_colors)], name=f"g{i+1}"))

        # State timers
        self.frightened_timer = 0.0
        self.consecutive_ghost_bonus = 0
        self.spawn_safe_timer = SPAWN_FREEZE if run_full else max(1.2, SPAWN_FREEZE - 0.3)

        # Evolution ability timers
        self.clip_timer = 0.0
        self.stun_timer = 0.0
        self.shift_timer = 0.0

        for g in self.ghosts:
            g.dir = DIRS["STOP"]
            g.frozen = False

        self.pacman.dir = self.pacman.desired_dir = DIRS["STOP"]

        if self.tier() >= 2 and len(self.level.special) == 0:
            self.level.spawn_special()

    def try_activate_ability(self):
        t = self.tier()
        if t >= 3:
            if self.shift_timer <= 0:
                self.shift_timer = SHIFT_DURATION
        elif t >= 1:
            if self.clip_timer <= 0:
                self.clip_timer = CLIP_DURATION

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit(); sys.exit(0)
                if event.key == pygame.K_r and self.game_over:
                    self.reset(run_full=True)
                if event.key in (pygame.K_SPACE, pygame.K_e):
                    self.try_activate_ability()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.pacman.desired_dir = DIRS["UP"]
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.pacman.desired_dir = DIRS["DOWN"]
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.pacman.desired_dir = DIRS["LEFT"]
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.pacman.desired_dir = DIRS["RIGHT"]

    def update(self, dt):
        if self.game_over:
            return

        # Ability timers tick
        if self.clip_timer > 0:   self.clip_timer = max(0.0, self.clip_timer - dt)
        if self.shift_timer > 0:  self.shift_timer = max(0.0, self.shift_timer - dt)
        if self.stun_timer > 0:
            self.stun_timer = max(0.0, self.stun_timer - dt)
            if self.stun_timer == 0:
                for g in self.ghosts:
                    g.frozen = False

        # Update Pac-Man with phasing if clip/shift active
        phasing = (self.clip_timer > 0) or (self.shift_timer > 0)
        self.pacman.update(dt, self.level, phasing=phasing)

        # Eat pellets / power pellets / special pellets
        pc, pr = pos_to_cell(self.pacman.x, self.pacman.y)
        ate_any_pellet = False
        if (pc, pr) in self.level.pellets:
            self.level.pellets.remove((pc, pr))
            self.score += 10
            self.pellets_eaten += 1
            ate_any_pellet = True
        if (pc, pr) in self.level.power:
            self.level.power.remove((pc, pr))
            self.score += 50
            self.pellets_eaten += 1
            ate_any_pellet = True
            self.frightened_timer = 7.0
            self.consecutive_ghost_bonus = 0
            for g in self.ghosts:
                g.dir = OPPOSITE.get(g.dir, g.dir)
        if (pc, pr) in self.level.special:
            self.level.special.remove((pc, pr))
            # Trigger ghost stun (freeze)
            self.stun_timer = STUN_DURATION
            for g in self.ghosts:
                g.frozen = True

        if ate_any_pellet:
            if self.tier() >= 2 and len(self.level.special) == 0:
                self.level.spawn_special()

        if self.frightened_timer > 0:
            self.frightened_timer -= dt

        if self.spawn_safe_timer > 0:
            self.spawn_safe_timer -= dt
            return

        if self.stun_timer <= 0:
            for g in self.ghosts:
                g.update(dt, self.pacman, self.frightened_timer)

        # Collisions (Dimension Shift grants invulnerability)
        if self.shift_timer <= 0:
            p_rect = self.pacman.rect()
            for g in self.ghosts:
                if p_rect.colliderect(g.rect()):
                    if g.state == "frightened":
                        bonus = 200 * (2 ** self.consecutive_ghost_bonus)
                        self.consecutive_ghost_bonus = min(self.consecutive_ghost_bonus + 1, 3)
                        self.score += bonus
                        g.state = "eyes"
                    elif g.state != "eyes":
                        self.lives -= 1
                        if self.lives < 0:
                            self.game_over = True
                        self.reset(run_full=False)
                        return

        # Level complete?
        if not self.level.pellets and not self.level.power and not self.level.special:
            self.level.reset_collectibles(self.base_map)
            self.level_num += 1
            self.pellets_eaten = 0
            self.clip_timer = self.stun_timer = self.shift_timer = 0.0
            self.pacman.speed = min(self.pacman.speed + 8, 180)
            for g in self.ghosts:
                g.base_speed = min(g.base_speed + 8, 180)
                g.frightened_speed = min(g.frightened_speed + 6, 160)
            self.total_pellets = len(self.level.pellets) + len(self.level.power)

    # ---------- Drawing ----------
    def draw_grid(self, surf):
        # Chunky tile walls
        for w in self.level.walls:
            pygame.draw.rect(surf, BLUE, w)

        # Pellets
        for (c, r) in self.level.pellets:
            cx, cy = cell_to_center(c, r)
            pygame.draw.circle(surf, WHITE, (cx, cy), 3)

        # Power pellets
        for (c, r) in self.level.power:
            cx, cy = cell_to_center(c, r)
            pygame.draw.circle(surf, WHITE, (cx, cy), 6, width=2)

        # Special pellets
        for (c, r) in self.level.special:
            cx, cy = cell_to_center(c, r)
            pygame.draw.circle(surf, VIOLET, (cx, cy), 6)
            pygame.draw.circle(surf, WHITE, (cx, cy), 2)

    def _draw_progress_bar(self, surf, x, y, w, h, pct, fill_color=BAR_FILL):
        pygame.draw.rect(surf, BAR_BG, (x, y, w, h), border_radius=6)
        if pct > 0:
            fw = max(0, int((w - 2) * max(0.0, min(1.0, pct))))
            pygame.draw.rect(surf, fill_color, (x+1, y+1, fw, h-2), border_radius=6)

    def _draw_side_panel(self, x, title):
        # Panel background
        pygame.draw.rect(self.screen, PANEL_BG, (x, 0, SIDE_HUD_W, self.screen_h))
        # Header line
        pygame.draw.line(self.screen, PANEL_ACCENT, (x, 32), (x + SIDE_HUD_W, 32), 2)
        # Title (outlined)
        self._blit_text(self.screen, self.font_title, title, x + HUD_PADDING, 6, GOLD, outline=1)

    def draw_left_hud(self):
        x = 0
        self._draw_side_panel(x, "Status")
        y = 40

        # Score / Lives / Level
        self._blit_text(self.screen, self.font_body, f"Score", x + HUD_PADDING, y, WHITE); y += 20
        self._blit_text(self.screen, self.font_title, f"{self.score}", x + HUD_PADDING, y, GOLD); y += 30

        self._blit_text(self.screen, self.font_body, f"Lives: {max(self.lives,0)}", x + HUD_PADDING, y, WHITE); y += 22
        self._blit_text(self.screen, self.font_body, f"Level: {self.level_num}", x + HUD_PADDING, y, WHITE); y += 24

        # Pellet progress
        y += 6
        self._blit_text(self.screen, self.font_body, "Pellets Progress", x + HUD_PADDING, y, WHITE); y += 20
        total = max(1, self.total_pellets)
        pct = min(1.0, self.pellets_eaten / float(total))
        self._draw_progress_bar(self.screen, x + HUD_PADDING, y, SIDE_HUD_W - HUD_PADDING*2, 14, pct, BAR_FILL_GOLD); y += 24
        self._blit_text(self.screen, self.font_small, f"{self.pellets_eaten}/{total}", x + SIDE_HUD_W - HUD_PADDING, y-22, WHITE, align="right")

        # Abilities / timers
        y += 8
        self._blit_text(self.screen, self.font_body, "Abilities", x + HUD_PADDING, y, WHITE); y += 20
        line = f"Tier: {self.tier_name()}"
        self._blit_text(self.screen, self.font_body, line, x + HUD_PADDING, y, GOLD); y += 20

        if self.clip_timer > 0:
            self._blit_text(self.screen, self.font_small, f"Wall Clip: {self.clip_timer:0.1f}s", x + HUD_PADDING, y, CYAN); y += 18
        if self.stun_timer > 0:
            self._blit_text(self.screen, self.font_small, f"Ghost Stun: {self.stun_timer:0.1f}s", x + HUD_PADDING, y, (160,200,255)); y += 18
        if self.shift_timer > 0:
            self._blit_text(self.screen, self.font_small, f"Dimension Shift: {self.shift_timer:0.1f}s", x + HUD_PADDING, y, GOLD); y += 18

        # Controls
        y += 8
        self._blit_text(self.screen, self.font_body, "Controls", x + HUD_PADDING, y, WHITE); y += 20
        for t in ["Arrows/WASD: Move", "Space/E: Use Ability", "R: Restart (Game Over)", "Esc/Q: Quit"]:
            self._blit_text(self.screen, self.font_small, t, x + HUD_PADDING, y, WHITE); y += 18

    def draw_right_hud(self):
        x = SIDE_HUD_W + WIDTH
        self._draw_side_panel(x, "Evolution")
        y = 40

        # Tiers list
        tiers = [
            ("0–29", "Standard movement"),
            ("30–59", "Wall Clip (2s, Space/E)"),
            ("60–89", "Special Pellets: Ghost Stun (5s)"),
            ("90+", "Dimension Shift (4s, Space/E)"),
        ]
        for idx, (range_txt, desc) in enumerate(tiers):
            unlocked = self.tier() >= idx
            color = GOLD if unlocked else WHITE
            bullet = "✓ " if unlocked else "• "
            self._blit_text(self.screen, self.font_body, bullet + f"Tier {idx}: {range_txt}", x + HUD_PADDING, y, color); y += 18
            self._blit_text(self.screen, self.font_small, desc, x + HUD_PADDING + 16, y, WHITE); y += 18

        y += 6
        self._blit_text(self.screen, self.font_body, "Hints", x + HUD_PADDING, y, WHITE); y += 20
        hints = [
            "Turn early near intersections",
            "Power pellet -> Frighten ghosts",
            "Special pellet -> Stun ghosts",
            "Shift = invulnerable + phase",
        ]
        for h in hints:
            self._blit_text(self.screen, self.font_small, "– " + h, x + HUD_PADDING, y, WHITE); y += 18

    def render(self):
        # Main background
        self.screen.fill(DARK)

        # Left and Right HUDs
        self.draw_left_hud()
        self.draw_right_hud()

        # Draw playfield to its own surface
        self.field.fill(BLACK)
        self.draw_grid(self.field)
        frightened_blink = self.frightened_timer > 0 and self.frightened_timer < 2.0 and (int(self.frightened_timer * 6) % 2 == 0)
        for g in self.ghosts:
            g.draw(self.field, frightened_blink=frightened_blink)
        self.pacman.draw(self.field, shift_active=self.shift_timer > 0, clip_active=(self.clip_timer > 0 and self.shift_timer <= 0))

        # Blit playfield centered between side HUDs
        field_x = SIDE_HUD_W
        self.screen.blit(self.field, (field_x, 0))

        # Overlays
        if self.game_over:
            self._blit_text(self.screen, self.font_title, "Game Over - Press R to Restart",
                            field_x + WIDTH // 2, HEIGHT // 2 - 10, WHITE, align="center", outline=1)
        elif self.spawn_safe_timer > 0:
            self._blit_text(self.screen, self.font_title, "READY!",
                            field_x + WIDTH // 2, HEIGHT // 2 - 10, YELLOW, align="center", outline=1)

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_input()
            self.update(dt)
            self.render()

if __name__ == "__main__":
    Game().run()