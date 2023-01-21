import pygame

from pygame.math import Vector2

from source.geometry import point_in_box_excl
from source.globals  import GRID_SIZE

class DraggableObject:
	def __init__(self, center_pos, radius):
		self.center_pos  = center_pos
		self.radius      = radius
		self.is_selected = False
		self.images = []

	def add_image(self, img_fn):
		self.images.append(pygame.image.load(img_fn).convert_alpha())

	def update(self, mousepos, grab_action, release_action):
		tl = Vector2(self.center_pos.x - self.radius, self.center_pos.y - self.radius)
		br = Vector2(self.center_pos.x + self.radius, self.center_pos.y + self.radius)
		released = False
		if grab_action:
			if point_in_box_excl(mousepos, tl, br):
				self.is_selected = True
			elif self.is_selected:
				self.is_selected = False
		if self.is_selected and release_action:
			self.is_selected = False
			released = True
		#
		if self.is_selected:
			snap_x = int(mousepos.x/GRID_SIZE + 0.5) * GRID_SIZE - int(GRID_SIZE/2)
			snap_y = int(mousepos.y/GRID_SIZE + 0.5) * GRID_SIZE - int(GRID_SIZE/2)
			self.center_pos = Vector2(snap_x, snap_y)
		return released

	def draw(self, screen, offset):
		for img in self.images:
			new_rect = img.get_rect(center=img.get_rect(center=self.center_pos+offset).center)
			screen.blit(img, new_rect)
