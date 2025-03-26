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

            int_radius = max(1, int(current_radius))

            try:
                flash_surf = pygame.Surface((int_radius * 2, int_radius * 2), pygame.SRCALPHA)
            except (pygame.error, ValueError):
                return

            flash_color = self.color[:3] + (current_alpha,)
            pygame.draw.circle(flash_surf, flash_color, (int_radius, int_radius), int_radius)
            surface.blit(flash_surf,
                        (self.position.x - int_radius + offset.x, self.position.y - int_radius + offset.y),
                        special_flags=pygame.BLEND_RGBA_ADD)


class Particle:
    """Simple particle that moves and fades over time"""

    def __init__(self, position, velocity, color, lifespan, radius):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.color = color
        self.lifespan = lifespan
        self.start_time = time.time()
        self.radius = max(1, radius)

    def update(self, dt):
        self.position += self.velocity * dt
        self.velocity *= 0.98 # Slight drag
        return (time.time() - self.start_time) < self.lifespan

    def draw(self, surface, offset):
        elapsed = time.time() - self.start_time
        progress = min(1.0, elapsed / self.lifespan)
        current_alpha = int(255 * (1 - progress**2))
        if current_alpha <= 0: return

        part_color = self.color[:3] + (current_alpha,)
        int_radius = int(self.radius)

        try:
            temp_surf = pygame.Surface((int_radius * 2, int_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surf, part_color, (int_radius, int_radius), int_radius)
            surface.blit(temp_surf,
                        (self.position.x - int_radius + offset.x, self.position.y - int_radius + offset.y),
                        special_flags=pygame.BLEND_RGBA_ADD)
        except (pygame.error, ValueError):
            return


class Ball:
    """Main ball entity with physics, collisions, and visual effects"""

    def __init__(self, position, velocity, radius, color, ball_id=None):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.radius = radius

        if not isinstance(color, pygame.Color):
            self.base_color = pygame.Color(color)
        else:
            self.base_color = pygame.Color(color.r, color.g, color.b, color.a)

        self.current_color = pygame.Color(self.base_color)
        self.mass = BASE_DENSITY * self.radius**2
        self.last_positions = []
        self.hit_wall_effect_info = None
        self.should_remove = False

        self.pulse_offset = random.uniform(0, 2 * math.pi)
        self.pulse_frequency = PULSE_FREQUENCY * random.uniform(0.8, 1.2)
        self.color_shift_rate = COLOR_SHIFT_BASE_RATE + random.uniform(-COLOR_SHIFT_VARIANCE, COLOR_SHIFT_VARIANCE)
        self.color_shift_direction = random.choice([-1, 1])
        self.color_oscillation_factor = COLOR_SHIFT_OSCILLATION

        # Use time-based gravity from game_state
        self.gravity_strength = game_state.get_current_value(INITIAL_GRAVITY_STRENGTH, FINAL_GRAVITY_STRENGTH)

        try:
            self.hue = self.base_color.hsva[0]
        except ValueError:
            self.hue = random.uniform(0, 360)
            self.current_color.hsva = (self.hue, 100, 100, 100)
            print(f"Warning: Initial color HSVA failed, resetting ball color.")

        if ball_id is None:
            self.id = game_state.next_ball_id
            game_state.next_ball_id += 1
        else:
            self.id = ball_id

    def update(self, dt):
        if dt > 0:
            self.last_positions.append(pygame.Vector2(self.position))
            if len(self.last_positions) > TRAIL_LENGTH:
                self.last_positions.pop(0)

        # --- Growth & Color Change based on chaos_factor ---
        current_growth_rate = game_state.get_current_value(INITIAL_GROWTH_RATE, FINAL_GROWTH_RATE)
        self.radius += current_growth_rate * dt

        if self.radius < MIN_RADIUS:
            self.should_remove = True
            return False

        # Update color
        elapsed_time_sim = time.time() # Use absolute time for smoother oscillation
        if self.color_oscillation_factor > 0:
            oscillation = math.sin(elapsed_time_sim * 0.3) * self.color_oscillation_factor
            shift_amount = (self.color_shift_rate + oscillation) * dt
        else:
            shift_amount = self.color_shift_rate * dt

        self.hue = (self.hue + (self.color_shift_direction * shift_amount)) % 360

        try:
            h_ignored, s, v, a = self.current_color.hsva
            pulse_value = (math.sin(elapsed_time_sim * 0.2 + self.pulse_offset) + 1) / 2
            s = max(80, min(100, 80 + pulse_value * 20))
            v = max(85, min(100, 85 + pulse_value * 15))
            a = max(0, min(100, a))
            self.current_color.hsva = (self.hue, s, v, a)
        except ValueError:
            self.current_color.hsva = (self.hue, 90, 95, 100)

        self.mass = BASE_DENSITY * self.radius**2

        # ----- GRAVITY -----
        # Update gravity strength based on chaos factor
        self.gravity_strength = game_state.get_current_value(INITIAL_GRAVITY_STRENGTH, FINAL_GRAVITY_STRENGTH)

        to_center = CENTER - self.position
        dist_sq = to_center.length_squared()
        if dist_sq > 1e-4:
            distance = math.sqrt(dist_sq)

            if distance > GRAVITY_CENTER_DEADZONE:
                adjusted_distance = distance - GRAVITY_CENTER_DEADZONE
                normalized_dist = min(1.0, adjusted_distance / (CONTAINER_RADIUS - GRAVITY_CENTER_DEADZONE))

                current_gravity = self.gravity_strength
                gravity_falloff = 1.0 / (0.2 + normalized_dist * normalized_dist)
                gravity_force = to_center.normalize() * current_gravity * self.mass * gravity_falloff
                gravity_accel = gravity_force / self.mass if self.mass > 1e-9 else pygame.Vector2(0,0)
                self.velocity += gravity_accel * dt

            elif distance < GRAVITY_CENTER_DEADZONE * 0.5 and random.random() < 0.05:
                nudge_dir = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
                self.velocity += nudge_dir * random.uniform(10, 30)

        # Apply Drag based on chaos_factor
        current_drag = game_state.get_current_value(INITIAL_DRAG_COEFFICIENT, FINAL_DRAG_COEFFICIENT)
        # Ensure drag never exceeds 1.0
        self.velocity *= min(1.0, current_drag)

        # Update position
        self.position += self.velocity * dt

        # Clamp velocity based on chaos_factor
        current_max_velocity = game_state.get_current_value(INITIAL_MAX_VELOCITY, FINAL_MAX_VELOCITY)
        speed_sq = self.velocity.length_squared()
        if speed_sq > current_max_velocity * current_max_velocity:
            self.velocity.scale_to_length(current_max_velocity)

        # Boundary collision
        dist_from_center = self.position.distance_to(CENTER)
        if dist_from_center + self.radius > CONTAINER_RADIUS:
            overlap = (dist_from_center + self.radius) - CONTAINER_RADIUS
            if dist_from_center > 1e-6:
                normal = (self.position - CENTER).normalize()
            else:
                normal = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
                if normal.length() < 1e-6: normal = pygame.Vector2(1, 0)

            self.position -= normal * overlap

            # Apply wall shrink based on chaos_factor
            wall_impact = abs(self.velocity.dot(normal)) / 1000.0
            current_wall_shrink_factor = game_state.get_current_value(INITIAL_COLLISION_SHRINK_FACTOR, FINAL_COLLISION_SHRINK_FACTOR) * 0.1 # Wall shrink less than ball-ball
            size_loss = self.radius * current_wall_shrink_factor * wall_impact
            self.radius = max(MIN_RADIUS, self.radius - size_loss)
            self.mass = BASE_DENSITY * self.radius**2

            # Bounce elasticity based on chaos_factor
            current_elasticity = game_state.get_current_value(INITIAL_BALL_ELASTICITY, FINAL_BALL_ELASTICITY)
            # Use a slightly lower elasticity for wall bounces compared to ball-ball
            wall_elasticity = max(0.9, current_elasticity * 0.95)

            self.velocity.reflect_ip(normal)
            self.velocity *= wall_elasticity

            # Add tangential velocity boost based on chaos_factor
            if random.random() < 0.1 + game_state.chaos_factor * 0.3: # More chance later
                tangent = pygame.Vector2(-normal.y, normal.x)
                tangent_strength = self.velocity.length() * random.uniform(0.05, 0.1 + 0.1 * game_state.chaos_factor) # Stronger later
                self.velocity += tangent * tangent_strength * random.choice([-1, 1])

            # Trigger wall hit effects
            impact_pos = self.position + normal * self.radius
            flash_color = pygame.Color('white')
            flash_radius = self.radius * 0.9
            self.hit_wall_effect_info = {'pos': impact_pos, 'color': flash_color, 'radius': flash_radius}

            audio_volume = 0.5 + (min(1.0, abs(self.velocity.dot(normal)) / 1000.0) * 0.5)
            audio_manager.play('collision', audio_volume, self.position)

        return True

    def draw(self, surface, current_time, offset):
        int_radius = max(1, int(self.radius))

        # --- Draw Trail ---
        if TRAIL_LENGTH > 0 and len(self.last_positions) > 0:
            num_trail_points = len(self.last_positions)
            for i, pos in enumerate(reversed(self.last_positions)):
                trail_alpha = int(TRAIL_ALPHA_START * ((num_trail_points - 1 - i) / num_trail_points))
                if trail_alpha > 5:
                    trail_color = self.current_color[:3] + (trail_alpha,)
                    trail_draw_radius = max(1, int(self.radius * ((num_trail_points - i) / (num_trail_points + 1))))
                    try:
                        temp_surf = pygame.Surface((trail_draw_radius * 2, trail_draw_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(temp_surf, trail_color, (trail_draw_radius, trail_draw_radius), trail_draw_radius)
                        surface.blit(temp_surf,
                                    (pos.x - trail_draw_radius + offset.x, pos.y - trail_draw_radius + offset.y),
                                    special_flags=pygame.BLEND_RGBA_ADD)
                    except (pygame.error, ValueError):
                        continue

        # --- Advanced Glow ---
        pulse = (math.sin(current_time * self.pulse_frequency + self.pulse_offset) + 1) / 2

        # 1. Core Ball
        try:
            h, s, v, a = self.current_color.hsva
            core_v = max(0, min(100, v * (1.0 + pulse * 0.1)))
            core_color = pygame.Color(0); core_color.hsva = (h, s, core_v, a)
        except ValueError:
            core_color = self.current_color

        pygame.draw.circle(surface, core_color, self.position + offset, int_radius)

        # 2. Bright Bloom Layer (Additive)
        bloom_radius = self.radius * GLOW_BLOOM_SIZE_FACTOR * (1.0 + pulse * PULSE_AMPLITUDE_BLOOM * 0.2)
        int_bloom_radius = max(1, int(bloom_radius))
        bloom_size = int_bloom_radius * 2
        bloom_intensity = GLOW_BLOOM_INTENSITY * (1.0 + pulse * PULSE_AMPLITUDE_BLOOM)

        try:
            bloom_surf = pygame.Surface((bloom_size, bloom_size), pygame.SRCALPHA)
            bloom_h, bloom_s, bloom_v, bloom_a = self.current_color.hsva
            bloom_s_adjusted = max(0, min(100, bloom_s * 0.8))
            bloom_color_base = pygame.Color(0); bloom_color_base.hsva = (bloom_h, bloom_s_adjusted, 100, 100)
            add_color_r = max(0, min(bloom_color_base.r, int(bloom_intensity)))
            add_color_g = max(0, min(bloom_color_base.g, int(bloom_intensity)))
            add_color_b = max(0, min(bloom_color_base.b, int(bloom_intensity)))
            add_color = pygame.Color(add_color_r, add_color_g, add_color_b)
            pygame.draw.circle(bloom_surf, add_color, (int_bloom_radius, int_bloom_radius), int_bloom_radius)
            surface.blit(bloom_surf,
                        (self.position.x - int_bloom_radius + offset.x, self.position.y - int_bloom_radius + offset.y),
                        special_flags=pygame.BLEND_RGB_ADD)
        except (ValueError, pygame.error):
            pass

        # 3. Soft Haze Layer (Alpha Blend)
        haze_radius = self.radius * GLOW_HAZE_SIZE_FACTOR * (1.0 + pulse * PULSE_AMPLITUDE_HAZE * 0.1)
        int_haze_radius = max(1, int(haze_radius))
        haze_size = int_haze_radius * 2
        haze_alpha = GLOW_HAZE_ALPHA * (1.0 + pulse * PULSE_AMPLITUDE_HAZE)
        haze_alpha = max(0, min(255, int(haze_alpha)))

        try:
            haze_surf = pygame.Surface((haze_size, haze_size), pygame.SRCALPHA)
            haze_color = self.current_color[:3] + (haze_alpha,)
            pygame.draw.circle(haze_surf, haze_color, (int_haze_radius, int_haze_radius), int_haze_radius)
            surface.blit(haze_surf,
                        (self.position.x - int_haze_radius + offset.x, self.position.y - int_haze_radius + offset.y))
        except (pygame.error, ValueError):
            pass