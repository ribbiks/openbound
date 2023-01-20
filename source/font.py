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
	def __init__(self, path, color, scalar=1):
		self.spacing = scalar
		self.character_order = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','.','-',',',':','+','\'','!','?','0','1','2','3','4','5','6','7','8','9','(',')','/','_','=','\\','[',']','*','"','<','>',';','|']
		font_img = pygame.image.load(path).convert_alpha()
		current_char_width = 0
		character_count    = 0
		self.characters    = {}
		# recolor
		for x in range(font_img.get_width()):
			for y in range(font_img.get_height()):
				if font_img.get_at((x,y)) == TEXT_CHARACTER_COLOR:
					font_img.set_at((x, y), pygame.Color(color[0], color[1], color[2], 255))
		# separate characters
		for x in range(font_img.get_width()):
			if font_img.get_at((x,0)) == COLUMN_DELIMITER_COLOR:
				char_img = clip(font_img, x - current_char_width, 0, current_char_width, font_img.get_height())
				c = self.character_order[character_count]
				self.characters[c] = char_img.copy()
				if scalar > 1:
					self.characters[c] = pygame.transform.scale(self.characters[c], (scalar*self.characters[c].get_width(), scalar*self.characters[c].get_height()))
				character_count   += 1
				current_char_width = 0
			else:
				current_char_width += 1
		self.char_height = self.characters['A'].get_height()
		self.char_width  = {k:self.characters[k].get_width() for k in self.characters.keys()}
		self.char_width[' '] = self.char_width['A']

	#
	#
	#
	def sanitize(self, text):
		return ''.join([n for n in text if (n in self.characters or n == ' ')])

	#
	#
	#
	def get_words_by_row(self, text, x_offset, max_width):
		words       = text.split(' ')
		split_words = []
		current_xi  = 0
		for i,word in enumerate(words):
			if i == 0:
				current_xi += len(word)
			else:
				current_xi += len(word) + 1
			my_word_width = x_offset[current_xi].x - x_offset[current_xi-len(word)].x
			rows_spanned  = int(my_word_width/max_width)
			#
			current_row_xoff = self.char_width[word[0]]
			split_j = [0]
			for j in range(1,len(word)):
				current_row_xoff += self.char_width[word[j]] + self.spacing
				if current_row_xoff > max_width:
					split_j.append(j)
					current_row_xoff = self.char_width[word[j]]
			split_j.append(len(word))
			for j in range(len(split_j)-1):
				split_words.append(word[split_j[j]:split_j[j+1]])
		split_words  = [(n, sum([self.char_width[m] for m in n])+len(n)*self.spacing) for n in split_words]
		words_by_row = [[]]
		current_row_width = 0
		for (word, width) in split_words:
			if current_row_width == 0:
				words_by_row[-1].append(word)
			elif current_row_width + width + self.char_width[' '] > max_width:
				words_by_row.append([word])
				current_row_width = 0
			else:
				words_by_row[-1].append(word)
			current_row_width += width + self.char_width[' ']
		return words_by_row

	#
	# returns True is everything can be rendered, False if text gets truncated
	#
	def can_be_fully_rendered(self, text, max_width=-1, num_rows=1):
		x_trim = len(text)
		while x_trim >= 1 and text[x_trim-1] == ' ':
			x_trim -= 1
		if x_trim == 0:
			return True
		text_trimmed = text[:x_trim]
		#
		x_offset = [Vector2(0,0)]
		for char in text_trimmed:
			x_offset.append(x_offset[-1] + Vector2(self.char_width[char] + self.spacing, 0))
		if max_width > 0 and num_rows == 1:
			for i in range(1,len(x_offset)):
				if x_offset[i].x > max_width:
					return False
		if max_width > 0 and num_rows > 1:
			words_by_row = self.get_words_by_row(text_trimmed, x_offset, max_width)
			if len(words_by_row) > num_rows:
				return False
		return True


	#
	#
	#
	def render(self, screen, text, pos, centered=False, max_width=-1, num_rows=1):
		#
		x_trim = len(text)
		while x_trim >= 1 and text[x_trim-1] == ' ':
			x_trim -= 1
		# word is only spaces, nothing to render
		if x_trim == 0:
			return None
		text_trimmed = text[:x_trim]
		#
		x_offset = [Vector2(0,0)]
		for char in text_trimmed:
			x_offset.append(x_offset[-1] + Vector2(self.char_width[char] + self.spacing, 0))
		#
		# if only one row, truncate string at max_width
		#
		x_truncate = None
		if max_width > 0 and num_rows == 1:
			for i in range(1,len(x_offset)):
				if x_offset[i].x > max_width:
					x_truncate = i-1
					break
		text_to_render = text_trimmed
		if x_truncate != None:
			if x_truncate <= 0:	# we don't have enough space to print anything
				return None
			x_offset = x_offset[:x_truncate]
			text_to_render = text_trimmed[:x_truncate]
		#
		# we're rendering multiple rows, lets split by word
		# -- if a word takes up more an entire row we're going to split it
		#
		if max_width > 0 and num_rows > 1:
			words_by_row = self.get_words_by_row(text_trimmed, x_offset, max_width)
			words_by_row = words_by_row[:num_rows]
			for i,words in enumerate(words_by_row):
				x_offset = [Vector2(0,0)]
				y_offset = [Vector2(0, (self.char_height + self.spacing) * i)]
				text_row = ' '.join(words)
				for char in text_row:
					x_offset.append(x_offset[-1] + Vector2(self.char_width[char] + self.spacing, 0))
					y_offset.append(Vector2(0, (self.char_height + self.spacing) * i))
				# for centering multi-row text, lets center each row without affecting y-offset
				centered_adj = Vector2(0,0)
				if centered:
					centered_adj = Vector2(int(x_offset[-1].x/2 - max_width/2), 0)
				for j,char in enumerate(text_row):
					if char != ' ':
						screen.blit(self.characters[char], pos + x_offset[j] + y_offset[j] - centered_adj)
		#
		else:
			centered_adj = Vector2(0,0)
			if centered:
				centered_adj = Vector2(int(x_offset[-1].x/2), int(self.char_height/2))
			for i,char in enumerate(text_to_render):
				if char != ' ':
					screen.blit(self.characters[char], pos + x_offset[i] - centered_adj)
