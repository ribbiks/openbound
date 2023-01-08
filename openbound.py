#!/usr/bin/env python
# encoding: utf-8
import argparse
import os
import pathlib
import pygame
import sys
import time

from pygame.locals import QUIT, KEYDOWN, KEYUP, K_UP, K_DOWN, K_LEFT, K_RIGHT, K_ESCAPE, K_LSHIFT, K_RSHIFT, MOUSEBUTTONDOWN, MOUSEBUTTONUP
from pygame.math   import Vector2

from source.animationmanager import AnimationManager
from source.audiomanager     import AudioManager
from source.cursor           import Cursor
from source.geometry         import value_clamp
from source.globals          import GRID_SIZE, PLAYER_RADIUS, SCROLL_SPEED
from source.mauzling         import Mauzling
from source.misc_gfx         import Color, draw_grid
from source.util             import get_file_paths
from source.worldmap         import WorldMap

GAME_VERS = 'OpenBound v0.1'
FRAMERATE = 23.8095

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
	py_dir  = pathlib.Path(__file__).resolve().parent
	GFX_DIR = os.path.join(py_dir, 'assets', 'gfx')
	SFX_DIR = os.path.join(py_dir, 'assets', 'audio')
	#
	cursor_img_fns = get_file_paths(GFX_DIR, ['cursor.png', 'cursor_shift.png'])
	player_img_fns = get_file_paths(GFX_DIR, ['sq16.png'])
	expovy_img_fns = get_file_paths(GFX_DIR, ['ovy0.png','ovy1.png','ovy2.png','ovy3.png','ovy4.png','ovy5.png'])
	expscr_img_fns = get_file_paths(GFX_DIR, ['scourge0.png','scourge1.png','scourge2.png','scourge3.png','scourge4.png','scourge5.png'])
	#
	exp_sound_fns = get_file_paths(SFX_DIR, ['zovdth00.wav', 'zavdth00.wav'])

	#
	# initialize pygame
	#
	pygame.mixer.pre_init(44100, -16, 2, 2048)	# possibly not necessary?
	pygame.init()
	pygame.display.set_caption(GAME_VERS)
	disp_flags = 0
	if RUN_FULLSCREEN:
		disp_flags |= pygame.FULLSCREEN
	screen     = pygame.display.set_mode(size=RESOLUTION, flags=disp_flags, depth=0, display=0, vsync=0)
	main_clock = pygame.time.Clock()

	#
	# load world and place player 1
	#
	world_map = WorldMap(INPUT_MAP)
	if world_map.p_starts[0] == None:
		print('No player 1 start found')
		exit(1)
	MAP_WIDTH  = world_map.map_width
	MAP_HEIGHT = world_map.map_height
	my_player  = Mauzling(world_map.p_starts[0], 0, player_img_fns[0])

	# load animation gfx
	my_animations = AnimationManager()
	my_animations.add_animation_cycle(expovy_img_fns, 'overlord')
	my_animations.add_animation_cycle(expscr_img_fns, 'scourge')

	# other gfx
	my_cursor     = Cursor(cursor_img_fns)
	WINDOW_OFFSET = Vector2(0, 0)
	SCROLL_X      = Vector2(SCROLL_SPEED, 0)
	SCROLL_Y      = Vector2(0, SCROLL_SPEED)
	TIME_SPENT    = [0.]

	# load sounds
	my_audio = AudioManager()
	my_audio.add_sound(exp_sound_fns[0], 'overlord')
	my_audio.add_sound(exp_sound_fns[1], 'scourge')

	# inputs that can be held down across frames
	left_clicking = False
	shift_pressed = False
	arrow_left    = False
	arrow_up      = False
	arrow_right   = False
	arrow_down    = False

	# Main game loop --------------------------------------------- #
	current_frame = 0
	while True:
		# Get keyboard / mouse inputs ---------------------------- #
		right_clicking = False
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
					left_clicking = False

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
		WINDOW_OFFSET.x = value_clamp(WINDOW_OFFSET.x, min(RESOLUTION.x -  MAP_WIDTH, 0), 0)
		WINDOW_OFFSET.y = value_clamp(WINDOW_OFFSET.y, min(RESOLUTION.y - MAP_HEIGHT, 0), 0)

		#
		# processing player inputs: movement orders
		#
		mx, my           = pygame.mouse.get_pos()
		mouse_pos_screen = Vector2(mx,my)
		mouse_pos_map    = mouse_pos_screen - WINDOW_OFFSET
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
		if current_frame % 20 == 0:
			my_animations.start_new_animation('scourge', Vector2(128+16,128+16))
			my_audio.play_sound('scourge', volume=0.5)

		# Background --------------------------------------------- #
		screen.fill(Color.BACKGROUND)
		grid_offset = Vector2(WINDOW_OFFSET.x % GRID_SIZE, WINDOW_OFFSET.y % GRID_SIZE)
		draw_grid(screen, RESOLUTION,   GRID_SIZE, grid_offset, Color.GRID_MINOR)
		draw_grid(screen, RESOLUTION, 2*GRID_SIZE, grid_offset, Color.GRID_MAJOR)

		# Terrain ------------------------------------------------ #
		world_map.draw(screen, WINDOW_OFFSET, draw_pathing=False)

		# Foreground objects ------------------------------------- #
		my_player.draw(screen, WINDOW_OFFSET, draw_bounding_box=False)
		my_animations.draw(screen, WINDOW_OFFSET)

		# Draw UI elements --------------------------------------- #

		# Draw cursor -------------------------------------------- #
		my_cursor.draw(screen)

		# Print FPS ---------------------------------------------- #
		fps_font = pygame.font.SysFont("Verdana", 20)
		fps_text = fps_font.render('{0:0.2f}'.format(main_clock.get_fps()), True, Color.INFO_TEXT)
		screen.blit(fps_text, (RESOLUTION[0]-64, 0))

		# Print mouse coordinates -------------------------------- #
		fps_font = pygame.font.SysFont("Verdana", 20)
		fps_text = fps_font.render('{0}, {1}'.format(int(mouse_pos_map.x), int(mouse_pos_map.y)), True, Color.INFO_TEXT)
		screen.blit(fps_text, (RESOLUTION[0]-96, RESOLUTION[1]-32))

		# Update ------------------------------------------------- #
		pygame.display.update()
		main_clock.tick_busy_loop(FRAMERATE)
		current_frame += 1

		##### print runtime stats every 100 frames
		####if current_frame % 100 == 0:
		####	print([int(1000.*n/current_frame) for n in TIME_SPENT], 'ms/frame')

if __name__ == '__main__':
	main()
