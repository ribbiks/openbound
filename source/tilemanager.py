import pygame
import os

from source.globals import GRID_SIZE

#
# (is_wall, image_fn)
#
TILE_NAME = [(0, ''),
             (1, ''),
             (0, 'blank.png'),
             (1, 'wall5.png'),
             (0, 'block.png'),
             (0, 'blank_light.png'),
             (0, 'jungle_test.png'),
             (1, 'jungle_test2.png')]

class TileManager:
	def __init__(self, tile_dir):
		self.tile_img     = []
		self.tile_img_2x2 = {}	# only used in TerrainMenu previews
		self.tile_img_4x4 = {}	# only used in TerrainMenu previews
		self.is_wall      = []
		self.is_wall_2x2  = {}	# only used in TerrainMenu previews
		self.is_wall_4x4  = {}	# only used in TerrainMenu previews
		self.tile_1x1     = []
		self.tile_2x2     = []
		self.tile_4x4     = []
		current_tile_num = 0
		for i, (is_wall, fn) in enumerate(TILE_NAME):
			# null tiles
			if not fn:
				self.tile_img.append(None)
				self.is_wall.append(is_wall)
				self.tile_1x1.append((current_tile_num,))
				self.tile_img_2x2[current_tile_num] = None
				self.is_wall_2x2[current_tile_num]  = is_wall
				self.tile_2x2.append(tuple([current_tile_num]*4))
				self.tile_img_4x4[current_tile_num] = None
				self.is_wall_4x4[current_tile_num]  = is_wall
				self.tile_4x4.append(tuple([current_tile_num]*16))
				current_tile_num += 1
			else:
				tile_fn    = os.path.join(tile_dir, fn)
				my_surface = pygame.image.load(tile_fn).convert()
				img_size   = my_surface.get_size()
				#
				if img_size == (16,16):
					self.tile_img.append(pygame.image.load(tile_fn).convert())
					self.is_wall.append(is_wall)
					self.tile_1x1.append((current_tile_num,))
					current_tile_num += 1
				#
				elif img_size == (32,32):
					self.tile_img_2x2[current_tile_num] = pygame.image.load(tile_fn).convert()
					self.is_wall_2x2[current_tile_num]  = is_wall
					self.tile_2x2.append(tuple([current_tile_num+n for n in range(4)]))
					base_img = self.tile_img_2x2[current_tile_num]
					for i in range(4):
						x = int(i/2)*GRID_SIZE
						y = (i%2)*GRID_SIZE
						rect = pygame.Rect([x, y, GRID_SIZE, GRID_SIZE])
						self.tile_img.append(pygame.Surface(rect.size).convert_alpha())
						self.tile_img[-1].blit(base_img, (0,0), rect)
						self.is_wall.append(is_wall)
						current_tile_num += 1
				#
				elif img_size == (64,64):
					self.tile_img_4x4[current_tile_num] = pygame.image.load(tile_fn).convert()
					self.is_wall_4x4[current_tile_num]  = is_wall
					self.tile_4x4.append(tuple([current_tile_num+n for n in range(16)]))
					base_img = self.tile_img_4x4[current_tile_num]
					for i in range(16):
						x = int(i/4)*GRID_SIZE
						y = (i%4)*GRID_SIZE
						rect = pygame.Rect([x, y, GRID_SIZE, GRID_SIZE])
						self.tile_img.append(pygame.Surface(rect.size).convert_alpha())
						self.tile_img[-1].blit(base_img, (0,0), rect)
						self.is_wall.append(is_wall)
						current_tile_num += 1
				else:
					print('skipping tile (invalid size):', fn)
