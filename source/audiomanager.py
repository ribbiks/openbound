import pygame

# a class that loads audio into memory, plays them when requested

class AudioManager:
	def __init__(self):
		self.all_sounds = {}
	
	def add_sound(self, sound_fn, sound_name):
		self.all_sounds[sound_name] = pygame.mixer.Sound(sound_fn)

	def play_music(self, music_fn, volume=1.0, loop=True):
		pygame.mixer.music.load(music_fn)
		if loop:
			pygame.mixer.music.play(-1)
		else:
			pygame.mixer.music.play(0)
		pygame.mixer.music.set_volume(volume)

	def play_sound(self, sound_name, volume=1.0):
		self.all_sounds[sound_name].play()
		self.all_sounds[sound_name].set_volume(volume)

	def stop_music(self):
		pygame.mixer.music.stop()
