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
from source.geometry         import get_window_offset, point_in_box_excl, value_clamp
from source.globals          import GRID_SIZE, PLAYER_RADIUS, WALL_UNITS
from source.mauzling         import Mauzling
from source.misc_gfx         import Color, draw_grid, draw_map_bounds, draw_selection_box, FADE_SEQUENCE
from source.obstacle         import Obstacle
from source.resizablebox     import ResizableBox
from source.selectionmenu    import MapMenu, TerrainMenu, UnitMenu
from source.textinput        import DigitInput, TextInput
from source.tilemap          import TileMap
from source.tilemanager      import TileManager
from source.uiwidget         import UIWidget
from source.util             import get_blank_obdata, get_file_paths, read_map_data_from_json, write_map_data_to_json
from source.worldmap         import WorldMap

GAME_VERS = 'OpenBound v0.1'
FRAMERATE = 23.8095

class GameState:
    START_MENU   = 0    #
    MAP_SELECT   = 1    # select a map to play
    MAP_SELECT_E = 2    # select a map to edit
    BOUNDING     = 3    #
    PAUSE_MENU   = 4    # pause screen while bounding
    PAUSE_MENU_E = 5    # fade screen when you select editor from main menu --> create new map or edit existing
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
    player_img_fns = get_file_paths(GFX_DIR, ['sq16.png', 'sq16_gray.png', 'zergling_sprites.png'])
    playerdeath_fg = get_file_paths(GFX_DIR, ['zerglingdeath0001.png', 'zerglingdeath0001.png',
                                              'zerglingdeath0002.png', 'zerglingdeath0002.png',
                                              'zerglingdeath0003.png', 'zerglingdeath0003.png',
                                              'zerglingdeath0004.png', 'zerglingdeath0004.png',
                                              'zerglingdeath0005.png', 'zerglingdeath0005.png',
                                              'zerglingdeath0006.png', 'zerglingdeath0006.png',
                                              'zerglingdeath0007.png', 'zerglingdeath0007.png'])
    playerdeath_bg = get_file_paths(GFX_DIR, ['zerglingdebris0000.png']*14 +
                                             ['zerglingdebris0001.png']*50 +
                                             ['zerglingdebris0002.png']*50 +
                                             ['zerglingdebris0003.png']*50 +
                                             ['zerglingdebris0004.png']*50 +
                                             ['zerglingdebris0005.png']*50)
    t_tool_img_fns = get_file_paths(GFX_DIR, ['pencil_button.png',
                                              'selection_rect_button.png',
                                              'move_button.png'])
    ui_gfx_img_fns = get_file_paths(GFX_DIR, ['ling_icon.png'])
    psiwal_img_fns = get_file_paths(GFX_DIR, ['psiemit0000.bmp', 'psiemit0000.bmp',
                                              'psiemit0001.bmp', 'psiemit0001.bmp',
                                              'psiemit0002.bmp', 'psiemit0002.bmp',
                                              'psiemit0003.bmp', 'psiemit0003.bmp',
                                              'psiemit0004.bmp', 'psiemit0004.bmp',
                                              'psiemit0005.bmp', 'psiemit0005.bmp'])
    crystl_img_fns = get_file_paths(GFX_DIR, ['khchunk0000.bmp'])
    expovy_img_fns = get_file_paths(GFX_DIR, ['zairdthl0000.bmp', 'zairdthl0000.bmp',
                                              'zairdthl0001.bmp', 'zairdthl0001.bmp',
                                              'zairdthl0002.bmp', 'zairdthl0002.bmp',
                                              'zairdthl0003.bmp', 'zairdthl0003.bmp',
                                              'zairdthl0004.bmp', 'zairdthl0004.bmp',
                                              'zairdthl0005.bmp', 'zairdthl0005.bmp',
                                              'zairdthl0006.bmp', 'zairdthl0006.bmp',
                                              'zairdthl0007.bmp', 'zairdthl0007.bmp'])
    expscr_img_fns = get_file_paths(GFX_DIR, ['zairdths0000.bmp', 'zairdths0000.bmp',
                                              'zairdths0001.bmp', 'zairdths0001.bmp',
                                              'zairdths0002.bmp', 'zairdths0002.bmp',
                                              'zairdths0003.bmp', 'zairdths0003.bmp',
                                              'zairdths0004.bmp', 'zairdths0004.bmp',
                                              'zairdths0005.bmp', 'zairdths0005.bmp',
                                              'zairdths0006.bmp', 'zairdths0006.bmp',
                                              'zairdths0007.bmp', 'zairdths0007.bmp'])
    tele_img_fns   = get_file_paths(GFX_DIR, ['ehamed0000.bmp', 'ehamed0000.bmp', 'ehamed0000.bmp',
                                              'ehamed0001.bmp', 'ehamed0001.bmp', 'ehamed0001.bmp',
                                              'ehamed0002.bmp', 'ehamed0002.bmp', 'ehamed0002.bmp',
                                              'ehamed0003.bmp', 'ehamed0003.bmp', 'ehamed0003.bmp',
                                              'ehamed0004.bmp', 'ehamed0004.bmp', 'ehamed0004.bmp',
                                              'ehamed0005.bmp', 'ehamed0005.bmp', 'ehamed0005.bmp',
                                              'ehamed0006.bmp', 'ehamed0006.bmp', 'ehamed0006.bmp',
                                              'ehamed0007.bmp', 'ehamed0007.bmp', 'ehamed0007.bmp',
                                              'ehamed0008.bmp', 'ehamed0008.bmp', 'ehamed0008.bmp',
                                              'ehamed0009.bmp', 'ehamed0009.bmp', 'ehamed0009.bmp',
                                              'ehamed0010.bmp', 'ehamed0010.bmp', 'ehamed0010.bmp',
                                              'ehamed0011.bmp', 'ehamed0011.bmp', 'ehamed0011.bmp',
                                              'ehamed0012.bmp', 'ehamed0012.bmp', 'ehamed0012.bmp'])
    wall_icons_fns = get_file_paths(GFX_DIR, ['nowall.png'])
    tele_icons_fns = get_file_paths(GFX_DIR, ['tele_origin.png', 'tele_dest.png'])
    #
    exp_sound_fns    = get_file_paths(SFX_DIR, ['zovdth00.wav', 'zavdth00.wav'])
    player_sound_fns = get_file_paths(SFX_DIR, ['zzedth00.wav'])
    tele_sound_fns   = get_file_paths(SFX_DIR, ['ptehal01.wav'])
    #
    pixel_font_fns = get_file_paths(FONT_DIR, ['small_font.png', 'large_font.png'])
    #
    all_map_files  = []
    map_fn_to_load = None
    world_map      = None
    map_width      = None
    map_height     = None
    my_player      = None
    #
    # sc player color translations
    #
    RED_REMAP    = [(247, 15, 15), (191, 23, 23), (191, 23, 23), (162, 15, 15),
                    (130,  0,  0), (107,  0,  0), ( 85,  0,  0), ( 38,  0,  0)]
    BLUE_REMAP   = [( 31,107,219), ( 23, 85,178), ( 23, 85,178), ( 44, 85,155),
                    ( 15, 61,134), (  0, 23,115), (  0, 38, 85), (  0,  0, 50)]
    TEAL_REMAP   = [( 76,201,175), ( 61,172,145), ( 61,172,145), ( 61,172,145),
                    ( 38,119, 94), ( 38,119, 94), ( 38,119, 94), (  0, 71,  0)]
    PURPLE_REMAP = [(165, 98,182), (165, 98,182), (165, 98,182), (137, 81,152),
                    (107, 56,115), (107, 56,115), (107, 56,115), ( 90, 38, 61)]
    ORANGE_REMAP = [(250,169, 44), (239,152, 66), (207,137, 66), (185,119, 56),
                    (155, 98, 50), (126, 76, 44), ( 85, 61, 31), ( 56, 38, 23)]
    BROWN_REMAP  = [(145, 81, 44), (126, 76, 44), (126, 76, 44), (102, 85, 23),
                    (102, 85, 23), ( 85, 61, 31), ( 85, 38, 23), ( 56, 38, 23)]
    WHITE_REMAP  = [(219,233,222), (213,210,207), (197,197,197), (178,175,169),
                    (162,148,148), (122,122,137), (102,102,102), ( 71, 71, 81)]
    YELLOW_REMAP = [(253,253, 90), (230,230, 94), (207,204, 85), (182,172, 98),
                    (145,134, 61), (126,119, 44), (102, 85, 23), ( 56, 38, 23)]
    #
    SC_PAL254 = (35,35,255,255) # used for transparent pixels in explosion sprites ripped from sc

    #
    # initialize pygame
    #
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
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
    pygame.mixer.set_num_channels(16)

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

    # load sounds
    my_audio = AudioManager()
    my_audio.add_sound(exp_sound_fns[0], 'overlord')
    my_audio.add_sound(exp_sound_fns[1], 'scourge')
    my_audio.add_sound(player_sound_fns[0], 'player_death')
    my_audio.add_sound(tele_sound_fns[0], 'hallucination')

    # load tiles
    tile_manager = TileManager(TILE_DIR)

    # load animation gfx
    my_animations_background = AnimationManager()
    my_animations_background.add_animation_cycle(playerdeath_bg, 'playerdebris')
    #
    my_animations = AnimationManager()
    my_animations.add_animation_cycle(expovy_img_fns, 'overlord', colorkey=SC_PAL254)
    my_animations.add_animation_cycle(expscr_img_fns, 'scourge',  colorkey=SC_PAL254)
    my_animations.add_animation_cycle(wall_icons_fns, 'nowall_icon')
    my_animations.add_animation_cycle(tele_icons_fns, 'tele_icons')
    my_animations.add_animation_cycle(tele_img_fns,   'hallucination')
    my_animations.add_animation_cycle(playerdeath_fg, 'playerdeath')
    my_animations.add_animation_cycle(psiwal_img_fns, 'psi_emitter', colorkey=SC_PAL254, swap_colors=WHITE_REMAP)
    my_animations.add_animation_cycle(crystl_img_fns, 'crystal',     colorkey=SC_PAL254)
    #
    explosion_imgs = {'overlord'         : my_animations.all_animations['overlord'][0],
                      'scourge'          : my_animations.all_animations['scourge'][0],
                      'psi_emitter'      : my_animations.all_animations['psi_emitter'][0],
                      'crystal'          : my_animations.all_animations['crystal'][0],
                      'remove_wall'      : my_animations.all_animations['nowall_icon'][0],
                      'tele_origin'      : my_animations.all_animations['tele_icons'][0],
                      'tele_destination' : my_animations.all_animations['tele_icons'][1]}

    # cursor object
    my_cursor = Cursor(cursor_img_fns)

    # initial geometry / gfx stuff
    DEFAULT_PLAYER_START  = Vector2(32,32)  # in map units
    DEFAULT_MAP_DIM       = Vector2(64,64)  # in 1x1 tiles
    DEFAULT_MAP_LIFECOUNT = 100
    DEFAULT_MAP_RATING    = 5
    current_map_bounds    = DEFAULT_MAP_DIM*GRID_SIZE
    current_window_offset = Vector2(0, 0)
    editor_resolution     = Vector2(RESOLUTION.x, RESOLUTION.y-128)
    editor_tilemap        = np.zeros((int(DEFAULT_MAP_DIM.x), int(DEFAULT_MAP_DIM.y)), dtype='<i4')
    editor_prevtilemapdim = editor_tilemap.shape
    editor_tiledrawer     = TileMap(tile_manager)
    editor_tiledrawer_sel = TileMap(tile_manager)
    editor_obdata         = []
    editor_currentobnum   = None
    editor_currentexpnum  = None
    highlight_walls       = False
    selected_terrain_box  = None
    current_terraintool   = None
    copied_tileblock      = None

    #
    #
    #   IN-GAME WIDGETS
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
    #   MAIN MENU WIDGETS
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
    #   MAP SELECTION SCREEN WIDGETS
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
    #   PAUSE MENU WIDGETS
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
    #   MAIN MENU --> EDITOR TRANSITION WIDGETS
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
    #   MAP PROPERTIES MODE WIDGETS
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
    digitinput_lives    = DigitInput(Vector2(tl.x, tl.y),     Vector2(br.x+2, br.y),   font_dict['small_w'], (0,9999), char_offset=Vector2(6,7), default_val=DEFAULT_MAP_LIFECOUNT, max_chars=4)
    digitinput_mapsizex = DigitInput(Vector2(tl.x+96, tl.y),  Vector2(br.x+96, br.y),  font_dict['small_w'], (16,256), char_offset=Vector2(6,7), default_val=int(DEFAULT_MAP_DIM.x),  max_chars=3)
    digitinput_mapsizey = DigitInput(Vector2(tl.x+144, tl.y), Vector2(br.x+144, br.y), font_dict['small_w'], (16,256), char_offset=Vector2(6,7), default_val=int(DEFAULT_MAP_DIM.y),  max_chars=3)
    #
    (tl, br) = (Vector2(208, 440 + VBUFF), Vector2(240, 464 - VBUFF))
    digitinput_rating  = DigitInput(Vector2(tl.x, tl.y),     Vector2(br.x+2, br.y),   font_dict['small_w'], (0,99),  char_offset=Vector2(6,7), default_val=DEFAULT_MAP_RATING, max_chars=2)
    #
    draggable_playerstart = DraggableObject(DEFAULT_PLAYER_START, PLAYER_RADIUS, grid_snap=int(GRID_SIZE/2), pos_offset=Vector2(0,0), init_image_fn=player_img_fns[0])
    #
    #
    #   TERRAIN MODE WIDGETS
    #
    #
    (tl, br) = (Vector2(208, 368), Vector2(448, 464))
    widget_terrainmode_text = UIWidget()
    widget_terrainmode_text.add_rect(Vector2(tl.x-64, tl.y), Vector2(tl.x-16, br.y-40), Color.PAL_BLUE_5, border_radius=4)
    widget_terrainmode_text.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_5, border_radius=4)
    (tl, br) = (Vector2(464, 368), Vector2(560, 464))
    widget_terrainmode_text.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_5, border_radius=4)
    #
    widget_terraintool_icons = UIWidget()
    widget_terraintool_icons.add_image(Vector2(tl.x+13, tl.y+9),  t_tool_img_fns[0])
    widget_terraintool_icons.add_image(Vector2(tl.x+8,  tl.y+40), t_tool_img_fns[1])
    widget_terraintool_icons.add_image(Vector2(tl.x+9,  tl.y+66), t_tool_img_fns[2])
    #
    terraintool_selection_menu = UnitMenu(Vector2(tl.x+4, tl.y+6), ['draw', 'select', 'move'], font_dict['large_w'], num_rows=3, row_height=28, col_width=88, offset=Vector2(38,6), autodeselect=True)
    #
    (tl, br) = (Vector2(144, 432), Vector2(192, 464))
    widget_terrainmode_highlightwalls = UIWidget()
    widget_terrainmode_highlightwalls.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_4, border_radius=14, mouseover_condition=(True,False))
    widget_terrainmode_highlightwalls.add_rect(Vector2(tl.x, tl.y), Vector2(br.x, br.y), Color.PAL_BLUE_3, border_radius=14, mouseover_condition=(False,True))
    widget_terrainmode_highlightwalls.add_text((tl+br)/2 + Vector2(1,-4), 'Highlight', 'highlight', font_dict['small_w'], is_centered=True)
    widget_terrainmode_highlightwalls.add_text((tl+br)/2 + Vector2(1,7),  'walls',     'walls',     font_dict['small_w'], is_centered=True)
    widget_terrainmode_highlightwalls.add_return_message('toggle_wall_highlighting')
    #
    terraindim_selection_menu = UnitMenu(Vector2(154, 372), ['16x16', '32x32', '64x64'], font_dict['small_w'], num_rows=3, row_height=16, col_width=28, autodeselect=True)
    #
    (tl, br) = (Vector2(208, 368), Vector2(432, 464))
    terrain_selection_menu_1x1 = TerrainMenu(tl, tile_manager, tile_dim=1)
    terrain_selection_menu_2x2 = TerrainMenu(tl, tile_manager, tile_dim=2, num_rows=2, num_cols=5, row_height=40, col_width=40)
    terrain_selection_menu_4x4 = TerrainMenu(tl, tile_manager, tile_dim=4, num_rows=1, num_cols=3, row_height=72, col_width=72)
    #
    #
    #   LOCATIONS MODE WIDGETS
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
    #   EXPLOSIONS MODE WIDGETS
    #
    #
    (tl, br) = (Vector2(148, 368 + 5), Vector2(224, RESOLUTION.y-16))
    widget_explosionsmode_text = UIWidget()
    widget_explosionsmode_text.add_rect(Vector2(tl.x, tl.y+20), Vector2(br.x, br.y), Color.PAL_BLUE_5, border_radius=4)
    widget_explosionsmode_text.add_text(Vector2(tl.x+2, tl.y), 'Event type:', 't1', font_dict['large_w'])
    event_selection_menu = UnitMenu(Vector2(tl.x+4, tl.y+24), ['explosion', 'wall', 'teleport'], font_dict['small_w'], num_rows=4, row_height=16, col_width=68)
    #
    widget_explosionsmode_submenu_explosion = UIWidget()
    widget_explosionsmode_submenu_explosion.add_rect(Vector2(tl.x+96, tl.y+20), Vector2(br.x+96, br.y), Color.PAL_BLUE_5, border_radius=4)
    widget_explosionsmode_submenu_explosion.add_text(Vector2(tl.x+98, tl.y), 'Unit:', 't1', font_dict['large_w'])
    unit_selection_menu_explosion = UnitMenu(Vector2(tl.x+100, tl.y+24), ['overlord', 'scourge'],             font_dict['small_w'], num_rows=4, row_height=16, col_width=68)
    unit_selection_menu_wall      = UnitMenu(Vector2(tl.x+100, tl.y+24), ['psi_emitter', 'crystal'],                     font_dict['small_w'], num_rows=4, row_height=16, col_width=68)
    unit_selection_menu_teleport  = UnitMenu(Vector2(tl.x+100, tl.y+24), ['tele_origin', 'tele_destination'], font_dict['small_w'], num_rows=4, row_height=16, col_width=68)
    #
    tl = Vector2(352, 400)
    widget_explosionsmode_control_1 = UIWidget()
    widget_explosionsmode_control_1.add_rect(Vector2(tl.x-4, tl.y), Vector2(tl.x+32-4, tl.y+32), Color.PAL_BLUE_4, border_radius=2, mouseover_condition=(True,False))
    widget_explosionsmode_control_1.add_rect(Vector2(tl.x-4, tl.y), Vector2(tl.x+32-4, tl.y+32), Color.PAL_BLUE_3, border_radius=2, mouseover_condition=(False,True))
    widget_explosionsmode_control_1.add_text(tl + Vector2(16-4,16), '<<', '<<', font_dict['large_w'], is_centered=True)
    widget_explosionsmode_control_1.add_return_message('<<')
    #
    widget_explosionsmode_control_2 = UIWidget()
    widget_explosionsmode_control_2.add_rect(Vector2(tl.x+32, tl.y), Vector2(tl.x+64, tl.y+32), Color.PAL_BLUE_4, border_radius=2, mouseover_condition=(True,False))
    widget_explosionsmode_control_2.add_rect(Vector2(tl.x+32, tl.y), Vector2(tl.x+64, tl.y+32), Color.PAL_BLUE_3, border_radius=2, mouseover_condition=(False,True))
    widget_explosionsmode_control_2.add_text(tl + Vector2(48,16), '<', '<', font_dict['large_w'], is_centered=True)
    widget_explosionsmode_control_2.add_return_message('<')
    #
    widget_explosionsmode_control_3 = UIWidget()
    widget_explosionsmode_control_3.add_rect(Vector2(tl.x+64+4, tl.y-16+4), Vector2(tl.x+128-4, tl.y+48-4), Color.PAL_BLUE_4, border_radius=2)
    widget_explosionsmode_control_3.add_rect(Vector2(tl.x+64+8, tl.y-16+8), Vector2(tl.x+128-8, tl.y+48-8), Color.PAL_BLUE_5, border_radius=2)
    widget_explosionsmode_control_3.add_text(tl + Vector2(96,16), '1', 'exp_num', font_dict['large_w'], is_centered=True)
    widget_explosionsmode_control_3.add_text(tl + Vector2(71,53), 'delay:', 't1', font_dict['small_w'])
    #
    digitinput_expdelay = DigitInput(tl + Vector2(96,48), tl + Vector2(124,64), font_dict['small_w'], (0,999), char_offset=Vector2(6,5), default_val=0, max_chars=3)
    #
    widget_explosionsmode_control_4 = UIWidget()
    widget_explosionsmode_control_4.add_rect(Vector2(tl.x+128, tl.y), Vector2(tl.x+160, tl.y+32), Color.PAL_BLUE_4, border_radius=2, mouseover_condition=(True,False))
    widget_explosionsmode_control_4.add_rect(Vector2(tl.x+128, tl.y), Vector2(tl.x+160, tl.y+32), Color.PAL_BLUE_3, border_radius=2, mouseover_condition=(False,True))
    widget_explosionsmode_control_4.add_text(tl + Vector2(144,16), '>', '>', font_dict['large_w'], is_centered=True)
    widget_explosionsmode_control_4.add_return_message('>')
    #
    widget_explosionsmode_control_5 = UIWidget()
    widget_explosionsmode_control_5.add_rect(Vector2(tl.x+160+4, tl.y), Vector2(tl.x+192+4, tl.y+32), Color.PAL_BLUE_4, border_radius=2, mouseover_condition=(True,False))
    widget_explosionsmode_control_5.add_rect(Vector2(tl.x+160+4, tl.y), Vector2(tl.x+192+4, tl.y+32), Color.PAL_BLUE_3, border_radius=2, mouseover_condition=(False,True))
    widget_explosionsmode_control_5.add_text(tl + Vector2(176+4,16), '>>', '>>', font_dict['large_w'], is_centered=True)
    widget_explosionsmode_control_5.add_return_message('>>')
    #
    widget_explosionsmode_control_6 = UIWidget()
    widget_explosionsmode_control_6.add_rect(Vector2(tl.x+4, tl.y+40), Vector2(tl.x+56, tl.y+64), Color.PAL_BLUE_4, border_radius=12, mouseover_condition=(True,False))
    widget_explosionsmode_control_6.add_rect(Vector2(tl.x+4, tl.y+40), Vector2(tl.x+56, tl.y+64), Color.PAL_BLUE_3, border_radius=12, mouseover_condition=(False,True))
    widget_explosionsmode_control_6.add_text(tl + Vector2(30,48), 'Insert', 'insert', font_dict['small_w'], is_centered=True)
    widget_explosionsmode_control_6.add_text(tl + Vector2(30,57), 'copy',   'copy',   font_dict['small_w'], is_centered=True)
    widget_explosionsmode_control_6.add_return_message('insert')
    #
    widget_explosionsmode_control_7 = UIWidget()
    widget_explosionsmode_control_7.add_rect(Vector2(tl.x+4+132, tl.y+40), Vector2(tl.x+56+132, tl.y+64), Color.PAL_BLUE_4, border_radius=12, mouseover_condition=(True,False))
    widget_explosionsmode_control_7.add_rect(Vector2(tl.x+4+132, tl.y+40), Vector2(tl.x+56+132, tl.y+64), Color.PAL_BLUE_3, border_radius=12, mouseover_condition=(False,True))
    widget_explosionsmode_control_7.add_text(tl + Vector2(30+132,52), 'Delete', 'delete', font_dict['small_w'], is_centered=True)
    widget_explosionsmode_control_7.add_return_message('delete')
    #
    #
    #   VARIOUS EDITOR MODE WIDGETS
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

    # misc gamestate stuff
    next_gamestate   = None
    transition_alpha = deque([])
    editor_states    = [GameState.EDITOR_PROPERTIES, GameState.EDITOR_TERRAIN, GameState.EDITOR_LOCATIONS, GameState.EDITOR_EXPLOSIONS, GameState.EDITOR_SAVE]
    previous_editor_state = None

    # inputs that can be held down across frames
    shift_pressed      = False
    control_pressed    = False
    arrow_left         = False
    arrow_up           = False
    arrow_right        = False
    arrow_down         = False
    selection_box      = [None, None]
    leftclick_is_down  = False
    rightclick_is_down = False

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
        copy_pressed    = False
        paste_pressed   = False
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
                if event.key == pl.K_ESCAPE:
                    escape_pressed = True
                if event.key == pl.K_RETURN:
                    return_pressed = True
                if event.key == pl.K_LSHIFT or event.key == pl.K_RSHIFT:
                    shift_pressed = True
                if event.key == pl.K_LCTRL or event.key == pl.K_RCTRL or event.key == pl.K_LMETA or event.key == pl.K_RMETA:
                    control_pressed = True
                if event.key == pl.K_c and control_pressed:
                    copy_pressed = True
                if event.key == pl.K_v and control_pressed:
                    paste_pressed = True
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
                if event.key == pl.K_LCTRL or event.key == pl.K_RCTRL or event.key == pl.K_LMETA or event.key == pl.K_RMETA:
                    control_pressed = False
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
            upscaled_size = upscale_screen.get_size()   # might be 2x resoltuion, might be full monitor resolution
            mouse_scale_factor = (RESOLUTION.x/upscaled_size[0], RESOLUTION.y/upscaled_size[1])
            mouse_pos_screen = Vector2(int(mx*mouse_scale_factor[0] + 0.5), int(my*mouse_scale_factor[1] + 0.5))
        else:
            mouse_pos_screen = Vector2(mx,my)
        mouse_pos_map = mouse_pos_screen - current_window_offset
        #
        if left_clicking:
            leftclick_is_down = True
            selection_box = [Vector2(mouse_pos_map.x, mouse_pos_map.y), None]
        if left_released:
            leftclick_is_down = False
            if selection_box[0] != None:
                if selection_box[1] == None:
                    selection_box[1] = selection_box[0]
        if selection_box[0] != None:
            selection_box[1] = Vector2(mouse_pos_map.x, mouse_pos_map.y)
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
        if current_gamestate not in [GameState.BOUNDING, GameState.PAUSE_MENU]:
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
        elif current_gamestate in [GameState.MAP_SELECT, GameState.MAP_SELECT_E]:
            #
            if current_gamestate == GameState.MAP_SELECT:
                widget_mapselect_play.text_data['play'] = 'Play'
            elif current_gamestate == GameState.MAP_SELECT_E:
                widget_mapselect_play.text_data['play'] = 'Open in editor'
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
                        if current_gamestate == GameState.MAP_SELECT:
                            next_gamestate = GameState.BOUNDING
                        elif current_gamestate == GameState.MAP_SELECT_E:
                            next_gamestate = GameState.EDITOR_PROPERTIES
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

        ############################################################
        #                                                          #
        #   WE ARE BOUNDING                                        #
        #                                                          #
        ############################################################
        #
        elif current_gamestate == GameState.BOUNDING or current_gamestate == GameState.PAUSE_MENU:
            #
            current_mapsize = world_map.get_mapsize()
            mouse_in_playable_maparea = point_in_box_excl(mouse_pos_map, Vector2(0,0), current_mapsize)
            #
            if current_gamestate == GameState.BOUNDING:
                current_volume = 0.350
                #
                # processing player inputs
                #
                if left_released and selection_box[0] != None:
                    if (selection_box[1] - selection_box[0]).length() < 4:
                        my_player.check_selection_click(selection_box[1])
                    else:
                        my_player.check_selection_box([selection_box[0], selection_box[1]])
                #
                if right_clicking and mouse_in_playable_maparea:
                    draw_cursor = my_player.issue_new_order(mouse_pos_map, shift_pressed)
                    if draw_cursor:
                        my_cursor.start_click_animation(mouse_pos_screen, shift_pressed)
            #
            elif current_gamestate == GameState.PAUSE_MENU:
                current_volume = 0.125
            #
            # update players
            #
            my_player.tick(world_map)

            #
            # update obstacles
            #
            for obnum,ob in world_map.obstacles.items():
                #
                obstart_actions = ob.check_for_ob_start(my_player.position)
                #
                if obstart_actions != None:
                    for n in obstart_actions:
                        if n[0] == 'add_lives':
                            my_player.add_lives(n[1], ob.revive_coords)
                        elif n[0] == 'set_lives':
                            my_player.add_lives(n[1], ob.revive_coords, set_lives=True)
                        elif n[0] == 'move_player' and n[1] == 1:
                            my_player.update_position(ob.revive_coords)
                            my_player.clear_orders_and_reset_state(deselect=False)
                        elif n[0] == 'change_music' and n[1] != '':
                            my_audio.stop_music()
                            my_audio.play_music(n[1])
                #
                (ob_gfx, ob_snd, ob_kill, ob_tele, ob_wall) = ob.tick()
                #
                for n in ob_gfx:
                    if n[0] == 'hallucination':
                        my_animations.start_new_animation(n[0], n[1]+Vector2(5,0), alpha_layer=True)
                    else:
                        my_animations.start_new_animation(n[0], n[1])
                #
                for n in ob_snd:
                    my_audio.play_sound(n, volume=current_volume)
                #
                if ob_kill:
                    player_died = my_player.check_kill_boxes(ob_kill)
                    if player_died:
                        my_audio.play_sound('player_death', volume=current_volume)
                        my_animations.start_new_animation('playerdeath', my_player.position + Vector2(-30,-30), centered=False, prepend=True)
                        my_animations_background.start_new_animation('playerdebris', my_player.position + Vector2(-30,-30), centered=False, prepend=True)
                        my_player.revive_at_pos(ob.revive_coords)
                #
                for n in ob_tele:
                    if point_in_box_excl(my_player.position, n[0], n[1]):
                        my_player.update_position(n[2])
                        my_player.clear_orders_and_reset_state(deselect=False)
                #
                for n in ob_wall:
                    (wall_key, wall_onoff, wall_strings, wall_pos) = n
                    for i in range(len(wall_onoff)):
                        my_wall_string = str(wall_key[0]) + '-' + wall_strings[i]
                        if wall_onoff[i]:
                            my_animations.start_looping_animation(WALL_UNITS[wall_onoff[i]-1], wall_pos[i], my_wall_string)
                        else:
                            my_animations.remove_looping_animation(my_wall_string)
                    world_map.change_wall_state(wall_key[0], wall_key[1])
                #
                ob_ended = ob.check_for_ob_end(my_player.position)
                #
                if ob_ended:
                    for loc_name in ob.locs.keys():
                        my_animations.remove_looping_animation(str(ob.obnum) + '-' + loc_name)
                    world_map.change_wall_state(ob.obnum, 0)

            # Terrain / Obstacles ------------------------------------ #
            world_map.draw(screen, current_window_offset, draw_tiles=True,
                                                          draw_obs=False,
                                                          draw_walkable=False,
                                                          draw_pathing=False)

            # Foreground objects ------------------------------------- #
            my_animations_background.draw(screen, current_window_offset)
            my_player.draw(screen, current_window_offset, draw_bounding_box=False)
            my_animations.draw(screen, current_window_offset)

            # Draw UI elements --------------------------------------- #
            if current_gamestate == GameState.BOUNDING:
                if selection_box[0] != None:
                    draw_selection_box(screen, selection_box, current_window_offset, Color.SELECTION)
            #
            if my_player.is_selected:
                widget_playerselected.text_data['lifecount'] = str(my_player.num_lives)
                widget_playerselected.draw(screen)
            #
            if current_gamestate == GameState.BOUNDING:
                my_cursor.draw(screen)
            #
            current_window_offset = get_window_offset((arrow_left, arrow_up, arrow_right, arrow_down), current_window_offset, current_map_bounds, RESOLUTION)

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
        elif current_gamestate in editor_states:
            #
            mouse_in_editor_region = point_in_box_excl(mouse_pos_screen, Vector2(0,0), editor_resolution)
            dragaction_activation  = left_clicking and mouse_in_editor_region
            dragaction_released    = left_released
            #
            any_selectionmenu_selected = any([terraindim_selection_menu.is_selected,
                                              terraintool_selection_menu.is_selected,
                                              terrain_selection_menu_1x1.is_selected,
                                              terrain_selection_menu_2x2.is_selected,
                                              terrain_selection_menu_4x4.is_selected,
                                              currentob_selection_menu.is_selected,
                                              obinfo_move_menu.is_selected,
                                              obinfo_life_menu.is_selected,
                                              event_selection_menu.is_selected,
                                              unit_selection_menu_explosion.is_selected,
                                              unit_selection_menu_teleport.is_selected])
            any_textinput_selected = any([textinput_mapname.is_selected,
                                          textinput_author.is_selected,
                                          textinput_description.is_selected,
                                          digitinput_lives.is_selected,
                                          digitinput_rating.is_selected,
                                          digitinput_mapsizex.is_selected,
                                          digitinput_mapsizey.is_selected,
                                          digitinput_oblives.is_selected,
                                          textinput_musicname.is_selected,
                                          digitinput_expdelay.is_selected])
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
            # set area where mapobjects can be placed/dragged so that they can't overlap editor elements at the bottom
            #
            mapobject_limits = [Vector2(1*GRID_SIZE,1*GRID_SIZE),
                                Vector2((editor_tilemap.shape[0] - 1)*GRID_SIZE, int(min(editor_tilemap.shape[1]*GRID_SIZE, 352-current_window_offset.y)/GRID_SIZE - 1)*GRID_SIZE)]
            #
            editor_tiledrawer.draw(screen, current_window_offset, editor_tilemap, highlight_walls)
            if selected_terrain_box != None and selected_terrain_box[2]:
                sel_tb_off  = selected_terrain_box[0]*GRID_SIZE
                move_tb_off = selected_terrain_box[3]*GRID_SIZE
                editor_tiledrawer_sel.draw(screen, current_window_offset+sel_tb_off+move_tb_off, selected_tileblock, highlight_walls)
            #
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
                                     digitinput_mapsizey]
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
                draggable_playerstart.draw(screen, current_window_offset)

            #
            # (2) TERRAIN MODE
            #
            if current_gamestate == GameState.EDITOR_TERRAIN:
                #
                menu_widgets_2 = [widget_terrainmode_text,
                                  widget_terrainmode_highlightwalls]
                #
                prev_terraintool = current_terraintool
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
                terraindim_selection_menu.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
                terraintool_selection_menu.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
                terraindim_selection_menu.draw(screen)
                terraintool_selection_menu.draw(screen)
                widget_terraintool_icons.draw(screen)
                current_terraintool      = terraintool_selection_menu.get_selected_content()
                current_terrain_tile_dim = terraindim_selection_menu.get_selected_content()
                if current_terrain_tile_dim == '16x16':
                    current_terrain_sel_menu = terrain_selection_menu_1x1
                    draw_tilesize = 1
                elif current_terrain_tile_dim == '32x32':
                    current_terrain_sel_menu = terrain_selection_menu_2x2
                    draw_tilesize = 2
                elif current_terrain_tile_dim == '64x64':
                    current_terrain_sel_menu = terrain_selection_menu_4x4
                    draw_tilesize = 4
                else:
                    print('Invalid terrain mode.')
                    exit(1)
                #
                if arrow_left and not arrow_right:
                    current_terrain_sel_menu.move_left()
                elif arrow_right and not arrow_left:
                    current_terrain_sel_menu.move_right()
                elif arrow_up and not arrow_down:
                    current_terrain_sel_menu.move_up()
                elif arrow_down and not arrow_up:
                    current_terrain_sel_menu.move_down()
                new_tile_selected = current_terrain_sel_menu.update(mouse_pos_screen, left_clicking, return_pressed)
                current_terrain_sel_menu.draw(screen, highlight_walls)
                (tile_num_tuple, tile_wall, tile_img) = current_terrain_sel_menu.get_selected_content()
                #
                if new_tile_selected:
                    current_terraintool = 'draw'
                    terraintool_selection_menu.index = 0
                #
                if selected_terrain_box != None and selected_terrain_box[2]:
                    if terrainbox_blink_ind > 4:
                        draw_selection_box(screen, [selected_terrain_box[0]*GRID_SIZE, selected_terrain_box[1]*GRID_SIZE], current_window_offset+selected_terrain_box[3]*GRID_SIZE, Color.PAL_YEL_2)
                    else:
                        draw_selection_box(screen, [selected_terrain_box[0]*GRID_SIZE, selected_terrain_box[1]*GRID_SIZE], current_window_offset+selected_terrain_box[3]*GRID_SIZE, Color.PAL_YEL_3)
                    terrainbox_blink_ind -= 1
                    if terrainbox_blink_ind <= 0:
                        terrainbox_blink_ind = 8
                #
                # terrain editing
                #
                snap_x = int(mouse_pos_map.x/GRID_SIZE)
                snap_y = int(mouse_pos_map.y/GRID_SIZE)
                clear_sel_tb = False
                #
                if copy_pressed and selected_terrain_box != None:
                    copied_tilesize = selected_tileblock.shape
                    stb = [[int(selected_terrain_box[0].x) + int(selected_terrain_box[3].x), int(selected_terrain_box[0].y) + int(selected_terrain_box[3].y)],
                           [int(selected_terrain_box[1].x) + int(selected_terrain_box[3].x), int(selected_terrain_box[1].y) + int(selected_terrain_box[3].y)]]
                    editor_tilemap[stb[0][0]:stb[1][0], stb[0][1]:stb[1][1]] = selected_tileblock
                if paste_pressed and copied_tilesize != None:
                    new_pos = (int(-current_window_offset.x/GRID_SIZE + mapobject_limits[0].x/GRID_SIZE + 0.6),
                               int(-current_window_offset.y/GRID_SIZE + mapobject_limits[0].y/GRID_SIZE + 0.6))
                    # bounds check, trim if we did something pathologically weird
                    dx = editor_tilemap.shape[0] - (new_pos[0]+copied_tilesize[0])
                    dy = editor_tilemap.shape[1] - (new_pos[1]+copied_tilesize[1])
                    if dx < 0:
                        selected_tileblock = selected_tileblock[0:copied_tilesize[0]+dx,:]
                        copied_tilesize = (copied_tilesize[0]+dx, copied_tilesize[1])
                    if dy < 0:
                        selected_tileblock = selected_tileblock[:,0:copied_tilesize[1]+dy]
                        copied_tilesize = (copied_tilesize[0], copied_tilesize[1]+dy)
                    selected_terrain_box = [Vector2(new_pos[0], new_pos[1]), Vector2(new_pos[0]+copied_tilesize[0], new_pos[1]+copied_tilesize[1]), True, Vector2(0,0), Vector2(0,0), False]
                    copied_tilesize = None
                    current_terraintool = 'move'
                    terraintool_selection_menu.index = 2
                #
                # draw terrain
                #
                if current_terraintool == 'draw':
                    if mouse_in_editor_region and snap_x < editor_tilemap.shape[0] and snap_y < editor_tilemap.shape[1]:
                        new_tile = np.zeros((draw_tilesize,draw_tilesize))
                        del_tile = np.zeros((draw_tilesize,draw_tilesize))
                        for ti,tk in enumerate(tile_num_tuple):
                            new_tile[int(ti/draw_tilesize),ti%draw_tilesize] = tk
                        # bounds check
                        dx = editor_tilemap.shape[0] - (snap_x + new_tile.shape[0])
                        dy = editor_tilemap.shape[1] - (snap_y + new_tile.shape[1])
                        if dx < 0:
                            new_tile = new_tile[:dx,:]
                        if dy < 0:
                            new_tile = new_tile[:,:dy]
                        #
                        mouse_tile_highlight = pygame.Surface(Vector2(new_tile.shape[0]*GRID_SIZE-1, new_tile.shape[1]*GRID_SIZE-1))
                        mouse_tile_highlight.fill(Color.PAL_WHITE)
                        mouse_tile_highlight.set_alpha(40)
                        screen.blit(mouse_tile_highlight, Vector2(snap_x*GRID_SIZE+1, snap_y*GRID_SIZE+1) + current_window_offset, special_flags=pygame.BLEND_ALPHA_SDL2)
                        #
                        if leftclick_is_down:
                            editor_tilemap[snap_x:snap_x+new_tile.shape[0],snap_y:snap_y+new_tile.shape[1]] = new_tile
                        elif rightclick_is_down:
                            editor_tilemap[snap_x:snap_x+del_tile.shape[0],snap_y:snap_y+del_tile.shape[1]] = del_tile
                    if selected_terrain_box != None:
                        clear_sel_tb = True
                #
                # select terrain
                #
                if current_terraintool == 'select':
                    if prev_terraintool == 'move':
                        clear_sel_tb = True
                    else:
                        if mouse_in_editor_region and snap_x < editor_tilemap.shape[0] and snap_y < editor_tilemap.shape[1]:
                            if selection_box[0] != None:
                                if selected_terrain_box != None and selected_terrain_box[2]:
                                    clear_sel_tb = True
                                else:
                                    tl = Vector2(min(selection_box[0].x, selection_box[1].x), min(selection_box[0].y, selection_box[1].y))
                                    br = Vector2(max(selection_box[0].x, selection_box[1].x), max(selection_box[0].y, selection_box[1].y))
                                    tl = Vector2(int(tl.x/GRID_SIZE), int(tl.y/GRID_SIZE))
                                    br = Vector2(int(br.x/GRID_SIZE + 1), int(br.y/GRID_SIZE + 1))
                                    selected_terrain_box = [Vector2(tl.x, tl.y), Vector2(br.x, br.y), False, Vector2(0,0), Vector2(0,0), False]
                        if selected_terrain_box != None and not selected_terrain_box[2]:
                            draw_selection_box(screen, [selected_terrain_box[0]*GRID_SIZE, selected_terrain_box[1]*GRID_SIZE], current_window_offset, Color.SELECTION)
                        if left_released and selected_terrain_box != None:
                            selected_terrain_box = [Vector2(tl.x, tl.y), Vector2(br.x, br.y), True, Vector2(0,0), Vector2(0,0), False]
                            stb = [[int(selected_terrain_box[0].x), int(selected_terrain_box[0].y)],
                                   [int(selected_terrain_box[1].x), int(selected_terrain_box[1].y)]]
                            selected_tileblock   = np.copy(editor_tilemap[stb[0][0]:stb[1][0], stb[0][1]:stb[1][1]])
                            terrainbox_blink_ind = 8
                            editor_tilemap[stb[0][0]:stb[1][0], stb[0][1]:stb[1][1]] = 0
                        if right_clicking and selected_terrain_box != None:
                            clear_sel_tb = True
                #
                # move terrain
                #
                if current_terraintool == 'move':
                    if mouse_in_editor_region and snap_x < editor_tilemap.shape[0] and snap_y < editor_tilemap.shape[1]:
                        if selection_box[0] != None and selected_terrain_box != None:
                            if not selected_terrain_box[5]:
                                tl = selected_terrain_box[0]*GRID_SIZE + selected_terrain_box[3]*GRID_SIZE
                                br = selected_terrain_box[1]*GRID_SIZE + selected_terrain_box[3]*GRID_SIZE
                                selected_terrain_box[5] = point_in_box_excl(selection_box[0], tl, br)
                            elif selected_terrain_box[5]:
                                selected_terrain_box[3] = Vector2(value_clamp(int((selection_box[1].x-selection_box[0].x)/GRID_SIZE + selected_terrain_box[4].x), -int(selected_terrain_box[0].x), int(editor_tilemap.shape[0]-selected_terrain_box[1].x)),
                                                                  value_clamp(int((selection_box[1].y-selection_box[0].y)/GRID_SIZE + selected_terrain_box[4].y), -int(selected_terrain_box[0].y), int(editor_tilemap.shape[1]-selected_terrain_box[1].y)))
                    if left_released and selected_terrain_box != None:
                        selected_terrain_box[4] = Vector2(selected_terrain_box[3].x, selected_terrain_box[3].y)
                        selected_terrain_box[5] = False
                    if (right_clicking or return_pressed) and selected_terrain_box != None:
                        clear_sel_tb = True
                #
                if clear_sel_tb and selected_terrain_box != None:
                    stb = [[int(selected_terrain_box[0].x) + int(selected_terrain_box[3].x), int(selected_terrain_box[0].y) + int(selected_terrain_box[3].y)],
                           [int(selected_terrain_box[1].x) + int(selected_terrain_box[3].x), int(selected_terrain_box[1].y) + int(selected_terrain_box[3].y)]]
                    editor_tilemap[stb[0][0]:stb[1][0], stb[0][1]:stb[1][1]] = selected_tileblock
                    selected_terrain_box = None

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
                        # editor_obdata[i] = [revive_object, startloc, endloc, list_of_exploding_locs, start_actions, explosions_data]
                        #
                        if msg == 'addnew_ob':
                            num_obs = len(currentob_selection_menu.content)
                            currentob_selection_menu.content.append(('Obstacle '+str(num_obs+1),))
                            currentob_selection_menu.index = num_obs
                            currentob_selection_menu.current_range = (max(num_obs+1-currentob_selection_menu.num_rows, 0), num_obs+1)
                            new_pos = (int(-current_window_offset.x/GRID_SIZE + 0.6)*GRID_SIZE + mapobject_limits[0].x,
                                       int(-current_window_offset.y/GRID_SIZE + 0.6)*GRID_SIZE + mapobject_limits[0].y)
                            editor_obdata.append(get_blank_obdata(new_pos, font_dict, player_img_fns[1]))
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
                            if editor_currentobnum == range_end:
                                editor_currentobnum -= 1
                            if not currentob_selection_menu.content:
                                editor_currentobnum = None
                #
                changing_selected_ob = currentob_selection_menu.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
                currentob_selection_menu.draw(screen)
                #
                # save start actions from current ob (if we have one) before updating ob selection
                #
                no_text_menus_selected = not digitinput_oblives.is_selected and not textinput_musicname.is_selected
                if (no_text_menus_selected or adding_new_ob or changing_selected_ob) and editor_currentobnum != None:
                    editor_obdata[editor_currentobnum][4]['move_mode']   = obinfo_move_menu.index
                    editor_obdata[editor_currentobnum][4]['life_mode']   = obinfo_life_menu.index
                    editor_obdata[editor_currentobnum][4]['life_amount'] = digitinput_oblives.get_value()
                    editor_obdata[editor_currentobnum][4]['music']       = textinput_musicname.get_value()
                #
                if not currentob_selection_menu.content:
                    editor_obdata        = []
                    editor_currentobnum  = None
                    editor_currentexpnum = None
                    digitinput_expdelay.reset_with_new_str('0')
                elif adding_new_ob or changing_selected_ob:
                    editor_currentobnum    = currentob_selection_menu.index
                    editor_currentexpnum   = 0
                    obinfo_move_menu.index = editor_obdata[editor_currentobnum][4]['move_mode']
                    obinfo_life_menu.index = editor_obdata[editor_currentobnum][4]['life_mode']
                    obinfo_move_menu.is_selected = False
                    obinfo_life_menu.is_selected = False
                    digitinput_oblives.reset_with_new_str(str(editor_obdata[editor_currentobnum][4]['life_amount']))
                    textinput_musicname.reset_with_new_str(str(editor_obdata[editor_currentobnum][4]['music']))
                    digitinput_expdelay.reset_with_new_str(str(editor_obdata[editor_currentobnum][5][editor_currentexpnum]['delay']))
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
                    locs_mouseover         = [n.is_mouseover for n in editor_obdata[editor_currentobnum][3]]
                    special_locs_mouseover = [n.is_mouseover for n in editor_obdata[editor_currentobnum][:3]]
                    #
                    # draw locs for currently selected ob
                    #
                    box_actions = (dragaction_activation, dragaction_released)
                    #
                    editor_obdata[editor_currentobnum][0].update(mouse_pos_map, box_actions[0], box_actions[1], mapobject_limits)
                    if editor_obdata[editor_currentobnum][0].is_selected:
                        box_actions = (False, False)
                    #
                    for exploding_loc in editor_obdata[editor_currentobnum][3]:
                        exploding_loc.update(mouse_pos_map, box_actions[0], box_actions[1], mapobject_limits)
                        if exploding_loc.is_selected:
                            box_actions = (False, False)
                    #
                    editor_obdata[editor_currentobnum][1].update(mouse_pos_map, box_actions[0], box_actions[1], mapobject_limits)
                    if editor_obdata[editor_currentobnum][1].is_selected:
                        box_actions = (False, False)
                    editor_obdata[editor_currentobnum][2].update(mouse_pos_map, box_actions[0], box_actions[1], mapobject_limits)
                    #
                    for exploding_loc in editor_obdata[editor_currentobnum][3]:
                        exploding_loc.draw(screen, current_window_offset, mouse_in_editor_region)
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
                        # decrement loc names
                        for exploding_loc in editor_obdata[editor_currentobnum][3]:
                            if int(exploding_loc.text) > smallest_loc+1:
                                exploding_loc.text = str(int(exploding_loc.text)-1)
                        # decrement loc index in explosion data
                        for expnum in range(len(editor_obdata[editor_currentobnum][5])):
                            for loc_k in sorted(list(editor_obdata[editor_currentobnum][5][expnum]['explode_locs'].keys())):
                                if loc_k == smallest_loc:
                                    del editor_obdata[editor_currentobnum][5][expnum]['explode_locs'][loc_k]
                                elif loc_k > smallest_loc:
                                    editor_obdata[editor_currentobnum][5][expnum]['explode_locs'][loc_k-1] = editor_obdata[editor_currentobnum][5][expnum]['explode_locs'][loc_k]
                                    del editor_obdata[editor_currentobnum][5][expnum]['explode_locs'][loc_k]
                        # delete counts if they no longer have any explosions
                        del_list = []
                        for expnum in range(len(editor_obdata[editor_currentobnum][5])-1,-1,-1):
                            if editor_obdata[editor_currentobnum][5][expnum]['explode_locs'] == {}:
                                del_list.append(expnum)
                        for di in del_list:
                            del editor_obdata[editor_currentobnum][5][di]
                        # reset explosion count index if we deleted any counts
                        if del_list:
                            editor_currentexpnum = 0
                    #
                    # want to add a new loc?
                    #
                    if left_clicking and mouse_in_editor_region and not any(locs_mouseover+special_locs_mouseover):
                        candidate_tl = Vector2(int(mouse_pos_map.x/GRID_SIZE)*GRID_SIZE, int(mouse_pos_map.y/GRID_SIZE)*GRID_SIZE)
                        candidate_br = Vector2(candidate_tl.x+16, candidate_tl.y+16)
                        if candidate_tl.x >= mapobject_limits[0].x and candidate_tl.y >= mapobject_limits[0].y and candidate_br.x <= mapobject_limits[1].x and candidate_br.y <= mapobject_limits[1].y:
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
                menu_widgets_2 = [widget_explosionsmode_text,
                                  widget_explosionsmode_control_1,
                                  widget_explosionsmode_control_2,
                                  widget_explosionsmode_control_4,
                                  widget_explosionsmode_control_5,
                                  widget_explosionsmode_control_6,
                                  widget_explosionsmode_control_7]
                #
                mw_output_msgs_2 = {}
                for mw in menu_widgets_2:
                    mw_output_msgs_2[mw.update(mouse_pos_screen, left_clicking)] = True
                    mw.draw(screen)
                #
                digitinput_expdelay.update(mouse_pos_screen, left_clicking, return_pressed, pygame_events)
                digitinput_expdelay.draw(screen)
                if editor_currentobnum != None:
                    editor_obdata[editor_currentobnum][5][editor_currentexpnum]['delay'] = digitinput_expdelay.get_value()
                #
                any_control_messages = False
                for msg in mw_output_msgs_2:
                    if editor_currentobnum != None and not transition_alpha:
                        #
                        current_count_is_empty = editor_obdata[editor_currentobnum][5][editor_currentexpnum]['explode_locs'] == {}
                        last_i = len(editor_obdata[editor_currentobnum][5]) - 1
                        last_count_is_empty = editor_obdata[editor_currentobnum][5][last_i]['explode_locs'] == {}
                        #
                        if msg == '<<':
                            editor_currentexpnum = 0
                            any_control_messages = True
                        #
                        elif msg == '<':
                            editor_currentexpnum = max(editor_currentexpnum - 1, 0)
                            any_control_messages = True
                        #
                        elif msg == '>':
                            if not current_count_is_empty:
                                if editor_currentexpnum < len(editor_obdata[editor_currentobnum][5]) - 1:
                                    editor_currentexpnum += 1
                                else:
                                    prev_delay = editor_obdata[editor_currentobnum][5][editor_currentexpnum]['delay']
                                    editor_currentexpnum += 1
                                    editor_obdata[editor_currentobnum][5].append({'explode_locs':{}, 'delay':prev_delay})
                                any_control_messages = True
                        #
                        elif msg == '>>':
                            if last_count_is_empty:
                                editor_currentexpnum = last_i - 1
                            else:
                                editor_currentexpnum = last_i
                            any_control_messages = True
                        #
                        elif msg == 'insert':
                            if not current_count_is_empty:
                                editor_obdata[editor_currentobnum][5].insert(editor_currentexpnum,
                                                                             {'explode_locs':{k:editor_obdata[editor_currentobnum][5][editor_currentexpnum]['explode_locs'][k]
                                                                              for k in editor_obdata[editor_currentobnum][5][editor_currentexpnum]['explode_locs'].keys()},
                                                                              'delay':editor_obdata[editor_currentobnum][5][editor_currentexpnum]['delay']})
                                editor_currentexpnum += 1
                            any_control_messages = True
                        #
                        elif msg == 'delete':
                            if len(editor_obdata[editor_currentobnum][5]) > 1:
                                del editor_obdata[editor_currentobnum][5][editor_currentexpnum]
                                if editor_currentexpnum == len(editor_obdata[editor_currentobnum][5]):
                                    editor_currentexpnum -= 1
                            else:
                                editor_obdata[editor_currentobnum][5] = [{'explode_locs':{}, 'delay':0}]
                            any_control_messages = True
                #
                if any_control_messages:
                    for loc_box in editor_obdata[editor_currentobnum][3]:
                        loc_box.clear_icon()
                    my_exp_dict = editor_obdata[editor_currentobnum][5][editor_currentexpnum]['explode_locs']
                    for k in my_exp_dict.keys():
                        editor_obdata[editor_currentobnum][3][k].change_icon(explosion_imgs[my_exp_dict[k]])
                    digitinput_expdelay.reset_with_new_str(str(editor_obdata[editor_currentobnum][5][editor_currentexpnum]['delay']))
                else:
                    if editor_currentexpnum != None:
                        editor_obdata[editor_currentobnum][5][editor_currentexpnum]['delay'] = digitinput_expdelay.get_value()
                #
                if editor_currentexpnum == None:
                    widget_explosionsmode_control_3.text_data['exp_num'] = ''
                else:
                    widget_explosionsmode_control_3.text_data['exp_num'] = str(editor_currentexpnum+1)
                widget_explosionsmode_control_3.update(mouse_pos_screen, left_clicking)
                widget_explosionsmode_control_3.draw(screen)
                #
                event_selection_menu.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
                event_selection_menu.draw(screen)
                event_submode = event_selection_menu.get_selected_content()
                selected_exploding_unit = None
                if event_submode in ['explosion', 'wall', 'teleport']:
                    widget_explosionsmode_submenu_explosion.update(mouse_pos_screen, left_clicking)
                    widget_explosionsmode_submenu_explosion.draw(screen)
                    if event_submode == 'explosion':
                        unit_selection_menu_explosion.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
                        unit_selection_menu_explosion.draw(screen)
                        selected_exploding_unit = unit_selection_menu_explosion.get_selected_content()
                    elif event_submode == 'wall':
                        unit_selection_menu_wall.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
                        unit_selection_menu_wall.draw(screen)
                        selected_exploding_unit = unit_selection_menu_wall.get_selected_content()
                    elif event_submode == 'teleport':
                        unit_selection_menu_teleport.update(mouse_pos_screen, left_clicking, return_pressed, inc_menus_key, dec_menus_key)
                        unit_selection_menu_teleport.draw(screen)
                        selected_exploding_unit = unit_selection_menu_teleport.get_selected_content()
                else:
                    unit_selection_menu_explosion.is_selected = False
                #
                if editor_currentobnum != None:
                    #
                    # highlight locs on mouseover but don't allow any resizing / dragging
                    #
                    for exploding_loc in editor_obdata[editor_currentobnum][3]:
                        exploding_loc.update(mouse_pos_map, False, False, mapobject_limits)
                        exploding_loc.draw(screen, current_window_offset, mouse_in_editor_region, highlight_edges=False)
                    editor_obdata[editor_currentobnum][0].update(mouse_pos_map, False, False, mapobject_limits)
                    editor_obdata[editor_currentobnum][1].update(mouse_pos_map, False, False, mapobject_limits)
                    editor_obdata[editor_currentobnum][2].update(mouse_pos_map, False, False, mapobject_limits)
                    editor_obdata[editor_currentobnum][1].draw(screen, current_window_offset, mouse_in_editor_region, highlight_edges=False)
                    editor_obdata[editor_currentobnum][2].draw(screen, current_window_offset, mouse_in_editor_region, highlight_edges=False)
                    editor_obdata[editor_currentobnum][0].draw(screen, current_window_offset)
                    #
                    # are we adding an explosion to a location?
                    #
                    locs_mouseover = [n.is_mouseover for n in editor_obdata[editor_currentobnum][3]]
                    if left_clicking and mouse_in_editor_region and any(locs_mouseover) and selected_exploding_unit != None:
                        smallest_loc = [(editor_obdata[editor_currentobnum][3][n].get_area(), n) for n in range(len(editor_obdata[editor_currentobnum][3])) if locs_mouseover[n]]
                        smallest_loc = sorted(smallest_loc)[0][1]
                        tele_origin_placed      = any([unit_name == 'tele_origin' for (loc_i, unit_name) in editor_obdata[editor_currentobnum][5][editor_currentexpnum]['explode_locs'].items()])
                        tele_destination_placed = any([unit_name == 'tele_destination' for (loc_i, unit_name) in editor_obdata[editor_currentobnum][5][editor_currentexpnum]['explode_locs'].items()])
                        explosion_is_placeable  = (selected_exploding_unit not in ['tele_origin', 'tele_destination'] or
                                                   (selected_exploding_unit == 'tele_origin' and not tele_origin_placed) or
                                                   (selected_exploding_unit == 'tele_destination' and not tele_destination_placed))
                        if explosion_is_placeable:
                            editor_obdata[editor_currentobnum][3][smallest_loc].change_icon(explosion_imgs[selected_exploding_unit])
                            editor_obdata[editor_currentobnum][5][editor_currentexpnum]['explode_locs'][smallest_loc] = selected_exploding_unit
                    #
                    # are we removing an explosion?
                    #
                    if right_clicking and mouse_in_editor_region and any(locs_mouseover):
                        smallest_loc = [(editor_obdata[editor_currentobnum][3][n].get_area(), n) for n in range(len(editor_obdata[editor_currentobnum][3])) if locs_mouseover[n]]
                        smallest_loc = sorted(smallest_loc)[0][1]
                        editor_obdata[editor_currentobnum][3][smallest_loc].clear_icon()
                        if smallest_loc in editor_obdata[editor_currentobnum][5][editor_currentexpnum]['explode_locs']:
                            del editor_obdata[editor_currentobnum][5][editor_currentexpnum]['explode_locs'][smallest_loc]
                    #
                    for exploding_loc in editor_obdata[editor_currentobnum][3]:
                        exploding_loc.draw_icon(screen, current_window_offset)

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
                            all_map_objects = (textinput_mapname,
                                               textinput_author,
                                               textinput_description,
                                               digitinput_lives,
                                               digitinput_rating,
                                               digitinput_mapsizex,
                                               digitinput_mapsizey,
                                               draggable_playerstart,
                                               #
                                               editor_tilemap,
                                               editor_obdata)
                            out_json_fn  = os.path.join(MAP_DIR, textinput_mapname.get_value().replace(' ','_') + '.json')
                            save_message = write_map_data_to_json(out_json_fn, all_map_objects, tile_manager)
                            print(save_message)
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
                selected_terrain_box = None
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
                if current_gamestate == GameState.START_MENU:
                    #
                    # reset everything
                    #
                    my_animations.active_animations = []
                    my_animations_background.active_animations = []
                    #
                    current_map_bounds    = DEFAULT_MAP_DIM*GRID_SIZE
                    current_window_offset = Vector2(0, 0)
                    editor_resolution     = Vector2(RESOLUTION.x, RESOLUTION.y-128)
                    editor_tilemap        = np.zeros((int(DEFAULT_MAP_DIM.x), int(DEFAULT_MAP_DIM.y)), dtype='<i4')
                    editor_prevtilemapdim = editor_tilemap.shape
                    editor_tiledrawer     = TileMap(tile_manager)
                    editor_obdata         = []
                    editor_currentobnum   = None
                    editor_currentexpnum  = None
                    highlight_walls       = False
                    #
                    textinput_mapname.reset_with_new_str('')
                    textinput_author.reset_with_new_str('')
                    textinput_description.reset_with_new_str('')
                    digitinput_lives.reset_with_new_str(str(DEFAULT_MAP_LIFECOUNT))
                    digitinput_rating.reset_with_new_str(str(DEFAULT_MAP_RATING))
                    digitinput_mapsizex.reset_with_new_str(str(int(DEFAULT_MAP_DIM.x)))
                    digitinput_mapsizey.reset_with_new_str(str(int(DEFAULT_MAP_DIM.y)))
                    draggable_playerstart.center_pos = DEFAULT_PLAYER_START
                    #
                    terraindim_selection_menu.index  = 0
                    terrain_selection_menu_1x1.index = 0
                    terrain_selection_menu_2x2.index = 0
                    terrain_selection_menu_4x4.index = 0
                    terraintool_selection_menu.index = 0
                    selected_terrain_box             = None
                    current_terraintool              = None
                    #
                    currentob_selection_menu.content       = []
                    currentob_selection_menu.index         = 0
                    currentob_selection_menu.current_range = (0,0)
                    #
                    my_animations.remove_all_animations()
                #
                elif current_gamestate in [GameState.MAP_SELECT, GameState.MAP_SELECT_E]:
                    all_map_names = [n for n in os.listdir(MAP_DIR) if n[-5:] == '.json']
                    all_map_files = get_file_paths(MAP_DIR, all_map_names)
                    for i in range(len(all_map_names)):
                        all_map_files[i] = (all_map_names[i][:-5], all_map_files[i])
                    map_selection_menu = MapMenu(MAPSELECT_MENU_POS, all_map_files, font_dict['small_w'], num_rows=15, row_height=16, col_width=248, sort_field=0)
                #
                elif current_gamestate == GameState.BOUNDING:
                    if map_fn_to_load != None:
                        #
                        # load map json and set up world objects
                        #
                        world_map = WorldMap(map_fn_to_load, tile_manager)
                        current_map_bounds = Vector2(world_map.map_width * GRID_SIZE, world_map.map_height * GRID_SIZE)
                        my_player = Mauzling(world_map.start_pos, 0, player_img_fns[0], player_img_fns[2], swap_colors=WHITE_REMAP)
                        my_player.num_lives = world_map.init_lives
                        current_map_fn = map_fn_to_load
                        map_fn_to_load = None
                #
                elif current_gamestate == GameState.EDITOR_PROPERTIES:
                    #
                    # load map data into the editor
                    #
                    if map_fn_to_load != None:
                        all_map_objects = (textinput_mapname,
                                           textinput_author,
                                           textinput_description,
                                           digitinput_lives,
                                           digitinput_rating,
                                           digitinput_mapsizex,
                                           digitinput_mapsizey,
                                           draggable_playerstart)
                        (editor_tilemap, editor_obdata) = read_map_data_from_json(map_fn_to_load, all_map_objects, font_dict, player_img_fns[1])
                        #
                        currentob_selection_menu.content       = [('Obstacle '+str(n+1),) for n in range(len(editor_obdata))]
                        currentob_selection_menu.index         = 0
                        currentob_selection_menu.current_range = (0, min(len(editor_obdata), currentob_selection_menu.num_rows))
                        if currentob_selection_menu.content:
                            editor_currentobnum  = 0
                            editor_currentexpnum = 0
                            obinfo_move_menu.index = editor_obdata[editor_currentobnum][4]['move_mode']
                            obinfo_life_menu.index = editor_obdata[editor_currentobnum][4]['life_mode']
                            obinfo_move_menu.is_selected = False
                            obinfo_life_menu.is_selected = False
                            digitinput_oblives.reset_with_new_str(str(editor_obdata[editor_currentobnum][4]['life_amount']))
                            textinput_musicname.reset_with_new_str(str(editor_obdata[editor_currentobnum][4]['music']))
                            digitinput_expdelay.reset_with_new_str(str(editor_obdata[editor_currentobnum][5][editor_currentexpnum]['delay']))
                            for i in range(len(editor_obdata)):
                                my_exp_dict = editor_obdata[i][5][editor_currentexpnum]['explode_locs']
                                for k in my_exp_dict.keys():
                                    editor_obdata[i][3][k].change_icon(explosion_imgs[my_exp_dict[k]])
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
