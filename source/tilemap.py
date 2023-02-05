import pygame
import numpy as np

from pygame.math import Vector2

from source.globals   import GRID_SIZE
from source.misc_gfx  import Color
from source.tile_data import TILE_DATA

class TileMap:
	def __init__(self, tile_filename_list):
		self.tile_fns = {}
		for i,my_tile_fn in enumerate(tile_filename_list):
			if my_tile_fn:
				self.tile_fns[i] = my_tile_fn
		self.tile_keys = sorted(TILE_DATA.keys())
		self.tile_dat = []
		for k in self.tile_keys:
			if k in self.tile_fns:
				self.tile_dat.append((k, TILE_DATA[k][0], TILE_DATA[k][1], pygame.image.load(self.tile_fns[k]).convert()))
			else:
				self.tile_dat.append((k, TILE_DATA[k][0], TILE_DATA[k][1], None))
		self.wall_highlight = pygame.Surface(Vector2(GRID_SIZE, GRID_SIZE))
		self.wall_highlight.fill(Color.PAL_YEL_2)
		self.wall_highlight.set_alpha(128)

	def draw(self, screen, offset, map_array, highlight_walls=False):
		for x in range(map_array.shape[0]):
			for y in range(map_array.shape[1]):
				my_pos = Vector2(x*GRID_SIZE, y*GRID_SIZE)
				my_tid = map_array[x,y]
				if self.tile_dat[my_tid][3] != None:
					screen.blit(self.tile_dat[my_tid][3], my_pos + offset)
				if highlight_walls and self.tile_dat[my_tid][1]:
					screen.blit(self.wall_highlight, my_pos + offset, special_flags=pygame.BLEND_ALPHA_SDL2)
