import pygame

from pygame.math import Vector2

from source.geometry import point_in_box_excl
from source.globals  import GRID_SIZE

class DraggableObject:
	def __init__(self, center_pos, radius, grid_snap=GRID_SIZE, pos_offset=Vector2(-int(GRID_SIZE/2), -int(GRID_SIZE/2))):
		self.center_pos   = center_pos
		self.radius       = radius
		self.grid_snap    = grid_snap
		self.pos_offset   = Vector2(pos_offset.x, pos_offset.y)
		self.is_selected  = False
		self.is_mouseover = False
		self.images = []

	def add_image(self, img_fn):
		self.images.append(pygame.image.load(img_fn).convert_alpha())

	def update(self, mousepos, grab_action, release_action):
		tl = Vector2(self.center_pos.x - self.radius, self.center_pos.y - self.radius)
		br = Vector2(self.center_pos.x + self.radius, self.center_pos.y + self.radius)
		self.is_mouseover = point_in_box_excl(mousepos, tl, br)
		released = False
		if grab_action:
			if self.is_mouseover:
				self.is_selected = True
			elif self.is_selected:
				self.is_selected = False
		if self.is_selected and release_action:
			self.is_selected = False
			released = True
		#
		if self.is_selected:
			snap_x = int(mousepos.x/self.grid_snap + 0.5) * self.grid_snap
			snap_y = int(mousepos.y/self.grid_snap + 0.5) * self.grid_snap
			self.center_pos = Vector2(snap_x, snap_y) + self.pos_offset
		return released

	def draw(self, screen, offset):
		for img in self.images:
			new_rect = img.get_rect(center=img.get_rect(center=self.center_pos+offset).center)
			screen.blit(img, new_rect)
