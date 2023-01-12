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
from source.tile_data        import TILE_DATA
from source.uiwidget         import UIWidget
from source.util             import get_file_paths
from source.worldmap         import WorldMap

GAME_VERS = 'OpenBound v0.1'
FRAMERATE = 23.8095

class GameState:
	START_MENU   = 0
	MAP_SELECT   = 1
	BOUNDING     = 2
	PAUSE_MENU   = 3
	ED_TERRAIN   = 4
	ED_UNITS     = 5
	ED_LOCATIONS = 6
	ED_OBSTACLE  = 7

UPSCALE_2X = True

def main(raw_args=None):
	parser = argparse.ArgumentParser(description=GAME_VERS, formatter_class=argparse.ArgumentDefaultsHelpFormatter,)
	parser.add_argument('-i',  type=str, required=True,  metavar='input.map', help="* map to load")
	parser.add_argument('-sw', type=int, required=False, metavar='640',       help="screen width",      default=640)
	parser.add_argument('-sh', type=int, required=False, metavar='480',       help="screen height",     default=480)
	parser.add_argument('--fullscreen',  required=False, action='store_true', help="run in fullscreen", default=False)
	args = parser.parse_args()
	#
	INPUT_MAP      = args.i
	RESOLUTION     = Vector2(args.sw, args.sh)
	RUN_FULLSCREEN = args.fullscreen
	#
	py_dir   = pathlib.Path(__file__).resolve().parent
	GFX_DIR  = os.path.join(py_dir, 'assets', 'gfx')
	SFX_DIR  = os.path.join(py_dir, 'assets', 'audio')
	FONT_DIR = os.path.join(py_dir, 'assets', 'font')
	TILE_DIR = os.path.join(py_dir, 'assets', 'tiles')
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
	font_dict = {'small' :    Font(pixel_font_fns[0], Color.PAL_BLACK),
	             'large' :    Font(pixel_font_fns[1], Color.PAL_BLACK),
	             'large_w' :  Font(pixel_font_fns[1], Color.PAL_WHITE),
	             'lifecount': Font(pixel_font_fns[1], Color.LIFECOUNT),
	             'fps':       Font(pixel_font_fns[1], Color.PAL_WHITE)}

	#
	# load world and place player 1
	#
	world_map = WorldMap(INPUT_MAP, tile_fns, font_dict)
	if world_map.p_starts[0] == None:
		print('No player 1 start found')
		exit(1)
	map_width  = world_map.map_width * GRID_SIZE
	map_height = world_map.map_height * GRID_SIZE
	my_player  = Mauzling(world_map.p_starts[0], 0, player_img_fns[0])
	my_player.num_lives = world_map.init_lives

	# load animation gfx
	my_animations = AnimationManager()
	my_animations.add_animation_cycle(expovy_img_fns, 'overlord')
	my_animations.add_animation_cycle(expscr_img_fns, 'scourge')

	# other gfx
	my_cursor = Cursor(cursor_img_fns)
	#
	widget_playerselected = UIWidget()
	widget_playerselected.add_element('rect', (Vector2(32, RESOLUTION.y - 64), Vector2(160, RESOLUTION.y - 32), Color.PAL_WHITE, 14))
	widget_playerselected.add_element('image', (Vector2(38, RESOLUTION.y - 62), ui_gfx_img_fns[0]))
	widget_playerselected.add_element('text', ('Lives:', 'lives', Vector2(76,  RESOLUTION.y - 55), font_dict['lifecount'], False))
	widget_playerselected.add_element('text', ('',   'lifecount', Vector2(120, RESOLUTION.y - 55), font_dict['lifecount'], False))
	#
	(tl, br) = (Vector2(96, RESOLUTION.y-96), Vector2(224, RESOLUTION.y-64))
	widget_button_play = UIWidget()
	widget_button_play.add_element('rect', (Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, 14), mouseover_condition=(True,False))
	widget_button_play.add_element('rect', (Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, 14), mouseover_condition=(False,True))
	widget_button_play.add_element('text', ('Play', 'play', (tl+br)/2 + Vector2(0,1), font_dict['large_w'], True))
	widget_button_play.add_return_message('play')
	#
	(tl, br) = (Vector2(256, RESOLUTION.y-96), Vector2(384, RESOLUTION.y-64))
	widget_button_editor = UIWidget()
	widget_button_editor.add_element('rect', (Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, 14), mouseover_condition=(True,False))
	widget_button_editor.add_element('rect', (Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, 14), mouseover_condition=(False,True))
	widget_button_editor.add_element('text', ('Map Editor', 'editor', (tl+br)/2 + Vector2(0,1), font_dict['large_w'], True))
	widget_button_editor.add_return_message('editor')
	#
	(tl, br) = (Vector2(416, RESOLUTION.y-96), Vector2(544, RESOLUTION.y-64))
	widget_button_options = UIWidget()
	widget_button_options.add_element('rect', (Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, 14), mouseover_condition=(True,False))
	widget_button_options.add_element('rect', (Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, 14), mouseover_condition=(False,True))
	widget_button_options.add_element('text', ('Options', 'options', (tl+br)/2 + Vector2(0,1), font_dict['large_w'], True))
	widget_button_options.add_return_message('options')

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
		for event in pygame.event.get():
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
					pygame.quit()
					sys.exit()
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
		if current_gamestate == GameState.START_MENU:
			#
			menu_widgets = [widget_button_play, widget_button_editor, widget_button_options]
			#
			mw_output_msgs = {}
			for mw in menu_widgets:
				mw_output_msgs[mw.update(mouse_pos_screen, left_clicking)] = True
				mw.draw(screen)
			for msg in mw_output_msgs:
				if msg == 'play' and not transition_alpha:
					next_gamestate   = GameState.BOUNDING
					transition_alpha = deque(FADE_SEQUENCE)

		#
		# MAP SELECTION MENU
		#
		elif current_gamestate == GameState.MAP_SELECT:
			#
			menu_widgets = []
			#
			mw_output_msgs = {}
			for mw in menu_widgets:
				mw_output_msgs[mw.update(mouse_pos_screen, left_clicking)] = True
				mw.draw(screen)

		#
		# WE ARE BOUNDING.
		#
		elif current_gamestate == GameState.BOUNDING:
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
					my_audio.play_sound(n[0], volume=0.3)
				if ob_kill:
					player_died = my_player.check_kill_boxes(ob_kill)
					if player_died:
						my_player.revive_at_pos(ob.revive_coords)
						my_audio.play_sound('player_death', volume=0.3)
				####if current_frame == 300:
				####	my_player.add_lives(10, ob.revive_coords)

			# Terrain / Obstacles ------------------------------------ #
			world_map.draw(screen, WINDOW_OFFSET, draw_tiles=True,
			                                      draw_obs=False,
			                                      draw_walkable=False,
			                                      draw_pathing=False)

			# Foreground objects ------------------------------------- #
			my_player.draw(screen, WINDOW_OFFSET, draw_bounding_box=False)
			my_animations.draw(screen, WINDOW_OFFSET)

			# Draw UI elements --------------------------------------- #
			if selection_box[0] != None:
				draw_selection_box(screen, selection_box, Color.SELECTION)
			if my_player.is_selected:
				widget_playerselected.text_data['lifecount'] = str(my_player.num_lives)
				widget_playerselected.draw(screen)

			# Draw cursor -------------------------------------------- #
			my_cursor.draw(screen)

		# Draw transition fade ----------------------------------- #
		if next_gamestate != None:
			current_opacity = transition_alpha.popleft()
			trans_fade.fill(Color.BACKGROUND)
			trans_fade.set_alpha(current_opacity)
			screen.blit(trans_fade, (0,0), special_flags=pygame.BLEND_ALPHA_SDL2)
			if current_opacity >= 255:
				current_gamestate = next_gamestate
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
