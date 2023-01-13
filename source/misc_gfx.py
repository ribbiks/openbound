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
	GRID_MAJOR  = ( 40,  40,  40)	#
	GRID_MINOR  = ( 25,  25,  25)	#
	HITBOX      = (200, 200, 100)	# player hitbox
	SELECTION   = ( 50, 200,  50)	# selection box (player left clicking)
	SEL_ELLIPSE = ( 50, 200,  50)	# ellipse that gets drawn underneath selected units
	OB_STARTBOX = (100, 250, 100)	#
	OB_ENDBOX   = (250, 100, 100)	#
	OB_REVIVE   = (220, 220, 220)	#
	LOC_BG      = (150, 150, 150)	#
	LIFECOUNT   = (163,  70, 163)
	PAL_BLUE_1  = (181, 245, 236)
	PAL_BLUE_2  = ( 91, 172, 227)
	PAL_BLUE_3  = ( 99, 106, 184)
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

def draw_grid(screen, screensize, gridsize, offset, color):
	for x in range(0, int(screensize.x)+1, gridsize):
		p1 = Vector2(x, -gridsize)
		p2 = Vector2(x, screensize.y + gridsize)
		pygame.draw.line(screen, color, p1+offset, p2+offset, width=1)
	for y in range(0, int(screensize.y)+1, gridsize):
		p1 = Vector2(-gridsize, y)
		p2 = Vector2(screensize.x + gridsize, y)
		pygame.draw.line(screen, color, p1+offset, p2+offset, width=1)

def draw_selection_box(screen, corner_points, color):
	if corner_points != None:
		dx = Vector2(corner_points[1].x - corner_points[0].x, 0)
		dy = Vector2(0, corner_points[1].y - corner_points[0].y)
		v  = corner_points[0]
		pygame.draw.line(screen, color,       v,    v+dx, width=1)
		pygame.draw.line(screen, color,    v+dx, v+dx+dy, width=1)
		pygame.draw.line(screen, color, v+dx+dy,    v+dy, width=1)
		pygame.draw.line(screen, color,    v+dy,       v, width=1)
