# Modern Pac-Man: Evolution Edition

<div align="center">

**A modern twist on the classic Pac-Man with an innovative Evolution System**

*Created for PLAY THE PROMPT Hackathon*
*Game Development Club, VIT Chennai*

[Setup](#setup) • [Features](#features) • [How to Play](#how-to-play) • [Controls](#controls) • [Demo](#demo)

</div>

---

## About

This is an enhanced Pac-Man game featuring a unique **Evolution System** that progressively unlocks powerful abilities as you collect pellets. Built with Python and Pygame, the game combines classic arcade gameplay with modern mechanics like wall clipping, ghost stunning, and dimensional shifting.

## Features

### Evolution System
The game features a progressive tier system that unlocks new abilities based on pellets collected:

| Tier | Pellets Required | Ability | Description |
|------|------------------|---------|-------------|
| **Tier 0** | 0-29 | Standard Movement | Classic Pac-Man gameplay |
| **Tier 1** | 30-59 | Wall Clip | Pass through maze walls for 2 seconds (Space/E) |
| **Tier 2** | 60-89 | Ghost Stun | Special violet pellets spawn that freeze all ghosts for 5 seconds |
| **Tier 3** | 90+ | Dimension Shift | Invulnerability + phasing through walls for 4 seconds (Space/E) |

### Game Features

- **Smooth Movement System**
  - Early turning at intersections for responsive controls
  - Corner assist when bumping into walls
  - Optimized hitbox for better corridor navigation

- **Enhanced Visuals**
  - Dual side HUD panels displaying game stats and evolution progress
  - Real-time ability timers
  - Visual indicators for active abilities (glowing auras)
  - Clean, modern UI with high-quality fonts

- **Dynamic Gameplay**
  - 4 intelligent ghosts with chase, frightened, and eyes states
  - Progressive difficulty: speeds increase with each level
  - Ghost spawning at maze corners with safe spawn timer
  - Consecutive ghost-eating bonus multiplier

- **Polish & UX**
  - Smooth animations (Pac-Man mouth opening/closing)
  - Frightened ghost blinking when timer runs low
  - Frozen ghost visual effects during stun
  - Progress bars for pellet collection

## Demo

A gameplay video (`Gameplay.mp4`) is included in the repository showcasing the evolution system and game mechanics.

## Setup

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd modern-packman-4-gpt5
   ```

2. **Install dependencies**
   ```bash
   pip install pygame
   ```

3. **Run the game**
   ```bash
   python pacman.py
   ```

### Alternative: Virtual Environment (Recommended)

For a cleaner setup, use a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install pygame

# Run the game
python pacman.py
```

## How to Play

### Objective
Navigate the maze, collect all pellets while avoiding ghosts, and survive as long as possible!

### Gameplay Tips

1. **Start Simple**: Begin with standard movement until you collect 30 pellets
2. **Unlock Abilities**: Collect pellets to unlock higher tiers and gain new powers
3. **Use Power Pellets**: Large pellets make ghosts frightened (blue) - eat them for bonus points!
4. **Special Pellets**: At Tier 2+, violet pellets appear that freeze all ghosts
5. **Master Abilities**:
   - Use Wall Clip (Tier 1) to escape tight situations
   - Save Dimension Shift (Tier 3) for emergencies - it makes you invulnerable
6. **Early Turning**: You can turn before reaching exact intersections for smoother navigation
7. **Level Progression**: Speed increases with each level - plan your moves carefully!

### Scoring

- Normal Pellet: **10 points**
- Power Pellet: **50 points**
- Frightened Ghost: **200, 400, 800, or 1600 points** (consecutive bonus)

## Controls

| Key | Action |
|-----|--------|
| **Arrow Keys** or **WASD** | Move Pac-Man |
| **Space** or **E** | Activate ability (Tier 1 or Tier 3) |
| **R** | Restart game (when game over) |
| **Esc** or **Q** | Quit game |

## Technical Details

### Configuration

Key game parameters can be adjusted in the config section of `pacman.py`:

```python
TILE = 24                  # Tile size (pixels)
FPS = 60                   # Frames per second
NUM_GHOSTS = 4             # Number of ghosts (3-4 recommended)
SPAWN_FREEZE = 1.5         # Safe spawn time (seconds)
CLIP_DURATION = 2.0        # Wall Clip duration
STUN_DURATION = 5.0        # Ghost Stun duration
SHIFT_DURATION = 4.0       # Dimension Shift duration
SPECIAL_SPAWN_COUNT = 3    # Number of special pellets
```

### Architecture

- **Level Class**: Manages maze layout, pellets, walls, and spawns
- **Pacman Class**: Player entity with movement, collision, and abilities
- **Ghost Class**: AI-controlled enemies with chase/frightened/eyes states
- **Game Class**: Main game loop, rendering, HUD, and state management

### Dependencies

- `pygame` - Game engine and rendering
- `pygame.freetype` - High-quality font rendering

## Development

### Project Structure

```
modern-packman-4-gpt5/
├── pacman.py          # Main game file
├── Gameplay.mp4       # Gameplay demonstration
└── README.md          # This file
```

### Git History

- **Final Submission**: Created HUD with instructions and evolution tracking
- **Border Blocks**: Added maze borders, refined edges, smoothened controls
- **Initial Version**: Repository initialization with safe version (V1)

## Hackathon Submission

**Event**: PLAY THE PROMPT
**Organizer**: Game Development Club, VIT Chennai
**Theme**: Modern twist on classic games with innovative mechanics

## Future Enhancements

Potential improvements for future versions:
- Multiple maze layouts
- Sound effects and background music
- High score persistence
- Additional ghost AI patterns
- More tier abilities
- Particle effects
- Mobile controls support

## License

This project was created for educational and hackathon purposes.

## Acknowledgments

- Classic Pac-Man by Namco for inspiration
- Game Development Club, VIT Chennai for organizing PLAY THE PROMPT
- Pygame community for excellent documentation and resources

---

<div align="center">

**Created with ❤️ for PLAY THE PROMPT Hackathon**

*VIT Chennai - Game Development Club*

</div>
