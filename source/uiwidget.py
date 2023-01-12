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

	def add_element(self, obj_type, obj_content, mouseover_condition=(True,True)):
		self.object_types.append(obj_type)
		self.mouseover_draw.append(mouseover_condition)
		#
		# IMAGE: obj_content = (pos, img_fn)
		#
		if obj_type == 'image':
			self.object_data.append((obj_content[0], pygame.image.load(obj_content[1]).convert_alpha()))
		#
		# LINE: obj_content = (p1, p2, width, color)
		#
		elif obj_type == 'line':
			self.object_data.append((obj_content[0], obj_content[1], obj_content[2], obj_content[3]))
		#
		# BOX: obj_content = (topleft, bottomright, color, border_radius)
		#
		elif obj_type == 'rect':
			self.object_data.append((obj_content[0], obj_content[1], obj_content[2], obj_content[3]))
		#
		# TEXT: obj_content = (text, text_key, pos, font_object, color)
		#
		elif obj_type == 'text':
			self.text_data[obj_content[1]] = obj_content[0]
			self.object_data.append((obj_content[1], obj_content[2], obj_content[3], obj_content[4]))

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
					(p1, p2, width, color) = obj_dat
					pygame.draw.line(screen, color, p1, p2, width=width)
				#
				#
				elif self.object_types[i] == 'rect':
					(tl, br, color, border_r) = obj_dat
					my_rect = pygame.Rect(tl, br-tl)
					pygame.draw.rect(screen, color, my_rect, border_radius=border_r)
				#
				#
				elif self.object_types[i] == 'text':
					(text_key, pos, font, color) = obj_dat
					text = font.render(self.text_data[text_key], True, color)
					text_rect = text.get_rect(center=pos)
					screen.blit(text, text_rect)
