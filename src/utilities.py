import pygame
import random
import math
import time
from src.config import *

# --- Color and Visual Utilities ---

def random_bright_color(use_harmony=True):
    """
    Generate a random vibrant color with more variety and better spectrum coverage.
    
    Args:
        use_harmony: If True, select colors from harmony groups for more pleasing combinations
    
    Returns:
        A pygame Color object
    """
    if use_harmony and random.random() < COLOR_HARMONY_CHANCE:
        # Select from one of the harmony groups for more pleasing combinations
        group = random.choice(COLOR_HARMONY_GROUPS)
        h = random.uniform(group[0], group[1])
    else:
        # Completely random hue across the full spectrum
        h = random.uniform(0, COLOR_SPECTRUM_RANGE)
    
    # More variance in saturation and value while keeping colors vibrant
    s = random.uniform(COLOR_SATURATION_RANGE[0], COLOR_SATURATION_RANGE[1])
    v = random.uniform(COLOR_VALUE_RANGE[0], COLOR_VALUE_RANGE[1])
    
    color = pygame.Color(0)
    color.hsva = (h, s, v, 100)
    return color

def generate_complementary_color(base_color):
    """
    Generate a color complementary to the base color (opposite on the color wheel)
    
    Args:
        base_color: The base pygame Color object
    
    Returns:
        A pygame Color object
    """
    try:
        h, s, v, a = base_color.hsva
        # Complementary color is 180 degrees away on the color wheel
        new_h = (h + 180) % 360
        
        # Keep the same saturation and value
        comp_color = pygame.Color(0)
        comp_color.hsva = (new_h, s, v, a)
        return comp_color
    except ValueError:
        # Fallback if HSVA conversion fails
        return random_bright_color(False)

def generate_analogous_color(base_color, angle_offset=30):
    """
    Generate a color analogous to the base color (nearby on the color wheel)
    
    Args:
        base_color: The base pygame Color object
        angle_offset: Degree offset from base color (typically 30 degrees)
    
    Returns:
        A pygame Color object
    """
    try:
        h, s, v, a = base_color.hsva
        # Randomly shift in positive or negative direction
        direction = random.choice([-1, 1])
        new_h = (h + direction * angle_offset) % 360
        
        # Keep similar saturation and value
        analog_color = pygame.Color(0)
        analog_color.hsva = (new_h, s, v, a)
        return analog_color
    except ValueError:
        # Fallback if HSVA conversion fails
        return random_bright_color(False)

def generate_color_palette(base_color, num_colors=3):
    """
    Generate a harmonious color palette based on a base color
    
    Args:
        base_color: The base pygame Color object
        num_colors: Number of colors to generate
    
    Returns:
        List of pygame Color objects
    """
    palette = [base_color]
    
    # Mix of complementary and analogous colors for a balanced palette
    palette.append(generate_complementary_color(base_color))
    
    # Add analogous colors with varying angles
    for i in range(num_colors - 2):
        offset = random.randint(20, 40)
        palette.append(generate_analogous_color(base_color, offset))
    
    return palette

def color_distance(c1, c2):
    """
    Calculates the Euclidean distance between two RGB colors.
    
    Args:
        c1, c2: pygame Color objects
    
    Returns:
        Float representing color distance
    """
    r1, g1, b1, _ = c1
    r2, g2, b2, _ = c2
    return math.sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2)

def lerp_color(c1, c2, factor):
    """
    Linearly interpolates between two colors.
    
    Args:
        c1, c2: pygame Color objects
        factor: Interpolation factor (0.0 to 1.0)
    
    Returns:
        Interpolated pygame Color
    """
    factor = max(0.0, min(1.0, factor))
    return c1.lerp(c2, factor)

# --- Effects & Particles ---

def spawn_particles(particles, pos, count, base_color, speed_min, speed_max, lifespan_mod=1.0):
    """
    Spawn particle effects at a position
    
    Args:
        particles: List to add particles to
        pos: Position to spawn particles
        count: Number of particles to spawn
        base_color: Base color for particles
        speed_min/max: Min/max particle speed
        lifespan_mod: Modifier for particle lifespan
    """
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(speed_min, speed_max)
        velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
        try:
            # Particle color variation
            h, s, v, a = base_color.hsva # Assuming base_color is valid
            part_h = (h + random.uniform(-20, 20)) % 360
            part_s = max(0, min(100, s * random.uniform(0.8, 1.2)))
            part_v = max(0, min(100, v * random.uniform(0.8, 1.2)))
            part_color = pygame.Color(0)
            part_color.hsva = (part_h, part_s, part_v, 100) # Alpha 100
            lifespan = PARTICLE_LIFESPAN * random.uniform(0.7, 1.3) * lifespan_mod
            part_radius = max(1, PARTICLE_RADIUS * random.uniform(0.8, 1.2)) # Ensure valid radius
            from src.entities import Particle  # Import here to avoid circular imports
            particles.append(Particle(pos, velocity, part_color, lifespan, part_radius))
        except ValueError:
            # Handle case where base_color might be invalid for HSVA
            continue

def trigger_screen_shake(duration=SHAKE_DURATION, intensity=SHAKE_INTENSITY):
    """
    Calculate a screen shake offset 
    
    Args:
        duration: Duration of the shake in seconds
        intensity: Intensity of the shake in pixels
        screen_shake_timer: Current shake timer
        
    Returns:
        Updated screen_shake_timer value
    """
    from src.game_state import game_state
    # Add to existing shake timer rather than replacing
    # Makes concurrent shakes stronger/longer
    # Prevent timer from getting excessively long
    game_state.screen_shake_timer = min(SHAKE_DURATION * 3, 
                                       game_state.screen_shake_timer + duration)
    return game_state.screen_shake_timer