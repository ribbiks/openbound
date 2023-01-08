import copy
import heapq
import numpy as np
import pygame

from collections import deque
from pygame.math import Vector2

from source.globals  import GRID_SIZE

UNIT_RADIUS_EPS = 0.01

#
#
#
def get_pathfinding_data(map_dat):
	tile_2_region_id = np.zeros((map_dat.shape[0], map_dat.shape[1]), dtype='i4') - 1
	num_regions      = 0
	# bfs to identify each fully-connected pathing regions
	visited = {}
	for x in range(1, map_dat.shape[0]-1):
		for y in range(1, map_dat.shape[1]-1):
			if (x,y) not in visited and map_dat[x,y] == 0:
				visited[(x,y)] = True
				tile_2_region_id[x,y] = num_regions
				queue = deque([(x,y)])
				while queue:
					(mx, my) = queue.popleft()
					for neighbor in [(mx-1,my), (mx+1,my), (mx,my-1), (mx,my+1)]:
						if neighbor not in visited and map_dat[neighbor[0],neighbor[1]] == 0:
							visited[neighbor] = True
							tile_2_region_id[neighbor[0],neighbor[1]] = num_regions
							queue.append(neighbor)
				num_regions += 1
	nodes           = [[] for n in range(num_regions)]
	collision_lines = [[] for n in range(num_regions)]
	#
	# for each region get pathing nodes and collision lines
	#
	for x in range(1, map_dat.shape[0]-1):
		for y in range(1, map_dat.shape[1]-1):
			if map_dat[x,y] == 0:
				a = (map_dat[x-1,y-1] == 0)
				b = (map_dat[x  ,y-1] == 0)
				c = (map_dat[x+1,y-1] == 0)
				d = (map_dat[x-1,y  ] == 0)
				e = (map_dat[x+1,y  ] == 0)
				f = (map_dat[x-1,y+1] == 0)
				g = (map_dat[x  ,y+1] == 0)
				h = (map_dat[x+1,y+1] == 0)
				#
				my_region_id = tile_2_region_id[x,y]
				#
				if (not a and b and d) or (not c and b and e) or (not f and d and g) or (not h and g and e):
					nodes[my_region_id].append((x,y))
				if not b:
					collision_lines[my_region_id].append([(x,y), (x+1,y), False])
				if not d:
					collision_lines[my_region_id].append([(x,y+1), (x,y), True])
				if not e:
					collision_lines[my_region_id].append([(x+1,y), (x+1,y+1), True])
				if not g:
					collision_lines[my_region_id].append([(x+1,y+1), (x,y+1), False])
	#
	# precompute which corners are clear for each node (for downstream pruning)
	# -- node has wall to NW, NE, SE, SW : &1, &2, &4, &8
	#
	node_angle_dict = [{} for n in range(num_regions)]
	for rid in range(num_regions):
		for node in nodes[rid]:
			node_angle_dict[rid][node] = 0
			if map_dat[node[0]-1,node[1]-1] == 1:
				node_angle_dict[rid][node] += 1
			if map_dat[node[0]+1,node[1]-1] == 1:
				node_angle_dict[rid][node] += 2
			if map_dat[node[0]+1,node[1]+1] == 1:
				node_angle_dict[rid][node] += 4
			if map_dat[node[0]-1,node[1]+1] == 1:
				node_angle_dict[rid][node] += 8
	#
	# merge attached line segments
	#
	merged_lines = []
	for rid in range(num_regions):
		all_adj = np.zeros((len(collision_lines[rid]), len(collision_lines[rid])), dtype='i4')
		for i in range(len(collision_lines[rid])):
			for j in range(i+1, len(collision_lines[rid])):
				if collision_lines[rid][i][2] == collision_lines[rid][j][2]:	# same orientation
					if collision_lines[rid][i][0] in collision_lines[rid][j] or collision_lines[rid][i][1] in collision_lines[rid][j]:
						all_adj[i,j] = 1
						all_adj[j,i] = 1
		clust_lines = []
		for i in range(len(collision_lines[rid])):
			found_a_home = False
			for ci in range(len(clust_lines)):
				for j in clust_lines[ci]:
					if all_adj[i,j]:
						clust_lines[ci].append(i)
						found_a_home = True
			if not found_a_home:
				clust_lines.append([i])
		merged_lines.append([])
		for lc in clust_lines:
			if collision_lines[rid][lc[0]][2] == False:
				my_xr = [collision_lines[rid][n][0][0] for n in lc] + [collision_lines[rid][n][1][0] for n in lc]
				my_x  = (min(my_xr), max(my_xr))
				my_y  = (collision_lines[rid][lc[0]][0][1], collision_lines[rid][lc[0]][0][1])
			else:
				my_x  = (collision_lines[rid][lc[0]][0][0], collision_lines[rid][lc[0]][0][0])
				my_yr = [collision_lines[rid][n][0][1] for n in lc] + [collision_lines[rid][n][1][1] for n in lc]
				my_y  = (min(my_yr), max(my_yr))
			merged_lines[-1].append([(my_x[0], my_y[0]), (my_x[1], my_y[1])])
	#
	return (nodes, node_angle_dict, merged_lines, tile_2_region_id)

#
#
#
def edge_is_collinear(edge, node_dict):
	x0 = edge[0][0]
	y0 = edge[0][1]
	dx = edge[1][0] - x0
	dy = edge[1][1] - y0
	steps = max(abs(dx), abs(dy))
	for i in range(1,steps):
		if ((i * dx) % steps == 0 and (i * dy) % steps == 0):
			x = int(x0 + (i * dx) / steps)
			y = int(y0 + (i * dy) / steps)
			if (x,y) in node_dict:
				#print(x, y, 'is redundant?')
				return True
	return False

#
#
#
def moving_into_clear_corner(dx, dy, node, node_dict):
	if dx > 0 and dy > 0:	# heading SE
		if node_dict[node] & 4:
			return False
	elif dx > 0 and dy < 0:	# heading NE
		if node_dict[node] & 2:
			return False
	elif dx < 0 and dy < 0:	# heading NW
		if node_dict[node] & 1:
			return False
	elif dx < 0 and dy > 0:	# heading SW
		if node_dict[node] & 8:
			return False
	return True

#
#
#
def edge_has_good_incoming_angles(edge, node_dict):
	x0 = edge[0][0]
	y0 = edge[0][1]
	x1 = edge[1][0]
	y1 = edge[1][1]
	if x0 == x1 or y0 == y1:	# horiz / vertical lines are fine
		return True
	# coming into (x1,y1) from (x0,y0)
	edge1_clear = moving_into_clear_corner(x1-x0, y1-y0, (x1,y1), node_dict)
	# coming into (x0,y0) from (x1,y1)
	edge2_clear = moving_into_clear_corner(x0-x1, y0-y1, (x0,y0), node_dict)
	#
	return edge1_clear or edge2_clear

#
#
#
def edge_is_traversable(edge, map_dat, unit_radius, stepsize=0.9):
	corner_offsets = [Vector2(-unit_radius, -unit_radius),
	                  Vector2(-unit_radius,  unit_radius),
	                  Vector2( unit_radius, -unit_radius),
	                  Vector2( unit_radius,  unit_radius)]
	dv = edge[1] - edge[0]
	nsteps = int(dv.length()/stepsize)-1
	if nsteps <= 0:
		return False
	dv.scale_to_length(stepsize)
	for co in corner_offsets:
		v = Vector2(edge[0].x, edge[0].y) + co	# need to make a new vec2 otherwise we modify the original variable (doh)
		for i in range(nsteps):
			v += dv
			(mx, my) = (int(v.x / GRID_SIZE), int(v.y / GRID_SIZE))
			if map_dat[mx,my] == 1:
				return False
	return True

#
#
#
def valid_player_pos(v, map_dat, unit_radius):
	corner_offsets = [Vector2(-unit_radius, -unit_radius),
	                  Vector2(-unit_radius,  unit_radius),
	                  Vector2( unit_radius, -unit_radius),
	                  Vector2( unit_radius,  unit_radius)]
	for co in corner_offsets:
		v_adj = v + co
		(mx, my) = (int(v_adj.x / GRID_SIZE), int(v_adj.y / GRID_SIZE))
		if map_dat[mx,my] == 1:
			return False
	return True

#
# returns reversed list of waypoints
#
def pathfind(world_object, starting_pos, ending_pos):
	#
	map_dat      = world_object.map_dat
	pf_nodes     = world_object.nodes
	pf_edges     = world_object.edges
	pf_regionmap = world_object.regionmap
	my_unitbuff  = world_object.p_loswidth
	#
	(ux,uy) = (int(starting_pos.x / GRID_SIZE), int(starting_pos.y / GRID_SIZE))
	(cx,cy) = (int(ending_pos.x / GRID_SIZE), int(ending_pos.y / GRID_SIZE))
	unit_region  = pf_regionmap[ux,uy]
	click_region = pf_regionmap[cx,cy]
	starting_pos_quant = Vector2(ux*GRID_SIZE + GRID_SIZE/2, uy*GRID_SIZE + GRID_SIZE/2)
	ending_pos_quant   = Vector2(cx*GRID_SIZE + GRID_SIZE/2, cy*GRID_SIZE + GRID_SIZE/2)
	#
	# if we clicked out of bounds move to the tile closest to the click position (that is in bounds)
	# --- draw a line from click pos towards current unit pos, looking for a valid destination
	#
	if click_region != unit_region:
		steps    = abs(cx-ux) + abs(cy-uy)
		(x0, y0) = (cx, cy)
		(dx, dy) = (ux-cx, uy-cy)
		found_valid_tile = False
		for i in range(steps):
			x = x0 + int(i*(dx/steps))
			y = y0 + int(i*(dy/steps))
			if pf_regionmap[x,y] == unit_region:
				ending_pos_quant = Vector2(x*GRID_SIZE + GRID_SIZE/2, y*GRID_SIZE + GRID_SIZE/2)
				found_valid_tile = True
				break
		# if that failed, lets do a bfs to find the nearest valid tile
		if not found_valid_tile:
			visited = {(cx,cy): True}
			found_tiles = []
			queue = deque([(cx, cy)])
			while queue:
				(x,y) = queue.popleft()
				if pf_regionmap[x,y] == unit_region:
					found_tiles = [(x,y)] + [n for n in queue if pf_regionmap[(n[0],n[1])] == unit_region]
					break
				for neighbor in [(x-1,y), (x+1,y), (x,y-1), (x,y+1)]:
					if neighbor[0] >= 0 and neighbor[0] < map_dat.shape[0] and neighbor[1] >= 0 and neighbor[1] < map_dat.shape[1]:
						if neighbor not in visited:
							visited[neighbor] = True
							queue.append(neighbor)
			if len(found_tiles):
				found_tiles = sorted([((Vector2(n[0],n[1]) - Vector2(cx,cy)).length(), n) for n in found_tiles])
				(x,y) = found_tiles[0][1]
				ending_pos_quant = Vector2(x*GRID_SIZE + GRID_SIZE/2, y*GRID_SIZE + GRID_SIZE/2)
				found_valid_tile = True
		# somehow that also failed, so we're not going to move at all. sorry!
		if not found_valid_tile:
			return []
	#
	# if ending position is not valid (e.g. in a wall) choose closest in-bounds tile and nudge towards desired coords
	#
	if not valid_player_pos(ending_pos, map_dat, my_unitbuff):
		#print('ending_pos:', ending_pos)
		#print('quant:     ', ending_pos_quant)
		nudged_pos = ending_pos_quant
		if nudged_pos.x > ending_pos.x:
			while nudged_pos.x > ending_pos.x and valid_player_pos(nudged_pos - Vector2(1,0), map_dat, my_unitbuff):
				nudged_pos -= Vector2(1,0)
		elif nudged_pos.x < ending_pos.x:
			while nudged_pos.x < ending_pos.x and valid_player_pos(nudged_pos + Vector2(1,0), map_dat, my_unitbuff):
				nudged_pos += Vector2(1,0)
		if nudged_pos.y > ending_pos.y:
			while nudged_pos.y > ending_pos.y and valid_player_pos(nudged_pos - Vector2(0,1), map_dat, my_unitbuff):
				nudged_pos -= Vector2(0,1)
		elif nudged_pos.y < ending_pos.y:
			while nudged_pos.y < ending_pos.y and valid_player_pos(nudged_pos + Vector2(0,1), map_dat, my_unitbuff):
				nudged_pos += Vector2(0,1)
		ending_pos = nudged_pos
	#
	# do we have a straight line between current position and where we want to go?
	# -- using an aggressively small stepsize here so that we don't fail LoS checks if start and end are very close
	#
	have_straight_line = edge_is_traversable([starting_pos, ending_pos], map_dat, my_unitbuff, stepsize=0.1)
	if have_straight_line:
		return [ending_pos, starting_pos]
	#
	# looks like we have to actually do pathfinding...
	#
	my_edges      = copy.deepcopy(pf_edges[unit_region])
	num_edges     = len(my_edges)
	starting_node = num_edges
	ending_node   = num_edges + 1
	#
	# insert starting position into graph
	#
	my_edges[starting_node] = []
	for i,v in enumerate(pf_nodes[unit_region]):
		if edge_is_traversable([starting_pos, v], map_dat, my_unitbuff):
			my_edges[i].append(starting_node)
			my_edges[starting_node].append(i)
	#
	# insert destination into graph
	#
	my_edges[ending_node] = []
	for i,v in enumerate(pf_nodes[unit_region]):
		if edge_is_traversable([v, ending_pos], map_dat, my_unitbuff):
			my_edges[i].append(ending_node)
			my_edges[ending_node].append(i)
	#
	if not my_edges[starting_node] or not my_edges[ending_node]:
		print('Error: something went wrong and we were unable to connect starting/ending nodes to graph')
		print(' -- starting_pos:', starting_pos)
		print(' -- ending_pos:  ', ending_pos)
		exit(1)
	#
	# astar
	#
	my_nodes = pf_nodes[unit_region] + [starting_pos, ending_pos]
	visited = {}
	came_from = {}
	traceback = None
	queue = []
	heapq.heappush(queue, (0, 0, starting_node))	# (fscore, gscore, node)
	while queue:
		(my_f, my_g, current_node) = heapq.heappop(queue)
		visited[current_node] = True
		if current_node == ending_node:
			traceback = [ending_node]
			while traceback[-1] != starting_node:
				traceback.append(came_from[traceback[-1]])
			break
		neighbors = [n for n in my_edges[current_node] if n not in visited]
		#
		for neighbor in neighbors:
			v1 = my_nodes[current_node]
			v2 = my_nodes[neighbor]
			v3 = ending_pos
			g  = my_g + (v2-v1).length()
			h  = (v3-v2).length()
			# if neighbor is in open list already with a lower g score --> skip
			insert_neighbor = True
			for n in queue:
				if n[2] == neighbor and n[1] <= g:
					insert_neighbor = False
					break
			# otherwise add neighbor to open list
			if insert_neighbor:
				h = (v3-v2).length()
				heapq.heappush(queue, (g+h, g, neighbor))
				came_from[neighbor] = current_node
	return [my_nodes[n] for n in traceback]
