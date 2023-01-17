#!/usr/bin/env python
# encoding: utf-8
import argparse
import os
import pathlib
import pygame
import sys
import time

from collections   import deque
from pygame.locals import QUIT, KEYDOWN, KEYUP, K_UP, K_DOWN, K_LEFT, K_RIGHT, K_ESCAPE, K_LSHIFT, K_RSHIFT, MOUSEBUTTONDOWN, MOUSEBUTTONUP
from pygame.math   import Vector2

from source.animationmanager import AnimationManager
from source.audiomanager     import AudioManager
from source.cursor           import Cursor
from source.font             import Font
from source.geometry         import value_clamp
from source.globals          import GRID_SIZE, PLAYER_RADIUS, SCROLL_SPEED
from source.mauzling         import Mauzling
from source.misc_gfx         import Color, draw_grid, draw_selection_box, FADE_SEQUENCE
from source.obstacle         import Obstacle
from source.selectionmenu    import SelectionMenu
from source.textinput        import TextInput
from source.tile_data        import TILE_DATA
from source.uiwidget         import UIWidget
from source.util             import get_file_paths
from source.worldmap         import WorldMap

GAME_VERS = 'OpenBound v0.1'
FRAMERATE = 23.8095

class GameState:
	START_MENU   = 0	#
	MAP_SELECT   = 1	# select a map to play
	MAP_SELECT_E = 2	# select a map to edit
	BOUNDING     = 3	#
	PAUSE_MENU   = 4	# pause screen while bounding
	PAUSE_MENU_E = 5	# fade screen when you select editor from main menu --> create new map or edit existing
	EDITOR_PROPERTIES = 6
	EDITOR_TERRAIN    = 7
	EDITOR_PLACE_OB   = 8
	EDITOR_EDIT_OB    = 9

UPSCALE_2X = True

def main(raw_args=None):
	parser = argparse.ArgumentParser(description=GAME_VERS, formatter_class=argparse.ArgumentDefaultsHelpFormatter,)
	parser.add_argument('-sw', type=int, required=False, metavar='640',       help="screen width",      default=640)
	parser.add_argument('-sh', type=int, required=False, metavar='480',       help="screen height",     default=480)
	parser.add_argument('--fullscreen',  required=False, action='store_true', help="run in fullscreen", default=False)
	args = parser.parse_args()
	#
	RESOLUTION     = Vector2(args.sw, args.sh)
	RUN_FULLSCREEN = args.fullscreen
	#
	py_dir   = pathlib.Path(__file__).resolve().parent
	GFX_DIR  = os.path.join(py_dir, 'assets', 'gfx')
	SFX_DIR  = os.path.join(py_dir, 'assets', 'audio')
	FONT_DIR = os.path.join(py_dir, 'assets', 'font')
	TILE_DIR = os.path.join(py_dir, 'assets', 'tiles')
	MAP_DIR  = os.path.join(py_dir, 'maps')
	#
	cursor_img_fns = get_file_paths(GFX_DIR, ['cursor.png', 'cursor_shift.png'])
	player_img_fns = get_file_paths(GFX_DIR, ['sq16.png'])
	ui_gfx_img_fns = get_file_paths(GFX_DIR, ['ling_icon.png'])
	expovy_img_fns = get_file_paths(GFX_DIR, ['ovy0.png', 'ovy0.png','ovy1.png','ovy2.png','ovy3.png','ovy4.png','ovy5.png'])
	expscr_img_fns = get_file_paths(GFX_DIR, ['scourge0.png','scourge1.png','scourge2.png','scourge3.png','scourge4.png','scourge5.png'])
	#
	exp_sound_fns    = get_file_paths(SFX_DIR, ['zovdth00.wav', 'zavdth00.wav'])
	player_sound_fns = get_file_paths(SFX_DIR, ['zzedth00.wav'])
	#
	pixel_font_fns = get_file_paths(FONT_DIR, ['small_font.png', 'large_font.png'])
	#
	tile_keys = sorted(TILE_DATA.keys())
	tile_fns  = get_file_paths(TILE_DIR, [TILE_DATA[n][2] for n in tile_keys])
	#
	MAPSELECT_MENU_POS = Vector2(48, 112)
	all_map_files      = []
	map_fn_to_load     = None
	world_map          = None
	map_width          = None
	map_height         = None
	my_player          = None

	#
	# initialize pygame
	#
	pygame.mixer.pre_init(44100, -16, 2, 2048)	# possibly not necessary?
	pygame.init()
	pygame.display.set_caption(GAME_VERS)
	disp_flags = 0
	if RUN_FULLSCREEN:
		disp_flags |= pygame.FULLSCREEN
	if UPSCALE_2X:
		upscale_screen = pygame.display.set_mode(size=2*RESOLUTION, flags=disp_flags, depth=0, display=0, vsync=0)
		screen         = pygame.Surface(RESOLUTION)
	else:
		screen = pygame.display.set_mode(size=RESOLUTION, flags=disp_flags, depth=0, display=0, vsync=0)
	trans_fade = pygame.Surface(RESOLUTION)
	main_clock = pygame.time.Clock()
	#pygame.event.set_grab(True)

	# font objects
	font_dict = {'small' :     Font(pixel_font_fns[0], Color.PAL_BLACK),
	             'small_w' :   Font(pixel_font_fns[0], Color.PAL_WHITE),
	             'large' :     Font(pixel_font_fns[1], Color.PAL_BLACK),
	             'large_w' :   Font(pixel_font_fns[1], Color.PAL_WHITE),
	             'lifecount':  Font(pixel_font_fns[1], Color.LIFECOUNT),
	             'fps':        Font(pixel_font_fns[1], Color.PAL_WHITE),
	             'titlepic':   Font(pixel_font_fns[1], Color.PAL_BLUE_2, scalar=8),
	             'titlepic2':  Font(pixel_font_fns[1], Color.PAL_BLUE_3, scalar=8),
	             'mapselect':  Font(pixel_font_fns[1], Color.PAL_BLUE_2, scalar=4),
	             'mapselect2': Font(pixel_font_fns[1], Color.PAL_BLUE_3, scalar=4)}

	# load animation gfx
	my_animations = AnimationManager()
	my_animations.add_animation_cycle(expovy_img_fns, 'overlord')
	my_animations.add_animation_cycle(expscr_img_fns, 'scourge')

	# other gfx
	my_cursor = Cursor(cursor_img_fns)
	#
	map_selection_menu = SelectionMenu(all_map_files, MAPSELECT_MENU_POS, font_dict['small_w'])
	#
	#
	#
	(tl, br) = (Vector2(32, RESOLUTION.y - 64), Vector2(160, RESOLUTION.y - 32))
	widget_playerselected = UIWidget()
	widget_playerselected.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_WHITE, border_radius=14)
	widget_playerselected.add_image(Vector2(tl.x+8, tl.y+2), ui_gfx_img_fns[0])
	widget_playerselected.add_text(Vector2(80,  RESOLUTION.y - 54), 'Lives:', 'lives', font_dict['lifecount'])
	widget_playerselected.add_text(Vector2(124, RESOLUTION.y - 54), '',   'lifecount', font_dict['lifecount'])
	#
	#
	#
	widget_titlepic = UIWidget()
	widget_titlepic.add_text(Vector2(RESOLUTION.x/2 + 3, 208) + Vector2(4,4), 'OpenBound', 'titlepic', font_dict['titlepic2'], is_centered=True)
	widget_titlepic.add_text(Vector2(RESOLUTION.x/2 + 3, 208), 'OpenBound', 'titlepic', font_dict['titlepic'], is_centered=True)
	#
	(tl, br) = (Vector2(96, RESOLUTION.y-96), Vector2(224, RESOLUTION.y-64))
	widget_title_play = UIWidget()
	widget_title_play.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_title_play.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_title_play.add_text((tl+br)/2 + Vector2(0,1), 'Play', 'play', font_dict['large_w'], is_centered=True)
	widget_title_play.add_return_message('play')
	#
	(tl, br) = (Vector2(256, RESOLUTION.y-96), Vector2(384, RESOLUTION.y-64))
	widget_title_editor = UIWidget()
	widget_title_editor.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_title_editor.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_title_editor.add_text((tl+br)/2 + Vector2(0,1), 'Map Editor', 'editor', font_dict['large_w'], is_centered=True)
	widget_title_editor.add_return_message('editor')
	#
	(tl, br) = (Vector2(416, RESOLUTION.y-96), Vector2(544, RESOLUTION.y-64))
	widget_title_options = UIWidget()
	widget_title_options.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_title_options.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_title_options.add_text((tl+br)/2 + Vector2(0,1), 'Options', 'options', font_dict['large_w'], is_centered=True)
	widget_title_options.add_return_message('options')
	#
	#
	#
	widget_mapselect_title = UIWidget()
	widget_mapselect_title.add_text(Vector2(RESOLUTION.x/2, 52) + Vector2(2,2), 'Map Select', 'mapselect', font_dict['mapselect2'], is_centered=True)
	widget_mapselect_title.add_text(Vector2(RESOLUTION.x/2, 52), 'Map Select', 'mapselect', font_dict['mapselect'], is_centered=True)
	#
	(tl, br) = (Vector2(512, RESOLUTION.y-64), Vector2(608, RESOLUTION.y-32))
	widget_mapselect_back = UIWidget()
	widget_mapselect_back.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_mapselect_back.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_mapselect_back.add_text((tl+br)/2 + Vector2(0,1), 'Back', 'back', font_dict['large_w'], is_centered=True)
	widget_mapselect_back.add_return_message('back')
	#
	(tl, br) = (Vector2(480, RESOLUTION.y-104), Vector2(608, RESOLUTION.y-72))
	widget_mapselect_play = UIWidget()
	widget_mapselect_play.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_mapselect_play.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_mapselect_play.add_text((tl+br)/2 + Vector2(0,1), 'Play', 'play', font_dict['large_w'], is_centered=True)
	widget_mapselect_play.add_return_message('play')
	#
	(tl, br) = (Vector2(32, RESOLUTION.y-96), Vector2(112, RESOLUTION.y-72))
	widget_mapselect_sort_filename = UIWidget()
	widget_mapselect_sort_filename.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_mapselect_sort_filename.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_mapselect_sort_filename.add_text((tl+br)/2 + Vector2(0,1), 'Filename', 'filename', font_dict['large_w'], is_centered=True)
	widget_mapselect_sort_filename.add_return_message('sort_filename')
	#
	(tl, br) = (Vector2(120, RESOLUTION.y-96), Vector2(200, RESOLUTION.y-72))
	widget_mapselect_sort_author = UIWidget()
	widget_mapselect_sort_author.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_mapselect_sort_author.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_mapselect_sort_author.add_text((tl+br)/2 + Vector2(0,1), 'Author', 'author', font_dict['large_w'], is_centered=True)
	widget_mapselect_sort_author.add_return_message('sort_author')
	#
	(tl, br) = (Vector2(208, RESOLUTION.y-96), Vector2(288, RESOLUTION.y-72))
	widget_mapselect_sort_diff = UIWidget()
	widget_mapselect_sort_diff.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_mapselect_sort_diff.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_mapselect_sort_diff.add_text((tl+br)/2 + Vector2(0,1), 'Difficulty', 'diff', font_dict['large_w'], is_centered=True)
	widget_mapselect_sort_diff.add_return_message('sort_diff')
	#
	widget_mapselect_sortby = UIWidget()
	widget_mapselect_sortby.add_text(Vector2(34,RESOLUTION.y-107), 'sort by:', 'sortby', font_dict['small_w'])
	#
	(tl, br) = (Vector2(32, 96), Vector2(312, RESOLUTION.y-112))
	widget_mapselect_menu = UIWidget()
	widget_mapselect_menu.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_5, border_radius=14)
	#
	(tl, br) = (Vector2(328, 96), Vector2(608, RESOLUTION.y-112))
	widget_mapselect_mapinfo = UIWidget()
	widget_mapselect_mapinfo.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_5, border_radius=14)
	widget_mapselect_mapinfo.add_text(Vector2(348,112), 'map-title',    'mapname',   font_dict['large_w'], max_width=240)
	widget_mapselect_mapinfo.add_text(Vector2(348,133), 'map-author',   'mapauthor', font_dict['small_w'], max_width=240)
	widget_mapselect_mapinfo.add_text(Vector2(348,160), 'Description:', 'desc',      font_dict['large_w'])
	widget_mapselect_mapinfo.add_text(Vector2(348,181), 'content',      'mapdesc',   font_dict['small_w'], max_width=240, num_rows=12)
	widget_mapselect_mapinfo.add_text(Vector2(348,304), 'Difficulty:',  'diff',      font_dict['large_w'])
	widget_mapselect_mapinfo.add_text(Vector2(424,304), 'content',      'mapdiff',   font_dict['large_w'], max_width=128)
	widget_mapselect_mapinfo.add_text(Vector2(348,328), 'Map size:',    'size',      font_dict['large_w'])
	widget_mapselect_mapinfo.add_text(Vector2(424,328), 'content',      'mapsize',   font_dict['large_w'], max_width=128)
	#
	#
	#
	(tl, br) = (Vector2(RESOLUTION.x/2 - 96, 176), Vector2(RESOLUTION.x/2 + 96, 208))
	widget_pausemenu_return = UIWidget()
	widget_pausemenu_return.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_pausemenu_return.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_pausemenu_return.add_text((tl+br)/2 + Vector2(0,1), 'Return to game', 'return', font_dict['large_w'], is_centered=True)
	widget_pausemenu_return.add_return_message('return')
	#
	(tl, br) = (Vector2(RESOLUTION.x/2 - 96, 224), Vector2(RESOLUTION.x/2 + 96, 256))
	widget_pausemenu_menu = UIWidget()
	widget_pausemenu_menu.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_pausemenu_menu.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_pausemenu_menu.add_text((tl+br)/2 + Vector2(0,1), 'Quit to menu', 'menu', font_dict['large_w'], is_centered=True)
	widget_pausemenu_menu.add_return_message('menu')
	#
	(tl, br) = (Vector2(RESOLUTION.x/2 - 96, 272), Vector2(RESOLUTION.x/2 + 96, 304))
	widget_pausemenu_quit = UIWidget()
	widget_pausemenu_quit.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_pausemenu_quit.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_pausemenu_quit.add_text((tl+br)/2 + Vector2(0,1), 'Quit to desktop', 'quit', font_dict['large_w'], is_centered=True)
	widget_pausemenu_quit.add_return_message('quit')
	#
	#
	#
	(tl, br) = (Vector2(RESOLUTION.x/2 - 96, 144), Vector2(RESOLUTION.x/2 + 96, 176))
	widget_editmenu_new = UIWidget()
	widget_editmenu_new.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmenu_new.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmenu_new.add_text((tl+br)/2 + Vector2(0,1), 'New', 'new', font_dict['large_w'], is_centered=True)
	widget_editmenu_new.add_return_message('new')
	#
	(tl, br) = (Vector2(RESOLUTION.x/2 - 96, 192), Vector2(RESOLUTION.x/2 + 96, 224))
	widget_editmenu_load = UIWidget()
	widget_editmenu_load.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmenu_load.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmenu_load.add_text((tl+br)/2 + Vector2(0,1), 'Load', 'load', font_dict['large_w'], is_centered=True)
	widget_editmenu_load.add_return_message('load')
	#
	(tl, br) = (Vector2(RESOLUTION.x/2 - 96, 240), Vector2(RESOLUTION.x/2 + 96, 272))
	widget_editmenu_back = UIWidget()
	widget_editmenu_back.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmenu_back.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmenu_back.add_text((tl+br)/2 + Vector2(0,1), 'Back', 'back', font_dict['large_w'], is_centered=True)
	widget_editmenu_back.add_return_message('back')
	#
	#
	#
	(tl, br) = (Vector2(128, 64), Vector2(256, 80))
	textinput_mapname = TextInput(Vector2(tl.x, tl.y), Vector2(br.x, br.y), font_dict['large_w'], char_offset=Vector2(5,2), num_rows=2)
	#
	(tl, br) = (Vector2(128, 96), Vector2(256, 112))
	textinput_author = TextInput(Vector2(tl.x, tl.y), Vector2(br.x, br.y), font_dict['small_w'])

	# load sounds
	my_audio = AudioManager()
	my_audio.add_sound(exp_sound_fns[0], 'overlord')
	my_audio.add_sound(exp_sound_fns[1], 'scourge')
	my_audio.add_sound(player_sound_fns[0], 'player_death')

	# misc vars
	WINDOW_OFFSET = Vector2(0, 0)
	SCROLL_X      = Vector2(SCROLL_SPEED, 0)
	SCROLL_Y      = Vector2(0, SCROLL_SPEED)
	TIME_SPENT    = [0.]
	selection_box = [None, None]

	#
	next_gamestate   = None
	transition_alpha = deque([])

	# inputs that can be held down across frames
	shift_pressed = False
	arrow_left    = False
	arrow_up      = False
	arrow_right   = False
	arrow_down    = False

	# Main game loop --------------------------------------------- #
	current_frame = 0
	current_gamestate = GameState.START_MENU
	while True:
		#
		# Get keyboard / mouse inputs ---------------------------- #
		#
		left_clicking   = False
		left_released   = False
		middle_clicking = False
		right_clicking  = False
		escape_pressed  = False
		pygame_events   = pygame.event.get()
		for event in pygame_events:
			if event.type == QUIT:
				pygame.quit()
				sys.exit()
			elif event.type == KEYDOWN:
				if event.key == K_LEFT:
					arrow_left = True
				if event.key == K_UP:
					arrow_up = True
				if event.key == K_RIGHT:
					arrow_right = True
				if event.key == K_DOWN:
					arrow_down = True
				if event.key == K_LSHIFT or event.key == K_RSHIFT:
					shift_pressed = True
				if event.key == K_ESCAPE:
					escape_pressed = True
			elif event.type == KEYUP:
				if event.key == K_LEFT:
					arrow_left = False
				if event.key == K_UP:
					arrow_up = False
				if event.key == K_RIGHT:
					arrow_right = False
				if event.key == K_DOWN:
					arrow_down = False
				if event.key == K_LSHIFT or event.key == K_RSHIFT:
					shift_pressed = False
			elif event.type == MOUSEBUTTONDOWN:
				if event.button == 1:
					left_clicking = True
				if event.button == 3:
					right_clicking = True
			elif event.type == MOUSEBUTTONUP:
				if event.button == 1:
					left_released = True
		#
		(mx,my) = pygame.mouse.get_pos()
		if UPSCALE_2X:
			upscaled_size = upscale_screen.get_size()	# might be 2x resoltuion, might be full monitor resolution
			mouse_scale_factor = (RESOLUTION.x/upscaled_size[0], RESOLUTION.y/upscaled_size[1])
			mouse_pos_screen = Vector2(int(mx*mouse_scale_factor[0] + 0.5), int(my*mouse_scale_factor[1] + 0.5))
		else:
			mouse_pos_screen = Vector2(mx,my)
		mouse_pos_map = mouse_pos_screen - WINDOW_OFFSET
		#
		if left_clicking:
			selection_box = [Vector2(mouse_pos_screen.x, mouse_pos_screen.y), None]
		if left_released:
			if selection_box[0] != None:
				if selection_box[1] == None:
					selection_box[1] = selection_box[0]
		if selection_box[0] != None:
			selection_box[1] = Vector2(mouse_pos_screen.x, mouse_pos_screen.y)

		# Background --------------------------------------------- #
		screen.fill(Color.BACKGROUND)
		grid_offset = Vector2(WINDOW_OFFSET.x % GRID_SIZE, WINDOW_OFFSET.y % GRID_SIZE)
		draw_grid(screen, RESOLUTION,   GRID_SIZE, grid_offset, Color.GRID_MINOR)
		draw_grid(screen, RESOLUTION, 2*GRID_SIZE, grid_offset, Color.GRID_MAJOR)

		#
		# STARTING MENU
		#
		if current_gamestate == GameState.START_MENU or current_gamestate == GameState.PAUSE_MENU_E:
			#
			menu_widgets = [widget_titlepic, widget_title_play, widget_title_editor, widget_title_options]
			for mw in menu_widgets:
				mw.draw(screen)
			#
			textinput_mapname.draw(screen)
			textinput_mapname.update(mouse_pos_screen, left_clicking, pygame_events)
			textinput_author.draw(screen)
			textinput_author.update(mouse_pos_screen, left_clicking, pygame_events)
			#
			if current_gamestate == GameState.START_MENU:
				mw_output_msgs = {}
				for mw in menu_widgets:
					mw_output_msgs[mw.update(mouse_pos_screen, left_clicking)] = True
				for msg in mw_output_msgs:
					if not transition_alpha:
						if msg == 'play':
							next_gamestate   = GameState.MAP_SELECT
							transition_alpha = deque(FADE_SEQUENCE)
						elif msg == 'editor':
							current_gamestate = GameState.PAUSE_MENU_E
						elif msg == 'options':
							pass
				if escape_pressed:
					pygame.quit()
					sys.exit()

			#
			# MENU: CREATE NEW MAP OR LOAD EXISTING MAP TO EDIT
			#
			elif current_gamestate == GameState.PAUSE_MENU_E:
				trans_fade.fill(Color.BACKGROUND)
				trans_fade.set_alpha(128)
				screen.blit(trans_fade, (0,0), special_flags=pygame.BLEND_ALPHA_SDL2)
				#
				menu_widgets_2 = [widget_editmenu_new, widget_editmenu_load, widget_editmenu_back]
				#
				mw_output_msgs = {}
				for mw in menu_widgets_2:
					mw_output_msgs[mw.update(mouse_pos_screen, left_clicking)] = True
					mw.draw(screen)
				for msg in mw_output_msgs:
					if not transition_alpha:
						if msg == 'new':
							pass
						elif msg == 'load':
							next_gamestate   = GameState.MAP_SELECT_E
							transition_alpha = deque(FADE_SEQUENCE)
						elif msg == 'back':
							current_gamestate = GameState.START_MENU
				if escape_pressed:
					current_gamestate = GameState.START_MENU

		#
		# MAP SELECTION MENU
		#
		elif current_gamestate == GameState.MAP_SELECT:
			#
			menu_widgets = [widget_mapselect_title,
			                widget_mapselect_menu,
			                widget_mapselect_sort_filename,
			                widget_mapselect_sort_author,
			                widget_mapselect_sort_diff,
			                widget_mapselect_sortby,
			                widget_mapselect_mapinfo,
			                widget_mapselect_play,
			                widget_mapselect_back]
			#
			(fn_print, mapfn, mapname, mapauthor, mapnotes, mapdiff, mapwidth, mapheight, maplives) = map_selection_menu.get_selected_mapinfo()
			widget_mapselect_mapinfo.text_data['mapname']   = str(mapname)
			widget_mapselect_mapinfo.text_data['mapauthor'] = str(mapauthor)
			widget_mapselect_mapinfo.text_data['mapdesc']   = str(mapnotes)
			widget_mapselect_mapinfo.text_data['mapdiff']   = str(mapdiff)
			widget_mapselect_mapinfo.text_data['mapsize']   = '{0}x{1}'.format(mapwidth, mapheight)
			#
			mw_output_msgs = {}
			for mw in menu_widgets:
				mw_output_msgs[mw.update(mouse_pos_screen, left_clicking)] = True
				mw.draw(screen)
			#
			if arrow_down and not arrow_up:
				map_selection_menu.increase_index()
			elif arrow_up and not arrow_down:
				map_selection_menu.decrease_index()
			#
			map_selection_menu.update(mouse_pos_screen, left_clicking)
			map_selection_menu.draw(screen)
			#
			for msg in mw_output_msgs:
				if not transition_alpha:
					if msg == 'play':
						next_gamestate   = GameState.BOUNDING
						map_fn_to_load   = mapfn
						transition_alpha = deque(FADE_SEQUENCE)
					elif msg == 'back':
						next_gamestate   = GameState.START_MENU
						transition_alpha = deque(FADE_SEQUENCE)
					elif msg == 'sort_filename':
						map_selection_menu.resort(0)
					elif msg == 'sort_author':
						map_selection_menu.resort(3)
					elif msg == 'sort_diff':
						map_selection_menu.resort(5)
			#
			if escape_pressed:
				next_gamestate   = GameState.START_MENU
				transition_alpha = deque(FADE_SEQUENCE)

		#
		# WE ARE BOUNDING.
		#
		elif current_gamestate == GameState.BOUNDING or current_gamestate == GameState.PAUSE_MENU:
			#
			if current_gamestate == GameState.BOUNDING:
				current_volume = 0.35
				#
				# processing player inputs: moving screen
				#
				if arrow_left and not arrow_right:
					WINDOW_OFFSET += SCROLL_X
				if arrow_right and not arrow_left:
					WINDOW_OFFSET -= SCROLL_X
				if arrow_up and not arrow_down:
					WINDOW_OFFSET += SCROLL_Y
				if arrow_down and not arrow_up:
					WINDOW_OFFSET -= SCROLL_Y
				WINDOW_OFFSET.x = value_clamp(WINDOW_OFFSET.x, min(RESOLUTION.x -  map_width, 0), 0)
				WINDOW_OFFSET.y = value_clamp(WINDOW_OFFSET.y, min(RESOLUTION.y - map_height, 0), 0)
				#
				# processing player inputs: selection + movement orders
				#
				if left_released and selection_box[0] != None:
					if (selection_box[1] - selection_box[0]).length() < 4:
						my_player.check_selection_click(selection_box[1] - WINDOW_OFFSET)
					else:
						my_player.check_selection_box([selection_box[0] - WINDOW_OFFSET, selection_box[1] - WINDOW_OFFSET])
				#
				if right_clicking:
					draw_cursor = my_player.issue_new_order(mouse_pos_map, shift_pressed)
					if draw_cursor:
						my_cursor.start_click_animation(mouse_pos_screen, shift_pressed)
			#
			elif current_gamestate == GameState.PAUSE_MENU:
				current_volume = 0.12
			#
			# update players
			#
			my_player.tick(world_map)

			#
			# update obstacles
			#
			for obname, ob in world_map.obstacles.items():
				ob.check_for_ob_start(my_player.position)
				ob.check_for_ob_end(my_player.position)
				(ob_gfx, ob_snd, ob_kill, ob_tele) = ob.tick()
				for n in ob_gfx:
					my_animations.start_new_animation(n[0], n[1])
				for n in ob_snd:
					my_audio.play_sound(n[0], volume=current_volume)
				if ob_kill:
					player_died = my_player.check_kill_boxes(ob_kill)
					if player_died:
						my_player.revive_at_pos(ob.revive_coords)
						my_audio.play_sound('player_death', volume=current_volume)
				####if current_frame == 300:
				####	my_player.add_lives(10, ob.revive_coords)

			# Terrain / Obstacles ------------------------------------ #
			world_map.draw(screen, WINDOW_OFFSET, draw_tiles=True,
			                                      draw_obs=False,
			                                      draw_walkable=False,
			                                      draw_pathing=False)

			# Foreground objects ------------------------------------- #
			my_player.draw(screen, WINDOW_OFFSET, draw_bounding_box=True)
			my_animations.draw(screen, WINDOW_OFFSET)

			# Draw UI elements --------------------------------------- #
			if current_gamestate == GameState.BOUNDING:
				if selection_box[0] != None:
					draw_selection_box(screen, selection_box, Color.SELECTION)
			#
			if my_player.is_selected:
				widget_playerselected.text_data['lifecount'] = str(my_player.num_lives)
				widget_playerselected.draw(screen)
			#
			if current_gamestate == GameState.BOUNDING:
				my_cursor.draw(screen)

			#
			# PAUSE MENU
			#
			if current_gamestate == GameState.PAUSE_MENU:
				trans_fade.fill(Color.BACKGROUND)
				trans_fade.set_alpha(128)
				screen.blit(trans_fade, (0,0), special_flags=pygame.BLEND_ALPHA_SDL2)
				#
				menu_widgets = [widget_pausemenu_return, widget_pausemenu_menu, widget_pausemenu_quit]
				#
				mw_output_msgs = {}
				for mw in menu_widgets:
					mw_output_msgs[mw.update(mouse_pos_screen, left_clicking)] = True
					mw.draw(screen)
				for msg in mw_output_msgs:
					if not transition_alpha:
						if msg == 'return':
							current_gamestate = GameState.BOUNDING
						elif msg == 'menu':
							next_gamestate   = GameState.START_MENU
							transition_alpha = deque(FADE_SEQUENCE)
						elif msg == 'quit':
							pygame.quit()
							sys.exit()
				if escape_pressed:
					current_gamestate = GameState.BOUNDING
			#
			elif escape_pressed:
				current_gamestate = GameState.PAUSE_MENU

		# Draw transition fade ----------------------------------- #
		if next_gamestate != None:
			current_opacity = transition_alpha.popleft()
			trans_fade.fill(Color.BACKGROUND)
			trans_fade.set_alpha(current_opacity)
			screen.blit(trans_fade, (0,0), special_flags=pygame.BLEND_ALPHA_SDL2)
			if current_opacity >= 255:
				current_gamestate = next_gamestate
				#
				if current_gamestate == GameState.MAP_SELECT:
					all_map_names = [n for n in os.listdir(MAP_DIR) if n[-5:] == '.json']
					all_map_files = get_file_paths(MAP_DIR, all_map_names)
					for i in range(len(all_map_names)):
						all_map_files[i] = (all_map_names[i][:-5], all_map_files[i])
					map_selection_menu = SelectionMenu(all_map_files, MAPSELECT_MENU_POS, font_dict['small_w'])
				#
				if current_gamestate == GameState.BOUNDING:
					if map_fn_to_load != None:
						#
						# load world and place player 1
						#
						world_map = WorldMap(map_fn_to_load, tile_fns, font_dict)
						if world_map.p_starts[0] == None:
							print('No player 1 start found')
							exit(1)
						map_width  = world_map.map_width * GRID_SIZE
						map_height = world_map.map_height * GRID_SIZE
						my_player  = Mauzling(world_map.p_starts[0], 0, player_img_fns[0])
						my_player.num_lives = world_map.init_lives
						map_fn_to_load = None
			if not transition_alpha:
				next_gamestate = None

		# Print FPS / mouse coords ------------------------------- #
		fps_str = '{0:0.2f}'.format(main_clock.get_fps())
		mxy_str = '{0}, {1}'.format(int(mouse_pos_map.x), int(mouse_pos_map.y))
		font_dict['fps'].render(screen, fps_str, Vector2(RESOLUTION[0]-34, 4), centered=False)
		font_dict['fps'].render(screen, mxy_str, Vector2(RESOLUTION[0]-58, RESOLUTION[1]-17), centered=False)

		# Stretch screen to fill upsized window (if needed) ------ #
		if UPSCALE_2X:
			scaled_screen = pygame.transform.scale(screen, upscale_screen.get_size())
			upscale_screen.blit(scaled_screen, (0,0))

		# Update ------------------------------------------------- #
		pygame.display.update()
		main_clock.tick_busy_loop(FRAMERATE)
		current_frame += 1

		if left_released:
			selection_box = [None, None]

		##### print runtime stats every 100 frames
		####if current_frame % 100 == 0:
		####	print([int(1000.*n/current_frame) for n in TIME_SPENT], 'ms/frame')

if __name__ == '__main__':
	try:
		main()
	finally:
		pygame.quit()
