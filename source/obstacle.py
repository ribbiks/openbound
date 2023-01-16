import copy
import pygame

from pygame.math import Vector2

from source.misc_gfx import Color, OB_REVIVE_RADIUS

# all boxes are defined by a list of Vector2s: [topleft, bottomright]

class Obstacle:
	def __init__(self, startbox, endbox, revive, font_loc=None):
		self.start_box     = startbox
		self.end_box       = endbox
		self.revive_coords = revive
		self.locs          = {}
		self.events        = [[]]
		self.event_index   = 0
		self.is_activated  = False
		self.was_activated = False
		self.font_loc      = font_loc

	#
	#
	#
	def draw(self, screen, offset):
		start_p  = [self.start_box[0] + offset,
		            Vector2(self.start_box[1].x, self.start_box[0].y) + offset,
		            self.start_box[1] + offset,
		            Vector2(self.start_box[0].x, self.start_box[1].y) + offset]
		end_p    = [self.end_box[0] + offset,
		            Vector2(self.end_box[1].x, self.end_box[0].y) + offset,
		            self.end_box[1] + offset,
		            Vector2(self.end_box[0].x, self.end_box[1].y) + offset]
		revive_p = [self.revive_coords + Vector2(-OB_REVIVE_RADIUS,-OB_REVIVE_RADIUS) + offset,
		            self.revive_coords + Vector2( OB_REVIVE_RADIUS,-OB_REVIVE_RADIUS) + offset,
		            self.revive_coords + Vector2( OB_REVIVE_RADIUS, OB_REVIVE_RADIUS) + offset,
		            self.revive_coords + Vector2(-OB_REVIVE_RADIUS, OB_REVIVE_RADIUS) + offset]
		loc_polygons = []
		loc_labels   = []
		for k in self.locs.keys():
			loc_polygons.append([self.locs[k][0] + offset,
			                     Vector2(self.locs[k][1].x, self.locs[k][0].y) + offset,
			                     self.locs[k][1] + offset,
			                     Vector2(self.locs[k][0].x, self.locs[k][1].y) + offset])
			loc_labels.append((k, self.locs[k][0] + Vector2(5,5) + offset))
		#
		for p in loc_polygons:
			pygame.draw.polygon(screen, Color.LOC_BG, p)
		if self.font_loc != None:
			for text_dat in loc_labels:
				self.font_loc.render(screen, text_dat[0], text_dat[1], centered=False)
		pygame.draw.polygon(screen, Color.OB_STARTBOX, start_p)
		pygame.draw.polygon(screen, Color.OB_ENDBOX, end_p)
		pygame.draw.polygon(screen, Color.OB_REVIVE, revive_p)

	#
	#
	#
	def check_for_ob_start(self, player_pos):
		if not self.was_activated and not self.is_activated:
			inside_box = (player_pos.x > self.start_box[0].x and
			              player_pos.x < self.start_box[1].x and
			              player_pos.y > self.start_box[0].y and
			              player_pos.y < self.start_box[1].y)
			if inside_box:
				self.is_activated  = True
				self.was_activated = True
				self.event_index   = 0

	#
	#
	#
	def check_for_ob_end(self, player_pos):
		if self.is_activated:
			inside_box = (player_pos.x > self.end_box[0].x and
			              player_pos.x < self.end_box[1].x and
			              player_pos.y > self.end_box[0].y and
			              player_pos.y < self.end_box[1].y)
			if inside_box:
				self.is_activated = False
				# FUTURE TODO: REMOVE ALL WALLS

	#
	#
	#
	def add_location(self, loc_name, topleft, bottomright, default_gfx, default_sound):
		self.locs[loc_name] = (topleft, bottomright, default_gfx, default_sound)

	#
	#
	#
	def add_event(self, event_type, event_dat, delay):
		new_events = []
		new_sounds = {}
		#
		# event_dat = list_of_locs
		#
		if event_type == 'explode_locs':
			for loc in event_dat:
				(tl, br, unit, sound) = self.locs[loc]
				loc_center = (tl+br)/2
				new_events.append(('kill', tl, br))
				new_events.append(('gfx', unit, loc_center))
				new_sounds[sound] = True
		#
		# event_dat = (list_of_locs, list_of_units, list_of_sounds)
		#
		elif event_type == 'explode_locs_advanced':
			pass
		#
		# event_dat = (list_of_box_tuples, list_of_units, list_of_sounds)
		#
		elif event_type == 'explode_by_pos':
			pass
		#
		#
		elif event_type == 'add_walls':
			pass
		#
		#
		elif event_type == 'remove_walls':
			pass
		#
		#
		elif event_type == 'teleport':
			pass
		#
		#
		elif event_type == 'play_sound':
			pass
		#
		for k in new_sounds.keys():
			new_events.append(('snd', k))
		if len(new_events):
			self.events[-1].extend(copy.deepcopy(new_events))
		for i in range(delay):
			self.events.append([])

	#
	#
	#
	def tick(self):
		gfx_out  = []
		snd_out  = []
		kill_out = []
		tele_out = []
		if self.is_activated:
			if len(self.events[self.event_index]):
				for event in self.events[self.event_index]:
					if event[0] == 'gfx':
						gfx_out.append([n for n in event[1:]])
					elif event[0] == 'snd':
						snd_out.append([n for n in event[1:]])
					elif event[0] == 'kill':
						kill_out.append([n for n in event[1:]])
					elif event[0] == 'tele':
						tele_out.append([n for n in event[1:]])
			self.event_index = (self.event_index + 1) % len(self.events)
		return (gfx_out, snd_out, kill_out, tele_out)
