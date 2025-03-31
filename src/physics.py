import pygame
import math
import random
import time
from src.config import *
from src.entities import Ball, Effect
from src.utilities import color_distance, lerp_color, spawn_particles, trigger_screen_shake
from src.audio import audio_manager
from src.game_state import game_state

def handle_ball_collisions(balls, dt, beat_intensity=0.5):
    """
    Handle collisions between balls with merging and splitting behavior,
    scaling effects based on game_state.chaos_factor.

    Args:
        balls: List of Ball objects
        dt: Time delta in seconds
        beat_intensity: Current audio beat intensity (0.0 to 1.0)

    Returns:
        Tuple of (balls_to_add, balls_to_remove)
    """
    balls_to_add = []
    balls_to_remove = set()
    collision_pairs_processed = set()

    # Get current time-based parameters from game_state
    chaos = game_state.chaos_factor # Alias for brevity
    collision_shrink_factor = game_state.get_current_value(INITIAL_COLLISION_SHRINK_FACTOR, FINAL_COLLISION_SHRINK_FACTOR)
    ball_elasticity = game_state.get_current_value(INITIAL_BALL_ELASTICITY, FINAL_BALL_ELASTICITY)
    split_chance = game_state.get_current_value(INITIAL_SPLIT_CHANCE, FINAL_SPLIT_CHANCE)
    merge_threshold = game_state.get_current_value(INITIAL_COLOR_DISTANCE_THRESHOLD, FINAL_COLOR_DISTANCE_THRESHOLD)
    split_mass_loss = game_state.get_current_value(INITIAL_SPLIT_MASS_LOSS_FACTOR, FINAL_SPLIT_MASS_LOSS_FACTOR)
    current_shake_intensity = game_state.get_current_value(INITIAL_SHAKE_INTENSITY, FINAL_SHAKE_INTENSITY)
    
    # Apply beat influence
    beat_influence = 0.7 + beat_intensity * 0.6  # Range from 0.7 to 1.3
    ball_elasticity *= beat_influence
    current_shake_intensity *= beat_influence

    for i in range(len(balls)):
        if balls[i].id in balls_to_remove:
            continue

        for j in range(i + 1, len(balls)):
            pair_id = tuple(sorted((balls[i].id, balls[j].id)))
            if balls[j].id in balls_to_remove or pair_id in collision_pairs_processed:
                continue

            ball_a = balls[i]
            ball_b = balls[j]

            vec_dist = ball_a.position - ball_b.position
            dist_sq = vec_dist.length_squared()
            min_dist = ball_a.radius + ball_b.radius
            min_dist_sq = min_dist * min_dist

            if dist_sq < min_dist_sq and dist_sq > 1e-9:
                dist = math.sqrt(dist_sq)
                normal = vec_dist / dist

                # 1. Resolve Overlap
                overlap = min_dist - dist
                total_mass = ball_a.mass + ball_b.mass
                if total_mass > 1e-9:
                    move_a = normal * (overlap * (ball_b.mass / total_mass))
                    move_b = -normal * (overlap * (ball_a.mass / total_mass))
                    ball_a.position += move_a
                    ball_b.position += move_b
                else:
                    ball_a.position += normal * overlap * 0.5
                    ball_b.position -= normal * overlap * 0.5

                # 2. Collision Response
                relative_velocity = ball_a.velocity - ball_b.velocity
                vel_along_normal = relative_velocity.dot(normal)

                if vel_along_normal < 0 :
                    m1 = ball_a.mass if ball_a.mass > 1e-9 else 1e-9
                    m2 = ball_b.mass if ball_b.mass > 1e-9 else 1e-9
                    inv_mass1 = 1.0 / m1
                    inv_mass2 = 1.0 / m2

                    impact_force = abs(vel_along_normal) / 2000.0
                    impact_force = min(1.0, impact_force)

                    # Use current elasticity (which ramps up over time)
                    current_elasticity = ball_elasticity

                    impulse_scalar = (- (1.0 + current_elasticity) * vel_along_normal) / (inv_mass1 + inv_mass2) # Simplified impulse calc

                    # -- Shrink ball size on collision --
                    shrink_amount = impact_force * collision_shrink_factor * dt * 60 # Scale shrink with impact and time factor

                    ball_a.radius -= shrink_amount * ball_a.radius
                    ball_b.radius -= shrink_amount * ball_b.radius

                    if ball_a.radius < MIN_RADIUS and BALLS_CAN_DIE: ball_a.should_remove = True
                    if ball_b.radius < MIN_RADIUS and BALLS_CAN_DIE: ball_b.should_remove = True

                    ball_a.mass = BASE_DENSITY * ball_a.radius**2
                    ball_b.mass = BASE_DENSITY * ball_b.radius**2

                    impulse_vec = impulse_scalar * normal
                    ball_a.velocity += impulse_vec * inv_mass1
                    ball_b.velocity -= impulse_vec * inv_mass2

                    # Add tangential velocity based on chaos_factor and impact
                    if random.random() < 0.15 + chaos * 0.4 + impact_force * 0.2: # Higher chance later & on big hits
                        tangent = pygame.Vector2(-normal.y, normal.x)
                        spin_factor = 0.05 + chaos * 0.15 # More spin later
                        ball_a.velocity += tangent * impulse_scalar * inv_mass1 * spin_factor * random.choice([-1, 1])
                        ball_b.velocity -= tangent * impulse_scalar * inv_mass2 * spin_factor * random.choice([-1, 1])

                    # --- Collision Effects ---
                    contact_point = ball_b.position + normal * ball_b.radius
                    avg_radius = (ball_a.radius + ball_b.radius) * 0.5
                    try:
                        avg_color = lerp_color(ball_a.current_color, ball_b.current_color, 0.5)
                    except (TypeError, ValueError):
                        avg_color = pygame.Color('white')

                    # Modify volume and flash size based on beat intensity
                    audio_volume = (0.5 + (impact_force * 0.5)) * beat_influence
                    audio_manager.play('collision', audio_volume, contact_point)

                    flash_size = avg_radius * (0.8 + (FLASH_RADIUS_FACTOR - 0.8) * impact_force)
                    flash_size *= (1.0 + (beat_intensity - 0.5) * 0.4)  # Adjust for beat
                    flash_duration = FLASH_DURATION * (0.6 + (0.4 * impact_force))
                    game_state.effects.append(Effect(contact_point, pygame.Color('white'),
                                                   avg_radius * 0.5, flash_size, flash_duration))

                    particle_count = int(PARTICLE_COUNT_COLLISION * (0.5 + (0.5 * impact_force)))
                    particle_count = int(particle_count * (1.0 + (beat_intensity - 0.5) * 0.5))  # More particles with beat
                    particle_speed_max = PARTICLE_SPEED_MAX * (1.0 + chaos * 0.5) # Faster particles later
                    particle_speed_max *= beat_influence  # Adjust for beat
                    spawn_particles(game_state.particles, contact_point, particle_count,
                                   avg_color, PARTICLE_SPEED_MIN, particle_speed_max)

                    # Screen shake based on impact and chaos factor
                    shake_intensity = current_shake_intensity * (0.3 + (0.7 * impact_force))
                    trigger_screen_shake(SHAKE_DURATION * (0.5 + 0.5 * impact_force), shake_intensity)


                    # 3. Splitting or Merging Logic
                    c_dist = color_distance(ball_a.current_color, ball_b.current_color)

                    # --- MERGE Condition (Harder over time) ---
                    if c_dist < merge_threshold:
                        collision_pairs_processed.add(pair_id)

                        total_area = math.pi * ball_a.radius**2 + math.pi * ball_b.radius**2
                        area_loss = 0.02 + (0.05 * impact_force)
                        new_radius = math.sqrt(total_area * (1 - area_loss) / math.pi) * MERGE_AREA_FACTOR
                        new_radius = max(MIN_RADIUS, min(new_radius, MAX_RADIUS * 1.1)) # Allow slightly larger merges
                        new_mass = BASE_DENSITY * new_radius**2

                        if total_mass > 1e-9:
                            new_pos = (ball_a.position * ball_a.mass + ball_b.position * ball_b.mass) / total_mass
                            new_vel = (ball_a.velocity * ball_a.mass + ball_b.velocity * ball_b.mass) / total_mass
                        else:
                            new_pos = (ball_a.position + ball_b.position) / 2
                            new_vel = (ball_a.velocity + ball_b.velocity) / 2

                        merged_ball = Ball(new_pos, new_vel, new_radius, avg_color)
                        balls_to_add.append(merged_ball)
                        balls_to_remove.add(ball_a.id)
                        balls_to_remove.add(ball_b.id)

                        # --- Merge Effects ---
                        merge_vol = (1.1 + chaos * 0.2) * beat_influence
                        audio_manager.play('collision', merge_vol, new_pos) # Louder merge later
                        
                        # Bigger flash with beat
                        flash_size_factor = 2.0 + chaos * 0.5 + (beat_intensity - 0.5) * 0.6
                        game_state.effects.append(Effect(new_pos, pygame.Color('white'),
                                                       new_radius, new_radius * flash_size_factor, FLASH_DURATION * 1.5)) # Bigger flash later
                        
                        # More particles with beat
                        particle_count = int(PARTICLE_COUNT_SPLIT_MERGE * (1 + chaos) * beat_influence)
                        spawn_particles(game_state.particles, new_pos, particle_count,
                                       avg_color, PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX * (1 + chaos*0.8), 1.5)
                        
                        trigger_screen_shake(SHAKE_DURATION * 1.2, current_shake_intensity * 1.5 * beat_influence)

                    # --- SPLIT Condition (Easier over time) ---
                    else:
                        effective_split_chance = split_chance * (0.5 + (impact_force * 0.5)) # Scale with impact

                        can_a_split = ball_a.radius >= MIN_SPLIT_RADIUS
                        can_b_split = ball_b.radius >= MIN_SPLIT_RADIUS
                        victim, other = None, None

                        if random.random() < effective_split_chance:
                            if can_a_split and can_b_split:
                                victim, other = (ball_a, ball_b) if ball_a.radius >= ball_b.radius else (ball_b, ball_a)
                            elif can_a_split: victim, other = ball_a, ball_b
                            elif can_b_split: victim, other = ball_b, ball_a

                            if victim:
                                victim_area = math.pi * victim.radius**2
                                # Use current split_mass_loss (ramps up over time)
                                current_split_mass_loss = split_mass_loss + impact_force * 0.1 # More loss on big impacts

                                new_area_each = victim_area / (2.0 * current_split_mass_loss)

                                if new_area_each > 0:
                                    new_radius = math.sqrt(new_area_each / math.pi)
                                else:
                                    new_radius = MIN_RADIUS

                                if new_radius >= MIN_RADIUS and BALLS_CAN_DIE:
                                    balls_to_remove.add(victim.id)
                                    collision_pairs_processed.add(pair_id)

                                    perp_normal = pygame.Vector2(-normal.y, normal.x) * random.choice([-1, 1])

                                    audio_manager.play('collision', (1.0 + chaos * 0.1) * beat_influence, victim.position) # Louder split later
                                    
                                    # Flash size enhanced by beat
                                    flash_size_factor = 1.5 + chaos * 0.5 + (beat_intensity - 0.5) * 0.4
                                    game_state.effects.append(Effect(victim.position, victim.current_color,
                                                                    victim.radius, victim.radius * flash_size_factor,
                                                                    FLASH_DURATION * 1.2))
                                                                    
                                    # More particles with stronger beat
                                    particle_count = int(PARTICLE_COUNT_SPLIT_MERGE * (1 + chaos) * beat_influence)
                                    spawn_particles(game_state.particles, victim.position,
                                                   particle_count, victim.current_color,
                                                   PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX * (1 + chaos*0.8))
                                                  
                                    trigger_screen_shake(SHAKE_DURATION * (1 + chaos * 0.3), 
                                                        current_shake_intensity * beat_influence)

                                    for k in range(2):
                                        offset_dir = perp_normal if k == 0 else -perp_normal
                                        new_pos = victim.position + offset_dir * (new_radius * 1.1 + 2)

                                        # Increase velocity of split balls based on chaos
                                        vel_bonus = 1.0 + chaos * 0.6
                                        vel_offset_magnitude = (victim.velocity.length() * 0.3 + 80) * vel_bonus * beat_influence
                                        new_vel = victim.velocity + offset_dir * vel_offset_magnitude * random.uniform(0.9, 1.1)

                                        try:
                                            tint_factor = SPLIT_TINT_FACTOR + chaos * 0.2 # More tint later
                                            tinted_color = lerp_color(victim.current_color,
                                                                     other.current_color,
                                                                     tint_factor * random.uniform(0.8, 1.2))
                                        except (TypeError, ValueError):
                                            tinted_color = avg_color

                                        balls_to_add.append(Ball(new_pos, new_vel, new_radius, tinted_color))

    return balls_to_add, balls_to_remove


def update_game_objects(dt, beat_intensity=0.5):
    """
    Update all game objects, applying time-based chaos scaling.

    Args:
        dt: Time delta in seconds
        beat_intensity: Current audio beat intensity (0.0 to 1.0)
    """
    # Limit dt to prevent huge steps that could cause instability
    dt = min(dt, 1.0 / 20.0)  # Cap at 20 FPS equivalent to prevent physics issues
    
    # Update chaos factor first
    game_state.update_chaos_factor()

    new_effects = []
    balls_to_remove_small = set()

    # Update balls with beat influence
    for ball in game_state.balls:
        # Scale the ball's pulse frequency with the beat_intensity
        beat_pulse_factor = 1.0 + (beat_intensity - 0.5) * 0.3  # Range 0.85 to 1.15
        original_freq = ball.pulse_frequency
        ball.pulse_frequency = PULSE_FREQUENCY * random.uniform(0.8, 1.2) * beat_pulse_factor
        
        update_result = ball.update(dt)
        
        # Reset frequency to avoid drift
        ball.pulse_frequency = original_freq
        
        # Only remove balls if they're explicitly marked for removal and BALLS_CAN_DIE is True
        if not update_result or (ball.should_remove and BALLS_CAN_DIE):
            balls_to_remove_small.add(ball.id)

            # --- Pop Animation Effects ---
            pop_radius_factor = 1.5 + game_state.chaos_factor * 1.5 # Bigger pop later
            pop_radius_factor *= 1.0 + (beat_intensity - 0.5) * 0.4  # Modify with beat
            
            pop_particle_count = int(PARTICLE_COUNT_POP * (1 + game_state.chaos_factor * 1.5)) # More particles later
            pop_particle_count = int(pop_particle_count * (1.0 + (beat_intensity - 0.5) * 0.5))  # More with beat
            
            pop_particle_speed = PARTICLE_SPEED_MAX * (1.0 + game_state.chaos_factor) # Faster particles later
            pop_particle_speed *= 1.0 + (beat_intensity - 0.5) * 0.4  # Faster with beat
            
            pop_shake_intensity = game_state.get_current_value(INITIAL_SHAKE_INTENSITY, FINAL_SHAKE_INTENSITY) * 0.5
            pop_shake_intensity *= 1.0 + (beat_intensity - 0.5) * 0.6  # Stronger with beat

            game_state.effects.append(
                Effect(ball.position, pygame.Color('white'),
                      ball.radius * 0.5, ball.radius * pop_radius_factor,
                      POP_FLASH_DURATION, "flash")
            )
            game_state.effects.append(
                Effect(ball.position, ball.current_color,
                      ball.radius * 0.3, ball.radius * (pop_radius_factor * 0.8),
                      POP_FLASH_DURATION * 0.7, "flash")
            )
            spawn_particles(game_state.particles, ball.position,
                           pop_particle_count, ball.current_color,
                           PARTICLE_SPEED_MIN * 1.2, pop_particle_speed, 1.2)
            
            # Audio volume varies with beat
            pop_volume = POP_SOUND_VOLUME * (1 + game_state.chaos_factor*0.5)
            pop_volume *= 1.0 + (beat_intensity - 0.5) * 0.5
            audio_manager.play('collision', pop_volume, ball.position) # Louder pop later
            
            trigger_screen_shake(SHAKE_DURATION * 0.4, pop_shake_intensity)

        if ball.hit_wall_effect_info:
            info = ball.hit_wall_effect_info
            new_effects.append(
                Effect(info['pos'], info['color'], info['radius'] * 0.5, info['radius'] * 1.2, FLASH_DURATION * 0.6)
            )
            ball.hit_wall_effect_info = None

    # Handle ball-ball collisions
    balls_to_add, balls_to_remove_collision = handle_ball_collisions(game_state.balls, dt, beat_intensity)

    balls_to_remove = balls_to_remove_small.union(balls_to_remove_collision)

    if balls_to_remove:
        game_state.balls = [ball for ball in game_state.balls if ball.id not in balls_to_remove]

    if balls_to_add:
        game_state.balls.extend(balls_to_add)

    # Update particles and effects
    game_state.particles = [p for p in game_state.particles if p.update(dt)]
    game_state.effects.extend(new_effects)
    game_state.effects = [e for e in game_state.effects if e.update()]

    # Update screen shake
    update_screen_shake(dt)

    # Limit max balls
    if len(game_state.balls) > MAX_BALL_COUNT:
        # Remove smallest balls first
        game_state.balls.sort(key=lambda b: b.radius)
        num_to_remove = len(game_state.balls) - MAX_BALL_COUNT
        removed_ids = {ball.id for ball in game_state.balls[:num_to_remove]}
        game_state.balls = game_state.balls[num_to_remove:]

    # Add new balls periodically based on chaos factor
    current_spawn_rate = game_state.get_current_value(INITIAL_SPAWN_RATE, FINAL_SPAWN_RATE)
    
    # Make the spawn rate pulse with the beat
    spawn_rate_beat_modifier = 1.0 + (beat_intensity - 0.5) * 0.6  # Range from 0.7 to 1.3
    current_spawn_rate *= spawn_rate_beat_modifier
    
    if random.random() < current_spawn_rate and len(game_state.balls) < MAX_BALL_COUNT:
        spawn_fresh_ball()


def update_screen_shake(dt):
    """
    Update screen shake effect
    """
    game_state.current_screen_offset = pygame.Vector2(0, 0)
    if game_state.screen_shake_timer > 0:
        game_state.screen_shake_timer -= dt
        if game_state.screen_shake_timer > 0:
            # Scale intensity with chaos factor
            current_shake_intensity = game_state.get_current_value(INITIAL_SHAKE_INTENSITY, FINAL_SHAKE_INTENSITY)
            game_state.current_screen_offset.x = random.uniform(-current_shake_intensity, current_shake_intensity)
            game_state.current_screen_offset.y = random.uniform(-current_shake_intensity, current_shake_intensity)
        else:
            game_state.screen_shake_timer = 0


def create_initial_balls():
    """
    Create the initial set of balls
    """
    for _ in range(INITIAL_BALLS):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(CONTAINER_RADIUS * 0.2, CONTAINER_RADIUS * 0.7)
        pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
        vel_mag = random.uniform(250, 400) # Slightly lower initial velocity
        vel_angle = random.uniform(0, 2 * math.pi)
        vel = pygame.Vector2(math.cos(vel_angle), math.sin(vel_angle)) * vel_mag
        radius = random.uniform(MIN_RADIUS * 1.5, MAX_RADIUS * 0.8)

        from src.utilities import random_bright_color
        color = random_bright_color()
        game_state.balls.append(Ball(pos, vel, radius, color))

    # Ensure initial colors are somewhat different
    if len(game_state.balls) > 1:
        initial_merge_threshold = INITIAL_COLOR_DISTANCE_THRESHOLD # Use initial threshold for check
        for i in range(len(game_state.balls)):
            for j in range(i + 1, len(game_state.balls)):
                retries = 0
                while color_distance(game_state.balls[i].current_color,
                                    game_state.balls[j].current_color) < initial_merge_threshold and retries < 10:
                    new_color = random_bright_color(False)
                    game_state.balls[j].base_color = pygame.Color(new_color)
                    game_state.balls[j].current_color = pygame.Color(new_color)
                    try:
                        game_state.balls[j].hue = new_color.hsva[0]
                    except ValueError:
                        game_state.balls[j].hue = random.uniform(0, 360)
                        game_state.balls[j].current_color.hsva = (game_state.balls[j].hue, 100, 100, 100)
                    retries += 1


def spawn_fresh_ball(sync_to_beat=False):
    """
    Spawn a fresh ball with properties scaled by chaos_factor.
    
    Args:
        sync_to_beat: If True, increase the size and velocity to emphasize beat
    """
    from src.utilities import random_bright_color, generate_analogous_color

    chaos = game_state.chaos_factor
    beat_intensity = audio_manager.get_beat_intensity() if sync_to_beat else 0.5
    beat_modifier = 1.0 + (beat_intensity - 0.5) * 0.6  # Range from 0.7 to 1.3

    # Position: More random over time
    angle = random.uniform(0, 2 * math.pi)
    dist_factor = random.uniform(0.8 - chaos * 0.6, 0.95) # Spawn closer to center later
    dist = CONTAINER_RADIUS * dist_factor
    pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist

    # Velocity: Higher and more random over time
    vel_mag = random.uniform(200 + chaos * 300, 400 + chaos * 400)
    if sync_to_beat:
        vel_mag *= beat_modifier  # Faster on beat
        
    # Direction: More outward bias initially, more random later
    base_dir = (pos - CENTER).normalize() if dist > 10 else pygame.Vector2(math.cos(angle), math.sin(angle))
    random_dir = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
    # Lerp between outward and random based on chaos
    vel_dir = lerp_vector(base_dir, random_dir, chaos * 0.7) # 70% random at peak chaos
    vel = vel_dir.normalize() * vel_mag


    # Size: Generally larger over time
    radius = random.uniform(MIN_RADIUS * (1.5 + chaos), MAX_RADIUS * (0.6 + chaos * 0.3))
    if sync_to_beat:
        radius *= beat_modifier  # Larger on beat
        
    radius = max(MIN_RADIUS, min(MAX_RADIUS, radius)) # Clamp size

    # Color: More chance of analogous colors later
    if len(game_state.balls) > 0 and random.random() < chaos * 0.6: # 60% chance at peak chaos
        reference_ball = random.choice(game_state.balls)
        color = generate_analogous_color(reference_ball.current_color,
                                       random.uniform(10, 30 + chaos * 20)) # Wider angle later
    else:
        color = random_bright_color()

    ball = Ball(pos, vel, radius, color)

    # Spawn effects scaled by chaos and beat
    particle_count = int(10 + chaos*10)
    if sync_to_beat:
        particle_count = int(particle_count * beat_modifier)
        
    particle_speed = 150 + chaos*100
    if sync_to_beat:
        particle_speed *= beat_modifier
        
    spawn_particles(game_state.particles, pos, particle_count, color, 50, particle_speed)
    
    flash_size = radius * (1.5 + chaos*0.5)
    if sync_to_beat:
        flash_size *= beat_modifier
        
    game_state.effects.append(Effect(pos, pygame.Color('white'), radius * 0.5, flash_size, 0.3))

    game_state.balls.append(ball)


def lerp_vector(v1, v2, factor):
    """Linearly interpolate between two pygame Vectors."""
    factor = max(0.0, min(1.0, factor))
    return v1 * (1.0 - factor) + v2 * factor