import pygame
import cv2
import time
import random
import os
import subprocess
import threading
from datetime import datetime
from src.config import *
from src.audio import audio_manager
from src.entities import Ball, Particle, Effect
from src.utilities import random_bright_color, spawn_particles, trigger_screen_shake
# Removed trigger_finale import, added spawn_fresh_ball
from src.physics import update_game_objects, create_initial_balls, spawn_fresh_ball
from src.game_state import game_state
import math

class AudioRecorder:
    """Handles recording of game audio - REPLACED with unified FFmpeg recorder approach"""
    
    def __init__(self):
        self.is_recording = False
        self.ffmpeg_process = None
        self.start_time = 0
    
    def setup_audio_recording(self, filename):
        """No longer used - audio is recorded with video by FFmpeg"""
        # This method is kept for compatibility but no longer does separate audio recording
        self.is_recording = True
        self.start_time = time.time()
        print("Audio will be recorded with video using FFmpeg")
    
    def stop_recording(self):
        """Stop the audio recording"""
        self.is_recording = False
        print("Audio recording will stop with video recording")

class GameRenderer:
    """Handles rendering for the game"""

    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        if self.font is None:
            self.font = pygame.font.SysFont("sans-serif", 24)
        self.audio_recorder = AudioRecorder()

    def setup_video_recording(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"physics_simulation_{timestamp}"
        
        # Setup video recording
        game_state.video_filename = f"{base_filename}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_fps = 60  # Make sure video FPS is consistent
        game_state.video_writer = cv2.VideoWriter(
            game_state.video_filename, fourcc, video_fps, (SCREEN_WIDTH, SCREEN_HEIGHT))
        game_state.recording = True
        print(f"Recording video to: {game_state.video_filename} at {video_fps} FPS")
        
        # Setup audio recording - start audio first to ensure it's ready when video starts
        game_state.audio_filename = f"{base_filename}.wav"
        self.audio_recorder.setup_audio_recording(game_state.audio_filename)
        
        # Store base filename for later use
        self.base_filename = base_filename
        
        # Add a short delay to ensure audio recording is properly initialized
        time.sleep(0.1)

    def render_frame(self, current_time):
        self.screen.fill(BACKGROUND_COLOR)
        draw_offset = game_state.current_screen_offset

        # Draw container circle (less prominent over time)
        # elapsed_time = game_state.get_elapsed_time()
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
            title_text = "Neon Physics Simulation"
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
        # Keep rendering the simulation state during fade out
        self.render_frame(time.time()) # Render current state first

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

    def capture_frame(self):
        if not game_state.recording or game_state.video_writer is None:
            return
        try:
            # Capture and write the video frame
            pygame_surface_data = pygame.surfarray.array3d(self.screen)
            cv2_frame = cv2.cvtColor(pygame_surface_data.swapaxes(0, 1), cv2.COLOR_RGB2BGR)
            game_state.video_writer.write(cv2_frame)
        except Exception as e:
            print(f"Error capturing video frame: {e}")

    def cleanup_recording(self):
        if game_state.recording and game_state.video_writer is not None:
            try:
                game_state.video_writer.release()
                print(f"Video recording completed: {game_state.video_filename}")
            except Exception as e:
                print(f"Error finalizing video: {e}")
        
        # Stop the audio recording
        self.audio_recorder.stop_recording()
        
        # Try to merge audio and video if both exist
        if os.path.exists(game_state.video_filename) and os.path.exists(game_state.audio_filename):
            self._merge_audio_video()
    
    def _merge_audio_video(self):
        """Attempt to merge audio and video files using FFmpeg if available"""
        try:
            # Check if ffmpeg is available
            try:
                subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                ffmpeg_available = True
            except (subprocess.SubprocessError, FileNotFoundError):
                ffmpeg_available = False
            
            if ffmpeg_available:
                output_filename = f"{self.base_filename}_with_audio.mp4"
                
                # Run FFmpeg to merge the files with reliable synchronization options
                cmd = [
                    "ffmpeg", "-y", 
                    "-i", game_state.video_filename, 
                    "-itsoffset", "0.2",  # Add a fixed audio offset to compensate for recording delay
                    "-i", game_state.audio_filename,
                    "-c:v", "copy", 
                    "-c:a", "aac", 
                    "-b:a", "192k",  # Better audio quality
                    output_filename
                ]
                
                print(f"Merging audio and video with command: {' '.join(cmd)}")
                subprocess.run(cmd, check=True)
                print(f"Successfully merged audio and video to: {output_filename}")
        
        except Exception as e:
            print(f"Error merging audio and video: {e}")
            print("\nTo manually add audio to your video:")
            print(f"1. Use a video editor to combine the files:")
            print(f"   - Video: {game_state.video_filename}")
            print(f"   - Audio: {game_state.audio_filename}")


class Game:
    """Main game class"""

    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = pygame.DOUBLEBUF
        try:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)) # Fallback
        pygame.display.set_caption("Physics Simulation")

        self.renderer = GameRenderer(self.screen)
        audio_manager.initialize()
        game_state.reset()
        game_state.intro_start_time = time.time()

        self.record_video = True # Set to False to disable recording
        if self.record_video:
            self.renderer.setup_video_recording()

    def run(self):
        try:
            while game_state.running:
                self._handle_events()
                dt = self.renderer.clock.tick(FPS) / 1000.0
                dt = min(dt, 0.05) # Cap dt
                current_time = time.time()

                if game_state.intro_phase:
                    self._run_intro_phase(current_time, dt)
                else:
                    self._run_game_phase(current_time, dt)

                pygame.display.flip()
                self.renderer.capture_frame()

            self._cleanup()

        except KeyboardInterrupt:
            self._cleanup()
        # Ensure cleanup runs even on other errors
        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup()


    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_state.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state.running = False
                # Spawn ball on spacebar (only in game)
                if event.key == pygame.K_SPACE and not game_state.intro_phase:
                    if len(game_state.balls) < MAX_BALL_COUNT:
                         spawn_fresh_ball() # Use the chaos-scaled spawner
            # Spawn ball on click (only in game)
            if event.type == pygame.MOUSEBUTTONDOWN and not game_state.intro_phase:
                 if event.button == 1: # Left click
                    if len(game_state.balls) < MAX_BALL_COUNT:
                        # Spawn at mouse position, with chaos scaling
                        spawn_fresh_ball() # Reuse spawner, maybe modify later for position control


    def _run_intro_phase(self, current_time, dt):
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
            audio_manager.play('start', 1.0)
            if len(game_state.balls) == 0:
                create_initial_balls() # Ensure balls exist
        else:
            self.renderer.render_intro(intro_progress)


    def _run_game_phase(self, current_time, dt):
        elapsed_time = current_time - game_state.game_start_time

        # Update game objects (physics, collisions, spawning)
        # Pass dt only, chaos factor is handled internally via game_state
        update_game_objects(dt)

        # Check for end of game based on duration
        if elapsed_time >= MAX_GAME_DURATION and game_state.running:
             # Don't immediately stop, let it run slightly over if needed for fade out
             if elapsed_time >= MAX_GAME_DURATION + 2.0: # Start ending fade after 2 extra seconds
                 self._run_ending_sequence(current_time)
                 return # Exit after starting ending sequence

        # Render the game
        self.renderer.render_frame(current_time)

    # Removed _handle_phase_transition method


    def _run_ending_sequence(self, current_time):
        # End simulation smoothly
        ending_duration = 3.0
        ending_start_time = time.time() # Use current time as start
        ending_running = True

        audio_manager.play('end', 1.0) # Play end sound

        while ending_running and game_state.running:
            # Still handle basic events like quit
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    game_state.running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game_state.running = False

            ending_elapsed = time.time() - ending_start_time
            ending_progress = min(1.0, ending_elapsed / ending_duration)

            # Minimal physics update during fade out to keep things moving a bit
            dt = self.renderer.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            update_game_objects(dt * (1.0 - ending_progress)) # Slow down physics

            # Render ending frame (which includes game state + fade)
            self.renderer.render_ending(ending_progress)

            pygame.display.flip()
            self.renderer.capture_frame()

            if ending_progress >= 1.0:
                ending_running = False
                game_state.running = False # Fully stop the game loop


    def _cleanup(self):
        print("Cleaning up...")
        self.renderer.cleanup_recording()
        audio_manager.cleanup()
        pygame.quit()


def run_game():
    game = Game()
    game.run()