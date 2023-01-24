#!/usr/bin/env python
# encoding: utf-8
import argparse
import os
import pathlib
import pygame
import sys
import time

from collections   import deque
from pygame.math   import Vector2

import pygame.locals as pl
import numpy as np

from source.animationmanager import AnimationManager
from source.audiomanager     import AudioManager
from source.cursor           import Cursor
from source.draggableobject  import DraggableObject
from source.font             import Font
from source.geometry         import get_window_offset, point_in_box_excl
from source.globals          import GRID_SIZE, PLAYER_RADIUS
from source.mauzling         import Mauzling
from source.misc_gfx         import Color, draw_grid, draw_map_bounds, draw_selection_box, FADE_SEQUENCE
from source.obstacle         import Obstacle
from source.resizablebox     import ResizableBox
from source.selectionmenu    import MapMenu, TerrainMenu, UnitMenu
from source.textinput        import DigitInput, TextInput
from source.tile_data        import TILE_DATA
from source.uiwidget         import UIWidget
from source.util             import get_file_paths
from source.worldmap         import TileMap, WorldMap

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
	EDITOR_LOCATIONS  = 8
	EDITOR_EXPLOSIONS = 9
	EDITOR_SAVE       = 10

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
	player_img_fns = get_file_paths(GFX_DIR, ['sq16.png', 'sq16_gray.png'])
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
	all_map_files  = []
	map_fn_to_load = None
	world_map      = None
	map_width      = None
	map_height     = None
	my_player      = None

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
	edbar_fade = pygame.Surface(Vector2(RESOLUTION.x, 128))
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

	# initial geometry stuff
	DEFAULT_PLAYER_START  = Vector2(1,1)
	DEFAULT_MAP_DIM       = Vector2(32,32)
	current_map_bounds    = DEFAULT_MAP_DIM*GRID_SIZE
	current_window_offset = Vector2(0, 0)
	selection_box         = [None, None]
	leftclick_is_down     = False
	rightclick_is_down    = False
	editor_resolution     = Vector2(RESOLUTION.x, RESOLUTION.y-128)
	editor_tilemap        = np.zeros((int(DEFAULT_MAP_DIM.x), int(DEFAULT_MAP_DIM.y)), dtype='<i4')
	editor_prevtilemapdim = editor_tilemap.shape
	editor_tiledrawer     = TileMap(tile_fns)
	editor_obdata         = []
	editor_currentobnum   = None

	# other gfx
	my_cursor          = Cursor(cursor_img_fns)
	map_selection_menu = None
	highlight_walls    = False

	#
	#
	#	IN-GAME WIDGETS
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
	#	MAIN MENU WIDGETS
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
	#	MAP SELECTION SCREEN WIDGETS
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
	MAPSELECT_MENU_POS = Vector2(48, 112)
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
	#	PAUSE MENU WIDGETS
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
	#	MAIN MENU --> EDITOR TRANSITION WIDGETS
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
	#	MAP PROPERTIES MODE WIDGETS
	#
	#
	tl = Vector2(148, 368 + 5)
	widget_propertiesmode_text = UIWidget()
	widget_propertiesmode_text.add_text(Vector2(tl.x, tl.y),     'Title:',           't1', font_dict['large_w'])
	widget_propertiesmode_text.add_text(Vector2(tl.x+254, tl.y), 'Map description:', 't2', font_dict['large_w'])
	tl = Vector2(148, 392 + 5)
	widget_propertiesmode_text.add_text(Vector2(tl.x, tl.y), 'Author:', 't3', font_dict['large_w'])
	tl = Vector2(148, 416 + 5)
	widget_propertiesmode_text.add_text(Vector2(tl.x, tl.y),     'Lives:', 't4', font_dict['large_w'])
	widget_propertiesmode_text.add_text(Vector2(tl.x+108, tl.y), 'Size:',  't5', font_dict['large_w'])
	widget_propertiesmode_text.add_text(Vector2(tl.x+193, tl.y), 'x',      't6', font_dict['large_w'])
	tl = Vector2(148, 440 + 5)
	widget_propertiesmode_text.add_text(Vector2(tl.x, tl.y),     'Rating:', 't7', font_dict['large_w'])
	widget_propertiesmode_text.add_text(Vector2(tl.x+108, tl.y), 'Start:',  't8', font_dict['large_w'])
	widget_propertiesmode_text.add_text(Vector2(tl.x+193, tl.y), 'x',       't9', font_dict['large_w'])
	#
	VBUFF    = 2
	(tl, br) = (Vector2(208, 368 + VBUFF), Vector2(384, 392 - VBUFF))
	textinput_mapname = TextInput(Vector2(tl.x, tl.y), Vector2(br.x, br.y), font_dict['small_w'], char_offset=Vector2(6,7), max_chars=100)
	#
	(tl, br) = (Vector2(208, 392 + VBUFF), Vector2(384, 416 - VBUFF))
	textinput_author      = TextInput(Vector2(tl.x, tl.y), Vector2(br.x, br.y), font_dict['small_w'], char_offset=Vector2(6,7), max_chars=100)
	textinput_description = TextInput(Vector2(tl.x+192, tl.y), Vector2(br.x+176, br.y+48), font_dict['small_w'], char_offset=Vector2(4,4), num_rows=7, max_chars=500)
	#
	(tl, br) = (Vector2(208, 416 + VBUFF), Vector2(240, 440 - VBUFF))
	digitinput_lives    = DigitInput(Vector2(tl.x, tl.y),     Vector2(br.x+2, br.y),   font_dict['small_w'], (0,9999), char_offset=Vector2(6,7), default_val=100, max_chars=4)
	digitinput_mapsizex = DigitInput(Vector2(tl.x+96, tl.y),  Vector2(br.x+96, br.y),  font_dict['small_w'], (16,256), char_offset=Vector2(6,7), default_val=int(DEFAULT_MAP_DIM.x),  max_chars=3)
	digitinput_mapsizey = DigitInput(Vector2(tl.x+144, tl.y), Vector2(br.x+144, br.y), font_dict['small_w'], (16,256), char_offset=Vector2(6,7), default_val=int(DEFAULT_MAP_DIM.y),  max_chars=3)
	#
	(tl, br) = (Vector2(208, 440 + VBUFF), Vector2(240, 464 - VBUFF))
	digitinput_rating  = DigitInput(Vector2(tl.x, tl.y),     Vector2(br.x+2, br.y),   font_dict['small_w'], (0,99),  char_offset=Vector2(6,7), default_val=5, max_chars=2)
	digitinput_playerx = DigitInput(Vector2(tl.x+96, tl.y),  Vector2(br.x+96, br.y),  font_dict['small_w'], (0,255), char_offset=Vector2(6,7), default_val=1, max_chars=3)
	digitinput_playery = DigitInput(Vector2(tl.x+144, tl.y), Vector2(br.x+144, br.y), font_dict['small_w'], (0,255), char_offset=Vector2(6,7), default_val=1, max_chars=3)
	#
	draggable_playerstart = DraggableObject(Vector2(DEFAULT_PLAYER_START.x*GRID_SIZE - GRID_SIZE/2, DEFAULT_PLAYER_START.y*GRID_SIZE - GRID_SIZE/2), PLAYER_RADIUS)
	draggable_playerstart.add_image(player_img_fns[0])
	#
	#
	#	TERRAIN MODE WIDGETS
	#
	#
	(tl, br) = (Vector2(208, 368), Vector2(448, 464))
	widget_terrainmode_text = UIWidget()
	widget_terrainmode_text.add_rect(Vector2(tl.x-64, tl.y), Vector2(tl.x-16, br.y-40), Color.PAL_BLUE_5, border_radius=4)
	widget_terrainmode_text.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_5, border_radius=4)
	(tl, br) = (Vector2(464, 368), Vector2(560, 464))
	widget_terrainmode_text.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_5, border_radius=4)
	widget_terrainmode_text.add_text(Vector2((tl.x+br.x)/2 - 1, tl.y + 12), 'tilename',  'tilename', font_dict['small_w'], max_width=84, is_centered=True)
	#
	(tl, br) = (Vector2(144, 432), Vector2(192, 464))
	widget_terrainmode_highlightwalls = UIWidget()
	widget_terrainmode_highlightwalls.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_terrainmode_highlightwalls.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_terrainmode_highlightwalls.add_text((tl+br)/2 + Vector2(1,-4), 'Highlight', 'highlight', font_dict['small_w'], is_centered=True)
	widget_terrainmode_highlightwalls.add_text((tl+br)/2 + Vector2(1,7),  'walls',     'walls',     font_dict['small_w'], is_centered=True)
	widget_terrainmode_highlightwalls.add_return_message('toggle_wall_highlighting')
	#
	terraindim_selection_menu = UnitMenu(Vector2(154, 372), ['16x16', '32x32', '64x64'], font_dict['small_w'], num_rows=3, row_height=16, col_width=28)
	#
	(tl, br) = (Vector2(208, 368), Vector2(432, 464))
	terrain_selection_menu = TerrainMenu(tl, tile_fns, font_dict['small_w'])
	#
	#
	#	LOCATIONS MODE WIDGETS
	#
	#
	(tl, br) = (Vector2(148, 368 + 5), Vector2(224, RESOLUTION.y-16))
	widget_locationsmode_text = UIWidget()
	widget_locationsmode_text.add_rect(Vector2(tl.x, tl.y+20), Vector2(br.x, br.y), Color.PAL_BLUE_5, border_radius=4)
	widget_locationsmode_text.add_text(Vector2(tl.x+2, tl.y), 'Current ob:', 't1', font_dict['large_w'])
	currentob_selection_menu = UnitMenu(Vector2(tl.x+4, tl.y+24), [], font_dict['small_w'], num_rows=4, row_height=16, col_width=68)
	currentob_selection_menu.empty_message = ''
	#
	(tl, br) = (Vector2(240, 392), Vector2(302, 424))
	widget_locationsmode_addnew = UIWidget()
	widget_locationsmode_addnew.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_locationsmode_addnew.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_locationsmode_addnew.add_text((tl+br)/2 + Vector2(1,1), 'New Ob', 'addnew_ob', font_dict['large_w'], is_centered=True)
	widget_locationsmode_addnew.add_return_message('addnew_ob')
	#
	(tl, br) = (Vector2(240, 432), Vector2(302, 464))
	widget_locationsmode_delete = UIWidget()
	widget_locationsmode_delete.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_locationsmode_delete.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_locationsmode_delete.add_text((tl+br)/2 + Vector2(1,1), 'Delete', 'delete_ob', font_dict['large_w'], is_centered=True)
	widget_locationsmode_delete.add_return_message('delete_ob')
	#
	(tl, br) = (Vector2(320, 392), Vector2(368, 424))
	widget_locationsmode_obselectedtext = UIWidget()
	widget_locationsmode_obselectedtext.add_rect(Vector2(tl.x+48, tl.y-4), Vector2(br.x+48, br.y+4), Color.PAL_BLUE_5, border_radius=4)
	widget_locationsmode_obselectedtext.add_rect(Vector2(tl.x+152, tl.y-4), Vector2(br.x+152, br.y+4), Color.PAL_BLUE_5, border_radius=4)
	widget_locationsmode_obselectedtext.add_text(Vector2(tl.x+2, tl.y+9),   'Move:',  't1', font_dict['large_w'])
	widget_locationsmode_obselectedtext.add_text(Vector2(tl.x+106, tl.y+9), 'Lives:', 't2', font_dict['large_w'])
	widget_locationsmode_obselectedtext.add_text(Vector2(tl.x+2, tl.y+49),  'Music:', 't3', font_dict['large_w'])
	#
	obinfo_move_menu = UnitMenu(Vector2(tl.x+48+4, tl.y), ['no move', 'to revive'], font_dict['small_w'], num_rows=2, row_height=16, col_width=40)
	#
	obinfo_life_menu = UnitMenu(Vector2(tl.x+152+4, tl.y), ['add lives', 'set lives'], font_dict['small_w'], num_rows=2, row_height=16, col_width=40)
	#
	(tl, br) = (Vector2(368, 432+6), Vector2(560, 464-6))
	textinput_musicname = TextInput(Vector2(tl.x, tl.y), Vector2(br.x, br.y), font_dict['small_w'], char_offset=Vector2(6,7), max_chars=100)
	#
	(tl, br) = (Vector2(528, 392+6), Vector2(560, 424-6))
	digitinput_oblives = DigitInput(Vector2(tl.x, tl.y), Vector2(br.x, br.y), font_dict['small_w'], (0,9999), char_offset=Vector2(6,7), default_val=0, max_chars=4)
	#
	#
	#	EXPLOSIONS MODE WIDGETS
	#
	#
	(tl, br) = (Vector2(148, 368 + 5), Vector2(224, RESOLUTION.y-16))
	widget_explosionsmode_text = UIWidget()
	widget_explosionsmode_text.add_rect(Vector2(tl.x, tl.y+20), Vector2(br.x, br.y), Color.PAL_BLUE_5, border_radius=4)
	widget_explosionsmode_text.add_text(Vector2(tl.x+2, tl.y), 'Event type:', 't1', font_dict['large_w'])
	event_selection_menu = UnitMenu(Vector2(tl.x+4, tl.y+24), ['explosion', 'add wall', 'remove wall', 'teleport'], font_dict['small_w'], num_rows=4, row_height=16, col_width=68)
	#
	widget_explosionsmode_submenu_explosion = UIWidget()
	widget_explosionsmode_submenu_explosion.add_rect(Vector2(tl.x+96, tl.y+20), Vector2(br.x+96, br.y), Color.PAL_BLUE_5, border_radius=4)
	widget_explosionsmode_submenu_explosion.add_text(Vector2(tl.x+98, tl.y), 'Unit:', 't1', font_dict['large_w'])
	unit_selection_menu_explosion = UnitMenu(Vector2(tl.x+100, tl.y+24), ['overlord', 'scourge'], font_dict['small_w'], num_rows=4, row_height=16, col_width=68)
	#
	#
	#	VARIOUS EDITOR MODE WIDGETS
	#
	#
	(tl, br) = (Vector2(16, RESOLUTION.y - 112 + 1), Vector2(128, RESOLUTION.y - 88 - 1))
	widget_editmode_properties = UIWidget()
	widget_editmode_properties.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmode_properties.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmode_properties.add_text((tl+br)/2 + Vector2(1,1), 'Map properties', 'properties', font_dict['large_w'], is_centered=True)
	widget_editmode_properties.add_return_message('change_edit_mode_to_properties')
	#
	(tl, br) = (Vector2(16, RESOLUTION.y - 88 + 1), Vector2(128, RESOLUTION.y - 64 - 1))
	widget_editmode_terrain = UIWidget()
	widget_editmode_terrain.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmode_terrain.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmode_terrain.add_text((tl+br)/2 + Vector2(1,1), 'Terrain', 'terrain', font_dict['large_w'], is_centered=True)
	widget_editmode_terrain.add_return_message('change_edit_mode_to_terrain')
	#
	(tl, br) = (Vector2(16, RESOLUTION.y - 64 + 1), Vector2(128, RESOLUTION.y - 40 - 1))
	widget_editmode_placeob = UIWidget()
	widget_editmode_placeob.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmode_placeob.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmode_placeob.add_text((tl+br)/2 + Vector2(1,1), 'Locations', 'placeob', font_dict['large_w'], is_centered=True)
	widget_editmode_placeob.add_return_message('change_edit_mode_to_locations')
	#
	(tl, br) = (Vector2(16, RESOLUTION.y - 40 + 1), Vector2(128, RESOLUTION.y - 16 - 1))
	widget_editmode_editob = UIWidget()
	widget_editmode_editob.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmode_editob.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmode_editob.add_text((tl+br)/2 + Vector2(1,1), 'Explosions', 'editob', font_dict['large_w'], is_centered=True)
	widget_editmode_editob.add_return_message('change_edit_mode_to_explosions')
	#
	(tl, br) = (Vector2(576, RESOLUTION.y - 112 + 4 + 1), Vector2(624, RESOLUTION.y - 88 + 4 - 1))
	widget_editmode_undo = UIWidget()
	widget_editmode_undo.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmode_undo.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmode_undo.add_text((tl+br)/2 + Vector2(1,1), 'Undo', 'undo', font_dict['large_w'], is_centered=True)
	widget_editmode_undo.add_return_message('undo')
	#
	(tl, br) = (Vector2(576, RESOLUTION.y - 88 + 4 + 1), Vector2(624, RESOLUTION.y - 64 + 4 - 1))
	widget_editmode_redo = UIWidget()
	widget_editmode_redo = UIWidget()
	widget_editmode_redo.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmode_redo.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmode_redo.add_text((tl+br)/2 + Vector2(1,1), 'Redo', 'redo', font_dict['large_w'], is_centered=True)
	widget_editmode_redo.add_return_message('redo')
	#
	(tl, br) = (Vector2(576, RESOLUTION.y - 64 + 4 + 1), Vector2(624, RESOLUTION.y - 40 + 4 - 1))
	widget_editmode_test = UIWidget()
	widget_editmode_test = UIWidget()
	widget_editmode_test.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editmode_test.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editmode_test.add_text((tl+br)/2 + Vector2(1,1), 'Test', 'test', font_dict['large_w'], is_centered=True)
	widget_editmode_test.add_return_message('test')
	#
	#
	#
	(tl, br) = (Vector2(RESOLUTION.x/2 - 96, 144), Vector2(RESOLUTION.x/2 + 96, 176))
	widget_editpause_save = UIWidget()
	widget_editpause_save.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editpause_save.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editpause_save.add_text((tl+br)/2 + Vector2(0,1), 'Save map', 'save', font_dict['large_w'], is_centered=True)
	widget_editpause_save.add_return_message('save')
	#
	(tl, br) = (Vector2(RESOLUTION.x/2 - 96, 192), Vector2(RESOLUTION.x/2 + 96, 224))
	widget_editpause_return = UIWidget()
	widget_editpause_return.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editpause_return.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editpause_return.add_text((tl+br)/2 + Vector2(0,1), 'Return to editor', 'return', font_dict['large_w'], is_centered=True)
	widget_editpause_return.add_return_message('return')
	#
	(tl, br) = (Vector2(RESOLUTION.x/2 - 96, 240), Vector2(RESOLUTION.x/2 + 96, 272))
	widget_editpause_quit = UIWidget()
	widget_editpause_quit.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
	widget_editpause_quit.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
	widget_editpause_quit.add_text((tl+br)/2 + Vector2(0,1), 'Quit to main menu', 'quit', font_dict['large_w'], is_centered=True)
	widget_editpause_quit.add_return_message('quit')
	#
	#
	#

	# load sounds
	my_audio = AudioManager()
	my_audio.add_sound(exp_sound_fns[0], 'overlord')
	my_audio.add_sound(exp_sound_fns[1], 'scourge')
	my_audio.add_sound(player_sound_fns[0], 'player_death')

	# misc gamestate stuff
	next_gamestate   = None
	transition_alpha = deque([])
	editor_states    = [GameState.EDITOR_PROPERTIES, GameState.EDITOR_TERRAIN, GameState.EDITOR_LOCATIONS, GameState.EDITOR_EXPLOSIONS, GameState.EDITOR_SAVE]
	previous_editor_state = None

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
		right_released  = False
		escape_pressed  = False
		return_pressed  = False
		pygame_events   = pygame.event.get()
		for event in pygame_events:
			if event.type == pl.QUIT:
				pygame.quit()
				sys.exit()
			elif event.type == pl.KEYDOWN:
				if event.key == pl.K_LEFT:
					arrow_left = True
				if event.key == pl.K_UP:
					arrow_up = True
				if event.key == pl.K_RIGHT:
					arrow_right = True
				if event.key == pl.K_DOWN:
					arrow_down = True
				if event.key == pl.K_LSHIFT or event.key == pl.K_RSHIFT:
					shift_pressed = True
				if event.key == pl.K_ESCAPE:
					escape_pressed = True
				if event.key == pl.K_RETURN:
					return_pressed = True
			elif event.type == pl.KEYUP:
				if event.key == pl.K_LEFT:
					arrow_left = False
				if event.key == pl.K_UP:
					arrow_up = False
				if event.key == pl.K_RIGHT:
					arrow_right = False
				if event.key == pl.K_DOWN:
					arrow_down = False
				if event.key == pl.K_LSHIFT or event.key == pl.K_RSHIFT:
					shift_pressed = False
			elif event.type == pl.MOUSEBUTTONDOWN:
				if event.button == 1:
					left_clicking = True
				if event.button == 3:
					right_clicking = True
			elif event.type == pl.MOUSEBUTTONUP:
				if event.button == 1:
					left_released = True
				if event.button == 3:
					right_released = True
		#
		(mx,my) = pygame.mouse.get_pos()
		if UPSCALE_2X:
			upscaled_size = upscale_screen.get_size()	# might be 2x resoltuion, might be full monitor resolution
			mouse_scale_factor = (RESOLUTION.x/upscaled_size[0], RESOLUTION.y/upscaled_size[1])
			mouse_pos_screen = Vector2(int(mx*mouse_scale_factor[0] + 0.5), int(my*mouse_scale_factor[1] + 0.5))
		else:
			mouse_pos_screen = Vector2(mx,my)
		mouse_pos_map = mouse_pos_screen - current_window_offset
		#
		if left_clicking:
			leftclick_is_down = True
			selection_box = [Vector2(mouse_pos_screen.x, mouse_pos_screen.y), None]
		if left_released:
			leftclick_is_down = False
			if selection_box[0] != None:
				if selection_box[1] == None:
					selection_box[1] = selection_box[0]
		if selection_box[0] != None:
			selection_box[1] = Vector2(mouse_pos_screen.x, mouse_pos_screen.y)
		#
		if right_clicking:
			rightclick_is_down = True
		if right_released:
			rightclick_is_down = False
		#
		inc_menus_key = arrow_down and not arrow_up
		dec_menus_key = arrow_up and not arrow_down

		# Background --------------------------------------------- #
		screen.fill(Color.BACKGROUND)
		grid_offset = Vector2(current_window_offset.x % (2*GRID_SIZE), current_window_offset.y % (2*GRID_SIZE))
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
				mw_output_msgs_2 = {}
				for mw in menu_widgets_2:
					mw_output_msgs_2[mw.update(mouse_pos_screen, left_clicking)] = True
					mw.draw(screen)
				for msg in mw_output_msgs_2:
					if not transition_alpha:
						if msg == 'new':
							next_gamestate   = GameState.EDITOR_PROPERTIES
							transition_alpha = deque(FADE_SEQUENCE)
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
			(fn_print, mapfn, mapname, mapauthor, mapnotes, mapdiff, mapwidth, mapheight, maplives) = map_selection_menu.get_selected_content(sanitize=True)
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
			map_selection_menu.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
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
				# processing player inputs
				#
				current_window_offset = get_window_offset((arrow_left, arrow_up, arrow_right, arrow_down), current_window_offset, current_map_bounds, RESOLUTION)
				#
				if left_released and selection_box[0] != None:
					if (selection_box[1] - selection_box[0]).length() < 4:
						my_player.check_selection_click(selection_box[1] - current_window_offset)
					else:
						my_player.check_selection_box([selection_box[0] - current_window_offset, selection_box[1] - current_window_offset])
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
			world_map.draw(screen, current_window_offset, draw_tiles=True,
			                                              draw_obs=False,
			                                              draw_walkable=False,
			                                              draw_pathing=False)

			# Foreground objects ------------------------------------- #
			my_player.draw(screen, current_window_offset, draw_bounding_box=True)
			my_animations.draw(screen, current_window_offset)

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

		############################################################
		#                                                          #
		#   MAP EDITOR                                             #
		#                                                          #
		############################################################
		#
		#
		elif current_gamestate in editor_states:
			#
			mouse_in_editor_region = point_in_box_excl(mouse_pos_screen, Vector2(0,0), editor_resolution)
			dragaction_activation  = left_clicking and mouse_in_editor_region
			dragaction_released    = left_released
			#
			any_selectionmenu_selected = any([terraindim_selection_menu.is_selected,
			                                  terrain_selection_menu.is_selected,
			                                  currentob_selection_menu.is_selected,
			                                  obinfo_move_menu.is_selected,
			                                  obinfo_life_menu.is_selected,
			                                  event_selection_menu.is_selected,
			                                  unit_selection_menu_explosion.is_selected])
			any_textinput_selected = any([textinput_mapname.is_selected,
			                              textinput_author.is_selected,
			                              textinput_description.is_selected,
			                              digitinput_lives.is_selected,
			                              digitinput_rating.is_selected,
			                              digitinput_mapsizex.is_selected,
			                              digitinput_mapsizey.is_selected,
			                              digitinput_playerx.is_selected,
			                              digitinput_playery.is_selected,
			                              digitinput_oblives.is_selected,
			                              textinput_musicname.is_selected])
			#
			# initial drawing of map area
			#
			di_x = digitinput_mapsizex.get_value()
			di_y = digitinput_mapsizey.get_value()
			current_map_bounds = Vector2(di_x*GRID_SIZE, di_y*GRID_SIZE)
			if di_x < editor_prevtilemapdim[0]:
				editor_tilemap = editor_tilemap[:di_x,:]
			elif di_x > editor_prevtilemapdim[0]:
				editor_tilemap = np.pad(editor_tilemap, [(0,di_x-editor_prevtilemapdim[0]), (0,0)])
			if di_y < editor_prevtilemapdim[1]:
				editor_tilemap = editor_tilemap[:,:di_y]
			elif di_y > editor_prevtilemapdim[1]:
				editor_tilemap = np.pad(editor_tilemap, [(0,0), (0,di_y-editor_prevtilemapdim[1])])
			editor_prevtilemapdim = editor_tilemap.shape
			#
			# shrink area that mapobjects can be placed/dragged into so that they can't overlap editor elements at the bottom
			#
			mapobject_limits = Vector2(editor_tilemap.shape[0]*GRID_SIZE,
			                           int(min(editor_tilemap.shape[1]*GRID_SIZE, 352 - current_window_offset.y)/GRID_SIZE)*GRID_SIZE)
			#
			editor_tiledrawer.draw(screen, current_window_offset, editor_tilemap, highlight_walls)
			draw_map_bounds(screen, current_map_bounds, current_window_offset, Color.PAL_WHITE)
			#
			# buttons and gfx that are present in every mode
			#
			edbar_fade.fill(Color.BACKGROUND)
			edbar_fade.set_alpha(128)
			screen.blit(edbar_fade, (0, RESOLUTION.y - 127), special_flags=pygame.BLEND_ALPHA_SDL2)
			#
			menu_widgets = [widget_editmode_properties,
			                widget_editmode_terrain,
			                widget_editmode_placeob,
			                widget_editmode_editob,
			                widget_editmode_undo,
			                widget_editmode_redo,
			                widget_editmode_test]
			#
			mw_output_msgs = {}
			for mw in menu_widgets:
				mw_output_msgs[mw.update(mouse_pos_screen, left_clicking)] = True
			# keep mode buttons highlighted based on what mode we're in
			if current_gamestate == GameState.EDITOR_PROPERTIES:
				menu_widgets[0].is_mouseover = True
			elif current_gamestate == GameState.EDITOR_TERRAIN:
				menu_widgets[1].is_mouseover = True
			elif current_gamestate == GameState.EDITOR_LOCATIONS:
				menu_widgets[2].is_mouseover = True
			elif current_gamestate == GameState.EDITOR_EXPLOSIONS:
				menu_widgets[3].is_mouseover = True
			#
			for mw in menu_widgets:
				mw.draw(screen)

			#
			# (1) MAP PROPERTIES MODE
			#
			if current_gamestate == GameState.EDITOR_PROPERTIES:
				#
				textinput_widgets = [textinput_mapname,
				                     textinput_author,
				                     textinput_description,
				                     digitinput_lives,
				                     digitinput_rating,
				                     digitinput_mapsizex,
				                     digitinput_mapsizey,
				                     digitinput_playerx,
				                     digitinput_playery]
				menu_widgets_2    = [widget_propertiesmode_text]
				#
				for tw in textinput_widgets:
					tw.update(mouse_pos_screen, left_clicking, return_pressed, pygame_events)
					tw.draw(screen)
				#
				mw_output_msgs_2 = {}
				for mw in menu_widgets_2:
					mw_output_msgs_2[mw.update(mouse_pos_screen, left_clicking)] = True
					mw.draw(screen)
				#
				draggable_player_released = draggable_playerstart.update(mouse_pos_map, dragaction_activation, dragaction_released, mapobject_limits)
				if not draggable_player_released and not draggable_playerstart.is_selected:
					if not digitinput_playerx.is_selected and not digitinput_playery.is_selected:
						draggable_playerstart.center_pos = Vector2(digitinput_playerx.get_value()*GRID_SIZE + int(GRID_SIZE/2),
						                                           digitinput_playery.get_value()*GRID_SIZE + int(GRID_SIZE/2))
				elif draggable_player_released:
					digitinput_playerx.reset_with_new_str(str(int(draggable_playerstart.center_pos.x/GRID_SIZE)))
					digitinput_playery.reset_with_new_str(str(int(draggable_playerstart.center_pos.y/GRID_SIZE)))
				draggable_playerstart.draw(screen, current_window_offset)

			#
			# (2) TERRAIN MODE
			#
			if current_gamestate == GameState.EDITOR_TERRAIN:
				#
				menu_widgets_2 = [widget_terrainmode_text,
				                  widget_terrainmode_highlightwalls]
				#
				(tile_k, tile_wall, tile_name, tile_img)      = terrain_selection_menu.get_selected_content()
				widget_terrainmode_text.text_data['tilename'] = str(tile_name)
				#
				mw_output_msgs_2 = {}
				for mw in menu_widgets_2:
					mw_output_msgs_2[mw.update(mouse_pos_screen, left_clicking)] = True
					mw.draw(screen)
				for msg in mw_output_msgs_2:
					if not transition_alpha:
						if msg == 'toggle_wall_highlighting':
							highlight_walls = not highlight_walls
				#
				terraindim_selection_menu.update(mouse_pos_screen, left_clicking, return_pressed)
				terraindim_selection_menu.draw(screen)
				current_terrain_tile_dim = terraindim_selection_menu.get_selected_content()
				#
				if tile_img != None:
					tile_img_preview = pygame.transform.scale(tile_img, (4*GRID_SIZE, 4*GRID_SIZE))
					screen.blit(tile_img_preview, (480,392))
				#
				if arrow_left and not arrow_right:
					terrain_selection_menu.move_left()
				elif arrow_right and not arrow_left:
					terrain_selection_menu.move_right()
				elif arrow_up and not arrow_down:
					terrain_selection_menu.move_up()
				elif arrow_down and not arrow_up:
					terrain_selection_menu.move_down()
				#
				terrain_selection_menu.update(mouse_pos_screen, left_clicking, return_pressed)
				terrain_selection_menu.draw(screen, highlight_walls)
				#
				# draw terrain!
				#
				if mouse_in_editor_region:
					snap_x = int(mouse_pos_map.x/GRID_SIZE)
					snap_y = int(mouse_pos_map.y/GRID_SIZE)
					if snap_x < editor_tilemap.shape[0] and snap_y < editor_tilemap.shape[1]:
						mouse_tile_highlight = pygame.Surface(Vector2(GRID_SIZE-1, GRID_SIZE-1))
						mouse_tile_highlight.fill(Color.PAL_WHITE)
						mouse_tile_highlight.set_alpha(40)
						screen.blit(mouse_tile_highlight, Vector2(snap_x*GRID_SIZE+1, snap_y*GRID_SIZE+1) + current_window_offset, special_flags=pygame.BLEND_ALPHA_SDL2)
						if leftclick_is_down:
							editor_tilemap[snap_x,snap_y] = tile_k
						elif rightclick_is_down:
							editor_tilemap[snap_x,snap_y] = 0

			#
			# (3) LOCATIONS MODE
			#
			if current_gamestate == GameState.EDITOR_LOCATIONS:
				#
				adding_new_ob = False
				#
				menu_widgets_2 = [widget_locationsmode_text,
				                  widget_locationsmode_addnew,
				                  widget_locationsmode_delete]
				#
				mw_output_msgs_2 = {}
				for mw in menu_widgets_2:
					mw_output_msgs_2[mw.update(mouse_pos_screen, left_clicking)] = True
					mw.draw(screen)
				for msg in mw_output_msgs_2:
					if not transition_alpha:
						#
						# editor_obdata[i] = [revive_object, startloc, endloc, list_of_exploding_locs, start_actions]
						#
						if msg == 'addnew_ob':
							num_obs = len(currentob_selection_menu.content)
							currentob_selection_menu.content.append(('Obstacle '+str(num_obs+1),))
							currentob_selection_menu.index = num_obs
							currentob_selection_menu.current_range = (max(num_obs+1-currentob_selection_menu.num_rows, 0), num_obs+1)
							new_pos = (int(current_window_offset.x/GRID_SIZE), int(current_window_offset.y/GRID_SIZE))
							editor_obdata.append([DraggableObject(Vector2(new_pos[0] + 2*GRID_SIZE, new_pos[1] + 2*GRID_SIZE),
							                      	              PLAYER_RADIUS,
							                                      int(GRID_SIZE/2),
							                                      Vector2(0,0)),
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
							                      {'move_mode':0,	# 0 = no move, 1 = move to revive
							                       'life_mode':0,	# 0 = add,     1 = set
							                       'life_amount':0,
							                       'music':''}])
							editor_obdata[-1][0].add_image(player_img_fns[1])
							adding_new_ob = True
						#
						#
						#
						elif msg == 'delete_ob' and currentob_selection_menu.content:
							obnum_were_deleting = int(currentob_selection_menu.content[currentob_selection_menu.index][0].split(' ')[1])
							del currentob_selection_menu.content[currentob_selection_menu.index]
							del editor_obdata[currentob_selection_menu.index]
							for i in range(len(currentob_selection_menu.content)):
								my_obnum = int(currentob_selection_menu.content[i][0].split(' ')[1])
								if my_obnum > obnum_were_deleting:
									currentob_selection_menu.content[i] = ('Obstacle '+str(my_obnum-1),)
							currentob_selection_menu.index = max(currentob_selection_menu.index-1, 0)
							range_start = max(currentob_selection_menu.current_range[0]-1, 0)
							range_end   = min(range_start+currentob_selection_menu.num_rows, len(currentob_selection_menu.content))
							currentob_selection_menu.current_range = (range_start, range_end)
				#
				changing_selected_ob = currentob_selection_menu.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
				currentob_selection_menu.draw(screen)
				#
				# save start actions from current ob (if we have one) before updating ob selection
				#
				if (adding_new_ob or changing_selected_ob) and editor_currentobnum != None and currentob_selection_menu.content:
					editor_obdata[editor_currentobnum][4]['move_mode']   = obinfo_move_menu.index
					editor_obdata[editor_currentobnum][4]['life_mode']   = obinfo_life_menu.index
					editor_obdata[editor_currentobnum][4]['life_amount'] = digitinput_oblives.get_value()
					editor_obdata[editor_currentobnum][4]['music']       = textinput_musicname.get_value()
				#
				if not currentob_selection_menu.content:
					editor_obdata       = []
					editor_currentobnum = None
				elif adding_new_ob or changing_selected_ob:
					editor_currentobnum = currentob_selection_menu.index
					obinfo_move_menu.index = editor_obdata[editor_currentobnum][4]['move_mode']
					obinfo_life_menu.index = editor_obdata[editor_currentobnum][4]['life_mode']
					obinfo_move_menu.is_selected = False
					obinfo_life_menu.is_selected = False
					digitinput_oblives.reset_with_new_str(str(editor_obdata[editor_currentobnum][4]['life_amount']))
					textinput_musicname.reset_with_new_str(str(editor_obdata[editor_currentobnum][4]['music']))
				#
				if editor_currentobnum != None:
					widget_locationsmode_obselectedtext.draw(screen)
					textinput_widgets = [textinput_musicname,
					                     digitinput_oblives]
					for tw in textinput_widgets:
						tw.update(mouse_pos_screen, left_clicking, return_pressed, pygame_events)
						tw.draw(screen)
					#
					obinfo_move_menu.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
					obinfo_life_menu.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
					obinfo_move_menu.draw(screen)
					obinfo_life_menu.draw(screen)
				#
				if editor_currentobnum != None:
					locs_mouseover  = [n.is_mouseover for n in editor_obdata[editor_currentobnum][3]]
					special_locs_mouseover = [n.is_mouseover for n in editor_obdata[editor_currentobnum][:3]]
					#
					# draw locs for currently selected ob
					#
					for exploding_loc in editor_obdata[editor_currentobnum][3]:
						exploding_loc.update(mouse_pos_map, dragaction_activation, dragaction_released, mapobject_limits)
						exploding_loc.draw(screen, current_window_offset, mouse_in_editor_region)
					editor_obdata[editor_currentobnum][0].update(mouse_pos_map, dragaction_activation, dragaction_released, mapobject_limits)
					editor_obdata[editor_currentobnum][1].update(mouse_pos_map, dragaction_activation, dragaction_released, mapobject_limits)
					editor_obdata[editor_currentobnum][2].update(mouse_pos_map, dragaction_activation, dragaction_released, mapobject_limits)
					editor_obdata[editor_currentobnum][1].draw(screen, current_window_offset, mouse_in_editor_region)
					editor_obdata[editor_currentobnum][2].draw(screen, current_window_offset, mouse_in_editor_region)
					editor_obdata[editor_currentobnum][0].draw(screen, current_window_offset)
					#
					# want to delete a loc?
					#
					if right_clicking and mouse_in_editor_region and any(locs_mouseover):
						smallest_loc = [(editor_obdata[editor_currentobnum][3][n].get_area(), n) for n in range(len(editor_obdata[editor_currentobnum][3])) if locs_mouseover[n]]
						smallest_loc = sorted(smallest_loc)[0][1]
						del editor_obdata[editor_currentobnum][3][smallest_loc]
						for exploding_loc in editor_obdata[editor_currentobnum][3]:
							if int(exploding_loc.text) > smallest_loc+1:
								exploding_loc.text = str(int(exploding_loc.text)-1)
					#
					# want to add a new loc?
					#
					if left_clicking and mouse_in_editor_region and not any(locs_mouseover+special_locs_mouseover):
						candidate_tl = Vector2(int(mouse_pos_map.x/GRID_SIZE)*GRID_SIZE, int(mouse_pos_map.y/GRID_SIZE)*GRID_SIZE)
						candidate_br = Vector2(candidate_tl.x+16, candidate_tl.y+16)
						if candidate_tl.x >= 0 and candidate_tl.y >= 0 and candidate_br.x <= mapobject_limits.x and candidate_br.y <= mapobject_limits.y:
							editor_obdata[editor_currentobnum][3].append(ResizableBox(candidate_tl, candidate_br, str(len(editor_obdata[editor_currentobnum][3])+1), font_dict['small_w']))
							# set to bottomleft-draggable
							editor_obdata[editor_currentobnum][3][-1].is_mouseover   = True
							editor_obdata[editor_currentobnum][3][-1].is_selected    = True
							editor_obdata[editor_currentobnum][3][-1].drag_mode      = (0,0,1,1)
							editor_obdata[editor_currentobnum][3][-1].edges_selected = (0,0,1,1)

			#
			# (4) EXPLOSIONS MODE
			#
			if current_gamestate == GameState.EDITOR_EXPLOSIONS:
				#
				menu_widgets_2 = [widget_explosionsmode_text]
				#
				mw_output_msgs_2 = {}
				for mw in menu_widgets_2:
					mw_output_msgs_2[mw.update(mouse_pos_screen, left_clicking)] = True
					mw.draw(screen)
				#
				event_selection_menu.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
				event_selection_menu.draw(screen)
				event_submode = event_selection_menu.get_selected_content()
				if event_submode == 'explosion':
					widget_explosionsmode_submenu_explosion.update(mouse_pos_screen, left_clicking)
					widget_explosionsmode_submenu_explosion.draw(screen)
					unit_selection_menu_explosion.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
					unit_selection_menu_explosion.draw(screen)
				else:
					unit_selection_menu_explosion.is_selected = False

			#
			# EDITOR PAUSE MENU
			#
			if current_gamestate == GameState.EDITOR_SAVE:
				trans_fade.fill(Color.BACKGROUND)
				trans_fade.set_alpha(128)
				screen.blit(trans_fade, (0,0), special_flags=pygame.BLEND_ALPHA_SDL2)
				#
				menu_widgets_2 = [widget_editpause_save, widget_editpause_return, widget_editpause_quit]
				#
				mw_output_msgs_2 = {}
				for mw in menu_widgets_2:
					mw_output_msgs_2[mw.update(mouse_pos_screen, left_clicking)] = True
					mw.draw(screen)
				for msg in mw_output_msgs_2:
					if not transition_alpha:
						if msg == 'save':
							pass
						elif msg == 'return':
							current_gamestate     = previous_editor_state
							previous_editor_state = GameState.EDITOR_SAVE
						elif msg == 'quit':
							next_gamestate   = GameState.START_MENU
							transition_alpha = deque(FADE_SEQUENCE)
				if escape_pressed:
					current_gamestate     = previous_editor_state
					previous_editor_state = GameState.EDITOR_SAVE

			#
			# adjust editor window offsets
			#
			digitinput_playerx.bounds = (0, digitinput_mapsizex.get_value() - 1)
			digitinput_playery.bounds = (0, digitinput_mapsizey.get_value() - 1)
			if not any_selectionmenu_selected and not any_textinput_selected:
				current_window_offset = get_window_offset((arrow_left, arrow_up, arrow_right, arrow_down), current_window_offset, current_map_bounds, editor_resolution)

			#
			# change editor mode
			#
			changing_editor_state = False
			for msg in mw_output_msgs:
				if not transition_alpha:
					if msg == 'change_edit_mode_to_properties' and current_gamestate != GameState.EDITOR_PROPERTIES:
						current_gamestate     = GameState.EDITOR_PROPERTIES
						changing_editor_state = True
					elif msg == 'change_edit_mode_to_terrain' and current_gamestate != GameState.EDITOR_TERRAIN:
						current_gamestate     = GameState.EDITOR_TERRAIN
						changing_editor_state = True
					elif msg == 'change_edit_mode_to_locations' and current_gamestate != GameState.EDITOR_LOCATIONS:
						current_gamestate     = GameState.EDITOR_LOCATIONS
						changing_editor_state = True
					elif msg == 'change_edit_mode_to_explosions' and current_gamestate != GameState.EDITOR_EXPLOSIONS:
						current_gamestate     = GameState.EDITOR_EXPLOSIONS
						changing_editor_state = True
			if escape_pressed and previous_editor_state != GameState.EDITOR_SAVE:
				previous_editor_state = current_gamestate
				current_gamestate     = GameState.EDITOR_SAVE
				changing_editor_state = True
			#
			if changing_editor_state:
				# TODO: deselect all interactable objects
				pass
			if previous_editor_state == GameState.EDITOR_SAVE:
				previous_editor_state = current_gamestate

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
					map_selection_menu = MapMenu(MAPSELECT_MENU_POS, all_map_files, font_dict['small_w'], num_rows=15, row_height=16, col_width=248, sort_field=0)
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
						current_map_bounds = Vector2(world_map.map_width * GRID_SIZE, world_map.map_height * GRID_SIZE)
						my_player = Mauzling(world_map.p_starts[0], 0, player_img_fns[0])
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

if __name__ == '__main__':
	try:
		main()
	finally:
		pygame.quit()
