import pygame

from pygame.math import Vector2

PF_NODE_RADIUS   = 4	# width of pathfinding nodes (for drawing)
OB_REVIVE_RADIUS = 3	# width of revive spot (for drawing)

# opacity (out of 255) for fading to black during screen transitions
# -- gamestate changes occur on the first instance of 255
FADE_SEQUENCE = [50, 100, 150, 200, 250, 255, 250, 150, 100, 50]

class Color:
	BACKGROUND  = (  0,   0,   0)	#
	INFO_TEXT   = (255, 255, 255)	# fps indicators, mouse positioning, etc
	GRID_MAJOR  = ( 36,  36,  36)	#
	GRID_MINOR  = ( 22,  22,  22)	#
	HITBOX      = (200, 200, 100)	# player hitbox
	SELECTION   = ( 50, 200,  50)	# selection box (player left clicking)
	SEL_ELLIPSE = ( 50, 200,  50)	# ellipse that gets drawn underneath selected units
	OB_STARTBOX = (100, 250, 100)	#
	OB_ENDBOX   = (250, 100, 100)	#
	OB_REVIVE   = (220, 220, 220)	#
	LOC_BG      = (150, 150, 150)	#
	LIFECOUNT   = (163,  70, 163)
	PAL_BLUE_1  = (222, 245, 246)
	PAL_BLUE_2  = ( 91, 172, 227)
	PAL_BLUE_2B = (136, 143, 243)
	PAL_BLUE_3  = ( 97, 104, 182)
	PAL_BLUE_4  = ( 87,  65, 117)
	PAL_BLUE_5  = ( 47,  35,  56)
	PAL_WHITE   = (255, 255, 255)
	PAL_BLACK   = (  0,   0,   0)
	PAL_YEL_1   = (247, 255, 237)
	PAL_YEL_2   = (245, 229, 191)
	PAL_YEL_3   = (232, 173, 128)
	PAL_YEL_4   = (207, 120,  76)
	PAL_YEL_5   = (173,  88,  69)
	PAL_YEL_6   = (115,  56,  62)
	PAL_GREEN_1 = (237, 245, 247)
	PAL_GREEN_2 = (162, 237,  23)
	PAL_GREEN_3 = ( 57, 180,  12)
	PAL_GREEN_4 = (  0, 112,  17)
	PAL_RED_1   = (255, 232, 232)
	PAL_RED_2   = (255, 130, 130)
	PAL_RED_3   = (217,  55,  50)
	PAL_RED_4   = (135,  10,  17)

def clip(surf, x, y, x_size, y_size):
	handle_surf = surf.copy()
	clipR = pygame.Rect(x,y,x_size,y_size)
	handle_surf.set_clip(clipR)
	image = surf.subsurface(handle_surf.get_clip())
	return image.copy()

def draw_grid(screen, screensize, gridsize, offset, color):
	for x in range(0, int(screensize.x)+2, gridsize):
		p1 = Vector2(x, -gridsize)
		p2 = Vector2(x, screensize.y + gridsize)
		pygame.draw.line(screen, color, p1+offset, p2+offset, width=1)
	for y in range(0, int(screensize.y)+2, gridsize):
		p1 = Vector2(-gridsize, y)
		p2 = Vector2(screensize.x + gridsize, y)
		pygame.draw.line(screen, color, p1+offset, p2+offset, width=1)

def draw_selection_box(screen, box, offset, color):
	if box != None:
		dx = Vector2(box[1].x - box[0].x, 0)
		dy = Vector2(0, box[1].y - box[0].y)
		v  = box[0]
		pygame.draw.line(screen, color,       v+offset,    v+dx+offset, width=1)
		pygame.draw.line(screen, color,    v+dx+offset, v+dx+dy+offset, width=1)
		pygame.draw.line(screen, color, v+dx+dy+offset,    v+dy+offset, width=1)
		pygame.draw.line(screen, color,    v+dy+offset,       v+offset, width=1)

def draw_map_bounds(screen, mapsize, offset, color):
	dx = Vector2(mapsize.x, 0)
	dy = Vector2(0, mapsize.y)
	pygame.draw.line(screen, color,       offset,    dx+offset, width=3)
	pygame.draw.line(screen, color,    dx+offset, dx+dy+offset, width=3)
	pygame.draw.line(screen, color, dx+dy+offset,    dy+offset, width=3)
	pygame.draw.line(screen, color,    dy+offset,       offset, width=3)
