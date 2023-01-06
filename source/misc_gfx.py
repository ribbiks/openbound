import pygame

from pygame.math import Vector2

PF_NODE_RADIUS = 4	# width of pathfinding nodes (for drawing)

class Color:
	BACKGROUND = (  0,   0,   0)	#
	INFO_TEXT  = (255, 255, 255)	# fps indicators, mouse positioning, etc
	TERRAIN    = (  0,  60, 180)	# blocking tiles
	PF_COLL    = (  0, 150, 250)	# boundaries of blocking tiles
	PF_NODE    = (200,  30,  30)	# pathfinding nodes
	PF_EDGE    = (  0, 100,   0)	# pathfinding edges
	GRID_MAJOR = ( 40,  40,  40)	#
	GRID_MINOR = ( 25,  25,  25)	#
	HITBOX     = (200, 200, 100)	# player hitbox
	PREVIEW = '#475569'
	GRAPH   = '#60a5fa'

def draw_grid(screen, screensize, gridsize, offset, color):
	for x in range(0, int(screensize.x)+1, gridsize):
		p1 = Vector2(x, -gridsize)
		p2 = Vector2(x, screensize.y + gridsize)
		pygame.draw.line(screen, color, p1+offset, p2+offset, width=1)
	for y in range(0, int(screensize.y)+1, gridsize):
		p1 = Vector2(-gridsize, y)
		p2 = Vector2(screensize.x + gridsize, y)
		pygame.draw.line(screen, color, p1+offset, p2+offset, width=1)
