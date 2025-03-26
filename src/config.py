import pygame

# --- Display and Performance ---
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 900
FPS = 144
CENTER = pygame.Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
CONTAINER_RADIUS = 400

# --- Physics ---
GRAVITY_STRENGTH = 100.0  # Reduced gravity for less center gathering
MAX_VELOCITY = 1000      # Higher max velocity for more exciting motion
GRAVITY_CENTER_DEADZONE = 0  # New: Radius around center with reduced gravity

# --- Ball Properties ---
INITIAL_BALLS = 3         # Reduced to 3 balls as requested
MIN_RADIUS = 10
MAX_RADIUS = 40           # Smaller max size for better visibility
BASE_DENSITY = 0.1
MIN_BALL_ELASTICITY = 1  # New: Minimum elasticity for more bounce
MAX_BALL_ELASTICITY = 1.2   # New: Maximum elasticity when ramped up
DRAG_COEFFICIENT = 0.999   # New: Reduced drag for more dynamic movement

# --- Color and Visual Dynamics ---
# Enhanced color control for more varied and harmonious colors
COLOR_SPECTRUM_RANGE = 360  # Full color spectrum
COLOR_HARMONY_GROUPS = [
    (0, 40),        # Red group
    (30, 70),       # Orange/Yellow group
    (60, 100),      # Yellow/Chartreuse
    (90, 150),      # Green group
    (150, 210),     # Cyan/Blue group
    (210, 270),     # Blue/Purple group
    (270, 330),     # Purple/Magenta
    (330, 360)      # Magenta/Red
]
COLOR_HARMONY_CHANCE = 0  # Reduced chance to allow more random vibrant colors
COLOR_SATURATION_RANGE = (80, 100)  # Allow for more saturation variety
COLOR_VALUE_RANGE = (85, 100)       # Allow for more brightness variety

# Dynamic behavior 
COLOR_SHIFT_BASE_RATE = 5.0        # Reduced color shift rate for less chaotic appearance
COLOR_SHIFT_VARIANCE = 1.5         # Reduced random variance in shift rate per ball
COLOR_SHIFT_OSCILLATION = 0.6      # Oscillation factor (0 = constant, 1 = fully varying)
GROWTH_RATE = 0.3                  # Ball growth rate (reduced from 1.2 for more stability)

# --- Splitting and Merging ---
COLOR_DISTANCE_THRESHOLD = 70     # Higher threshold - easier to merge
SPLIT_TINT_FACTOR = 0
MERGE_AREA_FACTOR = 1.0
SPLIT_MASS_LOSS_FACTOR = 1.2     # Reduced mass loss during splitting for more stability
MIN_SPLIT_RADIUS = 12            # Increased min split radius to prevent excessive splitting

# --- Visual Effects ---
BACKGROUND_COLOR = pygame.Color(5, 0, 10)  # Very dark purple/blue

# Glow Layers: Core -> Bright Bloom (Add) -> Soft Haze (Alpha)
GLOW_BLOOM_SIZE_FACTOR = 1.2      # Size factor for bloom effect
GLOW_BLOOM_INTENSITY = 80         # Bloom intensity
GLOW_HAZE_SIZE_FACTOR = 2.2       # Size factor for haze effect
GLOW_HAZE_ALPHA = 35              # Base alpha for haze effect

# Pulse Effect
PULSE_FREQUENCY = 1.5
PULSE_FREQUENCY_VARIANCE = 0.5    # Added variance in pulse frequency
PULSE_AMPLITUDE_BLOOM = 0.4       # Bloom pulse effect
PULSE_AMPLITUDE_HAZE = 0.3        # Haze pulse effect

# Trails
TRAIL_LENGTH = 8
TRAIL_ALPHA_START = 60

# Flash Effects
FLASH_DURATION = 0.2
FLASH_RADIUS_FACTOR = 2.0

# Particles
PARTICLE_COUNT_COLLISION = 15
PARTICLE_COUNT_SPLIT_MERGE = 30
PARTICLE_COUNT_POP = 20       # New: Particle count for pop animation
PARTICLE_LIFESPAN = 0.6       # Seconds
PARTICLE_SPEED_MIN = 50
PARTICLE_SPEED_MAX = 200
PARTICLE_RADIUS = 2.5
POP_FLASH_DURATION = 0.3      # New: Duration for pop flash effect
POP_SOUND_VOLUME = 0.8        # New: Volume for pop sound

# Screen Shake
SHAKE_DURATION = 0.15
SHAKE_INTENSITY = 5               # Pixels

# --- Game Flow ---
INTRO_DURATION = 3.0              # Intro animation duration (seconds)
INTRO_FADE_OVERLAP = 0.5          # Overlap for smoother transition from intro to game
MAX_GAME_DURATION = 60.0          # 60 seconds for YouTube shorts
FINALE_START_TIME = 55.0          # Start finale at 55 seconds
FINALE_BALLS_COUNT = 0           # Number of balls to spawn during finale
FINALE_MIN_RADIUS = 5
FINALE_MAX_RADIUS = 20
MAX_BALL_COUNT = 15               # Maximum number of balls for performance

# --- Sound ---
SOUND_ENABLED = True              # Master switch
SOUND_VOLUME_MASTER = 0.6
SOUND_VOLUME_AMBIENT = 0.2

# Sound files - Simplified to just 4 essential sounds
SOUND_FILES = {
    'collision': 'collision.ogg',  # Single sound for all collisions and bounces
    'ambient': 'ambient.ogg',      # Background ambient sound
    'start': 'start.ogg',          # Sound played at the start
    'end': 'end.ogg'               # Sound played at the end
}