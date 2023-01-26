import os

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
	 #
	 editor_obdata) = all_map_objects
	#
	if not textinput_mapname.get_value():
		return 'Cannot save map: mapname is empty'
	overwriting_existing = False
	if exists_and_is_nonzero(out_fn):
		overwriting_existing = True
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
				f.write('                   [' + ','.join([str(n) for n in editor_tilemap[:,j].tolist()]) + ']],\n')
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
			for j,exp_dat in enumerate(ob_data[5]):
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
				if j == len(ob_data[5]) - 1:
					f.write(']\n')
				else:
					f.write('],\n')
			#
			f.write('    }\n')
		f.write('}')
		#
		return 'saved map as: ' + out_fn
