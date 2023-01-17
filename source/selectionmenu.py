import json
import pygame

from pygame.math import Vector2

from source.geometry import point_in_box_excl
from source.misc_gfx import Color

NUM_ROWS   = 15
ROW_HEIGHT = 16
COL_WIDTH  = 248

class SelectionMenu:
	def __init__(self, mapfile_list, pos, font_dict, sort_field=0):
		self.pos     = pos
		self.content = []
		self.index   = 0
		#
		for (filename_clean, fn) in mapfile_list:
			with open(fn,'r') as f:
				json_dat = json.load(f)
			self.content.append((filename_clean,				# 0 - sort by fn
			                     fn,							# 1
			                     json_dat['map_name'],			# 2
			                     json_dat['map_author'],		# 3 - sort by author
			                     json_dat['map_notes'],			# 4
			                     json_dat['difficulty'],		# 5 - sort by diff
			                     json_dat['map_width'],			# 6
			                     json_dat['map_height'],		# 7
			                     json_dat['starting_lives']))	# 8
		self.resort(sort_field)
		self.font_dict = font_dict
		self.current_delay = 0
		self.current_range = (0, min(NUM_ROWS, len(self.content)))

	def resort(self, sort_field):
		sorted_content = sorted([(n[sort_field], n) for n in self.content])
		self.content   = [n[1] for n in sorted_content]
		self.index     = 0

	def get_selected_mapinfo(self):
		if not self.content:
			return None
		return self.content[self.index]

	def increase_index(self):
		if self.current_delay <= 0 and self.index < len(self.content)-1:
			self.index += 1
			self.current_delay = 2
			if self.index >= self.current_range[1]:
				self.current_range = (self.index + 1 - NUM_ROWS, self.index + 1)

	def decrease_index(self):
		if self.current_delay <= 0 and self.index > 0:
			self.index -= 1
			self.current_delay = 2
			if self.index < self.current_range[0]:
				self.current_range = (self.index, self.index + NUM_ROWS)

	def update(self, mousepos, activation):
		which_index = None
		for i in range(self.current_range[0], self.current_range[1]):
			tl = self.pos + Vector2(0, (i - self.current_range[0]) * ROW_HEIGHT)
			br = self.pos + Vector2(COL_WIDTH, (i - self.current_range[0] + 1) * ROW_HEIGHT)
			if point_in_box_excl(mousepos, tl, br):
				which_index = i
				break
		if activation and which_index != None:
			self.index = which_index
		if self.current_delay > 0:
			self.current_delay -= 1

	def draw(self, screen):
		if not self.content:
			offset = Vector2(4,4)
			self.font_dict['small_w'].render(screen, 'no maps found...', self.pos + offset)
		else:
			tl = self.pos + Vector2(0, (self.index - self.current_range[0]) * ROW_HEIGHT)
			br = self.pos + Vector2(COL_WIDTH, (self.index - self.current_range[0] + 1) * ROW_HEIGHT)
			my_rect = pygame.Rect(tl, br-tl)
			pygame.draw.rect(screen, Color.PAL_BLUE_4, my_rect, border_radius=2)
			#
			for i in range(self.current_range[0], self.current_range[1]):
				offset = Vector2(4, (i - self.current_range[0]) * ROW_HEIGHT + 5)
				self.font_dict['small_w'].render(screen, self.content[i][0], self.pos + offset)
