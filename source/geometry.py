
# basically a tolerance for floating point precision when determining equalities
SMALL_NUMBER = 1e-6

def angle_clamp(angle):
	if abs(angle) < SMALL_NUMBER:
		return 0.
	while angle < 0:
		angle += 360
	while angle > 360:
		angle -= 360
	return angle

def value_clamp(v, v_min, v_max):
	if v <= v_min:
		return v_min
	if v >= v_max:
		return v_max
	return v

##### do line segments AB and CD intersect?
####def segments_intersect(A,B,C,D):
####	return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)
####
####def ccw(A,B,C):
####	return (C.y-A.y) * (B.x-A.x) > (B.y-A.y) * (C.x-A.x)
