import json
import pygame

from pygame.math import Vector2

from source.geometry  import point_in_box_excl
from source.globals   import GRID_SIZE
from source.misc_gfx  import Color

#
# base menu class
#
class SelectionMenu:
	def __init__(self, pos, content, font, num_rows=8, row_height=8, col_width=128, sort_field=None, offset=Vector2(4,4), autodeselect=False):
		self.pos     = pos
		self.content = []
		self.font    = font
		self.index   = 0
		self.offset  = Vector2(offset.x, offset.y)
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
		self.autodeselect  = autodeselect

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
		if self.autodeselect:
			self.is_selected = False
		if self.is_selected and self.current_delay <= 0 and self.index < len(self.content)-1:
			self.index += 1
			self.current_delay = 2
			if self.index >= self.current_range[1]:
				self.current_range = (self.index + 1 - self.num_rows, self.index + 1)
			return True
		return False

	def decrease_index(self):
		if self.autodeselect:
			self.is_selected = False
		if self.is_selected and self.current_delay <= 0 and self.index > 0:
			self.index -= 1
			self.current_delay = 2
			if self.index < self.current_range[0]:
				self.current_range = (self.index, self.index + self.num_rows)
			return True
		return False

	def update(self, mousepos, activation, release, inc_activation, dec_activation):
		if inc_activation:
			return self.increase_index()
		elif dec_activation:
			return self.decrease_index()
		else:
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
			if release:
				self.is_selected = False
			if self.current_delay > 0:
				self.current_delay -= 1
			if self.autodeselect:
				self.is_selected = False
			return output_bool

	def draw(self, screen):
		if not self.content and self.empty_message:
			self.font.render(screen, self.empty_message, self.pos + self.offset)
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
				offset = self.offset + Vector2(0, (i - self.current_range[0]) * self.row_height + 1)
				self.font.render(screen, self.content[i][0], self.pos + offset, max_width=self.col_width-4)

#
#
#
class MapMenu(SelectionMenu):
	def __init__(self, pos, mapfile_list, font, num_rows=15, row_height=16, col_width=248, sort_field=0, offset=Vector2(4,4), autodeselect=False):
		#
		super().__init__(pos, mapfile_list, font,
		                 num_rows=num_rows,
		                 row_height=row_height,
		                 col_width=col_width,
		                 sort_field=sort_field,
		                 offset=offset,
		                 autodeselect=autodeselect)
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
			                     int(json_dat['init_lives'])))	    # 8
		self.resort(sort_field)
		self.empty_message = 'no maps found.'

#
#
#
class UnitMenu(SelectionMenu):
	def __init__(self, pos, unitdat_list, font, num_rows=5, row_height=16, col_width=128, sort_field=None, offset=Vector2(4,4), autodeselect=False):
		#
		super().__init__(pos, unitdat_list, font,
		                 num_rows=num_rows,
		                 row_height=row_height,
		                 col_width=col_width,
		                 sort_field=sort_field,
		                 offset=offset,
		                 autodeselect=autodeselect)
		#
		self.empty_message = 'no units found.'
		self.is_selected   = False

	def get_selected_content(self):
		if not self.content:
			return None
		else:
			return self.content[self.index][0]

#
#
#
class TerrainMenu:
	def __init__(self, pos, tile_manager, tile_dim=1, num_rows=4, num_cols=10, row_height=24, col_width=24, sort_field=None, offset=Vector2(4,4)):
		#
		self.pos            = pos
		self.index          = 0
		self.num_rows       = num_rows
		self.row_height     = row_height
		self.col_width      = col_width
		self.current_delay  = 0
		self.tile_dim       = tile_dim
		self.tile_manager   = tile_manager
		self.wall_highlight = pygame.Surface(Vector2(self.tile_dim*GRID_SIZE, self.tile_dim*GRID_SIZE))
		self.wall_highlight.fill(Color.PAL_YEL_2)
		self.wall_highlight.set_alpha(128)
		#
		self.content = []
		if self.tile_dim == 1 and self.tile_manager.tile_1x1:
			self.content.append([])
			for i,tile_num in enumerate(self.tile_manager.tile_1x1):
				self.content[-1].append((tile_num, self.tile_manager.is_wall[tile_num[0]], self.tile_manager.tile_img[tile_num[0]]))
				if (i+1)%num_cols == 0 and i < len(tile_dat)-1:
					self.content.append([])
		elif self.tile_dim == 2 and self.tile_manager.tile_2x2:
			self.content.append([])
			for i,tile_num in enumerate(self.tile_manager.tile_2x2):
				self.content[-1].append((tile_num, self.tile_manager.is_wall_2x2[tile_num[0]], self.tile_manager.tile_img_2x2[tile_num[0]]))
				if (i+1)%num_cols == 0 and i < len(tile_dat)-1:
					self.content.append([])
		elif self.tile_dim == 4 and self.tile_manager.tile_4x4:
			self.content.append([])
			for i,tile_num in enumerate(self.tile_manager.tile_4x4):
				self.content[-1].append((tile_num, self.tile_manager.is_wall_4x4[tile_num[0]], self.tile_manager.tile_img_4x4[tile_num[0]]))
				if (i+1)%num_cols == 0 and i < len(tile_dat)-1:
					self.content.append([])
		#
		self.current_range = (0, min(self.num_rows, len(self.content)))
		self.is_selected   = False
		self.current_col   = 0

	def get_selected_content(self):
		if not self.content:
			return None
		else:
			return self.content[self.index][self.current_col]

	def move_up(self):
		if self.is_selected and self.current_delay <= 0 and self.index > 0:
			self.index -= 1
			self.current_delay = 2
			if self.index < self.current_range[0]:
				self.current_range = (self.index, self.index + self.num_rows)

	def move_down(self):
		if self.is_selected and self.current_delay <= 0 and self.index < len(self.content)-1:
			self.index += 1
			self.current_delay = 2
			self.current_col = min(self.current_col, len(self.content[self.index])-1)
			if self.index >= self.current_range[1]:
				self.current_range = (self.index + 1 - self.num_rows, self.index + 1)

	def move_left(self):
		if self.is_selected and self.current_delay <= 0 and self.current_col > 0:
			self.current_col  -= 1
			self.current_delay = 2

	def move_right(self):
		if self.is_selected and self.current_delay <= 0 and self.current_col < len(self.content[self.index])-1:
			self.current_col  += 1
			self.current_delay = 2

	def update(self, mousepos, activation, release):
		which_index = None
		which_col   = None
		for i in range(self.current_range[0], self.current_range[1]):
			for j in range(len(self.content[i])):
				tl = self.pos + Vector2(j*self.col_width, (i - self.current_range[0]) * self.row_height)
				br = self.pos + Vector2((j+1)*self.col_width, (i - self.current_range[0] + 1) * self.row_height)
				if point_in_box_excl(mousepos, tl, br):
					which_index = i
					which_col   = j
					break
			if which_index != None:
				break
		output_bool = False
		if activation and which_index != None:
			self.index = which_index
			self.current_col = which_col
			self.is_selected = True
			output_bool = True
		elif activation:
			self.is_selected = False
		if release:
			self.is_selected = False
		if self.current_delay > 0:
			self.current_delay -= 1
		return output_bool

	def draw(self, screen, highlight_walls=False):
		if self.content:
			tl = self.pos + Vector2(self.current_col*self.col_width, (self.index - self.current_range[0]) * self.row_height)
			br = self.pos + Vector2((self.current_col+1)*self.col_width, (self.index - self.current_range[0] + 1) * self.row_height)
			my_rect = pygame.Rect(tl, br-tl)
			if self.is_selected:
				pygame.draw.rect(screen, Color.PAL_BLUE_3, my_rect, border_radius=2)
			else:
				pygame.draw.rect(screen, Color.PAL_BLUE_4, my_rect, border_radius=2)
			#
			for i in range(self.current_range[0], self.current_range[1]):
				for j in range(len(self.content[i])):
					offset = Vector2(j*self.col_width + 4, (i - self.current_range[0])*self.row_height + 4)
					my_pos = self.pos + offset
					if self.content[i][j][2] != None:
						screen.blit(self.content[i][j][2], my_pos)
					else:
						dx = Vector2(self.tile_dim*GRID_SIZE, 0)
						dy = Vector2(0, self.tile_dim*GRID_SIZE)
						pygame.draw.line(screen, Color.PAL_BLUE_3,       my_pos,    my_pos+dx, width=1)
						pygame.draw.line(screen, Color.PAL_BLUE_3,    my_pos+dx, my_pos+dx+dy, width=1)
						pygame.draw.line(screen, Color.PAL_BLUE_3, my_pos+dx+dy,    my_pos+dy, width=1)
						pygame.draw.line(screen, Color.PAL_BLUE_3,    my_pos+dy,       my_pos, width=1)
					if highlight_walls and self.content[i][j][1]:
						screen.blit(self.wall_highlight, my_pos, special_flags=pygame.BLEND_ALPHA_SDL2)
