import pygame
import math
import random
import time
from src.config import *
from src.entities import Ball, Effect
from src.utilities import color_distance, lerp_color, spawn_particles, trigger_screen_shake
from src.audio import audio_manager
from src.game_state import game_state

def handle_ball_collisions(balls, dt, elapsed_time):
    """
    Handle collisions between balls with merging and splitting behavior.
    
    Args:
        balls: List of Ball objects
        dt: Time delta in seconds
        elapsed_time: Current elapsed game time
        
    Returns:
        Tuple of (balls_to_add, balls_to_remove)
    """
    balls_to_add = []
    balls_to_remove = set()
    collision_pairs_processed = set()
    
    # Update game state phase and adaptive parameters
    game_state.update_phase(elapsed_time)
    game_state.update_adaptive_parameters()
    
    # Get current phase-based parameters
    collision_shrink_factor = game_state.current_collision_shrink_factor
    elasticity_base = game_state.current_elasticity_base
    elasticity_variance = game_state.current_elasticity_variance
    split_chance = game_state.current_split_chance
    merge_threshold = game_state.current_merge_threshold

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

                # 1. Resolve Overlap proportionally to inverse mass (lighter moves more)
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

                # 2. Collision Response with improved elasticity for bouncier collisions
                relative_velocity = ball_a.velocity - ball_b.velocity
                vel_along_normal = relative_velocity.dot(normal)

                if vel_along_normal < 0:
                    m1 = ball_a.mass if ball_a.mass > 1e-9 else 1e-9
                    m2 = ball_b.mass if ball_b.mass > 1e-9 else 1e-9
                    inv_mass1 = 1.0 / m1
                    inv_mass2 = 1.0 / m2

                    # Compute collision intensity based on relative velocity
                    impact_force = abs(vel_along_normal) / 2000.0  # Normalize to 0-1 range
                    impact_force = min(1.0, impact_force)  # Cap at 1.0
                    
                    # Use phase-based elasticity with variance for more unpredictable bounces
                    elasticity = elasticity_base + random.uniform(-elasticity_variance, elasticity_variance)
                    elasticity = max(0.9, min(1.3, elasticity))  # Constrain to reasonable values
                    
                    impulse_scalar = (-2.0 * elasticity * vel_along_normal) / (inv_mass1 + inv_mass2)
                    
                    # -- NEW: Reduce ball size on collision based on impact --
                    # Stronger impacts cause more reduction, harder in later phases
                    shrink_amount = impact_force * collision_shrink_factor * dt * 60
                    
                    # Ensure balls don't shrink below minimum size
                    ball_a.radius -= shrink_amount * ball_a.radius
                    ball_b.radius -= shrink_amount * ball_b.radius
                    
                    # Mark for removal if too small
                    if ball_a.radius < MIN_RADIUS:
                        ball_a.should_remove = True
                    if ball_b.radius < MIN_RADIUS:
                        ball_b.should_remove = True
                        
                    # Update mass after size change
                    ball_a.mass = BASE_DENSITY * ball_a.radius**2
                    ball_b.mass = BASE_DENSITY * ball_b.radius**2

                    impulse_vec = impulse_scalar * normal
                    ball_a.velocity += impulse_vec * inv_mass1
                    ball_b.velocity -= impulse_vec * inv_mass2
                    
                    # Add tangential velocity based on impact_force for more dynamic collisions
                    if random.random() < 0.25 + (impact_force * 0.5):  # Higher chance with stronger impacts
                        tangent = pygame.Vector2(-normal.y, normal.x)
                        # Smaller balls get more spin
                        spin_factor = 0.08 * (1.0 - (min(ball_a.radius, ball_b.radius) / MAX_RADIUS))
                        # Higher spin in later phases
                        phase_spin_bonus = 0.0
                        if game_state.current_phase == "BUILD":
                            phase_spin_bonus = 0.05
                        elif game_state.current_phase == "CHAOS":
                            phase_spin_bonus = 0.1
                        elif game_state.current_phase == "FINALE":
                            phase_spin_bonus = 0.15
                            
                        spin_factor += phase_spin_bonus
                        
                        ball_a.velocity += tangent * impulse_scalar * inv_mass1 * spin_factor * random.choice([-1, 1])
                        ball_b.velocity -= tangent * impulse_scalar * inv_mass2 * spin_factor * random.choice([-1, 1])

                    # --- Collision Effects with intensity scaling ---
                    contact_point = ball_b.position + normal * ball_b.radius
                    avg_radius = (ball_a.radius + ball_b.radius) * 0.5
                    try:
                        avg_color = lerp_color(ball_a.current_color, ball_b.current_color, 0.5)
                    except (TypeError, ValueError):
                        avg_color = pygame.Color('white')

                    # Sound effects based on impact
                    audio_volume = 0.5 + (impact_force * 0.5) # Scale volume with impact
                    audio_manager.play('collision', audio_volume, contact_point)
                    
                    # Flash size and duration based on impact
                    flash_size = avg_radius * (0.8 + (FLASH_RADIUS_FACTOR - 0.8) * impact_force)
                    flash_duration = FLASH_DURATION * (0.6 + (0.4 * impact_force))
                    game_state.effects.append(Effect(contact_point, pygame.Color('white'), 
                                                   avg_radius * 0.5, flash_size, flash_duration))
                    
                    # Scale particle count with impact
                    particle_count = int(PARTICLE_COUNT_COLLISION * (0.5 + (0.5 * impact_force)))
                    particle_speed = PARTICLE_SPEED_MAX * (0.6 + (0.4 * impact_force))
                    spawn_particles(game_state.particles, contact_point, particle_count, 
                                   avg_color, PARTICLE_SPEED_MIN * 0.5, particle_speed)
                    
                    # Screen shake based on impact
                    shake_intensity = SHAKE_INTENSITY * (0.3 + (0.7 * impact_force))
                    # Increase shake in later phases
                    if game_state.current_phase == "BUILD":
                        shake_intensity *= 1.2
                    elif game_state.current_phase == "CHAOS":
                        shake_intensity *= 1.5
                    elif game_state.current_phase == "FINALE":
                        shake_intensity *= 2.0
                        
                    trigger_screen_shake(SHAKE_DURATION * (0.3 + 0.3 * impact_force), shake_intensity)

                    # 3. Splitting or Merging Logic with phase-based probabilities
                    c_dist = color_distance(ball_a.current_color, ball_b.current_color)
                    
                    # --- MERGE Condition ---
                    if c_dist < merge_threshold:
                        collision_pairs_processed.add(pair_id)

                        # Calculate combined area with some loss
                        total_area = math.pi * ball_a.radius**2 + math.pi * ball_b.radius**2
                        area_loss = 0.02 + (0.05 * impact_force)  # Lose 2-7% area on merge
                        new_radius = math.sqrt(total_area * (1 - area_loss) / math.pi) * MERGE_AREA_FACTOR
                        new_radius = max(MIN_RADIUS, min(new_radius, MAX_RADIUS * 1.2))
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
                        audio_manager.play('collision', 1.1, new_pos)
                        game_state.effects.append(Effect(new_pos, pygame.Color('white'), 
                                                       new_radius, new_radius * 2.2, FLASH_DURATION * 1.5))
                        spawn_particles(game_state.particles, new_pos, PARTICLE_COUNT_SPLIT_MERGE, 
                                       avg_color, PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX, 1.5)
                        trigger_screen_shake(SHAKE_DURATION * 1.2, SHAKE_INTENSITY * 1.5)

                    # --- SPLIT Condition ---
                    else:
                        # Scale split chance with impact force
                        effective_split_chance = split_chance * (0.5 + (impact_force * 0.5))
                        
                        can_a_split = ball_a.radius >= MIN_SPLIT_RADIUS
                        can_b_split = ball_b.radius >= MIN_SPLIT_RADIUS
                        victim, other = None, None

                        if random.random() < effective_split_chance:
                            if can_a_split and can_b_split: 
                                # Prefer splitting the larger ball
                                if ball_a.radius > ball_b.radius:
                                    victim, other = ball_a, ball_b
                                elif ball_b.radius > ball_a.radius:
                                    victim, other = ball_b, ball_a
                                else:
                                    victim, other = random.choice([(ball_a, ball_b), (ball_b, ball_a)])
                            elif can_a_split: victim, other = ball_a, ball_b
                            elif can_b_split: victim, other = ball_b, ball_a

                            if victim:
                                victim_area = math.pi * victim.radius**2
                                # Higher mass loss in later phases
                                # Define mass loss factor for each phase
                                phase_mass_loss = {
                                    "CALM": 1.05,
                                    "BUILD": 1.15,
                                    "CHAOS": 1.25,
                                    "FINALE": 1.35
                                }
                                split_mass_loss = phase_mass_loss.get(game_state.current_phase, SPLIT_MASS_LOSS_FACTOR)
                                
                                # Additional mass loss based on impact force
                                split_mass_loss += impact_force * 0.2
                                
                                new_area_each = victim_area / (2.0 * split_mass_loss)

                                if new_area_each > 0:
                                    new_radius = math.sqrt(new_area_each / math.pi)
                                else:
                                    new_radius = MIN_RADIUS

                                if new_radius >= MIN_RADIUS:
                                    balls_to_remove.add(victim.id)
                                    collision_pairs_processed.add(pair_id)

                                    perp_normal = pygame.Vector2(-normal.y, normal.x) * random.choice([-1, 1])

                                    audio_manager.play('collision', 1.0, victim.position)
                                    game_state.effects.append(Effect(victim.position, victim.current_color,
                                                                    victim.radius, victim.radius * 1.8, 
                                                                    FLASH_DURATION * 1.2))
                                    spawn_particles(game_state.particles, victim.position, 
                                                   PARTICLE_COUNT_SPLIT_MERGE, victim.current_color, 
                                                   PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX * 1.2)
                                    trigger_screen_shake(SHAKE_DURATION, SHAKE_INTENSITY)

                                    for k in range(2):
                                        offset_dir = perp_normal if k == 0 else -perp_normal
                                        new_pos = victim.position + offset_dir * (new_radius * 1.1 + 2)

                                        # Increase velocity of split balls based on phase
                                        phase_vel_bonus = 1.0
                                        if game_state.current_phase == "BUILD":
                                            phase_vel_bonus = 1.2
                                        elif game_state.current_phase == "CHAOS":
                                            phase_vel_bonus = 1.4
                                        elif game_state.current_phase == "FINALE":
                                            phase_vel_bonus = 1.6
                                        
                                        vel_offset_magnitude = (victim.velocity.length() * 0.3 + 80) * phase_vel_bonus
                                        new_vel = victim.velocity + offset_dir * vel_offset_magnitude * random.uniform(0.9, 1.1)

                                        try:
                                            # Increase color variation in later phases
                                            color_variance = 0.1  # Base variance
                                            if game_state.current_phase == "BUILD":
                                                color_variance = 0.2
                                            elif game_state.current_phase == "CHAOS":
                                                color_variance = 0.3
                                            elif game_state.current_phase == "FINALE":
                                                color_variance = 0.4
                                                
                                            tint_factor = SPLIT_TINT_FACTOR + color_variance
                                            tinted_color = lerp_color(victim.current_color, 
                                                                     other.current_color, 
                                                                     tint_factor * random.uniform(0.8, 1.2))
                                        except (TypeError, ValueError):
                                            tinted_color = avg_color

                                        balls_to_add.append(Ball(new_pos, new_vel, new_radius, tinted_color))
    
    return balls_to_add, balls_to_remove


def update_game_objects(dt, elapsed_time=0):
    """
    Update all game objects
    
    Args:
        dt: Time delta in seconds
        elapsed_time: Current elapsed game time
    """
    # Update all balls and track which ones should be removed
    new_effects = []
    balls_to_remove_small = set()
    
    # Update game state phase and adaptive parameters if needed
    game_state.update_phase(elapsed_time)
    game_state.update_adaptive_parameters()
    
    # Apply gravity with phase-based strength
    gravity_strength = game_state.current_gravity_strength
    
    # Check explicitly for balls that are marked for removal or too small
    for ball in game_state.balls:
        # Update ball with current gravity strength
        ball.gravity_strength = gravity_strength
        
        # Update ball and check its return value - ball.update returns False when ball should be removed
        update_result = ball.update(dt)
        if not update_result or ball.should_remove or ball.radius < MIN_RADIUS:
            balls_to_remove_small.add(ball.id)
            
            # --- Enhanced Pop Animation Effects ---
            # 1. Create a flash at the ball's position
            game_state.effects.append(
                Effect(ball.position, pygame.Color('white'), 
                      ball.radius * 0.5, ball.radius * 2.5, 
                      POP_FLASH_DURATION, "flash")
            )
            
            # 2. Create a colored flash (using ball's color)
            game_state.effects.append(
                Effect(ball.position, ball.current_color, 
                      ball.radius * 0.3, ball.radius * 2.0, 
                      POP_FLASH_DURATION * 0.7, "flash")
            )
            
            # 3. Spawn particles that explode outward
            spawn_particles(game_state.particles, ball.position, 
                           PARTICLE_COUNT_POP, ball.current_color, 
                           PARTICLE_SPEED_MIN * 1.5, PARTICLE_SPEED_MAX * 1.5, 1.2)
            
            # 4. Play pop sound
            audio_manager.play('collision', POP_SOUND_VOLUME, ball.position)
            
            # 5. Add a small screen shake
            trigger_screen_shake(SHAKE_DURATION * 0.4, SHAKE_INTENSITY * 0.5)
        
        # Check for wall hit effect trigger after update
        if ball.hit_wall_effect_info:
            info = ball.hit_wall_effect_info
            new_effects.append(
                Effect(info['pos'], info['color'], info['radius'] * 0.5, info['radius'] * 1.2, FLASH_DURATION * 0.6)
            )
            ball.hit_wall_effect_info = None

    # Handle ball-ball collisions and update ball list
    balls_to_add, balls_to_remove_collision = handle_ball_collisions(game_state.balls, dt, elapsed_time)
    
    # Combine both sets of balls to remove
    balls_to_remove = balls_to_remove_small.union(balls_to_remove_collision)
    
    # Remove balls marked for removal
    if balls_to_remove:
        game_state.balls = [ball for ball in game_state.balls if ball.id not in balls_to_remove]
        
    # Add new balls from collisions
    if balls_to_add:
        game_state.balls.extend(balls_to_add)

    # Update particles and remove dead ones
    game_state.particles = [p for p in game_state.particles if p.update(dt)]

    # Update effects and remove finished ones
    game_state.effects.extend(new_effects)
    game_state.effects = [e for e in game_state.effects if e.update()]
    
    # Update screen shake
    update_screen_shake(dt)
    
    # Limit max balls for performance
    if len(game_state.balls) > MAX_BALL_COUNT:
        game_state.balls.sort(key=lambda b: b.radius)
        excess = len(game_state.balls) - MAX_BALL_COUNT
        game_state.balls = game_state.balls[excess:]
    
    # Add new balls periodically in later phases to maintain excitement
    if game_state.current_phase == "BUILD" and random.random() < 0.01:
        if len(game_state.balls) < MAX_BALL_COUNT * 0.3:  # Only add if we're below 80% capacity
            # Add occasional fresh balls to keep the simulation dynamic
            spawn_fresh_ball(elapsed_time)
    if game_state.current_phase == "CHAOS" and random.random() < 0.01:
        if len(game_state.balls) < MAX_BALL_COUNT * 0.5:  # Only add if we're below 80% capacity
            # Add occasional fresh balls to keep the simulation dynamic
            spawn_fresh_ball(elapsed_time)

    if game_state.current_phase == "FINALE" and random.random() < 0.01:
        if len(game_state.balls) < MAX_BALL_COUNT * 0.8:  # Only add if we're below 80% capacity
            # Add occasional fresh balls to keep the simulation dynamic
            spawn_fresh_ball(elapsed_time)



def update_screen_shake(dt):
    """
    Update screen shake effect
    
    Args:
        dt: Time delta in seconds
    """
    # Clear previous offset
    game_state.current_screen_offset = pygame.Vector2(0, 0)
    
    # Apply screen shake if timer is active
    if game_state.screen_shake_timer > 0:
        game_state.screen_shake_timer -= dt
        if game_state.screen_shake_timer > 0:
            # Simple shake: random offset based on intensity
            game_state.current_screen_offset.x = random.uniform(-SHAKE_INTENSITY, SHAKE_INTENSITY)
            game_state.current_screen_offset.y = random.uniform(-SHAKE_INTENSITY, SHAKE_INTENSITY)
        else:
            game_state.screen_shake_timer = 0


def create_initial_balls():
    """
    Create the initial set of balls for the simulation
    """
    for _ in range(INITIAL_BALLS):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(CONTAINER_RADIUS * 0.2, CONTAINER_RADIUS * 0.7)
        pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
        vel_mag = random.uniform(350, 500)  # Much higher initial velocities for dynamic movement
        vel_angle = random.uniform(0, 2 * math.pi)
        vel = pygame.Vector2(math.cos(vel_angle), math.sin(vel_angle)) * vel_mag
        radius = random.uniform(MIN_RADIUS * 1.5, MAX_RADIUS * 0.8)
        
        # Use the enhanced color generation - sometimes using full spectrum 
        from src.utilities import random_bright_color
        color = random_bright_color()
        game_state.balls.append(Ball(pos, vel, radius, color))
    
    # Ensure initial colors are different enough
    if len(game_state.balls) > 1:
        for i in range(len(game_state.balls)):
            for j in range(i + 1, len(game_state.balls)):
                while color_distance(game_state.balls[i].current_color, 
                                    game_state.balls[j].current_color) < COLOR_DISTANCE_THRESHOLD:
                    # If colors are too similar, generate a new color for the second ball
                    new_color = random_bright_color(False)  # Force full spectrum color
                    game_state.balls[j].base_color = pygame.Color(new_color)
                    game_state.balls[j].current_color = pygame.Color(new_color)
                    try:
                        game_state.balls[j].hue = new_color.hsva[0]
                    except ValueError:
                        game_state.balls[j].hue = random.uniform(0, 360)
                        game_state.balls[j].current_color.hsva = (game_state.balls[j].hue, 100, 100, 100)


def trigger_finale():
    """Trigger the finale sequence with a burst of new balls"""
    if game_state.finale_triggered:
        return
        
    game_state.finale_triggered = True
    audio_manager.play('end', 1.0)
    
    # Create a burst of balls with special colors
    finale_colors = []
    # Generate a consistent color palette for the finale
    from src.utilities import random_bright_color, generate_complementary_color, generate_color_palette
    
    # Create base colors that will work well together
    base_color = random_bright_color()
    finale_palette = generate_color_palette(base_color, 8)
    
    for i in range(FINALE_BALLS_COUNT):
        angle = random.uniform(0, 2 * math.pi)
        # Position balls in a ring or spiral pattern
        dist_factor = i / FINALE_BALLS_COUNT
        dist = CONTAINER_RADIUS * (0.1 + 0.8 * dist_factor)
        pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
        
        # Give them velocities that create interesting patterns
        vel_factor = 1.0 - dist_factor  # Inverse velocity (faster for inner balls)
        vel_mag = 100 + vel_factor * 300
        # Use either tangential or radial velocities
        if i % 2 == 0:  # Tangential (creates swirl)
            vel = pygame.Vector2(-math.sin(angle), math.cos(angle)) * vel_mag
        else:  # Radial (creates explosion/implosion)
            vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * vel_mag
            
        radius = FINALE_MIN_RADIUS + dist_factor * (FINALE_MAX_RADIUS - FINALE_MIN_RADIUS)
        # Use colors from our palette for more cohesive look
        color = finale_palette[i % len(finale_palette)]
        game_state.balls.append(Ball(pos, vel, radius, color))
        
        # Spawn particles for dramatic effect
        spawn_particles(game_state.particles, pos, 10, color, PARTICLE_SPEED_MIN * 1.5, PARTICLE_SPEED_MAX * 1.5)
    
    # Big screen shake for finale
    trigger_screen_shake(SHAKE_DURATION * 2, SHAKE_INTENSITY * 1.5)


def spawn_fresh_ball(elapsed_time):
    """
    Spawn a fresh ball with properties appropriate for the current phase
    
    Args:
        elapsed_time: Current elapsed time for phase-appropriate properties
    """
    from src.utilities import random_bright_color
    
    # Determine phase-appropriate properties
    phase = game_state.current_phase
    
    # Ball position - spawn near the edge in early phases, more random in later phases
    if phase == "CALM" or phase == "BUILD":
        # Spawn near the edge with inward velocity for early phases
        angle = random.uniform(0, 2 * math.pi)
        dist_factor = random.uniform(0.8, 0.95)  # Near the edge
        dist = CONTAINER_RADIUS * dist_factor
        pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
        
        # Velocity pointing inward with moderate speed
        vel_mag = random.uniform(200, 400)
        # Mostly inward but with some tangential component
        inward_dir = (CENTER - pos).normalize()
        tangent_dir = pygame.Vector2(-inward_dir.y, inward_dir.x)
        # Mix of inward (80%) and tangential (20%) for some initial spin
        vel_dir = inward_dir * 0.8 + tangent_dir * 0.2 * random.choice([-1, 1])
        vel = vel_dir.normalize() * vel_mag
        
    else:  # CHAOS or FINALE
        # More random position for chaotic phases
        angle = random.uniform(0, 2 * math.pi)
        dist_factor = random.uniform(0.3, 0.9)  # Anywhere in the container
        dist = CONTAINER_RADIUS * dist_factor
        pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
        
        # Higher velocity with more random direction
        vel_mag = random.uniform(400, 700)
        vel_angle = random.uniform(0, 2 * math.pi)  # Random direction
        vel = pygame.Vector2(math.cos(vel_angle), math.sin(vel_angle)) * vel_mag
    
    # Size - smaller in early phases, larger in later phases
    if phase == "CALM":
        radius = random.uniform(MIN_RADIUS * 1.5, MAX_RADIUS * 0.6)
    elif phase == "BUILD":
        radius = random.uniform(MIN_RADIUS * 1.5, MAX_RADIUS * 0.7)
    elif phase == "CHAOS":
        radius = random.uniform(MIN_RADIUS * 2, MAX_RADIUS * 0.8)
    else:  # FINALE
        radius = random.uniform(MIN_RADIUS * 2, MAX_RADIUS * 0.9)
    
    # Color - use complementary colors in later phases for more interesting merges/splits
    if phase == "CALM" or phase == "BUILD":
        color = random_bright_color()
    else:
        # In chaos phase, sometimes use colors similar to existing balls
        if len(game_state.balls) > 0 and random.random() < 0.5:
            # Pick a random existing ball and get a color close to it
            from src.utilities import generate_analogous_color
            reference_ball = random.choice(game_state.balls)
            color = generate_analogous_color(reference_ball.current_color, 
                                           random.uniform(10, 40))
        else:
            color = random_bright_color()
    
    # Create the ball
    ball = Ball(pos, vel, radius, color)
    
    # Add effects for the spawn
    spawn_particles(game_state.particles, pos, 15, color, 50, 150)
    game_state.effects.append(Effect(pos, pygame.Color('white'), radius * 0.5, radius * 2, 0.3))
    
    # Add to game state
    game_state.balls.append(ball)