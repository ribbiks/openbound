import json
import pygame
import numpy as np

from pygame.math import Vector2

from source.globals     import GRID_SIZE, PLAYER_RADIUS
from source.misc_gfx    import Color, PF_NODE_RADIUS
from source.obstacle    import Obstacle
from source.pathfinding import edge_is_collinear, edge_has_good_incoming_angles, edge_is_traversable
from source.pathfinding import get_pathfinding_data, UNIT_RADIUS_EPS
from source.tile_data   import TILE_DATA

class WorldMap:
	def __init__(self, map_filename, font_dict):
		#
		# load in basic map data
		#
		with open(map_filename,'r') as f:
			json_dat = json.load(f)
		self.map_name   = json_dat['map_name']
		self.map_author = json_dat['map_author']
		self.map_notes  = json_dat['map_notes']
		self.map_width  = json_dat['map_width']
		self.map_height = json_dat['map_height']
		self.init_lives = json_dat['starting_lives']
		self.p_starts   = [Vector2(n[0],n[1]) for n in json_dat['player_starts']]
		self.tile_dat   = np.array(json_dat['tile_dat']).T
		self.wall_map   = np.zeros((self.map_width, self.map_height))
		#
		for i in range(self.tile_dat.shape[0]):
			for j in range(self.tile_dat.shape[1]):
				(is_wall, name, image_fn) = TILE_DATA[self.tile_dat[i,j]]
				self.wall_map[i,j] = is_wall
		#
		self.p_loswidth = PLAYER_RADIUS - UNIT_RADIUS_EPS

		#
		# parse obstacles
		#
		self.obstacles = {}
		ob_keys = [k for k in json_dat.keys() if k[:9] == 'obstacle_']
		for k in ob_keys:
			my_ob_key  = int(k[9:])
			startbox   = json_dat[k]['startbox']
			endbox     = json_dat[k]['endbox']
			revive     = json_dat[k]['revive']
			loc_keys   = [k2 for k2 in json_dat[k].keys() if k2[:4] == 'loc_']
			event_keys = [k2 for k2 in json_dat[k].keys() if k2[:6] == 'event_']
			self.obstacles[my_ob_key] = Obstacle((Vector2(startbox[0], startbox[1]), Vector2(startbox[2], startbox[3])),
			                                     (Vector2(endbox[0], endbox[1]), Vector2(endbox[2], endbox[3])),
			                                     Vector2(revive[0], revive[1]),
			                                     font_loc=font_dict['large'])
			for k2 in loc_keys:
				my_loc_key = k2[4:]
				my_loc_dat = json_dat[k][k2]
				self.obstacles[my_ob_key].add_location(my_loc_key,
				                                       Vector2(my_loc_dat[0], my_loc_dat[1]),
				                                       Vector2(my_loc_dat[2], my_loc_dat[3]),
				                                       my_loc_dat[4],
				                                       my_loc_dat[5])
			for k2 in event_keys:
				my_event_dat = json_dat[k][k2]
				self.obstacles[my_ob_key].add_event(my_event_dat[0],
				                                    my_event_dat[1],
				                                    my_event_dat[2])

		#
		# lets construct all the stuff we need for pathfinding
		#
		(pf_nodes, pf_nodedict, pf_collision, pf_regionmap) = get_pathfinding_data(self.wall_map)
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
							if edge_is_traversable(edge_scaled, self.wall_map, self.p_loswidth, stepsize=0.9):
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
		for x in range(self.wall_map.shape[0]):
			for y in range(self.wall_map.shape[1]):
				if self.wall_map[x,y] == 1:
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
