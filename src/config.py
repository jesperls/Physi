import pygame

# --- Display and Performance ---
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 900
FPS = 144
CENTER = pygame.Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
CONTAINER_RADIUS = 400

# --- Physics (Values represent the state at the START of the simulation) ---
INITIAL_GRAVITY_STRENGTH = 300.0  # Starting gravity
FINAL_GRAVITY_STRENGTH = 100.0    # Gravity at 60 seconds
INITIAL_MAX_VELOCITY = 800        # Starting max velocity
FINAL_MAX_VELOCITY = 1500         # Max velocity at 60 seconds
GRAVITY_CENTER_DEADZONE = 0       # Radius around center with no gravity

# --- Ball Properties (Values represent the state at the START of the simulation) ---
INITIAL_BALLS = 3                 # Start with a few more balls
MIN_RADIUS = 8                   # Smaller minimum size
MAX_RADIUS = 35                  # Slightly smaller max size
BASE_DENSITY = 0.1
INITIAL_BALL_ELASTICITY = 1    # Start slightly bouncy
FINAL_BALL_ELASTICITY = 1.05      # Max elasticity at 60 seconds (can exceed 1.0 for energy gain)
INITIAL_DRAG_COEFFICIENT = 0.999  # Start with slight drag
FINAL_DRAG_COEFFICIENT = 0.9998   # Almost no drag at 60 seconds (0.9998 is closer to 1.0 than 0.999)

# --- Color and Visual Dynamics ---
COLOR_SPECTRUM_RANGE = 360
COLOR_HARMONY_GROUPS = [
    (0, 40), (30, 70), (60, 100), (90, 150),
    (150, 210), (210, 270), (270, 330), (330, 360)
]
COLOR_HARMONY_CHANCE = 0.1
COLOR_SATURATION_RANGE = (80, 100)
COLOR_VALUE_RANGE = (85, 100)
COLOR_SHIFT_BASE_RATE = 5.0
COLOR_SHIFT_VARIANCE = 1.5
COLOR_SHIFT_OSCILLATION = 0.6
INITIAL_GROWTH_RATE = 0.3         # Slower initial growth
FINAL_GROWTH_RATE = 0.5           # Faster growth towards the end

# --- Splitting and Merging (Values represent the state at the START of the simulation) ---
INITIAL_COLOR_DISTANCE_THRESHOLD = 20 # Harder to merge initially
FINAL_COLOR_DISTANCE_THRESHOLD = 60   # Easier to merge at 60 seconds
INITIAL_SPLIT_CHANCE = 0.02       # Low initial split chance
FINAL_SPLIT_CHANCE = 0.20         # High split chance at 60 seconds
INITIAL_COLLISION_SHRINK_FACTOR = 0.001 # Minimal shrink initially
FINAL_COLLISION_SHRINK_FACTOR = 0.03  # Significant shrink at 60 seconds
SPLIT_TINT_FACTOR = 0.1
MERGE_AREA_FACTOR = 1.0
INITIAL_SPLIT_MASS_LOSS_FACTOR = 1.05 # Less mass loss initially
FINAL_SPLIT_MASS_LOSS_FACTOR = 1.30 # More mass loss at 60 seconds
MIN_SPLIT_RADIUS = 10             # Min radius required to split

# --- Visual Effects ---
BACKGROUND_COLOR = pygame.Color(5, 0, 10)
GLOW_BLOOM_SIZE_FACTOR = 1.2
GLOW_BLOOM_INTENSITY = 80
GLOW_HAZE_SIZE_FACTOR = 2.2
GLOW_HAZE_ALPHA = 35
PULSE_FREQUENCY = 1.5
PULSE_FREQUENCY_VARIANCE = 0.5
PULSE_AMPLITUDE_BLOOM = 0.4
PULSE_AMPLITUDE_HAZE = 0.3
TRAIL_LENGTH = 8
TRAIL_ALPHA_START = 60
FLASH_DURATION = 0.2
FLASH_RADIUS_FACTOR = 2.0
PARTICLE_COUNT_COLLISION = 15
PARTICLE_COUNT_SPLIT_MERGE = 30
PARTICLE_COUNT_POP = 20
PARTICLE_LIFESPAN = 0.6
PARTICLE_SPEED_MIN = 50
PARTICLE_SPEED_MAX = 200
PARTICLE_RADIUS = 2.5
POP_FLASH_DURATION = 0.3
POP_SOUND_VOLUME = 0.8
SHAKE_DURATION = 0.15
INITIAL_SHAKE_INTENSITY = 3       # Lower initial shake
FINAL_SHAKE_INTENSITY = 10        # Higher shake intensity at 60 seconds

# --- Game Flow ---
INTRO_DURATION = 3.0
INTRO_FADE_OVERLAP = 0.5
MAX_GAME_DURATION = 60.0          # Target duration for chaos ramp-up
MAX_BALL_COUNT = 25               # Allow slightly more balls for chaos
INITIAL_SPAWN_RATE = 0.001        # Chance per frame to spawn a ball at start
FINAL_SPAWN_RATE = 0.005          # Chance per frame to spawn a ball at 60 seconds

# --- Sound ---
SOUND_ENABLED = True
SOUND_VOLUME_MASTER = 0.6
SOUND_VOLUME_AMBIENT = 0.2
SOUND_FILES = {
    'collision': 'collision.ogg',
    'ambient': 'ambient.ogg',
    'start': 'start.ogg',
    'end': 'end.ogg'
}