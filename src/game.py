import pygame
import time
import random
from src.config import *
from src.audio import audio_manager
from src.entities import Particle
from src.utilities import random_bright_color
from src.physics import update_game_objects, create_initial_balls, spawn_fresh_ball
from src.game_state import game_state
import math

class GameRenderer:
    """Handles rendering for the game"""

    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        if self.font is None:
            self.font = pygame.font.SysFont("sans-serif", 24)

    def render_frame(self, current_time):
        self.screen.fill(BACKGROUND_COLOR)
        draw_offset = game_state.current_screen_offset

        container_alpha = 1
        if container_alpha > 0.01:
            container_color_val = int(15 + 30 * container_alpha)
            container_color = (container_color_val, int(10 + 25 * container_alpha), int(20 + 35 * container_alpha))
            container_width = max(1, int(1 + 2 * container_alpha))
            pygame.draw.circle(self.screen, container_color, CENTER + draw_offset, CONTAINER_RADIUS, container_width)

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
            info_text = f"FPS: {self.clock.get_fps():.1f} Balls: {len(game_state.balls)} Chaos: {game_state.chaos_factor:.2f}"
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

    def render_intro(self, intro_progress):
        self.screen.fill(BACKGROUND_COLOR)
        container_size = CONTAINER_RADIUS * min(1.0, intro_progress * 1.2)
        pygame.draw.circle(self.screen, (30, 20, 40), CENTER, container_size, 2)

        title_font = pygame.font.Font(None, 60)
        if title_font:
            title_alpha = min(255, int(255 * (intro_progress * 1.5)))
            title_text = "Physics Simulation"
            title_surf = title_font.render(title_text, True, (200, 200, 255))
            title_surf.set_alpha(title_alpha)
            self.screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, SCREEN_HEIGHT//3))

        if intro_progress > 0.5:
            subtitle_font = pygame.font.Font(None, 36)
            if subtitle_font:
                subtitle_alpha = min(255, int(255 * ((intro_progress - 0.5) * 2.0)))
                subtitle_text = "Starting simulation..."
                subtitle_surf = subtitle_font.render(subtitle_text, True, (150, 150, 200))
                subtitle_surf.set_alpha(subtitle_alpha)
                self.screen.blit(subtitle_surf, (SCREEN_WIDTH//2 - subtitle_surf.get_width()//2, SCREEN_HEIGHT//2))

        particle_chance = 0.2 + intro_progress * 0.4
        if random.random() < particle_chance:
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
                
                # Calculate physics step size (capped for stability)
                dt = frame_delta
                
                if game_state.intro_phase:
                    self._run_intro_phase(current_time, dt)
                else:
                    self._run_game_phase(current_time, dt)
                
                # Update display
                pygame.display.flip()
                
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


    def _run_game_phase(self, current_time, dt):
        elapsed_time = current_time - game_state.game_start_time
        update_game_objects(dt)

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

            # Minimal physics update during fade out to keep things moving a bit
            dt = min(1.0 / FPS, 0.05)  # Use a consistent dt
            update_game_objects(dt * (1.0 - ending_progress)) # Slow down physics

            # Render ending frame (which includes game state + fade)
            self.renderer.render_ending(ending_progress)
            
            # Update display
            pygame.display.flip()
            
            # Keep a stable framerate
            self.renderer.clock.tick(FPS)

            if ending_progress >= 1.0:
                ending_running = False
                game_state.running = False # Fully stop the game loop


    def _cleanup(self):
        print("Cleaning up...")
        audio_manager.cleanup()
        pygame.quit()


def run_game():
    game = Game()
    game.run()