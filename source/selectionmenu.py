import json
import pygame

from pygame.math import Vector2

from source.geometry import point_in_box_excl
from source.misc_gfx import Color

#
# base menu class
#
class SelectionMenu:
	def __init__(self, pos, content, font, num_rows=8, row_height=8, col_width=128, sort_field=None):
		self.pos     = pos
		self.content = []
		self.font    = font
		self.index   = 0
		#
		self.content = [(n,) for n in content]
		if sort_field != None and sort_field >= 0:
			self.resort(sort_field)
		#
		self.num_rows   = num_rows
		self.row_height = row_height
		self.col_width  = col_width
		#
		self.current_delay = 0
		self.current_range = (0, min(self.num_rows, len(self.content)))
		self.empty_message = ''
		self.is_selected   = True

	def resort(self, sort_field):
		sorted_content = sorted([(n[sort_field], n) for n in self.content])
		self.content   = [n[1] for n in sorted_content]
		self.index     = 0

	def get_selected_content(self, sanitize=False):
		if not self.content:
			return None
		if sanitize:
			return (self.font.sanitize(str(n)) for n in self.content[self.index])
		else:
			return (n for n in self.content[self.index])

	def increase_index(self):
		if self.is_selected and self.current_delay <= 0 and self.index < len(self.content)-1:
			self.index += 1
			self.current_delay = 2
			if self.index >= self.current_range[1]:
				self.current_range = (self.index + 1 - self.num_rows, self.index + 1)

	def decrease_index(self):
		if self.is_selected and self.current_delay <= 0 and self.index > 0:
			self.index -= 1
			self.current_delay = 2
			if self.index < self.current_range[0]:
				self.current_range = (self.index, self.index + self.num_rows)

	def update(self, mousepos, activation):
		which_index = None
		for i in range(self.current_range[0], self.current_range[1]):
			tl = self.pos + Vector2(0, (i - self.current_range[0]) * self.row_height)
			br = self.pos + Vector2(self.col_width, (i - self.current_range[0] + 1) * self.row_height)
			if point_in_box_excl(mousepos, tl, br):
				which_index = i
				break
		output_bool = False
		if activation and which_index != None:
			self.index = which_index
			self.is_selected = True
			output_bool = True
		elif activation:
			self.is_selected = False
		if self.current_delay > 0:
			self.current_delay -= 1
		return output_bool

	def draw(self, screen):
		if not self.content and self.empty_message:
			offset = Vector2(4,4)
			self.font.render(screen, self.empty_message, self.pos + offset)
		else:
			tl = self.pos + Vector2(0, (self.index - self.current_range[0]) * self.row_height)
			br = self.pos + Vector2(self.col_width, (self.index - self.current_range[0] + 1) * self.row_height)
			my_rect = pygame.Rect(tl, br-tl)
			if self.is_selected:
				pygame.draw.rect(screen, Color.PAL_BLUE_3, my_rect, border_radius=2)
			else:
				pygame.draw.rect(screen, Color.PAL_BLUE_4, my_rect, border_radius=2)
			#
			for i in range(self.current_range[0], self.current_range[1]):
				offset = Vector2(4, (i - self.current_range[0]) * self.row_height + 5)
				self.font.render(screen, self.content[i][0], self.pos + offset, max_width=self.col_width-4)

#
#
#
class MapMenu(SelectionMenu):
	def __init__(self, pos, mapfile_list, font, num_rows=15, row_height=16, col_width=248, sort_field=0):
		#
		super().__init__(pos, mapfile_list, font,
		                 num_rows=num_rows,
		                 row_height=row_height,
		                 col_width=col_width,
		                 sort_field=sort_field)
		#
		self.content = []
		for (filename_clean, fn) in mapfile_list:
			with open(fn,'r') as f:
				json_dat = json.load(f)
			self.content.append((filename_clean,					# 0 - sort by fn
			                     fn,								# 1
			                     json_dat['map_name'],				# 2
			                     json_dat['map_author'],			# 3 - sort by author
			                     json_dat['map_notes'],				# 4
			                     int(json_dat['difficulty']),		# 5 - sort by diff
			                     int(json_dat['map_width']),		# 6
			                     int(json_dat['map_height']),		# 7
			                     int(json_dat['starting_lives'])))	# 8
		self.resort(sort_field)
		self.empty_message = 'no maps found.'

#
#
#
class UnitMenu(SelectionMenu):
	def __init__(self, pos, unitdat_list, font, num_rows=5, row_height=16, col_width=128, sort_field=None):
		#
		super().__init__(pos, unitdat_list, font,
		                 num_rows=num_rows,
		                 row_height=row_height,
		                 col_width=col_width,
		                 sort_field=sort_field)
		#
		self.empty_message = 'no units found.'
		self.is_selected   = False

	def get_selected_content(self):
		if not self.content:
			return None
		else:
			return self.content[self.index][0]
