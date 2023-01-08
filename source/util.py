import os

def exists_and_is_nonzero(fn):
	if os.path.isfile(fn):
		if os.path.getsize(fn) > 0:
			return True
	return False

def makedir(d):
	if not os.path.isdir(d):
		os.mkdir(d)

def rm(fn):
	if os.path.isdir(fn):
		os.rmdir(fn)
	elif os.path.isfile(fn):
		os.remove(fn)

def get_file_paths(d, img_list):
	path_list = [os.path.join(d, n) for n in img_list]
	for n in path_list:
		if not exists_and_is_nonzero(n):
			print('Error: file not found')
			print('--', n)
			exit(1)
	return path_list
