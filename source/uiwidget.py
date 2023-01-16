import pygame

from pygame.math import Vector2

from source.geometry import point_in_box_excl

class UIWidget:
	def __init__(self):
		self.object_types   = []
		self.object_data    = []
		self.text_data      = {}
		self.is_mouseover   = False
		self.mouseover_draw = []
		self.return_msg     = ''

	def add_image(self, pos, img_fn, mouseover_condition=(True,True)):
		self.object_types.append('image')
		self.mouseover_draw.append(mouseover_condition)
		self.object_data.append((pos, pygame.image.load(img_fn).convert_alpha()))

	def add_line(self, p1, p2, color, width=1, mouseover_condition=(True,True)):
		self.object_types.append('line')
		self.mouseover_draw.append(mouseover_condition)
		self.object_data.append((p1, p2, color, width))

	def add_rect(self, tl, br, color, border_radius=0, mouseover_condition=(True,True)):
		self.object_types.append('rect')
		self.mouseover_draw.append(mouseover_condition)
		self.object_data.append((tl, br, color, border_radius))

	def add_text(self, pos, text, text_key, font_object, is_centered=False, max_width=-1, num_rows=1, mouseover_condition=(True,True)):
		self.object_types.append('text')
		self.mouseover_draw.append(mouseover_condition)
		self.text_data[text_key] = text
		self.object_data.append((pos, text_key, font_object, is_centered, max_width, num_rows))

	def add_return_message(self, msg):
		self.return_msg = msg

	def update(self, mousepos, activation):
		self.is_mouseover = False
		for i,n in enumerate(self.object_data):
			if self.object_types[i] == 'rect':
				(tl, br, color, border_r) = n
				if point_in_box_excl(mousepos, tl, br):
					self.is_mouseover = True
					break
		if self.is_mouseover and activation:
			return self.return_msg
		return ''

	def draw(self, screen):
		for i,obj_dat in enumerate(self.object_data):
			if (self.is_mouseover and self.mouseover_draw[i][1]) or (not self.is_mouseover and self.mouseover_draw[i][0]):
				#
				#
				if self.object_types[i] == 'image':
					(pos, img) = obj_dat
					screen.blit(img, pos)
				#
				#
				elif self.object_types[i] == 'line':
					(p1, p2, color, width) = obj_dat
					pygame.draw.line(screen, color, p1, p2, width=width)
				#
				#
				elif self.object_types[i] == 'rect':
					(tl, br, color, border_radius) = obj_dat
					my_rect = pygame.Rect(tl, br-tl)
					pygame.draw.rect(screen, color, my_rect, border_radius=border_radius)
				#
				#
				elif self.object_types[i] == 'text':
					(pos, text_key, font, is_centered, max_width, num_rows) = obj_dat
					font.render(screen, self.text_data[text_key], pos, centered=is_centered, max_width=max_width, num_rows=num_rows)
