import pygame
import numpy as np

from pygame.math import Vector2

from source.globals     import GRID_SIZE, PLAYER_RADIUS
from source.misc_gfx    import Color, PF_NODE_RADIUS
from source.pathfinding import edge_is_collinear, edge_has_good_incoming_angles, edge_is_traversable
from source.pathfinding import get_pathfinding_data, UNIT_RADIUS_EPS

CHAR_MAP   = {'.':0, 'T':1, '@':1}
PLAYER_MAP = {'1':0, '2':1, '3':2, '4':3, '5':4, '6':5, '7':6, '8':7}

class WorldMap:
	def __init__(self, map_filename):
		temp_map_dat  = []
		self.p_starts = [None for n in PLAYER_MAP]
		with open(map_filename,'r') as f:
			for line in f:
				temp_map_dat.append([])
				for n in line.strip():
					if n in CHAR_MAP:
						temp_map_dat[-1].append(CHAR_MAP[n])
					elif n in PLAYER_MAP:
						self.p_starts[PLAYER_MAP[n]] = (len(temp_map_dat[-1]), len(temp_map_dat)-1)
						temp_map_dat[-1].append(0)
		self.map_dat = np.array(temp_map_dat).T
		for i,v in enumerate(self.p_starts):
			if v != None:
				self.p_starts[i] = Vector2(v[0]*GRID_SIZE + GRID_SIZE/2, v[1]*GRID_SIZE + GRID_SIZE/2)
		self.p_loswidth = PLAYER_RADIUS - UNIT_RADIUS_EPS	# a slightly trimmed player width used for los checks
		self.map_width  = self.map_dat.shape[0]*GRID_SIZE
		self.map_height = self.map_dat.shape[1]*GRID_SIZE
		#
		(pf_nodes, pf_nodedict, pf_collision, pf_regionmap) = get_pathfinding_data(self.map_dat)
		#
		pf_collision_scaled = []
		for rid in range(len(pf_nodes)):
			pf_collision_scaled.append([])
			for line in pf_collision[rid]:
				pf_collision_scaled[-1].append((Vector2(line[0][0]*GRID_SIZE, line[0][1]*GRID_SIZE),
				                                Vector2(line[1][0]*GRID_SIZE, line[1][1]*GRID_SIZE)))
		#
		pf_nodes_scaled = []
		for rid in range(len(pf_nodes)):
			pf_nodes_scaled.append([])
			for (x,y) in pf_nodes[rid]:
				pf_nodes_scaled[-1].append(Vector2(x*GRID_SIZE + GRID_SIZE/2, y*GRID_SIZE + GRID_SIZE/2))
		#
		filt_count = [0,0,0,0]
		pf_edges = []
		for rid in range(len(pf_nodes)):
			pf_edges.append({})
			for i in range(len(pf_nodes[rid])):
				for j in range(i+1,len(pf_nodes[rid])):
					edge        = [pf_nodes[rid][i], pf_nodes[rid][j]]
					edge_scaled = [pf_nodes_scaled[rid][i], pf_nodes_scaled[rid][j]]
					filt_count[0] += 1
					if not edge_is_collinear(edge, pf_nodedict[rid]):
						filt_count[1] += 1
						if edge_has_good_incoming_angles(edge, pf_nodedict[rid]):
							filt_count[2] += 1
							if edge_is_traversable(edge_scaled, self.map_dat, self.p_loswidth, stepsize=0.9):
								filt_count[3] += 1
								if i not in pf_edges[-1]:
									pf_edges[-1][i] = []
								if j not in pf_edges[-1]:
									pf_edges[-1][j] = []
								pf_edges[-1][i].append(j)
								pf_edges[-1][j].append(i)
		#
		self.nodes     = pf_nodes_scaled
		self.edges     = pf_edges
		self.collision = pf_collision_scaled
		self.regionmap = pf_regionmap

	#
	#
	#
	def draw(self, screen, offset, draw_pathing=False):
		terrain_polygons = []
		for x in range(self.map_dat.shape[0]):
			for y in range(self.map_dat.shape[1]):
				if self.map_dat[x,y] == 1:
					terrain_polygons.append([Vector2(    x*GRID_SIZE,     y*GRID_SIZE) + offset,
					                         Vector2((x+1)*GRID_SIZE,     y*GRID_SIZE) + offset,
					                         Vector2((x+1)*GRID_SIZE, (y+1)*GRID_SIZE) + offset,
					                         Vector2(    x*GRID_SIZE, (y+1)*GRID_SIZE) + offset])
		num_regions = len(self.nodes)
		collision_lines_draw = []
		for rid in range(num_regions):
			for line in self.collision[rid]:
				collision_lines_draw.append([line[0] + offset,
				                             line[1] + offset])
		all_edges_draw = []
		if draw_pathing:
			for rid in range(num_regions):
				region_edges = {}
				for i in self.edges[rid].keys():
					for j in self.edges[rid][i]:
						if (i,j) not in region_edges and (j,i) not in region_edges:
							region_edges[(i,j)] = True
				for (i,j) in region_edges.keys():
					all_edges_draw.append([self.nodes[rid][i] + offset,
										   self.nodes[rid][j] + offset])
		pf_ext_polygons = []
		if draw_pathing:
			for rid in range(num_regions):
				for [x,y] in self.nodes[rid]:
					pf_ext_polygons.append([Vector2(x - PF_NODE_RADIUS, y - PF_NODE_RADIUS) + offset,
					                        Vector2(x + PF_NODE_RADIUS, y - PF_NODE_RADIUS) + offset,
					                        Vector2(x + PF_NODE_RADIUS, y + PF_NODE_RADIUS) + offset,
					                        Vector2(x - PF_NODE_RADIUS, y + PF_NODE_RADIUS) + offset])
		#
		for p in terrain_polygons:
			pygame.draw.polygon(screen, Color.TERRAIN, p)
		for edge in collision_lines_draw:
			pygame.draw.line(screen, Color.PF_COLL, edge[0], edge[1], width=2)
		for edge in all_edges_draw:
			pygame.draw.line(screen, Color.PF_EDGE, edge[0], edge[1], width=1)
		for p in pf_ext_polygons:
			pygame.draw.polygon(screen, Color.PF_NODE, p)
