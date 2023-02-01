import json
import os
import pygame
import numpy as np

from pygame.math import Vector2

from source.draggableobject import DraggableObject
from source.misc_gfx        import Color
from source.globals         import GRID_SIZE, PLAYER_RADIUS
from source.resizablebox    import ResizableBox
from source.tile_data       import TILE_DATA

def exists_and_is_nonzero(fn):
	if os.path.isfile(fn):
		if os.path.getsize(fn) > 0:
			return True
	return False

def makedir(d):
	if not os.path.isdir(d):
		os.mkdir(d)

def rm(fn):
	if os.path.isdir(fn):
		os.rmdir(fn)
	elif os.path.isfile(fn):
		os.remove(fn)

def get_file_paths(d, img_list):
	path_list = [(len(n) > 0)*os.path.join(d, n) for n in img_list]
	for n in path_list:
		if len(n) and not exists_and_is_nonzero(n):
			print('Error: file not found')
			print('--', n)
			exit(1)
	return path_list

def get_box_str_from_tl(tl):
	return '[' + ','.join([str(int(n)) for n in [tl.x, tl.y]]) + ']'

def get_box_str_from_tlbr(tl, br):
	return '[' + ','.join([str(int(n)) for n in [tl.x, tl.y, br.x, br.y]]) + ']'

#
#
#
def write_map_data_to_json(out_fn, all_map_objects):
	(textinput_mapname,
	 textinput_author,
	 textinput_description,
	 digitinput_lives,
	 digitinput_rating,
	 digitinput_mapsizex,
	 digitinput_mapsizey,
	 draggable_playerstart,
	 #
	 editor_tilemap,
	 editor_obdata) = all_map_objects
	#
	if not textinput_mapname.get_value():
		return 'Cannot save map: mapname is empty'
	#
	wall_map = np.zeros((editor_tilemap.shape[0], editor_tilemap.shape[1]))
	for i in range(editor_tilemap.shape[0]):
		for j in range(editor_tilemap.shape[1]):
			(is_wall, name, image_fn) = TILE_DATA[editor_tilemap[i,j]]
			wall_map[i,j] = is_wall
	for i in range(wall_map.shape[0]):
		wall_map[i,0] = 1
		wall_map[i,wall_map.shape[1]-1] = 1
	for j in range(wall_map.shape[1]):
		wall_map[0,j] = 1
		wall_map[wall_map.shape[0]-1,j] = 1
	v = PLAYER_RADIUS - 0.01
	check_pos = [draggable_playerstart.center_pos + Vector2(-v,-v),
	             draggable_playerstart.center_pos + Vector2( v,-v),
	             draggable_playerstart.center_pos + Vector2( v, v),
	             draggable_playerstart.center_pos + Vector2(-v, v)]
	for pos in check_pos:
		if wall_map[int(pos.x/GRID_SIZE),int(pos.y/GRID_SIZE)]:
			return 'Cannot save map: player position is inside a wall'
	#
	overwriting_existing = False
	if exists_and_is_nonzero(out_fn):
		overwriting_existing = True
	#
	with open(out_fn, 'w') as f:
		f.write('{\n')
		f.write('    "map_name":   "' + str(textinput_mapname.get_value()) + '",\n')
		f.write('    "map_author": "' + str(textinput_author.get_value()) + '",\n')
		f.write('    "map_notes":  "' + str(textinput_description.get_value()) + '",\n')
		f.write('    "difficulty": '  + str(digitinput_rating.get_value()) + ',\n')
		f.write('    "map_width":  '  + str(digitinput_mapsizex.get_value()) + ',\n')
		f.write('    "map_height": '  + str(digitinput_mapsizey.get_value()) + ',\n')
		f.write('    "init_lives": '  + str(digitinput_lives.get_value()) + ',\n')
		f.write('    "start_pos":  '  + get_box_str_from_tl(draggable_playerstart.center_pos) + ',\n')
		for j in range(editor_tilemap.shape[1]):
			if j == 0:
				f.write('    "tile_dat":   [[' + ','.join([str(n) for n in editor_tilemap[:,j].tolist()]) + '],\n')
			elif j == editor_tilemap.shape[1] - 1:
				if len(editor_obdata):
					f.write('                   [' + ','.join([str(n) for n in editor_tilemap[:,j].tolist()]) + ']],\n')
				else:
					f.write('                   [' + ','.join([str(n) for n in editor_tilemap[:,j].tolist()]) + ']]\n')
			else:
				f.write('                   [' + ','.join([str(n) for n in editor_tilemap[:,j].tolist()]) + '],\n')
		for i,ob_data in enumerate(editor_obdata):
			f.write('    "obstacle_' + str(i+1) + '": {\n')
			f.write('        "startbox": ' + get_box_str_from_tlbr(ob_data[1].tl, ob_data[1].br) + ',\n')
			f.write('        "endbox":   ' + get_box_str_from_tlbr(ob_data[2].tl, ob_data[2].br) + ',\n')
			f.write('        "revive":   ' + get_box_str_from_tl(ob_data[0].center_pos) + ',\n')
			f.write('        "actions":  [')
			#
			if ob_data[4]['move_mode'] == 0:
				f.write('["move_player", 0], ')
			elif ob_data[4]['move_mode'] == 1:
				f.write('["move_player", 1], ')
			if ob_data[4]['life_mode'] == 0:
				f.write('["add_lives", ' + str(ob_data[4]['life_amount']) + '], ')
			elif ob_data[4]['life_mode'] == 1:
				f.write('["set_lives", ' + str(ob_data[4]['life_amount']) + '], ')
			f.write('["change_music", "' + str(ob_data[4]['music']) + '"]],\n')
			#
			for j,loc_box in enumerate(ob_data[3]):
				# json formatting will look pretty up until 999999 locs / counts, lol.
				name_len = len(str(j+1))
				if name_len == 1: my_spaces = '    '
				elif name_len == 2: my_spaces = '   '
				elif name_len == 3: my_spaces = '  '
				elif name_len == 4: my_spaces = ' '
				else: my_spaces = ''
				f.write('        "loc_' + str(j+1) + '":' + my_spaces + get_box_str_from_tlbr(loc_box.tl, loc_box.br) + ',\n')
			#
			ob_data_to_output = [ob_data[5][n] for n in range(len(ob_data[5])) if len(ob_data[5][n]['explode_locs'])]
			#
			for j,exp_dat in enumerate(ob_data_to_output):
				name_len = len(str(j+1))
				if name_len == 1: my_spaces = '    '
				elif name_len == 2: my_spaces = '   '
				elif name_len == 3: my_spaces = '  '
				elif name_len == 4: my_spaces = ' '
				else: my_spaces = ''
				my_locs = sorted(list(exp_dat['explode_locs'].keys()))
				f.write('        "exp_' + str(j+1) + '":' + my_spaces + '[')
				f.write('[' + ','.join(['"'+str(n+1)+'"' for n in my_locs]) + '], ')
				f.write('[' + ','.join(['"'+str(exp_dat['explode_locs'][n])+'"' for n in my_locs]) + '], ')
				f.write(str(exp_dat['delay']))
				if j == len(ob_data_to_output) - 1:
					f.write(']\n')
				else:
					f.write('],\n')
			#
			if i == len(editor_obdata) - 1:
				f.write('    }\n')
			else:
				f.write('    },\n')
		f.write('}')
		#
		return 'saved map as: ' + out_fn

#
#
#
def get_blank_obdata(new_pos, font_dict, revive_img):
	return [DraggableObject(Vector2(new_pos[0] + 2*GRID_SIZE, new_pos[1] + 2*GRID_SIZE),
	                        PLAYER_RADIUS,
	                        grid_snap=int(GRID_SIZE/2),
	                        pos_offset=Vector2(0,0),
	                        init_image_fn=revive_img),
	        ResizableBox(Vector2(new_pos[0] + 4*GRID_SIZE, new_pos[1]),
	                     Vector2(new_pos[0] + 8*GRID_SIZE, new_pos[1] + 4*GRID_SIZE),
	                     'start',
	                     font_dict['small_w'],
	                     box_color=Color.PAL_GREEN_4,
	                     box_color_highlight=Color.PAL_GREEN_3,
	                     line_color=Color.PAL_GREEN_3,
	                     line_color_highlight=Color.PAL_GREEN_1),
	        ResizableBox(Vector2(new_pos[0] + 8*GRID_SIZE,  new_pos[1]),
	                     Vector2(new_pos[0] + 12*GRID_SIZE, new_pos[1] + 4*GRID_SIZE),
	                     'end',
	                     font_dict['small_w'],
	                     box_color=Color.PAL_RED_4,
	                     box_color_highlight=Color.PAL_RED_3,
	                     line_color=Color.PAL_RED_3,
	                     line_color_highlight=Color.PAL_RED_1),
	        [],
	        {'move_mode':0,			# 0 = no move, 1 = move to revive
	         'life_mode':0,			# 0 = add,     1 = set
	         'life_amount':0,
	         'music':''},
	        [{'explode_locs':{},	# explode_locs[locname] = unit
	          'delay':0}]]

#
#
#
def read_map_data_from_json(in_fn, all_map_objects, font_dict, revive_img):
	(textinput_mapname,
	 textinput_author,
	 textinput_description,
	 digitinput_lives,
	 digitinput_rating,
	 digitinput_mapsizex,
	 digitinput_mapsizey,
	 draggable_playerstart) = all_map_objects
	#
	with open(in_fn,'r') as f:
		json_dat = json.load(f)
	#
	spos_quant = (int(json_dat['start_pos'][0]/GRID_SIZE), int(json_dat['start_pos'][1]/GRID_SIZE))
	#
	textinput_mapname.reset_with_new_str(json_dat['map_name'])
	textinput_author.reset_with_new_str(json_dat['map_author'])
	textinput_description.reset_with_new_str(json_dat['map_notes'])
	digitinput_lives.reset_with_new_str(str(json_dat['init_lives']))
	digitinput_rating.reset_with_new_str(str(json_dat['difficulty']))
	digitinput_mapsizex.reset_with_new_str(str(json_dat['map_width']))
	digitinput_mapsizey.reset_with_new_str(str(json_dat['map_height']))
	draggable_playerstart.center_pos = Vector2(json_dat['start_pos'][0], json_dat['start_pos'][1])
	#
	editor_tilemap = np.array(json_dat['tile_dat']).T
	#
	ob_keys = [n[1] for n in sorted([(int(k[9:]), k) for k in json_dat.keys() if k[:9] == 'obstacle_'])]
	editor_obdata = []
	for k in ob_keys:
		startbox = json_dat[k]['startbox']
		endbox   = json_dat[k]['endbox']
		revive   = json_dat[k]['revive']
		actions  = json_dat[k]['actions']
		#
		loc_keys = [n[1] for n in sorted([(int(k2[4:]), k2) for k2 in json_dat[k].keys() if k2[:4] == 'loc_'])]
		exp_keys = [n[1] for n in sorted([(int(k2[4:]), k2) for k2 in json_dat[k].keys() if k2[:4] == 'exp_'])]
		#
		editor_obdata.append(get_blank_obdata(Vector2(0,0), font_dict, revive_img))
		editor_obdata[-1][0].center_pos = Vector2(revive[0], revive[1])
		editor_obdata[-1][1].tl = Vector2(startbox[0], startbox[1])
		editor_obdata[-1][1].br = Vector2(startbox[2], startbox[3])
		editor_obdata[-1][2].tl = Vector2(endbox[0], endbox[1])
		editor_obdata[-1][2].br = Vector2(endbox[2], endbox[3])
		for k2 in loc_keys:
			loc_pos = json_dat[k][k2]
			editor_obdata[-1][3].append(ResizableBox(Vector2(loc_pos[0], loc_pos[1]),
			                                         Vector2(loc_pos[2], loc_pos[3]),
			                                         str(k2[4:]),
			                                         font_dict['small_w']))
		#
		for action_tuple in actions:
			if action_tuple[0] == 'move_player':
				editor_obdata[-1][4]['move_mode'] = action_tuple[1]
			elif action_tuple[0] == 'add_lives':
				editor_obdata[-1][4]['life_mode'] = 0
				editor_obdata[-1][4]['life_amount'] = action_tuple[1]
			elif action_tuple[0] == 'set_lives':
				editor_obdata[-1][4]['life_mode'] = 1
				editor_obdata[-1][4]['life_amount'] = action_tuple[1]
			elif action_tuple[0] == 'change_music':
				editor_obdata[-1][4]['music'] = action_tuple[1]
		#
		editor_obdata[-1][5] = [{'explode_locs':{},'delay':0} for n in exp_keys]
		for exp_num,k2 in enumerate(exp_keys):
			exp_dat = json_dat[k][k2]
			exp_ind = int(k2[4:]) - 1
			for i in range(len(exp_dat[0])):
				editor_obdata[-1][5][exp_num]['explode_locs'][int(exp_dat[0][i])-1] = exp_dat[1][i]
			editor_obdata[-1][5][exp_num]['delay'] = exp_dat[2]
	#
	return (editor_tilemap, editor_obdata)