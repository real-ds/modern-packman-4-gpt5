import pygame
import sys
import random
import math

# -----------------------------
# Config & Level
# -----------------------------
TILE = 24
FPS = 60
NUM_GHOSTS = 4          # number of ghosts to spawn (use 3 or 4)
SPAWN_FREEZE = 1.5      # seconds ghosts are frozen after each spawn/reset

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
WIDTH = COLS * TILE
HEIGHT = ROWS * TILE

# Colors
BLACK  = (0, 0, 0)
BLUE   = (0, 80, 200)
YELLOW = (255, 210, 0)
WHITE  = (255, 255, 255)
PINK   = (255, 105, 180)
RED    = (255, 60, 60)
CYAN   = (0, 255, 255)
ORANGE = (255, 165, 0)
GREY   = (100, 100, 100)

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
            # fallback to a default open tile
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
        for r, row in enumerate(base_map):
            for c, ch in enumerate(row):
                if ch == '.':
                    self.pellets.add((c, r))
                elif ch == 'o':
                    self.power.add((c, r))

    # ------ NEW: corner spawn helpers ------
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
            # avoid placing a ghost on Pac-Man's tile
            if s == self.pacman_spawn:
                s = self.nearest_open(s[0] + 1, s[1])
            spawns.append(s)
        return spawns

# -----------------------------
# Entities
# -----------------------------
class Pacman:
    def __init__(self, level):
        self.level = level
        sx, sy = cell_to_center(*level.pacman_spawn)
        self.x = float(sx)
        self.y = float(sy)
        self.size = int(TILE * 0.8)
        self.speed = 120.0  # px/s
        self.dir = DIRS["LEFT"]
        self.desired_dir = DIRS["LEFT"]
        self.alive = True
        self.mouth_timer = 0.0
        self.mouth_open = True

    def rect(self):
        return rect_from_center(self.x, self.y, self.size)

    def can_move_dir(self, direction, level, step=4):
        # Test small step in desired direction
        test_rect = self.rect().copy()
        test_rect.centerx += direction[0] * step
        test_rect.centery += direction[1] * step
        for w in level.walls:
            if test_rect.colliderect(w):
                return False
        return True

    def update(self, dt, level):
        # Try to change direction if requested and possible (near intersections)
        if self.desired_dir != self.dir:
            if self.can_move_dir(self.desired_dir, level, step=8):
                self.dir = self.desired_dir

        # Move with collision resolution by axis
        vx = self.dir[0] * self.speed * dt
        vy = self.dir[1] * self.speed * dt

        # Horizontal
        self.x += vx
        r = self.rect()
        for w in level.walls:
            if r.colliderect(w):
                if vx > 0:
                    self.x = w.left - self.size / 2
                elif vx < 0:
                    self.x = w.right + self.size / 2
                r.centerx = int(self.x)

        # Vertical
        self.y += vy
        r = self.rect()
        for w in level.walls:
            if r.colliderect(w):
                if vy > 0:
                    self.y = w.top - self.size / 2
                elif vy < 0:
                    self.y = w.bottom + self.size / 2
                r.centery = int(self.y)

        # Mouth animation
        self.mouth_timer += dt
        if self.mouth_timer > 0.08:
            self.mouth_open = not self.mouth_open
            self.mouth_timer = 0.0

    def draw(self, surf):
        # Draw Pac-Man with simple mouth animation
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
        # Choose direction at intersections based on state
        options = self.available_dirs(exclude_back=True)
        if not options:
            options = self.available_dirs(exclude_back=False)
        if not options:
            return self.dir

        if self.state == "frightened":
            # Random choice when frightened
            return random.choice(options)

        # Chase (or eyes returning): greedy to minimize distance to target
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
        # Update state
        if self.state != "eyes":
            if frightened_timer > 0:
                self.state = "frightened"
            else:
                self.state = "chase"

        # Decide target
        if self.state == "eyes":
            tx, ty = cell_to_center(*self.spawn)
            speed = self.eyes_speed
        elif self.state == "frightened":
            tx, ty = random.randint(0, WIDTH), random.randint(0, HEIGHT)
            speed = self.frightened_speed
        else:
            tx, ty = pacman.x, pacman.y
            speed = self.base_speed

        # Choose direction at tile centers to avoid jitter
        if self.at_tile_center():
            self.dir = self.choose_dir((tx, ty))

        vx = self.dir[0] * speed * dt
        vy = self.dir[1] * speed * dt

        # Move with collision handling
        # Horizontal
        self.x += vx
        r = self.rect()
        for w in self.level.walls:
            if r.colliderect(w):
                if vx > 0:
                    self.x = w.left - self.size / 2
                elif vx < 0:
                    self.x = w.right + self.size / 2
                r.centerx = int(self.x)

        # Vertical
        self.y += vy
        r = self.rect()
        for w in self.level.walls:
            if r.colliderect(w):
                if vy > 0:
                    self.y = w.top - self.size / 2
                elif vy < 0:
                    self.y = w.bottom + self.size / 2
                r.centery = int(self.y)

        # If in eyes state and reached spawn center, revert to chase
        if self.state == "eyes":
            sx, sy = cell_to_center(*self.spawn)
            if distance((self.x, self.y), (sx, sy)) < 4:
                self.state = "chase"
                # randomize next dir to avoid oscillation
                self.dir = random.choice([DIRS["LEFT"], DIRS["RIGHT"], DIRS["UP"], DIRS["DOWN"]])

    def draw(self, surf, frightened_blink=False):
        cx, cy = int(self.x), int(self.y)
        w = self.size
        h = self.size
        body_color = self.color
        if self.state == "frightened":
            body_color = CYAN if not frightened_blink else WHITE
        if self.state == "eyes":
            body_color = GREY

        # Ghost body (rounded top + flat bottom)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (cx, cy)
        top_rect = pygame.Rect(rect.left, rect.top, w, h // 2 + 4)
        pygame.draw.ellipse(surf, body_color, top_rect)
        bottom_rect = pygame.Rect(rect.left, rect.top + h // 3, w, h // 2)
        pygame.draw.rect(surf, body_color, bottom_rect)

        # Feet bumps
        feet = 4
        foot_w = w // feet
        for i in range(feet):
            center = (rect.left + foot_w * i + foot_w // 2, rect.bottom)
            pygame.draw.circle(surf, body_color, center, foot_w // 2)

        # Eyes
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
        pygame.display.set_caption("Pac-Man (Pygame)")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20)
        self.level = Level(LEVEL_MAP)
        self.base_map = LEVEL_MAP  # for resetting pellets between levels
        self.reset(run_full=True)

    def reset(self, run_full=False):
        # Full reset (new game) or partial reset (after death)
        if run_full:
            self.score = 0
            self.lives = 3
            self.level.reset_collectibles(self.base_map)
            self.level_over = False
            self.game_over = False
            self.level_num = 1

        # Spawns
        self.pacman = Pacman(self.level)

        # Ghosts start in the corners (ignore 'G' from the map)
        corner_cells = self.level.corner_spawns()
        ghost_colors = [RED, PINK, CYAN, ORANGE]
        self.ghosts = []
        for i in range(NUM_GHOSTS):
            cell = corner_cells[i % len(corner_cells)]
            self.ghosts.append(Ghost(self.level, cell, ghost_colors[i % len(ghost_colors)], name=f"g{i+1}"))

        # Frightened state + bonus chain
        self.frightened_timer = 0.0
        self.consecutive_ghost_bonus = 0

        # Short freeze so ghosts don't insta-catch Pac-Man
        self.spawn_safe_timer = SPAWN_FREEZE if run_full else max(1.2, SPAWN_FREEZE - 0.3)
        self.pacman.dir = self.pacman.desired_dir = DIRS["STOP"]
        for g in self.ghosts:
            g.dir = DIRS["STOP"]

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit(); sys.exit(0)
                if event.key == pygame.K_r and self.game_over:
                    self.reset(run_full=True)
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.pacman.desired_dir = DIRS["UP"]
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.pacman.desired_dir = DIRS["DOWN"]
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.pacman.desired_dir = DIRS["LEFT"]
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.pacman.desired_dir = DIRS["RIGHT"]

    def update(self, dt):
        if self.game_over:
            return

        # Update Pac-Man
        self.pacman.update(dt, self.level)

        # Eat pellets / power pellets
        pc, pr = pos_to_cell(self.pacman.x, self.pacman.y)
        if (pc, pr) in self.level.pellets:
            self.level.pellets.remove((pc, pr))
            self.score += 10
        if (pc, pr) in self.level.power:
            self.level.power.remove((pc, pr))
            self.score += 50
            self.frightened_timer = 7.0
            self.consecutive_ghost_bonus = 0
            for g in self.ghosts:
                g.dir = OPPOSITE.get(g.dir, g.dir)

        # Tick frightened timer
        if self.frightened_timer > 0:
            self.frightened_timer -= dt

        # Spawn safety window: ghosts are frozen and can't collide with Pac-Man
        if self.spawn_safe_timer > 0:
            self.spawn_safe_timer -= dt
            return

        # Update ghosts
        for g in self.ghosts:
            g.update(dt, self.pacman, self.frightened_timer)

        # Collisions Pac-Man <-> Ghosts
        p_rect = self.pacman.rect()
        for g in self.ghosts:
            if p_rect.colliderect(g.rect()):
                if g.state == "frightened":
                    bonus = 200 * (2 ** self.consecutive_ghost_bonus)
                    self.consecutive_ghost_bonus = min(self.consecutive_ghost_bonus + 1, 3)
                    self.score += bonus
                    g.state = "eyes"
                elif g.state != "eyes":
                    # Pac-Man dies
                    self.lives -= 1
                    if self.lives < 0:
                        self.game_over = True
                    # reset positions (but keep pellets/score/lives)
                    self.reset(run_full=False)
                    return

        # Level complete?
        if not self.level.pellets and not self.level.power:
            # Next level: reset pellets, slightly faster ghosts and Pac-Man
            self.level.reset_collectibles(self.base_map)
            self.level_num += 1
            self.pacman.speed = min(self.pacman.speed + 8, 180)
            for g in self.ghosts:
                g.base_speed = min(g.base_speed + 8, 180)
                g.frightened_speed = min(g.frightened_speed + 6, 160)

    def draw_grid(self, surf):
        # Draw walls (rounded rectangles for aesthetics)
        for w in self.level.walls:
            pygame.draw.rect(surf, BLUE, w)

        # Draw pellets
        for (c, r) in self.level.pellets:
            cx, cy = cell_to_center(c, r)
            pygame.draw.circle(surf, WHITE, (cx, cy), 3)

        # Draw power pellets
        for (c, r) in self.level.power:
            cx, cy = cell_to_center(c, r)
            pygame.draw.circle(surf, WHITE, (cx, cy), 6, width=2)

    def draw_ui(self, surf):
        # Score & lives
        text = f"Score: {self.score}    Lives: {max(self.lives,0)}    Level: {self.level_num}"
        img = self.font.render(text, True, WHITE)
        surf.blit(img, (10, 4))

        if self.game_over:
            msg = self.font.render("Game Over - Press R to Restart", True, WHITE)
            surf.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - msg.get_height()//2))

    def render(self):
        self.screen.fill(BLACK)
        self.draw_grid(self.screen)
        # Draw entities
        frightened_blink = self.frightened_timer > 0 and self.frightened_timer < 2.0 and (int(self.frightened_timer * 6) % 2 == 0)
        for g in self.ghosts:
            g.draw(self.screen, frightened_blink=frightened_blink)
        self.pacman.draw(self.screen)
        self.draw_ui(self.screen)

        # "READY!" overlay during spawn safety window
        if not self.game_over and self.spawn_safe_timer > 0:
            msg = self.font.render("READY!", True, YELLOW)
            self.screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - msg.get_height()//2))

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_input()
            self.update(dt)
            self.render()

if __name__ == "__main__":
    Game().run()