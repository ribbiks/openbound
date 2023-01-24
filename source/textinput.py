import pygame
import pygame.locals as pl

from pygame.math import Vector2

from typing import List, Callable

from source.geometry import point_in_box_excl, value_clamp
from source.misc_gfx import Color

class TextInput:
	def __init__(self, tl, br, font, max_chars=32, char_offset=Vector2(5,5), num_rows=1):
		self.tl           = tl
		self.br           = br
		self.font         = font
		self.is_selected  = False
		self.str_left     = ''
		self.str_right    = ''
		self.cursor_delay = 0
		self.draw_cursor  = False
		self.char_offset  = Vector2(char_offset.x, char_offset.y)
		self.max_width    = br.x - tl.x - 2*self.char_offset.x
		self.max_chars    = max_chars
		self.num_rows     = num_rows
		self.manager      = TextInputManager(validator = lambda input: (len(input) <= self.max_chars and self.font.can_be_fully_rendered(input+'|', self.max_width, self.num_rows)))

	def get_value(self):
		return ''.join(self.str_left) + ''.join(self.str_right)

	def reset_with_new_str(self, new_str):
		self.is_selected   = False
		self.str_left      = new_str[:]
		self.str_right     = ''
		self.manager.left  = self.str_left[:]
		self.manager.right = ''

	def update(self, mousepos, activation, release, pygame_events):
		if activation:
			if point_in_box_excl(mousepos, self.tl, self.br):
				self.is_selected = True
			else:
				self.reset_with_new_str(self.str_left + self.str_right)
		#
		if release:
			self.reset_with_new_str(self.str_left + self.str_right)
		#
		if self.is_selected:
			self.manager.update(pygame_events)
			self.str_left  = self.font.sanitize(self.manager.left)
			self.str_right = self.font.sanitize(self.manager.right)
		if self.cursor_delay > 0:
			self.cursor_delay -= 1
		else:
			self.draw_cursor = not self.draw_cursor
			self.cursor_delay = 5

	def draw(self, screen):
		my_rect = pygame.Rect(self.tl, self.br - self.tl)
		if self.is_selected:
			pygame.draw.rect(screen, Color.PAL_BLUE_4, my_rect, border_radius=2)
		else:
			pygame.draw.rect(screen, Color.PAL_BLUE_5, my_rect, border_radius=2)
		#
		if self.is_selected:
			if self.draw_cursor:
				self.font.render(screen, self.str_left + '|' + self.str_right, self.tl + self.char_offset, max_width=self.max_width, num_rows=self.num_rows)
			else:
				self.font.render(screen, self.str_left + ' ' + self.str_right, self.tl + self.char_offset, max_width=self.max_width, num_rows=self.num_rows)
		else:
			self.font.render(screen, self.str_left, self.tl + self.char_offset, max_width=self.max_width, num_rows=self.num_rows)

#
#
#
class DigitInput(TextInput):
	def __init__(self, tl, br, font, value_bounds, default_val=None, max_chars=3, char_offset=Vector2(5,5), num_rows=1):
		#
		super().__init__(tl, br, font,
		                 max_chars=max_chars,
		                 char_offset=char_offset,
		                 num_rows=num_rows)
		self.manager = TextInputManager(validator = lambda input: (len(input) <= max_chars and input.isdigit()) or len(input) == 0)
		self.bounds  = value_bounds
		if default_val != None:
			self.value = default_val
			self.str_left = str(self.value)
		else:
			self.value = self.bounds[0]
			self.str_left = str(self.value)

	def update(self, mousepos, activation, release, pygame_events):
		#
		super().update(mousepos, activation, release, pygame_events)
		#
		if not self.is_selected:
			if self.str_left:
				self.value    = value_clamp(int(self.str_left), self.bounds[0], self.bounds[1])
				self.str_left = str(self.value)
				self.manager.left  = self.str_left[:]
				self.manager.right = ''
			else:
				self.value = self.bounds[0]
				self.str_left = str(self.value)

	def get_value(self):
		return value_clamp(self.value, self.bounds[0], self.bounds[1])

#
#
#
"""
Copyright 2021, Silas Gyger, silasgyger@gmail.com, All rights reserved.

Borrowed from https://github.com/Nearoo/pygame-text-input under the MIT license.
"""
class TextInputManager:
	'''
	Keeps track of text inputted, cursor position, etc.
	Pass a validator function returning if a string is valid,
	and the string will only be updated if the validator function
	returns true. 

	For example, limit input to 5 characters:
	```
	limit_5 = lambda x: len(x) <= 5
	manager = TextInputManager(validator=limit_5)
	```
	
	:param initial: The initial string
	:param validator: A function string -> bool defining valid input
	'''

	def __init__(self, initial = "", validator: Callable[[str], bool] = lambda x: True):
		self.left = initial # string to the left of the cursor
		self.right = "" # string to the right of the cursor
		self.validator = validator
		

	@property
	def value(self):
		""" Get / set the value currently inputted. Doesn't change cursor position if possible."""
		return self.left + self.right
	
	@value.setter
	def value(self, value):
		cursor_pos = self.cursor_pos
		self.left = value[:cursor_pos]
		self.right = value[cursor_pos:]
	
	@property
	def cursor_pos(self):
		""" Get / set the position of the cursor. Will clamp to [0, length of input]. """
		return len(self.left)

	@cursor_pos.setter
	def cursor_pos(self, value):
		complete = self.value
		self.left = complete[:value]
		self.right = complete[value:]
	
	def update(self, events: List[pygame.event.Event]):
		"""
		Update the interal state with fresh pygame events.
		Call this every frame with all events returned by `pygame.event.get()`.
		"""
		for event in events:
			if event.type == pl.KEYDOWN:
				v_before = self.value
				c_before = self.cursor_pos
				self._process_keydown(event)
				if not self.validator(self.value):
					self.value = v_before
					self.cursor_pos = c_before

	def _process_keydown(self, ev):
		attrname = f"_process_{pygame.key.name(ev.key)}"
		if hasattr(self, attrname):
			getattr(self, attrname)()
		else:
			self._process_other(ev)

	def _process_delete(self):
		self.right = self.right[1:]
	
	def _process_backspace(self):
		self.left = self.left[:-1]
	
	def _process_right(self):
		self.cursor_pos += 1
	
	def _process_left(self):
		self.cursor_pos -= 1

	def _process_end(self):
		self.cursor_pos = len(self.value)
	
	def _process_home(self):
		self.cursor_pos = 0
	
	def _process_return(self):
		pass

	def _process_other(self, event):
		self.left += event.unicode
