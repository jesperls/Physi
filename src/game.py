import pygame
import time
import random
from src.config import *
from src.audio import audio_manager
from src.entities import Particle, Effect
from src.utilities import random_bright_color, spawn_particles, trigger_screen_shake
from src.physics import update_game_objects, create_initial_balls, spawn_fresh_ball
from src.game_state import game_state
from src.recording import recorder
import math

# Create a special effect class to use for beat effects
class BeatEffect(Effect):
    """Special effect that matches the Effect update signature but uses Particle visuals"""
    
    def __init__(self, position, velocity, color, lifespan, radius):
        super().__init__(position, color, radius, radius, lifespan)
        self.velocity = pygame.Vector2(velocity)
        self.start_radius = radius
        self.start_time = time.time()
        self.lifespan = lifespan
    
    def update(self):
        # Move based on velocity
        current_time = time.time()
        dt = current_time - self.start_time - self.last_update_time if hasattr(self, 'last_update_time') else 0.016
        self.last_update_time = current_time - self.start_time
        
        self.position += self.velocity * dt
        self.velocity *= 0.98  # Slight drag
        
        # Return True if the effect is still alive
        return (current_time - self.start_time) < self.lifespan
    
    def draw(self, surface, offset):
        current_time = time.time()
        elapsed = current_time - self.start_time
        progress = min(1.0, elapsed / self.lifespan)
        current_alpha = int(255 * (1 - progress**2))
        if current_alpha <= 0: return

        part_color = self.color[:3] + (current_alpha,)
        int_radius = int(self.start_radius)

        try:
            temp_surf = pygame.Surface((int_radius * 2, int_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surf, part_color, (int_radius, int_radius), int_radius)
            surface.blit(temp_surf,
                        (self.position.x - int_radius + offset.x, self.position.y - int_radius + offset.y),
                        special_flags=pygame.BLEND_RGBA_ADD)
        except (pygame.error, ValueError):
            return

class GameRenderer:
    """Handles rendering for the game"""

    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        if self.font is None:
            self.font = pygame.font.SysFont("sans-serif", 24)
        
        # Audio visualization
        self.beat_pulse = 0.0
        self.beat_fade_speed = 5.0
        self.container_pulse = 0.0
        self.last_beat_time = 0

    def render_frame(self, current_time):
        self.screen.fill(BACKGROUND_COLOR)
        draw_offset = game_state.current_screen_offset
        
        # Update beat visualization
        self.beat_pulse = max(0, self.beat_pulse - self.clock.get_time() / 1000.0 * self.beat_fade_speed)
        beat_intensity = audio_manager.get_beat_intensity()
        
        # Make container react to music
        container_alpha = 1.0 + beat_intensity * 0.5
        container_pulse_size = CONTAINER_RADIUS * (1.0 + self.beat_pulse * 0.03)
        if container_alpha > 0.01:
            # Base color that pulses with the beat
            base_intensity = 15 + int(beat_intensity * 20)
            r = base_intensity + int(self.beat_pulse * 50)
            g = int(10 + beat_intensity * 15) + int(self.beat_pulse * 20)
            b = int(20 + beat_intensity * 25) + int(self.beat_pulse * 30)
            container_color = (min(255, r), min(255, g), min(255, b))
            container_width = max(1, int(1 + 2 * container_alpha))
            pygame.draw.circle(self.screen, container_color, CENTER + draw_offset, 
                             container_pulse_size, container_width)

        for particle in game_state.particles:
            particle.draw(self.screen, draw_offset)
        for ball in game_state.balls:
             ball.draw(self.screen, current_time, draw_offset)
        for effect in game_state.effects:
             effect.draw(self.screen, draw_offset)

        if not game_state.intro_phase:
            self._draw_ui()

    def _draw_ui(self):
        try:
            # Add BPM info to the UI
            rhythm_info = audio_manager.get_rhythm_info()
            info_text = f"FPS: {self.clock.get_fps():.1f} Balls: {len(game_state.balls)} Chaos: {game_state.chaos_factor:.2f}"
            # if rhythm_info['bpm'] > 0:
            #     info_text += f" BPM: {rhythm_info['bpm']}"
                
            info_surf = self.font.render(info_text, True, pygame.Color('gray'))
            self.screen.blit(info_surf, (10, 10))

            if game_state.game_start_time > 0:
                elapsed_time = time.time() - game_state.game_start_time
                time_remaining = MAX_GAME_DURATION - elapsed_time
                if time_remaining > -5: # Show for a bit after 0
                    time_text = f"Time: {max(0, int(time_remaining))}s"
                    time_surf = self.font.render(time_text, True, pygame.Color('gray'))
                    self.screen.blit(time_surf, (SCREEN_WIDTH - time_surf.get_width() - 10,
                                                SCREEN_HEIGHT - time_surf.get_height() - 10))
        except pygame.error as e:
            print(f"Error rendering font: {e}")
            
    def on_beat_detected(self):
        """React to beat detection with visual cues"""
        # Strong pulse when a beat is detected
        self.beat_pulse = 1.0
        self.last_beat_time = time.time()
        
        # Container pulse animation gets boosted on beats
        self.container_pulse = 1.0

    def render_intro(self, intro_progress):
        self.screen.fill(BACKGROUND_COLOR)
        
        # Make container pulse with music during intro
        beat_intensity = audio_manager.get_beat_intensity()
        container_pulse = beat_intensity * 0.1
        container_size = CONTAINER_RADIUS * min(1.0, intro_progress * 1.2) * (1.0 + container_pulse)
        
        # Pulse container color with the beat
        base_r, base_g, base_b = 30, 20, 40
        pulse_factor = beat_intensity * 0.5
        container_color = (
            int(base_r + pulse_factor * 40),
            int(base_g + pulse_factor * 20),
            int(base_b + pulse_factor * 30)
        )
        
        pygame.draw.circle(self.screen, container_color, CENTER, container_size, 2)

        title_font = pygame.font.Font(None, 60)
        if title_font:
            title_alpha = min(255, int(255 * (intro_progress * 1.5)))
            title_text = "Physics Simulation"
            title_surf = title_font.render(title_text, True, (200, 200, 255))
            title_surf.set_alpha(title_alpha)
            
            # Add slight title movement with the beat
            title_offset_y = math.sin(time.time() * 3) * beat_intensity * 5
            self.screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, 
                                        SCREEN_HEIGHT//3 + title_offset_y))

        if intro_progress > 0.5:
            subtitle_font = pygame.font.Font(None, 36)
            if subtitle_font:
                subtitle_alpha = min(255, int(255 * ((intro_progress - 0.5) * 2.0)))
                subtitle_text = "Starting simulation..."
                subtitle_surf = subtitle_font.render(subtitle_text, True, (150, 150, 200))
                subtitle_surf.set_alpha(subtitle_alpha)
                self.screen.blit(subtitle_surf, (SCREEN_WIDTH//2 - subtitle_surf.get_width()//2, SCREEN_HEIGHT//2))

        # Create particles timed with the beat
        particle_chance = 0.2 + intro_progress * 0.4
        beat_boost = beat_intensity * 0.3  # Boost particle generation on beats
        
        if random.random() < (particle_chance + beat_boost):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(CONTAINER_RADIUS, CONTAINER_RADIUS * 1.2)
            pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
            vel = (CENTER - pos).normalize() * random.uniform(100, 200)
            color = random_bright_color()
            game_state.particles.append(Particle(pos, vel, color, 1.0, 3))

        game_state.particles = [p for p in game_state.particles if p.update(1/60)]
        for particle in game_state.particles:
            particle.draw(self.screen, pygame.Vector2(0, 0))

        if intro_progress > 0.8 and len(game_state.balls) == 0:
            create_initial_balls() # Create balls hidden

        if intro_progress > 0.9:
            fade_factor = max(0, (1.0 - intro_progress) / 0.1)
            fade_alpha = int(255 * fade_factor)
            if fade_alpha > 0:
                fade_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                fade_surf.fill((5, 0, 10, fade_alpha))
                self.screen.blit(fade_surf, (0, 0))

    def render_ending(self, ending_progress):
        self.render_frame(time.time())

        # Apply fade overlay
        fade_alpha = min(255, int(255 * ending_progress * 1.5)) # Faster fade
        fade_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade_surf.fill(BACKGROUND_COLOR)
        fade_surf.set_alpha(fade_alpha)
        self.screen.blit(fade_surf, (0, 0))

        title_font = pygame.font.Font(None, 60)
        if title_font:
            if ending_progress > 0.2 and ending_progress < 0.9:
                text_alpha = min(255, int(255 * math.sin(math.pi * (ending_progress - 0.2) / 0.7))) # Sine fade in/out
                text = "Simulation Complete"
                text_surf = title_font.render(text, True, (200, 200, 255))
                text_surf.set_alpha(text_alpha)
                self.screen.blit(text_surf, (SCREEN_WIDTH//2 - text_surf.get_width()//2, SCREEN_HEIGHT//2 - 40))


class Game:
    """Main game class"""

    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = pygame.DOUBLEBUF
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Physics Simulation")

        self.renderer = GameRenderer(self.screen)
        audio_manager.initialize()
        game_state.reset()
        game_state.intro_start_time = time.time()
        recorder.start_recording()
        
        # Beat-related state
        self.last_beat_time = 0
        self.beat_particle_cooldown = 0
        self.next_beat_particle_time = 0

    def run(self):
        try:
            last_frame_time = time.time()
            
            while game_state.running:
                # Handle events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        game_state.running = False
                        
                # Calculate frame timing
                current_time = time.time()
                frame_delta = current_time - last_frame_time
                last_frame_time = current_time
                
                # Update audio analysis and detect beats
                beat_detected = audio_manager.update()
                
                if beat_detected:
                    self._on_beat_detected()
                
                # Calculate physics step size (capped for stability)
                dt = frame_delta
                
                if game_state.intro_phase:
                    self._run_intro_phase(current_time, dt)
                else:
                    self._run_game_phase(current_time, dt, beat_detected)
                
                # Update display
                pygame.display.flip()
                
                # Capture frame for recording if active
                if game_state.recording:
                    recorder.capture_frame(self.screen)
                
                # Regulate framerate
                self.renderer.clock.tick(FPS)

            self._cleanup()

        except KeyboardInterrupt:
            self._cleanup()
        # Ensure cleanup runs even on other errors
        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup()

    def _on_beat_detected(self):
        """Handle beat detection with visual effects"""
        # Notify renderer of beat
        self.renderer.on_beat_detected()
        self.last_beat_time = time.time()
        
        # Create beat-synchronized particles
        self._create_beat_particles()
        
        # Random chance to spawn a new ball on beat
        chaos = game_state.chaos_factor
        if random.random() < (0.1 + chaos * 0.2) and len(game_state.balls) < MAX_BALL_COUNT:
            spawn_fresh_ball(sync_to_beat=True)
            
        # Add small screen shake on strong beats
        if random.random() < 0.3:
            intensity = 2 + game_state.chaos_factor * 5
            trigger_screen_shake(0.1, intensity)
        
        # Apply velocity boost to balls timed with the beat
        self._apply_beat_velocity_boost()
    
    def _create_beat_particles(self):
        """Create particles that sync with the beat"""
        # Skip if on cooldown
        current_time = time.time()
        if current_time < self.next_beat_particle_time:
            return
            
        # Set a cooldown to avoid too many particles
        self.next_beat_particle_time = current_time + 0.1
        
        # Create burst of particles from center
        chaos = game_state.chaos_factor
        particle_count = int(5 + chaos * 10)
        
        for _ in range(particle_count):
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(50, CONTAINER_RADIUS * 0.8)
            pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
            
            # Velocity points outward from center with beat timing
            vel_magnitude = 100 + random.uniform(0, 200) * (1 + chaos * 0.5)
            vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * vel_magnitude
            
            # Create bright particle with longer life
            color = random_bright_color()
            lifespan = 0.5 + random.uniform(0, 0.5)
            radius = 2 + random.uniform(0, 3)
            
            game_state.particles.append(Particle(pos, vel, color, lifespan, radius))
    
    def _apply_beat_velocity_boost(self):
        """Apply a velocity boost to balls timed with the beat"""
        if not game_state.balls:
            return
            
        chaos = game_state.chaos_factor
        
        # Apply boost to random balls
        boost_count = max(1, int(len(game_state.balls) * (0.2 + chaos * 0.3)))
        boost_balls = random.sample(game_state.balls, min(boost_count, len(game_state.balls)))
        
        for ball in boost_balls:
            # Calculate boost direction (random with slight bias toward center)
            center_dir = (CENTER - ball.position).normalize()
            random_dir = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
            
            # Blend between random and center directions
            blend = random.uniform(0.2, 0.8)
            boost_dir = center_dir * blend + random_dir * (1 - blend)
            boost_dir = boost_dir.normalize()
            
            # Apply velocity boost based on chaos level
            boost_magnitude = 50 + random.uniform(0, 150) * (1 + chaos)
            ball.velocity += boost_dir * boost_magnitude
            
            # Create a visual effect at the ball's position using our compatible BeatEffect class
            game_state.effects.append(
                BeatEffect(ball.position, ball.velocity * 0.2, ball.current_color, 0.3, ball.radius * 1.5)
            )

    def _run_intro_phase(self, current_time, dt):
        # Handle any additional events in the intro phase
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_state.running = False
                return
                
        intro_progress = (current_time - game_state.intro_start_time) / INTRO_DURATION

        if intro_progress > (1.0 - INTRO_FADE_OVERLAP) and len(game_state.balls) > 0:
            transition_factor = (intro_progress - (1.0 - INTRO_FADE_OVERLAP)) / INTRO_FADE_OVERLAP
            reduced_dt = dt * transition_factor
            # Only update physics minimally during fade-in
            for ball in game_state.balls:
                ball.update(reduced_dt * 0.2) # Very slow update initially

        if intro_progress >= 1.0:
            game_state.intro_phase = False
            game_state.game_start_time = current_time
            # audio_manager.play('start', 1.0)
            if len(game_state.balls) == 0:
                create_initial_balls() # Ensure balls exist
        else:
            self.renderer.render_intro(intro_progress)


    def _run_game_phase(self, current_time, dt, beat_detected):
        elapsed_time = current_time - game_state.game_start_time
        
        # Apply beat-influenced physics updates
        beat_intensity = audio_manager.get_beat_intensity()
        
        # Vary time scale slightly with beat to create rhythmic motion
        beat_time_scale = 1.0 + (beat_intensity - 0.5) * 0.2  # Range from 0.9 to 1.1
        dt_scaled = dt * beat_time_scale
        
        update_game_objects(dt_scaled, beat_intensity)

        # Check for end of game based on duration
        if elapsed_time >= MAX_GAME_DURATION and game_state.running:
             if elapsed_time >= MAX_GAME_DURATION:
                 self._run_ending_sequence(current_time)
                 return # Exit after starting ending sequence

        # Render the game
        self.renderer.render_frame(current_time)


    def _run_ending_sequence(self, current_time):
        # End simulation smoothly
        ending_duration = 3.0
        ending_start_time = time.time() # Use current time as start
        ending_running = True

        # audio_manager.play('end', 1.0) # Play end sound

        while ending_running and game_state.running:
            # Handle events to prevent freezing
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    ending_running = False
                    game_state.running = False
                        
            ending_elapsed = time.time() - ending_start_time
            ending_progress = min(1.0, ending_elapsed / ending_duration)

            # Update audio analysis
            beat_detected = audio_manager.update()
            
            # Minimal physics update during fade out to keep things moving a bit
            dt = min(1.0 / FPS, 0.05)  # Use a consistent dt
            
            # Apply beat influence even in the ending
            beat_intensity = audio_manager.get_beat_intensity()
            beat_time_scale = 1.0 + (beat_intensity - 0.5) * 0.2

            # Fade out all audio using a cosine curve for smooth transition
            fade_factor = math.cos(ending_progress * math.pi * 0.5)  # Smooth fade from 1 to 0
            audio_manager.set_master_volume(fade_factor)
            
            update_game_objects(dt * (1.0 - ending_progress) * beat_time_scale, beat_intensity) # Slow down physics

            # Render ending frame (which includes game state + fade)
            self.renderer.render_ending(ending_progress)
            
            # Update display
            pygame.display.flip()
            
            if game_state.recording:
                recorder.capture_frame(self.screen)
            
            # Keep a stable framerate
            self.renderer.clock.tick(FPS)

            if ending_progress >= 1.0:
                ending_running = False
                game_state.running = False # Fully stop the game loop


    def _cleanup(self):
        print("Cleaning up...")
        # Stop recording if it's active
        if game_state.recording:
            print("Finalizing recording...")
            recorder.stop_recording()
        audio_manager.cleanup()
        pygame.quit()


def run_game():
    game = Game()
    game.run()