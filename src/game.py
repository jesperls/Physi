import pygame
import cv2
import time
import numpy as np
import random
from datetime import datetime
from src.config import *
from src.audio import audio_manager
from src.entities import Ball, Particle, Effect
from src.utilities import random_bright_color, spawn_particles, trigger_screen_shake
from src.physics import update_game_objects, create_initial_balls, trigger_finale, spawn_fresh_ball
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
            
    def setup_video_recording(self):
        """Set up video recording with proper framerate and quality settings"""
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        game_state.video_filename = f"physics_simulation_{timestamp}.mp4"
        
        # Use h264 codec for better quality and compatibility
        # Switch to mp4v codec which has better compatibility
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4 codec
        
        # Fix the video framerate to 60fps for consistent playback regardless of game FPS
        # This helps solve the weird playback speed issues at high FPS values
        video_fps = 60
        
        game_state.video_writer = cv2.VideoWriter(
            game_state.video_filename, fourcc, video_fps, (SCREEN_WIDTH, SCREEN_HEIGHT))
        
        # Set recording flag
        game_state.recording = True
        print(f"Recording video to: {game_state.video_filename} at {video_fps} FPS (fixed rate)")
        
    def render_frame(self, current_time):
        """Render a complete frame"""
        # Clear the screen
        self.screen.fill(BACKGROUND_COLOR)
        
        # Get the screen shake offset for this frame
        draw_offset = game_state.current_screen_offset
            
        # Draw container circle with pulsing effect
        container_color = (15, 10, 20)  # Base color
        
        # If in game mode (not intro), handle container visibility based on elapsed time
        if not game_state.intro_phase and game_state.game_start_time > 0:
            elapsed_time = time.time() - game_state.game_start_time
            if elapsed_time < 5.0:
                # Make container more visible during early phase
                pulse_factor = 1.0 - (elapsed_time / 5.0)
                container_color = (
                    min(255, int(15 + 40 * pulse_factor)),
                    min(255, int(10 + 30 * pulse_factor)),
                    min(255, int(20 + 50 * pulse_factor))
                )
                container_width = max(3, int(3 * (3.0 - elapsed_time / 5.0)))
            else:
                container_width = 3
        else:
            # During intro, always show container more prominently
            container_width = 4
            
        pygame.draw.circle(self.screen, container_color, CENTER + draw_offset, CONTAINER_RADIUS, container_width)

        # Draw particles (behind balls)
        for particle in game_state.particles:
            particle.draw(self.screen, draw_offset)

        # Draw all balls
        for ball in game_state.balls:
             ball.draw(self.screen, current_time, draw_offset)

        # Draw effects (on top)
        for effect in game_state.effects:
             effect.draw(self.screen, draw_offset)
             
        # Draw UI if in game mode (not intro)
        if not game_state.intro_phase:
            self._draw_ui()
                
    def _draw_ui(self):
        """Draw game UI overlay"""
        try:
            # FPS/Ball count info in top-left
            info_text = f"FPS: {self.clock.get_fps():.1f} Balls: {len(game_state.balls)} Particles: {len(game_state.particles)}"
            info_surf = self.font.render(info_text, True, pygame.Color('gray'))
            self.screen.blit(info_surf, (10, 10))
            
            # Time indicator at bottom
            if game_state.game_start_time > 0:
                elapsed_time = time.time() - game_state.game_start_time
                time_remaining = MAX_GAME_DURATION - elapsed_time
                if time_remaining > 0:
                    time_text = f"Time: {int(time_remaining)}s"
                    time_surf = self.font.render(time_text, True, pygame.Color('gray'))
                    self.screen.blit(time_surf, (SCREEN_WIDTH - time_surf.get_width() - 10, 
                                                SCREEN_HEIGHT - time_surf.get_height() - 10))
        except pygame.error as e:
            print(f"Error rendering font: {e}")
            
    def render_intro(self, intro_progress):
        """
        Render intro animation with improved transitions
        
        Args:
            intro_progress: Progress value from 0.0 to 1.0
        """
        # Fill background
        self.screen.fill(BACKGROUND_COLOR)
        
        # Draw container with pulsing effect
        container_size = CONTAINER_RADIUS * min(1.0, intro_progress * 1.2)  # Grow slightly faster
        pygame.draw.circle(self.screen, (30, 20, 40), CENTER, container_size, 2)
        
        # Draw title text that fades in
        title_font = pygame.font.Font(None, 60)
        if title_font:
            title_alpha = min(255, int(255 * (intro_progress * 1.5)))
            title_text = "Neon Physics Simulation"
            title_surf = title_font.render(title_text, True, (200, 200, 255))
            title_surf.set_alpha(title_alpha)
            self.screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, SCREEN_HEIGHT//3))
        
        # Draw "Starting..." text
        if intro_progress > 0.5:  # Show earlier for smoother transition
            subtitle_font = pygame.font.Font(None, 36)
            if subtitle_font:
                subtitle_alpha = min(255, int(255 * ((intro_progress - 0.5) * 2.0)))  # Faster fade-in
                subtitle_text = "Starting simulation..."
                subtitle_surf = subtitle_font.render(subtitle_text, True, (150, 150, 200))
                subtitle_surf.set_alpha(subtitle_alpha)
                self.screen.blit(subtitle_surf, (SCREEN_WIDTH//2 - subtitle_surf.get_width()//2, SCREEN_HEIGHT//2))
        
        # Add more particles as intro progresses for better transition to game
        particle_chance = 0.2 + intro_progress * 0.4  # Increase particle rate near end
        if random.random() < particle_chance:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(CONTAINER_RADIUS, CONTAINER_RADIUS * 1.2)
            pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
            vel = (CENTER - pos).normalize() * random.uniform(100, 200)
            color = random_bright_color()
            game_state.particles.append(Particle(pos, vel, color, 1.0, 3))
        
        # Update and draw particles
        game_state.particles = [p for p in game_state.particles if p.update(1/60)]
        for particle in game_state.particles:
            particle.draw(self.screen, pygame.Vector2(0, 0))
            
        # If intro is ending, start generating the balls early but don't show them
        # This helps create a smoother transition to the simulation
        if intro_progress > 0.8 and len(game_state.balls) == 0:
            # Create balls off-screen to prepare for transition
            create_initial_balls()
            
        # Semi-transparent overlay that fades out at the end for smooth transition
        if intro_progress > 0.9:
            fade_factor = max(0, (1.0 - intro_progress) / 0.1)  # 1.0 at prog=0.9, 0.0 at prog=1.0
            fade_alpha = int(255 * fade_factor)
            if fade_alpha > 0:
                fade_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                fade_surf.fill((5, 0, 10, fade_alpha))  # Match background color with alpha
                self.screen.blit(fade_surf, (0, 0))
            
    def render_ending(self, ending_progress):
        """
        Render ending animation
        
        Args:
            ending_progress: Progress value from 0.0 to 1.0
        """
        # Clear with fade out
        fade_alpha = min(255, int(255 * ending_progress))
        fade_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade_surf.fill(BACKGROUND_COLOR)
        fade_surf.set_alpha(fade_alpha)
        
        # Continue drawing particles and effects
        for particle in game_state.particles:
            particle.draw(self.screen, pygame.Vector2(0, 0))
        for effect in game_state.effects:
            effect.draw(self.screen, pygame.Vector2(0, 0))
        
        # Apply fade overlay
        self.screen.blit(fade_surf, (0, 0))
        
        # Draw ending text
        title_font = pygame.font.Font(None, 60)
        if title_font:
            # Only show text in the middle of the fade
            if ending_progress > 0.3 and ending_progress < 0.9:
                text_alpha = min(255, int(255 * ((ending_progress - 0.3) / 0.6)))
                text = "Simulation Complete"
                text_surf = title_font.render(text, True, (200, 200, 255))
                text_surf.set_alpha(text_alpha)
                self.screen.blit(text_surf, (SCREEN_WIDTH//2 - text_surf.get_width()//2, SCREEN_HEIGHT//2 - 40))
                
                # Show saved message
                # if game_state.recording and ending_progress > 0.5:
                #     subtitle_font = pygame.font.Font(None, 36)
                #     if subtitle_font:
                #         sub_alpha = min(255, int(255 * ((ending_progress - 0.5) / 0.4)))
                #         sub_text = f"Video saved to: {game_state.video_filename}"
                #         sub_surf = subtitle_font.render(sub_text, True, (150, 150, 200))
                #         sub_surf.set_alpha(sub_alpha)
                #         self.screen.blit(sub_surf, (SCREEN_WIDTH//2 - sub_surf.get_width()//2, SCREEN_HEIGHT//2 + 20))
    
    def capture_frame(self):
        """Capture the current frame for video recording with improved quality"""
        if not game_state.recording or game_state.video_writer is None:
            return
            
        try:
            # Get raw pixel data from pygame surface
            pygame_surface_data = pygame.surfarray.array3d(self.screen)
            
            # OpenCV expects data in BGR format (pygame uses RGB) and with axes reordered
            cv2_frame = cv2.cvtColor(pygame_surface_data.swapaxes(0, 1), cv2.COLOR_RGB2BGR)
            
            # Write the frame to video
            game_state.video_writer.write(cv2_frame)
        except Exception as e:
            print(f"Error capturing video frame: {e}")
            
    def cleanup_recording(self):
        """Clean up video recording resources"""
        if game_state.recording and game_state.video_writer is not None:
            try:
                game_state.video_writer.release()
                print(f"Video recording completed: {game_state.video_filename}")
            except Exception as e:
                print(f"Error finalizing video: {e}")


class Game:
    """Main game class that handles all game phases"""
    
    def __init__(self):
        # Initialize pygame
        pygame.init()
        pygame.font.init()
        
        # Set up display
        flags = pygame.DOUBLEBUF
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
            pygame.display.set_caption("Neon Physics Simulation")
        except pygame.error as e:
            print(f"Error setting display mode: {e}")
            try:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                pygame.display.set_caption("Neon Physics Simulation")
            except pygame.error as e2:
                print(f"Fallback display mode failed: {e2}")
                raise RuntimeError("Could not initialize display")
                
        # Initialize renderer
        self.renderer = GameRenderer(self.screen)
        
        # Initialize audio
        audio_manager.initialize()
        
        # Initialize game state
        game_state.reset()
        game_state.intro_start_time = time.time()
        
        # Set up video recording
        self.record_video = True
        if self.record_video:
            self.renderer.setup_video_recording()
    
    def run(self):
        """Run the main game loop"""
        try:
            # Main game loop
            while game_state.running:
                # Process events
                self._handle_events()
                
                # Calculate time delta
                dt = self.renderer.clock.tick(FPS) / 1000.0
                dt = min(dt, 0.05)  # Cap delta time to prevent physics issues
                current_time = time.time()
                
                # Handle appropriate game phase
                if game_state.intro_phase:
                    self._run_intro_phase(current_time, dt)
                else:
                    self._run_game_phase(current_time, dt)
                    
                # Update display and capture frame
                pygame.display.flip()
                self.renderer.capture_frame()
                
            # Clean up resources when game ends
            self._cleanup()
            
        except KeyboardInterrupt:
            self._cleanup()
    
    def _handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_state.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state.running = False
                # Add ball on spacebar (only in game phase)
                if event.key == pygame.K_SPACE and not game_state.intro_phase:
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(0, CONTAINER_RADIUS * 0.9)
                    pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
                    vel = pygame.Vector2(random.uniform(-500, 500), random.uniform(-500, 500))
                    radius = random.uniform(MIN_RADIUS*2, MAX_RADIUS * 0.7)
                    color = random_bright_color()
                    game_state.balls.append(Ball(pos, vel, radius, color))
            # Add mouse click spawning (only in game phase)
            if event.type == pygame.MOUSEBUTTONDOWN and not game_state.intro_phase:
                if event.button == 1:
                    pos = pygame.Vector2(event.pos)
                    vel = pygame.Vector2(random.uniform(-150, 150), random.uniform(-150, 150))
                    radius = random.uniform(MIN_RADIUS*3, MAX_RADIUS * 0.8)
                    color = random_bright_color()
                    game_state.balls.append(Ball(pos, vel, radius, color))
    
    def _run_intro_phase(self, current_time, dt):
        """Run the intro animation phase"""
        intro_progress = (current_time - game_state.intro_start_time) / INTRO_DURATION
        
        # Near the end of intro, start updating ball physics for smoother transition
        if intro_progress > (1.0 - INTRO_FADE_OVERLAP) and len(game_state.balls) > 0:
            # Start partially updating the physics as we approach the end
            transition_factor = (intro_progress - (1.0 - INTRO_FADE_OVERLAP)) / INTRO_FADE_OVERLAP
            reduced_dt = dt * transition_factor  # Physics updates gradually increase
            
            # Update ball positions with reduced dt for transition
            for ball in game_state.balls:
                ball.update(reduced_dt)
                
        # Check if intro is complete
        if intro_progress >= 1.0:
            game_state.intro_phase = False
            game_state.game_start_time = current_time
            
            # Play start sound when simulation begins
            audio_manager.play('start', 1.0)
            
            # Ensure we have initial balls
            if len(game_state.balls) == 0:
                create_initial_balls()
        else:
            # Render intro animation
            self.renderer.render_intro(intro_progress)
    
    def _run_game_phase(self, current_time, dt):
        """Run the main simulation phase"""
        # Calculate elapsed time
        elapsed_time = current_time - game_state.game_start_time
            
        # Update game state phase
        phase_changed = game_state.update_phase(elapsed_time)
        
        # If phase changed, trigger appropriate effects
        if phase_changed:
            self._handle_phase_transition(elapsed_time)
            
        # Update game objects
        update_game_objects(dt, elapsed_time)
        
        # Check for finale trigger
        if elapsed_time >= FINALE_START_TIME and not game_state.finale_triggered:
            trigger_finale()
            
        # Check for end of game
        if elapsed_time >= MAX_GAME_DURATION:
            self._run_ending_sequence(current_time)
            return
        
        # Render the game
        self.renderer.render_frame(current_time)
        
    def _handle_phase_transition(self, elapsed_time):
        """
        Handle transitions between game phases with visual and audio effects
        
        Args:
            elapsed_time: Current elapsed game time
        """
        new_phase = game_state.current_phase
        
        # Add appropriate transition effects based on the new phase
        if new_phase == "BUILD":
            # Transition to BUILD phase (more energetic)
            print(f"Transitioning to BUILD phase at {elapsed_time:.1f}s")
            
            # Add some energy with a gentle screen shake
            trigger_screen_shake(0.5, SHAKE_INTENSITY * 0.8)
            
            # Spawn some decorative particles
            for _ in range(30):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(CONTAINER_RADIUS * 0.4, CONTAINER_RADIUS * 0.9)
                pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
                vel = pygame.Vector2(random.uniform(-100, 100), random.uniform(-100, 100))
                color = pygame.Color('cyan')
                game_state.particles.append(Particle(pos, vel, color, 1.5, 3))
                
            # Add a pulse effect
            # game_state.effects.append(Effect(CENTER, pygame.Color('white'), 
            #                                CONTAINER_RADIUS * 0.2, CONTAINER_RADIUS * 1.0, 
            #                                0.2, "flash"))
            
            # Play a transition sound
            audio_manager.play('collision', 1.0)
            
        elif new_phase == "CHAOS":
            # Transition to CHAOS phase (high energy)
            print(f"Transitioning to CHAOS phase at {elapsed_time:.1f}s")
            
            # Stronger screen shake
            trigger_screen_shake(0.8, SHAKE_INTENSITY * 1.3)
            
            # More energetic particles
            for _ in range(50):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(CONTAINER_RADIUS * 0.2, CONTAINER_RADIUS * 0.8)
                pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
                vel_mag = random.uniform(150, 300)
                vel_angle = random.uniform(0, 2 * math.pi)
                vel = pygame.Vector2(math.cos(vel_angle), math.sin(vel_angle)) * vel_mag
                color = pygame.Color('magenta')
                game_state.particles.append(Particle(pos, vel, color, 2.0, 4))
                
            # Add stronger pulse effects
            # game_state.effects.append(Effect(CENTER, pygame.Color('white'), 
            #                                CONTAINER_RADIUS * 0.3, CONTAINER_RADIUS * 1.2, 
            #                                1.0, "flash"))
            
            # Add an expanding ring effect
            game_state.effects.append(Effect(CENTER, pygame.Color(200, 100, 255), 
                                           5, CONTAINER_RADIUS * 0.95, 
                                           0.6, "flash"))
            
            # Play transition sound
            audio_manager.play('collision', 1.2)
            
            # Spawn some fresh balls for increased chaos
            for _ in range(2):
                spawn_fresh_ball(elapsed_time)
            
        elif new_phase == "FINALE":
            # Transition to FINALE phase (maximum energy)
            print(f"Transitioning to FINALE phase at {elapsed_time:.1f}s")
            
            # Maximum screen shake
            trigger_screen_shake(1.2, SHAKE_INTENSITY * 2.0)
            
            # Explosive particle effects
            for _ in range(80):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(CONTAINER_RADIUS * 0.1, CONTAINER_RADIUS * 0.9)
                pos = CENTER + pygame.Vector2(math.cos(angle), math.sin(angle)) * dist
                vel_mag = random.uniform(200, 400)
                vel_angle = random.uniform(0, 2 * math.pi)
                vel = pygame.Vector2(math.cos(vel_angle), math.sin(vel_angle)) * vel_mag
                
                # Rainbow colors for finale
                hue = random.uniform(0, 360)
                color = pygame.Color(0)
                color.hsva = (hue, 100, 100, 100)
                
                game_state.particles.append(Particle(pos, vel, color, 2.5, 5))
                
            # Add multiple pulse effects
            # game_state.effects.append(Effect(CENTER, pygame.Color('white'), 
            #                                CONTAINER_RADIUS * 0.4, CONTAINER_RADIUS * 1.3, 
            #                                1.2, "flash"))
            
            game_state.effects.append(Effect(CENTER, pygame.Color(255, 100, 100), 
                                           10, CONTAINER_RADIUS * 0.9, 
                                           0.8, "flash"))
            
            game_state.effects.append(Effect(CENTER, pygame.Color(100, 100, 255), 
                                           20, CONTAINER_RADIUS * 0.8, 
                                           0.7, "flash"))
            
            # Play finale sound
            audio_manager.play('end', 1.0)
            
            # Spawn multiple fresh balls for maximum chaos
            for _ in range(4):
                spawn_fresh_ball(elapsed_time)
    
    def _run_ending_sequence(self, current_time):
        """Run the ending animation sequence"""
        ending_duration = 3.0  # 3 second ending
        ending_start = current_time
        ending_phase = True
        
        while ending_phase and game_state.running:
            # Handle events during ending
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    ending_phase = False
                    game_state.running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    ending_phase = False
                    game_state.running = False
            
            # Calculate ending progress
            ending_elapsed = time.time() - ending_start
            ending_progress = ending_elapsed / ending_duration
            
            if ending_progress >= 1.0:
                ending_phase = False
                game_state.running = False
            
            # Render ending animation
            self.renderer.render_ending(ending_progress)
            
            # Update display and capture frame
            pygame.display.flip()
            self.renderer.capture_frame()
            
            # Maintain framerate
            self.renderer.clock.tick(FPS)
    
    def _cleanup(self):
        """Clean up game resources"""
        self.renderer.cleanup_recording()
        audio_manager.cleanup()
        pygame.quit()


# Function to run the game
def run_game():
    """Start and run the game"""
    game = Game()
    game.run()