import pygame

from pygame.math import Vector2

class UIWidget:
	def __init__(self):
		self.object_types = []
		self.object_data  = []
		self.text_data    = {}

	def add_element(self, obj_type, obj_content):
		self.object_types.append(obj_type)
		#
		# IMAGE: obj_content = (pos, img_fn)
		#
		if obj_type == 'image':
			self.object_data.append((obj_content[0], pygame.image.load(obj_content[1]).convert_alpha()))
		#
		# BOX: obj_content = (topleft, bottomright, color)
		#
		elif obj_type == 'box':
			self.object_data.append((obj_content[0], obj_content[1], obj_content[2]))
		#
		# TEXT: obj_content = (text, text_key, pos, font_object, color)
		#
		elif obj_type == 'text':
			self.text_data[obj_content[1]] = obj_content[0]
			self.object_data.append((obj_content[1], obj_content[2], obj_content[3], obj_content[4]))

	def draw(self, screen):
		for i,n in enumerate(self.object_data):
			#
			#
			#
			if self.object_types[i] == 'image':
				screen.blit(n[1], n[0])
			#
			#
			#
			elif self.object_types[i] == 'box':
				p = [n[0], Vector2(n[1].x, n[0].y), n[1], Vector2(n[0].x, n[1].y)]
				pygame.draw.polygon(screen, n[2], p)
			#
			#
			#
			elif self.object_types[i] == 'text':
				text = n[2].render(self.text_data[n[0]], True, n[3])
				screen.blit(text, n[1])
