import os
import time
import datetime
import threading
import pygame
import numpy as np
import cv2
import pyaudio
import wave
from src.config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from src.game_state import game_state

class Recorder:
    """Handles video and audio recording of the simulation"""
    
    def __init__(self):
        self.recording = False
        self.video_writer = None
        self.video_filename = ""
        
        # Audio recording properties
        self.audio_recording = False
        self.audio_thread = None
        self.audio_filename = ""
        self.audio_stream = None
        self.audio_frames = []
        self.pyaudio = None
        
        # Output directory
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recordings")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Recording parameters
        self.fps = FPS
        self.frame_size = (SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Audio parameters
        self.format = pyaudio.paInt16
        self.channels = 2
        self.rate = 44100
        self.chunk = 1024
        
    def start_recording(self):
        """Start recording both video and audio"""
        if self.recording:
            print("Recording already in progress")
            return
            
        # Generate timestamp for filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_filename = os.path.join(self.output_dir, f"simulation_{timestamp}.mp4")
        self.audio_filename = os.path.join(self.output_dir, f"simulation_{timestamp}.wav")
        
        # Start video recording
        self._start_video_recording()
        
        # Start audio recording in a separate thread
        self._start_audio_recording()
        
        self.recording = True
        game_state.recording = True
        print(f"Started recording to {self.video_filename}")
        
    def _start_video_recording(self):
        """Initialize the video writer"""
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(
            self.video_filename, 
            fourcc, 
            self.fps, 
            self.frame_size
        )
        
    def _start_audio_recording(self):
        """Start audio recording in a separate thread"""
        self.pyaudio = pyaudio.PyAudio()
        self.audio_frames = []
        self.audio_recording = True
        
        # Start audio recording in a separate thread
        self.audio_thread = threading.Thread(target=self._record_audio)
        self.audio_thread.daemon = True
        self.audio_thread.start()
        
    def _record_audio(self):
        """Audio recording thread function"""
        # Open audio stream
        try:
            self.audio_stream = self.pyaudio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            print("Audio recording started")
            
            # Record audio frames
            while self.audio_recording:
                data = self.audio_stream.read(self.chunk)
                self.audio_frames.append(data)
                
        except Exception as e:
            print(f"Error in audio recording: {e}")
        finally:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                
    def capture_frame(self, surface):
        """Capture a frame from the Pygame surface"""
        if not self.recording or self.video_writer is None:
            return
            
        # Convert Pygame surface to numpy array for OpenCV
        frame = pygame.surfarray.array3d(surface)
        frame = np.swapaxes(frame, 0, 1)  # Swap the axes as pygame and OpenCV store pixels differently
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert RGB to BGR for OpenCV
        
        # Write the frame
        self.video_writer.write(frame)
        
    def stop_recording(self):
        """Stop recording and save the files"""
        if not self.recording:
            return
            
        # Stop video recording
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            
        # Stop audio recording
        self.audio_recording = False
        if self.audio_thread:
            self.audio_thread.join(timeout=2.0)  # Wait for audio thread to finish
            
        # Close audio resources
        if self.pyaudio:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                
            # Save the audio frames to a WAV file
            self._save_audio()
            
            self.pyaudio.terminate()
            self.pyaudio = None
            
        # Combine audio and video
        self._combine_audio_video()
            
        self.recording = False
        game_state.recording = False
        print(f"Recording saved to {self.video_filename}")
        
    def _save_audio(self):
        """Save recorded audio frames to WAV file"""
        if len(self.audio_frames) == 0:
            print("No audio frames to save")
            return
            
        try:
            wf = wave.open(self.audio_filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.pyaudio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.audio_frames))
            wf.close()
            print(f"Audio saved to {self.audio_filename}")
        except Exception as e:
            print(f"Error saving audio: {e}")
            
    def _combine_audio_video(self):
        """Combine audio and video files into a single MP4 file"""
        if not os.path.exists(self.video_filename) or not os.path.exists(self.audio_filename):
            print("Video or audio file missing, cannot combine")
            return
            
        try:
            # Generate a temporary output filename
            output_file = self.video_filename.replace('.mp4', '_with_audio.mp4')
            
            # Use ffmpeg to combine audio and video
            import subprocess
            cmd = [
                'ffmpeg',
                '-i', self.video_filename,
                '-i', self.audio_filename,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-strict', 'experimental',
                output_file
            ]
            
            # Run the command
            subprocess.run(cmd, check=True)
            
            # Replace the original video file with the combined one
            os.replace(output_file, self.video_filename)
            
            # Remove the separate audio file
            os.remove(self.audio_filename)
            
            print(f"Combined audio and video into {self.video_filename}")
        except Exception as e:
            print(f"Error combining audio and video: {e}")
            print(f"The separate video and audio files have been preserved.")

# Global recorder instance
recorder = Recorder()