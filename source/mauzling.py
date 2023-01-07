import math
import pygame

from collections import deque
from pygame.math import Vector2

from source.geometry    import angle_clamp, SMALL_NUMBER
from source.misc_gfx    import Color
from source.pathfinding import pathfind
from source.globals     import GRID_SIZE, PLAYER_RADIUS

#
# basic stats
#
MOVE_CYCLE = [2,8,9,5,6,7,2]
TURN_SPEED = 40

#
# pathing / click delay stuff
#
MOVE_DELAY           = 3
QUEUE_DELAY          = 1
MAX_ORDERS_IN_QUEUE  = 32
CLICK_DEADZONE       = 4
HITBOX_DEADZONE_BUFF = 4

#
# player states
#
class State:
	IDLE    = 0		# idle
	DELAY   = 1		# received orders, but we're waiting before we accept them (to emulate click delay)
	TURNING = 2		# turning
	MOVING  = 3		# moving
	ARRIVED = 4		# destination reached, next frame we will process our next order if we have one
	DELAY_Q = 5		# we have an order in queue, but are waiting to accept it (to emulate shift-click delay)

#
# order types
#
class OrderType:
	NEW   = 0
	QUEUE = 1

#
#
#
class Mauzling:
	def __init__(self, pos, angle, image_filename):
		self.position    = pos
		self.angle       = angle_clamp(angle)
		self.radius      = PLAYER_RADIUS
		self.bbox        = (self.position.x - self.radius,
		                    self.position.x + self.radius,
		                    self.position.y - self.radius,
		                    self.position.y + self.radius)
		self.state       = State.IDLE
		self.iscript_ind = 0
		self.inc_orders  = []			# orders we're waiting to accept (click delay)
		self.order_queue = deque([])	# orders we have accepted
		self.img         = pygame.image.load(image_filename).convert_alpha()
	
	#
	#
	#
	def draw(self, screen, offset, draw_bounding_box=False):
		rotated_image = pygame.transform.rotate(self.img, self.angle)
		new_rect = rotated_image.get_rect(center=self.img.get_rect(center=self.position+offset).center)
		screen.blit(rotated_image, new_rect)
		if draw_bounding_box:
			edges_to_draw = [(Vector2(self.bbox[0], self.bbox[2]), Vector2(self.bbox[1], self.bbox[2])),
			                 (Vector2(self.bbox[1], self.bbox[2]), Vector2(self.bbox[1], self.bbox[3])),
			                 (Vector2(self.bbox[1], self.bbox[3]), Vector2(self.bbox[0], self.bbox[3])),
			                 (Vector2(self.bbox[0], self.bbox[3]), Vector2(self.bbox[0], self.bbox[2]))]
			for edge in edges_to_draw:
				pygame.draw.line(screen, Color.HITBOX, edge[0]+offset, edge[1]+offset, width=1)
	
	#
	#
	#
	def update_position(self, pos, angle):
		self.position = pos
		self.angle = angle
		self.bbox = (self.position.x - self.radius,
		             self.position.x + self.radius,
		             self.position.y - self.radius,
		             self.position.y + self.radius)
	
	#
	#
	#
	def reset_iscript(self):
		self.iscript_ind = 0
	
	#
	#
	#
	def increment_iscript(self):
		self.iscript_ind = (self.iscript_ind + 1) % len(MOVE_CYCLE)
	
	#
	#
	#
	def get_current_speed(self):
		return MOVE_CYCLE[self.iscript_ind]
	
	#
	#
	#
	def get_turn_angles(self, start_position, start_angle, goal_position, clickpos=None):
		d_vec = goal_position - start_position
		g_ang = angle_clamp(-math.degrees(math.atan2(d_vec.y, d_vec.x)))	# goal angle
		d_ang = min(abs(start_angle - g_ang),
		            abs(start_angle - g_ang + 360),
		            abs(start_angle - g_ang - 360))
		num_turn_frames = self.get_turn_delay(d_ang)
		#
		turn_cw   = angle_clamp(start_angle - d_ang)
		turn_ccw  = angle_clamp(start_angle + d_ang)
		delta_cw  = min(abs(turn_cw - g_ang),
		                abs(turn_cw - g_ang + 360),
		                abs(turn_cw - g_ang - 360))
		delta_ccw = min(abs(turn_ccw - g_ang),
		                abs(turn_ccw - g_ang + 360),
		                abs(turn_ccw - g_ang - 360))
		# oh wow, a tie! this can happen when clicking against a wall
		# it looks better if we turn in a direction towards the wall so lets try to do that
		if abs(delta_cw - delta_ccw) < SMALL_NUMBER and clickpos != None:
			d_vec2 = clickpos - start_position
			g_ang2 = angle_clamp(-math.degrees(math.atan2(d_vec2.y, d_vec2.x)))
			turn_cw2   = angle_clamp(start_angle - 1)
			turn_ccw2  = angle_clamp(start_angle + 1)
			delta_cw2  = min(abs(turn_cw2 - g_ang2),
			                 abs(turn_cw2 - g_ang2 + 360),
			                 abs(turn_cw2 - g_ang2 - 360))
			delta_ccw2 = min(abs(turn_ccw2 - g_ang2),
			                 abs(turn_ccw2 - g_ang2 + 360),
			                 abs(turn_ccw2 - g_ang2 - 360))
			is_clockwise = delta_cw2 < delta_ccw2
		else:
			is_clockwise = delta_cw < delta_ccw
		#
		upcoming_angs = []
		if num_turn_frames > 1:
			if is_clockwise:
				upcoming_angs += [angle_clamp(start_angle - n*TURN_SPEED) for n in range(1,num_turn_frames+1)]
			else:
				upcoming_angs += [angle_clamp(start_angle + n*TURN_SPEED) for n in range(1,num_turn_frames+1)]
		elif num_turn_frames == 1:
			if d_ang <= TURN_SPEED:
				upcoming_angs += [g_ang]
			else:
				if is_clockwise:
					upcoming_angs += [angle_clamp(start_angle - TURN_SPEED)]
				else:
					upcoming_angs += [angle_clamp(start_angle + TURN_SPEED)]
		upcoming_angs.append(g_ang)
		return deque(upcoming_angs)
	
	#
	# d_angle between [0,360]
	#
	def get_turn_delay(self, d_angle):
		if d_angle > 180:
			d_angle -= 360
		d_angle = abs(d_angle)
		if d_angle <= 40 and self.state in [State.MOVING, State.TURNING]:
			return 0
		elif d_angle <= 80:
			return 1
		elif d_angle <= 120:
			return 2
		elif d_angle <= 160:
			return 3
		else:
			return 4

	#
	# big scary function that handles all the movement logic
	#
	def tick(self, world_object):
		#
		if self.state == State.IDLE or self.state == State.DELAY_Q:
			self.reset_iscript()
		#
		if self.state == State.ARRIVED:
			self.state = State.IDLE
		#
		# decrement delay on incoming orders, if any are ready, add them to queue
		#
		for i, v in enumerate(self.inc_orders):
			self.inc_orders[i][1] -= 1
			if self.inc_orders[i][1] <= 0:
				if v[2] == OrderType.QUEUE and self.order_queue:
					# for shift-clicks delay will be QUEUE_DELAY, for subpaths of a larger path it will be 0
					order_dat = [v[0], QUEUE_DELAY, True, None]
					self.order_queue.append(order_dat)
				else:
					# for new moves accept_delay = 0
					order_dat = [v[0], 0, True, None]
					self.order_queue = deque([order_dat])
		self.inc_orders = [n for n in self.inc_orders if n[1] > 0]
		#
		# act out our current order if we have one. order = (goal_pos, accept_delay, request_new_path, clicked_pos)
		#
		if self.order_queue:
			#
			self.order_queue[0][1] -= 1
			if self.order_queue[0][1] > -1:
				self.state = State.DELAY_Q
			else:
				# order accepted, pathfind subpaths if this is a new command
				pathfind_success = True
				if self.order_queue[0][2]:
					pathfind_success = False
					clicked_pos = self.order_queue[0][0]
					waypoints = pathfind(world_object, self.position, clicked_pos)
					if waypoints:
						dist_togo = (waypoints[0] - self.position).length()
						# we're already at the destination? then lets just turn if we need to
						if dist_togo < SMALL_NUMBER:
							self.turn_angles = self.get_turn_angles(self.position, self.angle, self.order_queue[0][0])
							self.order_queue[0] = [self.position, -2, False, None]
						# otherwise assign all the subpaths as new move orders
						else:
							self.order_queue.popleft()
							for n in waypoints[:-1]:
								self.order_queue.appendleft([n, 0, False, clicked_pos])
							self.order_queue[0][1] = -1		# so we process the first subpath immediately
						pathfind_success = True
				# abandon this order if no path was returned
				if not pathfind_success:
					self.order_queue.popleft()
					self.state = State.ARRIVED
				else:
					# everything went ok, lets compute necessary turns before we can begin moving
					if self.order_queue[0][1] == -1:
						self.turn_angles = self.get_turn_angles(self.position, self.angle, self.order_queue[0][0], clickpos=self.order_queue[0][3])
					# do the actual turning
					if self.turn_angles:
						self.state = State.TURNING
						self.angle = self.turn_angles.popleft()
						if not self.turn_angles:
							self.state = State.MOVING
						else:
							self.update_position(self.position, self.angle)
							self.increment_iscript()
					# move if we're now ready
					if self.state == State.MOVING:
						d_vec       = self.order_queue[0][0] - self.position
						dist_togo   = d_vec.length()
						move_amount = self.get_current_speed()
						if dist_togo <= move_amount:
							new_position = self.order_queue[0][0]
							self.order_queue.popleft()
							self.state = State.ARRIVED
						else:
							move_vec = d_vec
							move_vec.scale_to_length(move_amount)
							new_position = self.position + move_vec
						self.update_position(new_position, self.angle)
						self.increment_iscript()

	#
	# returns True if cursor click animation should be drawn
	#
	def issue_new_order(self, order, shift_pressed):
		if shift_pressed:
			if len(self.order_queue) >= MAX_ORDERS_IN_QUEUE:
				print('rejected order:', order, '(queue full)')
				return True
			move_type = OrderType.QUEUE
		else:
			move_type = OrderType.NEW
		# don't accept redundant orders within move_delay window
		if len(self.inc_orders) and order == self.inc_orders[-1][0]:
			print('rejected order:', order, '(redundant)')
			return True
		# don't new accept orders if we're already on our way to that exact spot
		if move_type == OrderType.NEW and self.order_queue:
			if (order - self.order_queue[-1][0]).length() <= CLICK_DEADZONE:
				print('rejected order:', order, '(already moving there)')
				return True
		# only accept move orders outside our bounding box (+ buffer)
		inside_box = (order.x >= self.bbox[0] - HITBOX_DEADZONE_BUFF and
		              order.x <= self.bbox[1] + HITBOX_DEADZONE_BUFF and
		              order.y >= self.bbox[2] - HITBOX_DEADZONE_BUFF and
		              order.y <= self.bbox[3] + HITBOX_DEADZONE_BUFF)
		if inside_box:
			print('rejected order:', order, '(clicked inside player)')
			return False
		#
		self.inc_orders.append([order, MOVE_DELAY, move_type])
		if self.state == State.IDLE:
			self.state = State.DELAY
		return True
