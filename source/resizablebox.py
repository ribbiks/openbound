import pygame

from pygame.math import Vector2

from source.misc_gfx import Color
from source.geometry import point_in_box_excl, value_clamp
from source.globals  import GRID_SIZE

class ResizableBox:
	def __init__(self, tl, br, text, font,
	             box_color=Color.PAL_BLUE_3,
	             box_color_highlight=Color.PAL_BLUE_2B,
	             line_color=Color.PAL_BLUE_3,
	             line_color_highlight=Color.PAL_BLUE_1):
		self.tl = tl
		self.br = br
		self.is_mouseover   = False
		self.is_selected    = False
		self.clickdown_pos  = None
		self.drag_mode      = (0,0,0,0)
		self.edges_selected = (0,0,0,0)
		self.dragging_whole = False
		#
		self.font                 = font
		self.text                 = text
		self.box_color            = box_color
		self.box_color_highlight  = box_color_highlight
		self.line_color           = line_color
		self.line_color_highlight = line_color_highlight
		self.line_width           = 1

	def get_area(self):
		dx = self.br.x - self.tl.x
		dy = self.br.y - self.tl.y
		return dx*dy

	def update(self, mousepos, grab_action, release_action, limits):
		self.is_mouseover = point_in_box_excl(mousepos, self.tl, self.br)
		released = False
		if grab_action:
			if self.is_mouseover:
				self.is_selected = True
			elif self.is_selected:
				self.is_selected    = False
				self.clickdown_pos  = None
				self.drag_mode      = (0,0,0,0)
				self.dragging_whole = False
		if self.is_selected and release_action:
			self.is_selected    = False
			self.clickdown_pos  = None
			self.drag_mode      = (0,0,0,0)
			self.dragging_whole = False
			released = True
		#
		eps = 10
		if self.br.x - self.tl.x <= GRID_SIZE or self.br.y - self.tl.y <= GRID_SIZE:
			eps = 5
		left_box   = (self.tl, Vector2(self.tl.x+eps, self.br.y))
		top_box    = (self.tl, Vector2(self.br.x, self.tl.y+eps))
		right_box  = (Vector2(self.br.x-eps, self.tl.y), self.br)
		bottom_box = (Vector2(self.tl.x, self.br.y-eps), self.br)
		self.edges_selected = [1 * point_in_box_excl(mousepos, left_box[0],   left_box[1]  ),
		                       1 * point_in_box_excl(mousepos, top_box[0],    top_box[1]   ),
		                       1 * point_in_box_excl(mousepos, right_box[0],  right_box[1] ),
		                       1 * point_in_box_excl(mousepos, bottom_box[0], bottom_box[1])]
		if self.is_selected:
			if self.drag_mode == (0,0,0,0) and self.clickdown_pos == None:
				self.drag_mode = tuple(self.edges_selected[:])
				self.clickdown_pos = Vector2(mousepos.x, mousepos.y)
			snap_x = int(mousepos.x/GRID_SIZE + 0.5) * GRID_SIZE
			snap_y = int(mousepos.y/GRID_SIZE + 0.5) * GRID_SIZE
			#
			# drag left
			#
			if self.drag_mode[0]:
				if self.br.x - snap_x >= GRID_SIZE:
					self.tl = Vector2(max(snap_x,0), self.tl.y)
			#
			# drag top
			#
			if self.drag_mode[1]:
				if self.br.y - snap_y >= GRID_SIZE:
					self.tl = Vector2(self.tl.x, max(snap_y,0))
			#
			# drag right
			#
			if self.drag_mode[2]:
				if snap_x - self.tl.x >= GRID_SIZE:
					self.br = Vector2(min(snap_x,limits.x), self.br.y)
			#
			# drag bottom
			#
			if self.drag_mode[3]:
				if snap_y - self.tl.y >= GRID_SIZE:
					self.br = Vector2(self.br.x, min(snap_y,limits.y))
			#
			# drag entire box
			#
			if self.drag_mode == (0,0,0,0):
				new_tl = self.tl + mousepos - self.clickdown_pos
				new_tl = Vector2(int(new_tl.x/GRID_SIZE + 0.5) * GRID_SIZE, int(new_tl.y/GRID_SIZE + 0.5) * GRID_SIZE)
				dbox   = self.br - self.tl
				# snap against limits
				new_tl = Vector2(min(new_tl.x, limits.x-dbox.x), min(new_tl.y, limits.y-dbox.y))
				new_tl = Vector2(value_clamp(new_tl.x, 0, limits.x-dbox.x), value_clamp(new_tl.y, 0, limits.y-dbox.y))
				new_br = new_tl + dbox
				dtl    = new_tl - self.tl
				if new_tl.x >= 0 and new_tl.y >= 0 and new_br.x <= limits.x and new_br.y <= limits.y:
					self.tl = Vector2(new_tl.x, new_tl.y)
					self.br = Vector2(new_br.x, new_br.y)
					self.clickdown_pos += dtl
				self.dragging_whole = True
		return released

	def draw(self, screen, offset, mouseover_condition):
		box_surface = pygame.Surface(screen.get_size())
		tl = Vector2(self.tl.x + 1, self.tl.y + 1)
		br = Vector2(self.br.x - 1, self.br.y - 1)
		my_rect = pygame.Rect(tl + offset, br - tl)
		#
		col = self.box_color
		if mouseover_condition and (self.dragging_whole or self.is_mouseover or any(self.drag_mode)):
			col = self.box_color_highlight
		pygame.draw.rect(box_surface, col, my_rect)
		box_surface.set_alpha(96)
		screen.blit(box_surface, (0,0), special_flags=pygame.BLEND_ALPHA_SDL2)
		#
		col = self.line_color
		if mouseover_condition and self.dragging_whole == False and (self.edges_selected[0] or self.drag_mode[0]):
			col = self.line_color_highlight
		pygame.draw.line(screen, col, Vector2(self.tl.x, self.br.y-1) + offset, self.tl + offset, width=self.line_width)
		#
		col = self.line_color
		if mouseover_condition and self.dragging_whole == False and (self.edges_selected[1] or self.drag_mode[1]):
			col = self.line_color_highlight
		pygame.draw.line(screen, col, self.tl + offset, Vector2(self.br.x-1, self.tl.y) + offset, width=self.line_width)
		#
		col = self.line_color
		if mouseover_condition and self.dragging_whole == False and (self.edges_selected[2] or self.drag_mode[2]):
			col = self.line_color_highlight
		pygame.draw.line(screen, col, Vector2(self.br.x-1, self.tl.y) + offset, self.br - Vector2(1,1) + offset, width=self.line_width)
		#
		col = self.line_color
		if mouseover_condition and self.dragging_whole == False and (self.edges_selected[3] or self.drag_mode[3]):
			col = self.line_color_highlight
		pygame.draw.line(screen, col, self.br - Vector2(1,1) + offset, Vector2(self.tl.x, self.br.y-1) + offset, width=self.line_width)
		#
		text_width = self.br.x - self.tl.x - 4
		self.font.render(screen, self.text, self.tl + offset + Vector2(4,4), max_width=text_width)
