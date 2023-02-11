import pygame

from pygame.math import Vector2

from source.globals   import GRID_SIZE
from source.misc_gfx  import Color

class TileMap:
	def __init__(self, tile_manager):
		self.tile_manager   = tile_manager
		self.wall_highlight = pygame.Surface(Vector2(GRID_SIZE, GRID_SIZE))
		self.wall_highlight.fill(Color.PAL_YEL_2)
		self.wall_highlight.set_alpha(128)

	def draw(self, screen, offset, map_array, highlight_walls=False):
		for x in range(map_array.shape[0]):
			for y in range(map_array.shape[1]):
				my_pos = Vector2(x*GRID_SIZE, y*GRID_SIZE)
				my_tid = map_array[x,y]
				if self.tile_manager.tile_img[my_tid] != None:
					screen.blit(self.tile_manager.tile_img[my_tid], my_pos + offset)
				if highlight_walls and self.tile_manager.is_wall[my_tid]:
					screen.blit(self.wall_highlight, my_pos + offset, special_flags=pygame.BLEND_ALPHA_SDL2)
