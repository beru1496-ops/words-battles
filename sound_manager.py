import pygame
import os
import threading
import time
from gtts import gTTS

class SoundManager:
    """Manages BGM, SE, and Text-to-Speech (TTS) with async generation."""
    

    def __init__(self):
        # Initialize mixer
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"Warning: Failed to initialize mixer: {e}")

        # Paths
        self.voice_dir = os.path.join("assets", "voice")
        self.sound_dir = os.path.join("assets", "sounds")
        
        # Ensure directories exist
        os.makedirs(self.voice_dir, exist_ok=True)
        os.makedirs(self.sound_dir, exist_ok=True)
        
        # Caches
        self.voice_cache = {}  # {word: pygame.mixer.Sound}
        self.se_cache = {}     # {filename: pygame.mixer.Sound}
        
        # Async State
        self.generation_queue = []  # List of words pending generation
        self.ready_queue = []       # List of (word, path) ready to play
        self.generating_words = set() 
        self.lock = threading.Lock()
        
        # Auto-play request
        self.pending_play = None # Word requested to play but generation pending
        
        # Volume levels (0.0 - 1.0)
        self.volume_bgm = 0.3
        self.volume_se = 0.6
        self.volume_voice = 0.8
        
        # Daemon thread for generation
        self.thread = threading.Thread(target=self._generation_worker, daemon=True)
        self.thread.start()

    def update(self):
        """Call this in main loop to handle callbacks from threads."""
        with self.lock:
            while self.ready_queue:
                word, path = self.ready_queue.pop(0)
                try:
                    sound = pygame.mixer.Sound(path)
                    self.voice_cache[word] = sound
                    
                    # If this was the pending word, play it
                    if self.pending_play == word:
                        sound.play()
                        self.pending_play = None
                except Exception as e:
                    print(f"Error loading generated voice for {word}: {e}")

    def play_bgm(self, filename):
        """Play BGM on loop."""
        path = os.path.join(self.sound_dir, filename)
        if not os.path.exists(path):
            # print(f"BGM not found: {path}")
            return
            
        # Check if already playing
        if getattr(self, 'current_bgm', None) == filename and pygame.mixer.music.get_busy():
            return
            
        try:
            pygame.mixer.music.load(path)
            # Loop -1 means infinite loop
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(self.volume_bgm)
            self.current_bgm = filename
        except Exception as e:
            print(f"Error playing BGM: {e}")

    def stop_bgm(self):
        pygame.mixer.music.stop()
    
    def set_volume_bgm(self, vol):
        """Set BGM volume (0.0-1.0)."""
        self.volume_bgm = max(0.0, min(1.0, vol))
        pygame.mixer.music.set_volume(self.volume_bgm)
    
    def set_volume_se(self, vol):
        """Set SE volume (0.0-1.0)."""
        self.volume_se = max(0.0, min(1.0, vol))
        for sound in self.se_cache.values():
            sound.set_volume(self.volume_se)
    
    def set_volume_voice(self, vol):
        """Set Voice volume (0.0-1.0)."""
        self.volume_voice = max(0.0, min(1.0, vol))
        for sound in self.voice_cache.values():
            sound.set_volume(self.volume_voice)

    def play_se(self, filename):
        """Play Sound Effect."""
        if filename in self.se_cache:
            self.se_cache[filename].play()
            return
            
        path = os.path.join(self.sound_dir, filename)
        if not os.path.exists(path):
            return
            
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self.volume_se)
            self.se_cache[filename] = sound
            sound.play()
        except Exception as e:
            print(f"Error playing SE {filename}: {e}")

    def play_voice(self, word):
        """Play TTS for a word. Generate if missing."""
        word = word.lower().strip()
        if not word:
            return

        # 1. Memory Cache
        if word in self.voice_cache:
            self.voice_cache[word].set_volume(self.volume_voice)
            self.voice_cache[word].play()
            return

        # 2. Disk Cache
        filename = f"{word}.mp3"
        path = os.path.join(self.voice_dir, filename)
        
        if os.path.exists(path):
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(self.volume_voice)
                self.voice_cache[word] = sound
                sound.play()
                return
            except Exception as e:
                print(f"Error loading voice cache for {word}: {e}")
                # Fallthrough to regenerate

        # 3. Generate (Async)
        self.pending_play = word # Set request
        
        with self.lock:
            if word not in self.generating_words:
                self.generation_queue.append(word)
                self.generating_words.add(word)

    def _generation_worker(self):
        """Background thread to process TTS generation queue."""
        while True:
            word_to_process = None
            
            with self.lock:
                if self.generation_queue:
                    word_to_process = self.generation_queue.pop(0)
            
            if word_to_process:
                self._generate_and_cache(word_to_process)
            else:
                time.sleep(0.1)

    def _generate_and_cache(self, word):
        """Generate mp3 using gTTS and save to disk."""
        filename = f"{word}.mp3"
        path = os.path.join(self.voice_dir, filename)
        
        try:
            # Generate
            tts = gTTS(text=word, lang='en')
            tts.save(path)
            
            with self.lock:
                self.ready_queue.append((word, path))
                self.generating_words.discard(word)
            
        except Exception as e:
            print(f"Error generating TTS for {word}: {e}")
            with self.lock:
                self.generating_words.discard(word)
