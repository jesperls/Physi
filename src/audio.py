import pygame
import os
from src.config import *
import time

class AudioManager:
    """Manages loading and playing sounds with spatial audio support"""
    
    def __init__(self):
        self.sounds = {}
        self.sound_enabled = SOUND_ENABLED
        self.initialized = False
        self.last_played = {}  # Track when sounds were last played
        self.sound_cooldowns = {
            'collision': 0.05,  # Minimum time between collision sounds
            'start': 0.0,      # No cooldown for start sound
            'end': 0.0,        # No cooldown for end sound
            'ambient': 0.0     # No cooldown for ambient
        }
        self.global_cooldown = 0.01  # Global minimum between any sounds
        self.last_any_sound = 0
    
    def initialize(self):
        """Initialize the audio system"""
        if not self.sound_enabled:
            return
            
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            pygame.mixer.set_num_channels(16)  # Reduced number of channels to prevent audio issues
            print("Pygame mixer initialized.")
            self.initialized = True
        except pygame.error as e:
            print(f"Error initializing pygame mixer: {e}")
            self.sound_enabled = False
            return
            
        # Load all sounds defined in config
        self._load_sounds()
        
        # Start ambient sound if available
        if self.sounds.get('ambient') and self.sounds['ambient'] is not None:
            self.sounds['ambient'].set_volume(SOUND_VOLUME_AMBIENT)
            self.sounds['ambient'].play(loops=-1)
        elif self.sound_enabled:
            print("Warning: Ambient sound file not found or failed to load, cannot play.")
    
    def _load_sounds(self):
        """Load all sound files"""
        for name, filename in SOUND_FILES.items():
            if os.path.exists(filename):
                try:
                    self.sounds[name] = pygame.mixer.Sound(filename)
                    self.sounds[name].set_volume(SOUND_VOLUME_MASTER)
                    self.last_played[name] = 0  # Initialize last played time
                    print(f"Loaded sound: {filename}")
                except pygame.error as e:
                    print(f"Error loading sound '{filename}': {e}")
                    self.sounds[name] = None  # Mark as unloadable
            else:
                print(f"Warning: Sound file not found: {filename}")
                self.sounds[name] = None
    
    def play(self, name, volume_modifier=1.0, position=None):
        """
        Play a sound with optional positional audio
        
        Args:
            name: Name of the sound to play
            volume_modifier: Volume multiplier (0.0-1.0)
            position: Optional Vector2 position for spatial audio
        """
        if not self.sound_enabled or name not in self.sounds or self.sounds[name] is None:
            return
            
        # Check sound-specific cooldown
        current_time = time.time()
        cooldown = self.sound_cooldowns.get(name, 0.1)  # Default 0.1s cooldown
        
        # Skip if this sound is on cooldown or global cooldown is active
        if (current_time - self.last_played.get(name, 0) < cooldown or
            current_time - self.last_any_sound < self.global_cooldown):
            return
            
        # Update last played time
        self.last_played[name] = current_time
        self.last_any_sound = current_time

        try:
            channel = pygame.mixer.find_channel(False)  # Try to find available channel without forcing
            if channel is None:
                # If no free channels, only force for important sounds
                if name in ['start', 'end']:
                    channel = pygame.mixer.find_channel(True)  # Force only for important sounds
                else:
                    return  # Skip sound if no channels available
                    
            base_volume = SOUND_VOLUME_MASTER * volume_modifier

            # --- Simple Panning based on position ---
            if position:
                # Map x position (-1 left, 1 right)
                pan = (position.x - SCREEN_WIDTH / 2) / (SCREEN_WIDTH / 2)
                pan = max(-1.0, min(1.0, pan))
                # Pygame panning: set_volume(left_vol, right_vol)
                left_vol = base_volume * (1.0 - pan) / 2.0 * 2  # Multiply by 2 to maintain overall volume
                right_vol = base_volume * (1.0 + pan) / 2.0 * 2
                # Ensure volumes don't exceed 1.0 after potential modifiers
                left_vol = min(1.0, left_vol)
                right_vol = min(1.0, right_vol)
                channel.set_volume(left_vol, right_vol)
            else:
                channel.set_volume(base_volume)

            channel.play(self.sounds[name])
        except Exception as e:
            # Catch specific pygame errors if possible, otherwise broad Exception
            if isinstance(e, pygame.error):
                print(f"Pygame Error playing sound {name}: {e}")
            else:
                print(f"Error playing sound {name}: {e}")
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.sound_enabled and pygame.mixer.get_init():
            pygame.mixer.stop()
            pygame.mixer.quit()
            
# Global audio manager instance
audio_manager = AudioManager()