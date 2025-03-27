import pygame
import time
from src.config import MAX_GAME_DURATION

class GameState:
    """
    Singleton class to maintain global game state
    """
    def __init__(self):
        # Game flow control
        self.intro_phase = True
        self.intro_start_time = 0
        self.game_start_time = 0
        self.running = True

        # Entity collections
        self.balls = []
        self.particles = []
        self.effects = []

        # Ball ID counter
        self.next_ball_id = 0

        # Visual effects state
        self.screen_shake_timer = 0.0
        self.current_screen_offset = pygame.Vector2(0, 0)

        # Recording state
        self.recording = False
        self.video_writer = None
        self.video_filename = ""

        # Time-based chaos factor (0.0 at start, 1.0 at MAX_GAME_DURATION)
        self.chaos_factor = 0.0

    def reset(self):
        """Reset game state for a new game"""
        self.balls = []
        self.particles = []
        self.effects = []
        self.next_ball_id = 0
        self.intro_phase = True
        self.intro_start_time = time.time()
        self.game_start_time = 0
        self.screen_shake_timer = 0.0
        self.current_screen_offset = pygame.Vector2(0, 0)
        self.chaos_factor = 0.0
        self.running = True # Ensure running is true on reset

    def update_chaos_factor(self):
        """Update the chaos factor based on elapsed game time"""
        if self.game_start_time > 0 and not self.intro_phase:
            elapsed_time = time.time() - self.game_start_time
            self.chaos_factor = min(1.0, elapsed_time / MAX_GAME_DURATION)
        else:
            self.chaos_factor = 0.0

    def get_current_value(self, initial_value, final_value):
        """Linearly interpolate between an initial and final value based on chaos_factor."""
        return initial_value + (final_value - initial_value) * self.chaos_factor

    def get_elapsed_time(self):
        """Get elapsed time since game started"""
        if self.game_start_time is None or self.game_start_time == 0:
            return 0
        return time.time() - self.game_start_time

# Global game state instance
game_state = GameState()