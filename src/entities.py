import pygame
import random
import math
import time
from src.config import *
from src.utilities import lerp_color, spawn_particles
from src.audio import audio_manager
from src.game_state import game_state

class Effect:
    """Visual effect class (flashes, shockwaves, etc.)"""
    
    def __init__(self, position, color, start_radius, end_radius, duration, effect_type="flash"):
        self.position = pygame.Vector2(position)
        self.color = color
        self.start_radius = start_radius
        self.end_radius = end_radius
        self.duration = duration
        self.start_time = time.time()
        self.effect_type = effect_type

    def update(self):
        return (time.time() - self.start_time) < self.duration

    def draw(self, surface, offset):
        elapsed = time.time() - self.start_time
        progress = min(1.0, elapsed / self.duration)

        if self.effect_type == "flash":
            current_radius = self.start_radius + (self.end_radius - self.start_radius) * progress
            current_alpha = int(255 * (1 - progress**1.5)) # Fade alpha faster
            if current_radius < 1 or current_alpha <= 0: return

            # Ensure radius is positive for surface creation
            int_radius = max(1, int(current_radius))

            try:
                flash_surf = pygame.Surface((int_radius * 2, int_radius * 2), pygame.SRCALPHA)
            except (pygame.error, ValueError):
                # Skip drawing if we can't create the surface
                return

            flash_color = self.color[:3] + (current_alpha,)
            pygame.draw.circle(flash_surf, flash_color, (int_radius, int_radius), int_radius)
            # Apply offset when blitting
            surface.blit(flash_surf,
                        (self.position.x - int_radius + offset.x, self.position.y - int_radius + offset.y),
                        special_flags=pygame.BLEND_RGBA_ADD) # Additive flash


class Particle:
    """Simple particle that moves and fades over time"""
    
    def __init__(self, position, velocity, color, lifespan, radius):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.color = color
        self.lifespan = lifespan
        self.start_time = time.time()
        self.radius = max(1, radius) # Ensure radius is at least 1

    def update(self, dt):
        self.position += self.velocity * dt
        # Optional: Add slight drag or gravity
        self.velocity *= 0.98  # Slight drag for more natural motion
        return (time.time() - self.start_time) < self.lifespan

    def draw(self, surface, offset):
        elapsed = time.time() - self.start_time
        progress = min(1.0, elapsed / self.lifespan)
        current_alpha = int(255 * (1 - progress**2)) # Fade out faster
        if current_alpha <= 0: return

        # Draw simple particle circle with fading alpha
        part_color = self.color[:3] + (current_alpha,)
        int_radius = int(self.radius)

        try:
            temp_surf = pygame.Surface((int_radius * 2, int_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surf, part_color, (int_radius, int_radius), int_radius)
            # Apply additive blending for glow effect
            surface.blit(temp_surf,
                        (self.position.x - int_radius + offset.x, self.position.y - int_radius + offset.y),
                        special_flags=pygame.BLEND_RGBA_ADD)
        except (pygame.error, ValueError):
            # Skip drawing if there's an error
            return


class Ball:
    """Main ball entity with physics, collisions, and visual effects"""
    
    def __init__(self, position, velocity, radius, color, ball_id=None):
        """
        Create a new ball
        
        Args:
            position: Initial position
            velocity: Initial velocity
            radius: Radius of the ball
            color: Color of the ball
            ball_id: Optional ID (assigned automatically if None)
        """
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.radius = radius
        
        # Ensure color is a Pygame Color object
        if not isinstance(color, pygame.Color):
            self.base_color = pygame.Color(color)
        else:
            self.base_color = pygame.Color(color.r, color.g, color.b, color.a) # Make a copy

        # Set up color properties with improved dynamics
        self.current_color = pygame.Color(self.base_color) # Start with a copy
        
        # Initialize core attributes
        self.mass = BASE_DENSITY * self.radius**2
        self.last_positions = []
        self.hit_wall_effect_info = None
        self.should_remove = False  # Flag to mark ball for removal
        
        # Enhanced dynamic visual properties with more randomness
        self.pulse_offset = random.uniform(0, 2 * math.pi)
        self.pulse_frequency = PULSE_FREQUENCY * random.uniform(0.8, 1.2)  # Varied pulse frequency
        
        # Color change properties with more varied rates per ball
        # Each ball gets a random shift rate within a range for more variety
        self.color_shift_rate = COLOR_SHIFT_BASE_RATE + random.uniform(-COLOR_SHIFT_VARIANCE, COLOR_SHIFT_VARIANCE)
        # Direction of hue shift (1 or -1)
        self.color_shift_direction = random.choice([-1, 1])
        # Factor to make the shift oscillate rather than consistently increase
        self.color_oscillation_factor = COLOR_SHIFT_OSCILLATION  # 0 = constant, 1 = fully oscillating
        
        # Variable physics properties that can be adjusted during simulation
        self.gravity_strength = GRAVITY_STRENGTH  # Default gravity, can be changed by game state
        
        # Ensure hue is fetched correctly
        try:
            self.hue = self.base_color.hsva[0] # Store hue for shifting
        except ValueError:
            # Handle cases where color might be grayscale (S=0), HSVA might be unstable
            self.hue = random.uniform(0, 360) # Assign random hue if initial fails
            self.current_color.hsva = (self.hue, 100, 100, 100) # Reset to a valid color
            print(f"Warning: Initial color HSVA failed, resetting ball {ball_id or game_state.next_ball_id} color.")

        # Assign ID
        if ball_id is None:
            self.id = game_state.next_ball_id
            game_state.next_ball_id += 1
        else:
            self.id = ball_id

    def update(self, dt):
        """
        Update ball physics and visual properties
        
        Args:
            dt: Time delta in seconds
            
        Returns:
            Boolean: False if the ball should be removed, True otherwise
        """
        # Store position for trail effect
        if dt > 0: # Only update trail if time has passed
            self.last_positions.append(pygame.Vector2(self.position))
            if len(self.last_positions) > TRAIL_LENGTH:
                self.last_positions.pop(0)

        # --- Slow Growth & Enhanced Color Change ---
        self.radius += GROWTH_RATE * dt
        
        # Check if ball should be removed due to being too small
        if self.radius < MIN_RADIUS:  # Add some buffer below MIN_RADIUS
            self.should_remove = True
            return False
            
        self.radius = min(self.radius, MAX_RADIUS) # Clamp max radius

        # Update color using the enhanced color shifting system
        # Color shift with oscillation for more interesting patterns
        elapsed_time = time.time()
        if self.color_oscillation_factor > 0:
            # Apply oscillation to make the color shift back and forth
            oscillation = math.sin(elapsed_time * 0.3) * self.color_oscillation_factor
            shift_amount = (self.color_shift_rate + oscillation) * dt
        else:
            # Constant shift rate
            shift_amount = self.color_shift_rate * dt
            
        # Apply direction and shift the hue
        self.hue = (self.hue + (self.color_shift_direction * shift_amount)) % 360
        
        # Preserve original S, V, A when changing hue, ensure they are valid
        try:
            h_ignored, s, v, a = self.current_color.hsva
            # Slightly pulsate saturation for more vibrancy
            pulse_value = (math.sin(elapsed_time * 0.2 + self.pulse_offset) + 1) / 2
            s = max(80, min(100, 80 + pulse_value * 20))  # Keep saturation high (80-100)
            v = max(85, min(100, 85 + pulse_value * 15))  # Keep value high (85-100)
            a = max(0, min(100, a))
            self.current_color.hsva = (self.hue, s, v, a) # Update color based on shifted hue
        except ValueError:
            # Fallback if HSVA becomes invalid during update
            self.current_color.hsva = (self.hue, 90, 95, 100) # Reset to known valid bright color

        # Update mass based on potentially changed radius
        self.mass = BASE_DENSITY * self.radius**2

        # ----- IMPROVED GRAVITY WITH DEADZONE -----
        to_center = CENTER - self.position
        dist_sq = to_center.length_squared()
        if dist_sq > 1e-4:  # Avoid division by zero
            distance = math.sqrt(dist_sq)
            
            # Apply gravity only outside the center deadzone
            if distance > GRAVITY_CENTER_DEADZONE:
                # Calculate adjusted distance (from edge of deadzone)
                adjusted_distance = distance - GRAVITY_CENTER_DEADZONE
                normalized_dist = min(1.0, adjusted_distance / (CONTAINER_RADIUS - GRAVITY_CENTER_DEADZONE))
                
                # Use phase-based gravity strength from game state
                # for dynamic gravity changes throughout simulation
                current_gravity = self.gravity_strength
                
                # Inverse square law with a softer falloff
                gravity_falloff = 1.0 / (0.2 + normalized_dist * normalized_dist)
                
                # Apply scaled gravity force - weaker in center
                gravity_force = to_center.normalize() * current_gravity * self.mass * gravity_falloff
                
                # Convert force to acceleration (a = F/m)
                gravity_accel = gravity_force / self.mass if self.mass > 1e-9 else pygame.Vector2(0,0)
                self.velocity += gravity_accel * dt
            
            # If very close to center, apply a small random nudge to prevent stagnation
            elif distance < GRAVITY_CENTER_DEADZONE * 0.5 and random.random() < 0.05:
                nudge_dir = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
                self.velocity += nudge_dir * random.uniform(10, 30)

        # Apply improved drag coefficient
        # Adjust drag based on simulation phase for more dynamic behavior in later phases
        phase_drag = DRAG_COEFFICIENT
        if game_state.current_phase == "BUILD":
            phase_drag = min(1.0, DRAG_COEFFICIENT + 0.0005)  # Slightly less drag
        elif game_state.current_phase == "CHAOS":
            phase_drag = min(1.0, DRAG_COEFFICIENT + 0.001)   # Even less drag
        elif game_state.current_phase == "FINALE":
            phase_drag = min(1.0, DRAG_COEFFICIENT + 0.002)   # Minimal drag for chaos
            
        self.velocity *= phase_drag

        # Update position based on velocity
        self.position += self.velocity * dt

        # Clamp velocity to prevent extreme speeds
        # Allow higher max velocities in later phases
        phase_max_velocity = MAX_VELOCITY
        if game_state.current_phase == "BUILD":
            phase_max_velocity = MAX_VELOCITY * 1.2
        elif game_state.current_phase == "CHAOS":
            phase_max_velocity = MAX_VELOCITY * 1.5
        elif game_state.current_phase == "FINALE":
            phase_max_velocity = MAX_VELOCITY * 2.0
            
        speed_sq = self.velocity.length_squared()
        if speed_sq > phase_max_velocity * phase_max_velocity:
            self.velocity.scale_to_length(phase_max_velocity)

        # Boundary collision with container circle
        dist_from_center = self.position.distance_to(CENTER)
        if dist_from_center + self.radius > CONTAINER_RADIUS:
            overlap = (dist_from_center + self.radius) - CONTAINER_RADIUS
            # Prevent division by zero if ball is exactly at the center
            if dist_from_center > 1e-6:
                normal = (self.position - CENTER).normalize()
            else:
                normal = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
                if normal.length() < 1e-6: normal = pygame.Vector2(1, 0) # Final fallback

            # Resolve collision
            self.position -= normal * overlap
            
            # Apply size/mass loss on wall collision based on impact velocity
            # More loss in later phases
            if game_state.current_phase != "CALM":
                wall_impact = abs(self.velocity.dot(normal)) / 1000.0  # Scale 0-1
                wall_shrink_factor = 0.0
                
                if game_state.current_phase == "BUILD":
                    wall_shrink_factor = 0.001
                elif game_state.current_phase == "CHAOS":
                    wall_shrink_factor = 0.002
                elif game_state.current_phase == "FINALE":
                    wall_shrink_factor = 0.003
                
                size_loss = self.radius * wall_shrink_factor * wall_impact
                self.radius = max(MIN_RADIUS, self.radius - size_loss)
                self.mass = BASE_DENSITY * self.radius**2
            
            # Bounce elasticity varies by phase
            phase_elasticity = 0.98  # Base elasticity
            if game_state.current_phase == "BUILD":
                phase_elasticity = 0.985
            elif game_state.current_phase == "CHAOS":
                phase_elasticity = 0.99
            elif game_state.current_phase == "FINALE":
                phase_elasticity = 0.995
                
            # Improved bounce for more energetic wall collisions
            self.velocity.reflect_ip(normal)
            self.velocity *= phase_elasticity
            
            # Add a slight tangential velocity component for more interesting bounces
            if random.random() < 0.3:  # 30% chance
                # Create a tangent vector
                tangent = pygame.Vector2(-normal.y, normal.x)
                # Add a small tangential component (up to 10% of current velocity)
                tangent_strength = self.velocity.length() * random.uniform(0.05, 0.1)
                self.velocity += tangent * tangent_strength * random.choice([-1, 1])

            # Trigger wall hit effects (sound & visuals)
            impact_pos = self.position + normal * self.radius
            flash_color = pygame.Color('white') # Or use ball color
            flash_radius = self.radius * 0.9
            self.hit_wall_effect_info = {'pos': impact_pos, 'color': flash_color, 'radius': flash_radius}
            
            # Scale audio volume with impact
            audio_volume = 0.5 + (min(1.0, abs(self.velocity.dot(normal)) / 1000.0) * 0.5)
            audio_manager.play('collision', audio_volume, self.position)
            
        return True  # Return True to keep the ball in the game

    def draw(self, surface, current_time, offset):
        """
        Draw the ball with all visual effects
        
        Args:
            surface: Pygame surface to draw on
            current_time: Current game time
            offset: Screen shake offset
        """
        # Ensure radius is valid for drawing
        int_radius = max(1, int(self.radius))

        # --- Draw Trail ---
        if TRAIL_LENGTH > 0 and len(self.last_positions) > 0:
            num_trail_points = len(self.last_positions)
            for i, pos in enumerate(reversed(self.last_positions)):
                trail_alpha = int(TRAIL_ALPHA_START * ((num_trail_points - 1 - i) / num_trail_points))
                if trail_alpha > 5:
                    trail_color = self.current_color[:3] + (trail_alpha,)
                    # Ensure trail radius is valid
                    trail_draw_radius = max(1, int(self.radius * ((num_trail_points - i) / (num_trail_points + 1))))

                    try:
                        temp_surf = pygame.Surface((trail_draw_radius * 2, trail_draw_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(temp_surf, trail_color, (trail_draw_radius, trail_draw_radius), trail_draw_radius)
                        # Apply offset when blitting trail segment
                        surface.blit(temp_surf, 
                                    (pos.x - trail_draw_radius + offset.x, pos.y - trail_draw_radius + offset.y), 
                                    special_flags=pygame.BLEND_RGBA_ADD)
                    except (pygame.error, ValueError):
                        continue # Skip this trail segment

        # --- Advanced Glow ---
        # Calculate pulse with unique frequency per ball
        pulse = (math.sin(current_time * self.pulse_frequency + self.pulse_offset) + 1) / 2 # 0 to 1

        # 1. Core Ball with subtle pulsing
        try:
            h, s, v, a = self.current_color.hsva
            core_v = max(0, min(100, v * (1.0 + pulse * 0.1))) # Subtle brightness pulse
            core_color = pygame.Color(0); core_color.hsva = (h, s, core_v, a)
        except ValueError:
            core_color = self.current_color # Fallback if HSVA fails

        pygame.draw.circle(surface, core_color, self.position + offset, int_radius)

        # 2. Bright Bloom Layer (Additive)
        bloom_radius = self.radius * GLOW_BLOOM_SIZE_FACTOR * (1.0 + pulse * PULSE_AMPLITUDE_BLOOM * 0.2)
        int_bloom_radius = max(1, int(bloom_radius))
        bloom_size = int_bloom_radius * 2
        bloom_intensity = GLOW_BLOOM_INTENSITY * (1.0 + pulse * PULSE_AMPLITUDE_BLOOM)

        try:
            bloom_surf = pygame.Surface((bloom_size, bloom_size), pygame.SRCALPHA)
            # Bloom color slightly desaturated/whiter than core
            bloom_h, bloom_s, bloom_v, bloom_a = self.current_color.hsva
            # Ensure bloom saturation is valid
            bloom_s_adjusted = max(0, min(100, bloom_s * 0.8))
            bloom_color_base = pygame.Color(0); bloom_color_base.hsva = (bloom_h, bloom_s_adjusted, 100, 100)

            # Ensure additive color components are valid
            add_color_r = max(0, min(bloom_color_base.r, int(bloom_intensity)))
            add_color_g = max(0, min(bloom_color_base.g, int(bloom_intensity)))
            add_color_b = max(0, min(bloom_color_base.b, int(bloom_intensity)))
            add_color = pygame.Color(add_color_r, add_color_g, add_color_b)

            # Draw bloom circle onto its surface
            pygame.draw.circle(bloom_surf, add_color, (int_bloom_radius, int_bloom_radius), int_bloom_radius)
            # Blit bloom with additive blending
            surface.blit(bloom_surf,
                        (self.position.x - int_bloom_radius + offset.x, self.position.y - int_bloom_radius + offset.y),
                        special_flags=pygame.BLEND_RGB_ADD)
        except (ValueError, pygame.error):
            pass # Skip bloom if there's an issue

        # 3. Soft Haze Layer (Alpha Blend)
        haze_radius = self.radius * GLOW_HAZE_SIZE_FACTOR * (1.0 + pulse * PULSE_AMPLITUDE_HAZE * 0.1)
        int_haze_radius = max(1, int(haze_radius))
        haze_size = int_haze_radius * 2
        haze_alpha = GLOW_HAZE_ALPHA * (1.0 + pulse * PULSE_AMPLITUDE_HAZE)
        haze_alpha = max(0, min(255, int(haze_alpha)))

        try:
            haze_surf = pygame.Surface((haze_size, haze_size), pygame.SRCALPHA)
            haze_color = self.current_color[:3] + (haze_alpha,) # Use current ball color with alpha
            # Draw haze circle onto its surface
            pygame.draw.circle(haze_surf, haze_color, (int_haze_radius, int_haze_radius), int_haze_radius)
            # Blit haze with normal alpha blending
            surface.blit(haze_surf,
                        (self.position.x - int_haze_radius + offset.x, self.position.y - int_haze_radius + offset.y))
        except (pygame.error, ValueError):
            pass # Skip haze if there's an issue