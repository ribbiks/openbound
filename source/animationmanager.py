import pygame

from pygame.math import Vector2

# a class that loads gfx into memory, draws active animations

class AnimationManager:
	def __init__(self):
		self.all_animations = {}
		self.img_offsets    = {}	# for drawing centered
		self.active_animations = []

	def add_animation_cycle(self, img_fn_sequence, img_name):
		self.all_animations[img_name] = [pygame.image.load(n).convert_alpha() for n in img_fn_sequence]
		self.img_offsets[img_name]    = [Vector2(int(n.get_width()/2), int(n.get_height()/2)) for n in self.all_animations[img_name]]

	def start_new_animation(self, img_name, position, centered=True):
		self.active_animations.append([0, img_name, position, centered])

	def draw(self, screen, offset):
		for i,v in enumerate(self.active_animations):
			my_img = self.all_animations[v[1]][v[0]]
			my_pos = v[2]
			is_centered = v[3]
			if is_centered:
				centering_offset = self.img_offsets[v[1]][v[0]]
			else:
				centering_offset = Vector2(0,0)
			screen.blit(my_img, my_pos - centering_offset + offset)
			self.active_animations[i][0] += 1
		self.active_animations = [n for n in self.active_animations if n[0] < len(self.all_animations[n[1]])]
