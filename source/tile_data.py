
# (is_wall, name, image_fn)

TILE_DATA = { 0 : (0, 'blank_walkable', ''),
              1 : (1, 'blank_wall',     ''),
              2 : (0, 'test_walkable', 'blank.png'),
              3 : (1, 'test_wall',     'wall5.png'),
              4 : (0, 'blockfloor',    'block.png')}

META_TILES_1x1 = [[k, TILE_DATA[k][1]] for k in sorted(TILE_DATA.keys())]

META_TILES_2x2 = [[3,3,3,2, 'composite_test1'],
                  [3,3,2,3, 'composite_test2']]

META_TILES_4x4 = [4,4,4,4,4,3,3,4,4,3,3,4,4,4,4,4, 'composite_test3']
