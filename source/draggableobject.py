import pygame

from pygame.math import Vector2

from source.geometry import point_in_box_excl, value_clamp
from source.globals  import GRID_SIZE

CLICK_BUFF = 8

class DraggableObject:
	def __init__(self, center_pos, radius, grid_snap=GRID_SIZE, pos_offset=Vector2(-int(GRID_SIZE/2), -int(GRID_SIZE/2)), init_image_fn=None):
		self.center_pos   = center_pos
		self.radius       = radius
		self.grid_snap    = grid_snap
		self.pos_offset   = Vector2(pos_offset.x, pos_offset.y)
		self.is_selected  = False
		self.is_mouseover = False
		self.images = []
		if init_image_fn != None:
			self.add_image(init_image_fn)

	def add_image(self, img_fn):
		self.images.append(pygame.image.load(img_fn).convert_alpha())

	def update(self, mousepos, grab_action, release_action, limits):
		tl = Vector2(self.center_pos.x - self.radius - CLICK_BUFF, self.center_pos.y - self.radius - CLICK_BUFF)
		br = Vector2(self.center_pos.x + self.radius + CLICK_BUFF, self.center_pos.y + self.radius + CLICK_BUFF)
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
			snap_x = int((mousepos.x - self.pos_offset.x)/self.grid_snap + 0.5) * self.grid_snap
			snap_y = int((mousepos.y - self.pos_offset.y)/self.grid_snap + 0.5) * self.grid_snap
			snap_x = value_clamp(snap_x, limits[0].x + self.radius - self.pos_offset.x, limits[1].x - self.radius - self.pos_offset.x)
			snap_y = value_clamp(snap_y, limits[0].y + self.radius - self.pos_offset.y, limits[1].y - self.radius - self.pos_offset.y)
			self.center_pos = Vector2(snap_x, snap_y) + self.pos_offset
		return released

	def draw(self, screen, offset):
		for img in self.images:
			new_rect = img.get_rect(center=img.get_rect(center=self.center_pos+offset).center)
			screen.blit(img, new_rect)
