import pygame

from pygame.math import Vector2

PF_NODE_RADIUS   = 4	# width of pathfinding nodes (for drawing)
OB_REVIVE_RADIUS = 3	# width of revive spot (for drawing)

class Color:
	BACKGROUND  = (  0,   0,   0)	#
	INFO_TEXT   = (255, 255, 255)	# fps indicators, mouse positioning, etc
	TERRAIN     = (  0,  60, 180)	# blocking tiles
	PF_COLL     = (  0, 150, 250)	# boundaries of blocking tiles
	PF_NODE     = (200,  30,  30)	# pathfinding nodes
	PF_EDGE     = (  0, 100,   0)	# pathfinding edges
	GRID_MAJOR  = ( 40,  40,  40)	#
	GRID_MINOR  = ( 25,  25,  25)	#
	HITBOX      = (200, 200, 100)	# player hitbox
	SELECTION   = ( 50, 200,  50)	# selection box (player left clicking)
	WIDGET_SEL  = (200, 200, 200)	# background of player stat widget
	LIFECOUNT   = (160,   0, 160)	#
	SEL_ELLIPSE = ( 50, 200,  50)	# ellipse that gets drawn underneath selected units
	OB_STARTBOX = (100, 250, 100)	#
	OB_ENDBOX   = (250, 100, 100)	#
	OB_REVIVE   = (220, 220, 220)	#
	LOC_BG      = (100, 100, 100)	#
	LOC_TEXT    = (  0,   0,   0)	#
	MENU_BUTTON_BG         = (220, 220, 220)
	MENU_BUTTON_TEXT       = (  0,   0,   0)
	MENU_BUTTON_TEXT_HOVER = ( 70,  70,  70)

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
		pygame.draw.line(screen, color,       v,    v+dx, width=2)
		pygame.draw.line(screen, color,    v+dx, v+dx+dy, width=2)
		pygame.draw.line(screen, color, v+dx+dy,    v+dy, width=2)
		pygame.draw.line(screen, color,    v+dy,       v, width=2)
