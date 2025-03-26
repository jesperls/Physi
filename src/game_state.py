import pygame
import time

class GameState:
    """
    Singleton class to maintain global game state
    """
    def __init__(self):
        # Game flow control
        self.intro_phase = True
        self.intro_start_time = 0
        self.game_start_time = 0
        self.finale_triggered = False
        self.running = True
        
        # Simulation phase tracking (CALM -> BUILD -> CHAOS -> FINALE)
        self.current_phase = "CALM"  # CALM, BUILD, CHAOS, FINALE
        self.phase_start_times = {
            "CALM": 0,
            "BUILD": 0,
            "CHAOS": 0,
            "FINALE": 0
        }
        
        # Entity collections
        self.balls = []
        self.particles = []
        self.effects = []
        
        # Ball ID counter
        self.next_ball_id = 0
        
        # Visual effects state
        self.screen_shake_timer = 0.0
        self.current_screen_offset = pygame.Vector2(0, 0)
        
        # Adaptive physics parameters
        self.current_collision_shrink_factor = 0.0  # How much balls shrink on collision
        self.current_elasticity_base = 1.0  # Base elasticity value
        self.current_elasticity_variance = 0.0  # Random variance in elasticity
        self.current_split_chance = 0.0  # Chance of balls splitting
        self.current_merge_threshold = 70  # Color distance threshold for merging
        self.current_gravity_strength = 100.0  # Current gravity strength
        
        # Recording state
        self.recording = False
        self.video_writer = None
        self.video_filename = ""

    def reset(self):
        """Reset game state for a new game"""
        self.balls = []
        self.particles = []
        self.effects = []
        self.next_ball_id = 0
        self.intro_phase = True
        self.intro_start_time = time.time()
        self.game_start_time = 0
        self.finale_triggered = False
        self.screen_shake_timer = 0.0
        self.current_screen_offset = pygame.Vector2(0, 0)
        
        # Reset phase tracking
        self.current_phase = "CALM"
        current_time = time.time()
        self.phase_start_times = {
            "CALM": current_time,
            "BUILD": 0,
            "CHAOS": 0,
            "FINALE": 0
        }
        
        # Reset adaptive parameters
        self.current_collision_shrink_factor = 0.0
        self.current_elasticity_base = 1.0
        self.current_elasticity_variance = 0.0
        self.current_split_chance = 0.0
        self.current_merge_threshold = 70
        self.current_gravity_strength = 100.0
        
    def update_phase(self, elapsed_time):
        """
        Update the current simulation phase based on elapsed time
        
        Args:
            elapsed_time: Elapsed time in seconds since simulation start
        
        Returns:
            Boolean: True if phase changed, False otherwise
        """
        # Phase timing configuration
        phase_timings = {
            "CALM": (0, 15),          # 0-15 seconds: Calm phase
            "BUILD": (15, 35),        # 15-35 seconds: Building intensity
            "CHAOS": (35, 50),        # 35-50 seconds: Full chaos
            "FINALE": (50, 60)        # 50-60 seconds: Grand finale
        }
        
        # Determine current phase
        previous_phase = self.current_phase
        
        for phase, (start, end) in phase_timings.items():
            if start <= elapsed_time < end:
                if self.current_phase != phase:
                    # Phase has changed
                    self.current_phase = phase
                    self.phase_start_times[phase] = time.time()
                    return True
                return False
        
        return False
    
    def get_phase_progress(self):
        """
        Get the progress through the current phase (0.0 to 1.0)
        
        Returns:
            Float: Progress through current phase (0.0 to 1.0)
        """
        if self.current_phase == "CALM":
            return min(1.0, (time.time() - self.phase_start_times["CALM"]) / 15.0)
        elif self.current_phase == "BUILD":
            return min(1.0, (time.time() - self.phase_start_times["BUILD"]) / 20.0)
        elif self.current_phase == "CHAOS":
            return min(1.0, (time.time() - self.phase_start_times["CHAOS"]) / 15.0)
        elif self.current_phase == "FINALE":
            return min(1.0, (time.time() - self.phase_start_times["FINALE"]) / 10.0)
        return 0.0
    
    def update_adaptive_parameters(self):
        """Update physics parameters based on current phase and progress"""
        phase = self.current_phase
        progress = self.get_phase_progress()
        
        if phase == "CALM":
            # Calm phase - minimal changes, allow balls to interact gently
            self.current_collision_shrink_factor = 0.001 + (progress * 0.004)
            self.current_elasticity_base = 1.0
            self.current_elasticity_variance = 0.05 + (progress * 0.1)
            self.current_split_chance = 0.01 + (progress * 0.09)
            self.current_merge_threshold = 80
            self.current_gravity_strength = 100.0 + (progress * 50.0)
            
        elif phase == "BUILD":
            # Building phase - increasing energy and dynamics
            self.current_collision_shrink_factor = 0.005 + (progress * 0.015)
            self.current_elasticity_base = 1.0 + (progress * 0.1)
            self.current_elasticity_variance = 0.15 + (progress * 0.15)
            self.current_split_chance = 0.1 + (progress * 0.3)
            self.current_merge_threshold = 60
            self.current_gravity_strength = 150.0 + (progress * 150.0)
            
        elif phase == "CHAOS":
            # Chaos phase - maximum energy and dynamics
            self.current_collision_shrink_factor = 0.02 + (progress * 0.02)
            self.current_elasticity_base = 1.1 + (progress * 0.1)
            self.current_elasticity_variance = 0.3
            self.current_split_chance = 0.4 + (progress * 0.2)
            self.current_merge_threshold = 40
            self.current_gravity_strength = 300.0 + (progress * 200.0)
            
        elif phase == "FINALE":
            # Finale phase - complete chaos
            self.current_collision_shrink_factor = 0.04
            self.current_elasticity_base = 1.2
            self.current_elasticity_variance = 0.3
            self.current_split_chance = 0.6 + (progress * 0.3)
            self.current_merge_threshold = 20
            self.current_gravity_strength = 500.0 + (progress * 300.0)
        
    def get_elapsed_time(self):
        """Get elapsed time since game started"""
        if self.game_start_time is None or self.game_start_time == 0:
            return 0
        return time.time() - self.game_start_time

# Global game state instance
game_state = GameState()