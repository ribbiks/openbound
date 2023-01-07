import pygame

from pygame.math import Vector2

class Cursor:
	def __init__(self, img_filenames):
		self.position = Vector2(0,0)
		self.img      = [pygame.image.load(n).convert_alpha() for n in img_filenames]
		self.img_i    = 0
		self.frame    = -1
		self.scale    = [(27,27), (33,33), (39,39), (33,33)]
		self.offset   = [Vector2(14,14), Vector2(17,17), Vector2(20,20), Vector2(17,17)]

	def start_click_animation(self, position, shift_pressed=False):
		self.frame = 0
		self.position = position
		if shift_pressed:
			self.img_i = 1
		else:
			self.img_i = 0

	def draw(self, screen):
		if self.frame >= 0:
			my_img = pygame.transform.scale(self.img[self.img_i], self.scale[self.frame])
			my_pos = self.position - self.offset[self.frame]
			screen.blit(my_img, my_pos)
			self.frame += 1
		if self.frame >= len(self.scale):
			self.frame = -1