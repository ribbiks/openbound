import pygame

from pygame.math import Vector2

#
# Font class and pixel-art adapted from DaFluffyPotato's pygame tutorial series
# -- https://youtu.be/Lh-cc5qzDqk
#

def clip(surf, x, y, x_size, y_size):
	handle_surf = surf.copy()
	clipR = pygame.Rect(x,y,x_size,y_size)
	handle_surf.set_clip(clipR)
	image = surf.subsurface(handle_surf.get_clip())
	return image.copy()

COLUMN_DELIMITER_COLOR = (127, 127, 127, 255)
TEXT_CHARACTER_COLOR   = (  0,   0,   0, 255)

class Font():
	def __init__(self, path, color):
		self.spacing = 1
		self.character_order = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','.','-',',',':','+','\'','!','?','0','1','2','3','4','5','6','7','8','9','(',')','/','_','=','\\','[',']','*','"','<','>',';']
		font_img = pygame.image.load(path).convert_alpha()
		current_char_width = 0
		self.characters    = {}
		character_count    = 0
		# recolor
		for x in range(font_img.get_width()):
			for y in range(font_img.get_height()):
				if font_img.get_at((x,y)) == TEXT_CHARACTER_COLOR:
					font_img.set_at((x, y), pygame.Color(color[0], color[1], color[2], 255))
		# separate characters
		for x in range(font_img.get_width()):
			if font_img.get_at((x,0)) == COLUMN_DELIMITER_COLOR:
				char_img = clip(font_img, x - current_char_width, 0, current_char_width, font_img.get_height())
				self.characters[self.character_order[character_count]] = char_img.copy()
				character_count   += 1
				current_char_width = 0
			else:
				current_char_width += 1
		self.space_width = self.characters['A'].get_width()
		self.char_height = self.characters['A'].get_height()

	def render(self, screen, text, pos, centered=True):
		x_offset = [Vector2(0,0)]
		for char in text:
			if char != ' ':
				x_offset.append(x_offset[-1] + Vector2(self.characters[char].get_width() + self.spacing, 0))
			else:
				x_offset.append(x_offset[-1] + Vector2(self.space_width + self.spacing, 0))
		#
		centered_adj = Vector2(0,0)
		if centered:
			centered_adj = Vector2(int(x_offset[-1].x/2), int(self.char_height/2))
		#
		for i,char in enumerate(text):
			if char != ' ':
				screen.blit(self.characters[char], pos + x_offset[i] - centered_adj)
