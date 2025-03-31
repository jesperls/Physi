import pygame
import os
import random
from src.config import *
import time
import numpy as np
import math

class AudioManager:
    """Manages loading and playing sounds with spatial audio support"""
    
    def __init__(self):
        self.sound_categories = {}  # Dictionary of sound categories, each containing a list of sounds
        self.sound_enabled = SOUND_ENABLED
        self.initialized = False
        self.last_played = {}  # Track when sounds were last played
        self.sound_cooldowns = {
            'collision': 0.05,  # Minimum time between collision sounds
            'ambient': 0.0     # No cooldown for ambient
        }
        self.global_cooldown = 0.01  # Global minimum between any sounds
        self.last_any_sound = 0
        self.ambient_playing = None  # Currently playing ambient sound
        
        # Audio analysis and rhythm detection
        self.last_beat_time = 0
        self.beat_interval = 0.5  # Default beat interval (seconds)
        self.beat_energy_threshold = 0.3
        self.energy_history = []
        self.energy_window_size = 10
        self.beat_detected = False
        self.last_energy = 0
        self.smoothed_energy = 0
        self.beat_count = 0
        self.beat_phase = 0
        
        # Rhythm pattern detection
        self.beat_times = []
        self.max_beat_history = 20
        self.rhythm_detected = False
        self.estimated_bpm = 120  # Default BPM
        self.current_master_volume = 1.0
    
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
        self._play_ambient()
    
    def _load_sounds(self):
        """Load all sound files from folders"""
        for category, folder_path in SOUND_FOLDERS.items():
            self.sound_categories[category] = []
            self.last_played[category] = 0  # Initialize last played time
            
            # Create folder if it doesn't exist
            os.makedirs(folder_path, exist_ok=True)
            
            # Check if the folder exists and contains files
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                sound_files = [f for f in os.listdir(folder_path) 
                              if f.endswith(('.ogg', '.wav', '.mp3')) and os.path.isfile(os.path.join(folder_path, f))]
                
                # Fallback to current directory with naming pattern if folder is empty
                if not sound_files:
                    fallback_files = [f for f in os.listdir('.') 
                                     if f.startswith(category) and f.endswith(('.ogg', '.wav', '.mp3'))]
                    if fallback_files:
                        print(f"No files found in {folder_path}, using fallback files: {fallback_files}")
                        for filename in fallback_files:
                            try:
                                sound = pygame.mixer.Sound(filename)
                                sound.set_volume(SOUND_VOLUME_MASTER)
                                self.sound_categories[category].append(sound)
                                print(f"Loaded sound for {category}: {filename}")
                            except pygame.error as e:
                                print(f"Error loading sound '{filename}': {e}")
                else:
                    for filename in sound_files:
                        full_path = os.path.join(folder_path, filename)
                        try:
                            sound = pygame.mixer.Sound(full_path)
                            sound.set_volume(SOUND_VOLUME_MASTER)
                            self.sound_categories[category].append(sound)
                            print(f"Loaded sound for {category}: {full_path}")
                        except pygame.error as e:
                            print(f"Error loading sound '{full_path}': {e}")
            else:
                # Handle case where the specified folder doesn't exist
                fallback_files = [f for f in os.listdir('.') 
                                 if f.startswith(category) and f.endswith(('.ogg', '.wav', '.mp3'))]
                if fallback_files:
                    print(f"Folder {folder_path} not found, using fallback files: {fallback_files}")
                    for filename in fallback_files:
                        try:
                            sound = pygame.mixer.Sound(filename)
                            sound.set_volume(SOUND_VOLUME_MASTER)
                            self.sound_categories[category].append(sound)
                            print(f"Loaded sound for {category}: {filename}")
                        except pygame.error as e:
                            print(f"Error loading sound '{filename}': {e}")
                else:
                    print(f"Warning: No sounds found for category '{category}'")
    
    def _play_ambient(self):
        """Start playing ambient sounds if available"""
        ambient_sounds = self.sound_categories.get('ambient', [])
        if ambient_sounds:
            # Select a random ambient sound to play
            sound = random.choice(ambient_sounds)
            sound.set_volume(SOUND_VOLUME_AMBIENT)
            sound.play(loops=-1)
            self.ambient_playing = sound
            print(f"Playing ambient sound")
            
            # Estimate rhythm from the sound file name
            self._estimate_rhythm_from_filename(sound)
        elif self.sound_enabled:
            print("Warning: No ambient sounds found, cannot play.")
    
    def _estimate_rhythm_from_filename(self, sound):
        """Try to extract BPM information from the sound file's name"""
        try:
            # Get the filename from the sound object if possible
            if hasattr(sound, 'name'):
                filename = os.path.basename(sound.name)
            else:
                # If we can't get it directly, guess based on what files we have
                return
            
            # Look for BPM pattern in filename (e.g. "120bpm" or "bpm_120")
            import re
            bpm_match = re.search(r'(\d+)bpm|bpm[_\s]?(\d+)', filename.lower())
            
            if bpm_match:
                groups = bpm_match.groups()
                bpm = next((int(g) for g in groups if g is not None), None)
                if bpm and 60 <= bpm <= 200:  # Sanity check for reasonable BPM
                    self.estimated_bpm = bpm
                    self.beat_interval = 60.0 / bpm
                    print(f"Detected BPM {bpm} from filename")
                    self.rhythm_detected = True
            else:
                # Default values for different music types based on the filename
                if any(term in filename.lower() for term in ['slow', 'ambient', 'chill']):
                    self.estimated_bpm = 80
                elif any(term in filename.lower() for term in ['medium', 'moderate']):
                    self.estimated_bpm = 110
                elif any(term in filename.lower() for term in ['fast', 'upbeat', 'energetic']):
                    self.estimated_bpm = 140
                else:
                    # Use simulated rhythms for songs without BPM indication
                    self.estimated_bpm = 120  # Default mid-tempo
                
                self.beat_interval = 60.0 / self.estimated_bpm
                print(f"Using estimated BPM {self.estimated_bpm}")
        except Exception as e:
            print(f"Error estimating rhythm: {e}")
            self.estimated_bpm = 120  # Fallback
            self.beat_interval = 60.0 / self.estimated_bpm
    
    def update(self):
        """Update audio analysis and beat detection"""
        if not self.sound_enabled or not self.initialized or not self.ambient_playing:
            return False
        
        # Since we can't directly access audio data in pygame without FFT analysis,
        # we'll use a time-based approach to simulate beat detection
        current_time = time.time()
        
        # Simple beat simulation based on estimated rhythm
        if self.rhythm_detected:
            # Calculate beat phase (0 to 1) within the beat interval
            time_since_start = current_time % MAX_GAME_DURATION  # Reset every MAX_GAME_DURATION seconds
            beat_phase = (time_since_start / self.beat_interval) % 1.0
            self.beat_phase = beat_phase
            
            # We consider a beat when we're at the start of the phase (0 to 0.1)
            beat_detected = beat_phase < 0.1 and (current_time - self.last_beat_time) > self.beat_interval * 0.5
            
            if beat_detected:
                self.last_beat_time = current_time
                self.beat_count += 1
                return True  # Beat detected
        else:
            # Simulated beat detection using a time-based approach
            # This creates a predictable rhythm for visuals to sync with
            elapsed = current_time % self.beat_interval
            beat_detected = elapsed < 0.1 and (current_time - self.last_beat_time) > self.beat_interval * 0.5
            
            if beat_detected:
                self.last_beat_time = current_time
                self.beat_count += 1
                return True  # Beat detected
        
        return False  # No beat detected
    
    def get_beat_intensity(self):
        """Get the current beat intensity (0.0 to 1.0)"""
        # Calculate a sine wave based on the beat phase
        if not self.sound_enabled or not self.initialized:
            return 0.5  # Default middle value
        
        # Use both the beat phase and a secondary pulse for more variety
        current_time = time.time()
        beat_intensity = abs(math.sin(math.pi * self.beat_phase))
        
        # Add a secondary slower pulse for variety
        secondary_pulse = abs(math.sin(current_time * 0.5))
        
        # Combine both pulses with the beat phase being dominant
        combined_intensity = beat_intensity * 0.7 + secondary_pulse * 0.3
        
        return combined_intensity
    
    def get_beat_phase(self):
        """Get the current beat phase (0.0 to 1.0)"""
        return self.beat_phase
    
    def get_rhythm_info(self):
        """Get information about the current rhythm"""
        return {
            'bpm': self.estimated_bpm,
            'beat_interval': self.beat_interval,
            'beat_count': self.beat_count,
            'beat_phase': self.beat_phase
        }
    
    def set_master_volume(self, volume):
        """Set the master volume for all sounds (0.0 to 1.0)"""
        if not self.sound_enabled or not self.initialized:
            return
            
        # Clamp volume between 0 and 1
        volume = max(0.0, min(1.0, volume))
        
        # Update ambient sound volume if playing
        if self.ambient_playing:
            self.ambient_playing.set_volume(SOUND_VOLUME_AMBIENT * volume)
            
        # Update the base volume for future sound effects
        self.current_master_volume = volume
        
    def play(self, category, volume_modifier=1.0, position=None):
        """
        Play a random sound from the specified category with optional positional audio
        
        Args:
            category: Category name of sounds to choose from
            volume_modifier: Volume multiplier (0.0-1.0)
            position: Optional Vector2 position for spatial audio
        """
        if not self.sound_enabled or category not in self.sound_categories or not self.sound_categories[category]:
            return
            
        # Check sound-specific cooldown
        current_time = time.time()
        cooldown = self.sound_cooldowns.get(category, 0.1)  # Default 0.1s cooldown
        
        # Skip if this sound category is on cooldown or global cooldown is active
        if (current_time - self.last_played.get(category, 0) < cooldown or
            current_time - self.last_any_sound < self.global_cooldown):
            return
            
        # Update last played time
        self.last_played[category] = current_time
        self.last_any_sound = current_time

        try:
            channel = pygame.mixer.find_channel(False)  # Try to find available channel without forcing
            if channel is None:
                # If no free channels, only force for important sounds
                if category in ['start', 'end']:
                    channel = pygame.mixer.find_channel(True)  # Force only for important sounds
                else:
                    return  # Skip sound if no channels available
            
            # Select a random sound from the category
            sound = random.choice(self.sound_categories[category])
            base_volume = SOUND_VOLUME_MASTER * volume_modifier * (getattr(self, 'current_master_volume', 1.0))

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

            channel.play(sound)
        except Exception as e:
            # Catch specific pygame errors if possible, otherwise broad Exception
            if isinstance(e, pygame.error):
                print(f"Pygame Error playing sound from category {category}: {e}")
            else:
                print(f"Error playing sound from category {category}: {e}")
    
    def cleanup(self):
        """Clean up audio resources"""
        if self.sound_enabled and pygame.mixer.get_init():
            pygame.mixer.stop()
            pygame.mixer.quit()
            
# Global audio manager instance
audio_manager = AudioManager()