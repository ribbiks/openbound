import copy
import pygame

from pygame.math import Vector2

from source.geometry import point_in_box_excl
from source.misc_gfx import Color, OB_REVIVE_RADIUS

# all boxes are defined by a list of Vector2s: [topleft, bottomright]

class Obstacle:
	def __init__(self, obnum, startbox, endbox, revive, start_actions, font_loc=None):
		self.obnum         = obnum
		self.start_box     = startbox
		self.end_box       = endbox
		self.revive_coords = revive
		self.start_actions = sorted(start_actions)
		self.locs          = {}
		self.events        = [[]]
		self.event_index   = 0
		self.is_activated  = False
		self.was_activated = False
		self.font_loc      = font_loc

	def check_for_ob_start(self, player_pos):
		if not self.was_activated and not self.is_activated:
			if point_in_box_excl(player_pos, self.start_box[0], self.start_box[1]):
				self.is_activated  = True
				self.was_activated = True
				self.event_index   = 0
				return self.start_actions
		return None

	def check_for_ob_end(self, player_pos):
		if self.is_activated:
			if point_in_box_excl(player_pos, self.end_box[0], self.end_box[1]):
				self.is_activated = False
				return True
		return False

	def add_location(self, loc_name, tl, br):
		self.locs[loc_name] = (tl, br)

	def add_event_explode_locs(self, loc_list, unit_list, delay):
		new_events = []
		new_sounds = {}
		for i in range(len(loc_list)):
			(tl, br) = self.locs[loc_list[i]]
			new_events.append(('kill', Vector2(tl.x,tl.y), Vector2(br.x,br.y)))
			new_events.append(('gfx', unit_list[i], (tl+br)/2))
			new_sounds[unit_list[i]] = True
		self.update_events(new_events, new_sounds, delay)

	def add_event_teleport(self, origin_loc, destination_loc):
		new_events = []
		new_sounds = {}
		(tl1, br1) = self.locs[origin_loc]
		(tl2, br2) = self.locs[destination_loc]
		new_events.append(('gfx', 'hallucination', (tl1+br1)/2))
		new_events.append(('gfx', 'hallucination', (tl2+br2)/2))
		new_events.append(('tele', Vector2(tl1.x, tl1.y), Vector2(br1.x, br1.y), (tl2+br2)/2))
		new_sounds['hallucination'] = True
		self.update_events(new_events, new_sounds, 0)

	def change_wall_state(self, wall_state, state_tuple, obloc_string_list):
		wall_kills  = [(self.locs[n][0],  self.locs[n][1]) for i,n in enumerate(obloc_string_list) if state_tuple[i]]
		loc_box_out = [(self.locs[n][0] + self.locs[n][1])/2 for n in obloc_string_list]
		new_events  = []
		new_sounds  = {}
		for [tl,br] in wall_kills:
			new_events.append(('kill', Vector2(tl.x,tl.y), Vector2(br.x,br.y)))
		new_events.append(('change_wall_state', (self.obnum, wall_state), state_tuple, obloc_string_list, loc_box_out))
		self.update_events(new_events, new_sounds, 0)

	def update_events(self, new_events, new_sounds, delay):
		for k in new_sounds.keys():
			new_events.append(('snd', k))
		if len(new_events):
			self.events[-1].extend(copy.deepcopy(new_events))
		for i in range(delay):
			self.events.append([])

	#
	# call this once after adding all the ob events
	#
	def bake(self):
		if len(self.events) > 1:
			self.events[0].extend(copy.deepcopy(self.events[-1]))
			del self.events[-1]

	#
	# keeping this around so I have a record of functions to eventually implement properly
	#
	def add_event(self, event_type, event_dat, delay):
		new_events = []
		new_sounds = {}
		#
		# event_dat = list_of_locs
		#
		if event_type == 'explode_locs':
			pass
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

	def tick(self):
		gfx_out  = []
		snd_out  = {}
		kill_out = []
		tele_out = []
		wall_out = []
		if self.is_activated:
			if len(self.events[self.event_index]):
				for event in self.events[self.event_index]:
					if event[0] == 'gfx':
						gfx_out.append([n for n in event[1:]])
					elif event[0] == 'snd':
						snd_out[event[1]] = True
					elif event[0] == 'kill':
						kill_out.append([n for n in event[1:]])
					elif event[0] == 'tele':
						tele_out.append([n for n in event[1:]])
					elif event[0] == 'change_wall_state':
						wall_out.append([n for n in event[1:]])
			self.event_index = (self.event_index + 1) % len(self.events)
		snd_out = list(snd_out.keys())
		return (gfx_out, snd_out, kill_out, tele_out, wall_out)

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
