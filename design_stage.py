#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import string
from collections import namedtuple
from fractions import Fraction

Point = namedtuple('Point', ['x', 'y'])
Block = namedtuple('Block', ['point', 'all', 'internal', 'center', 'walls'])

def design_stage(MAP_WIDTH, MAP_HEIGHT, BLOCK_WIDTH, BLOCK_HEIGHT, ROOM_RATIO):
    # 返り値
    terrain = {}
    assign = {}

    # 壁で埋める
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            terrain[Point(x, y)] = '#'
            assign[Point(x, y)] = '_'

    # ブロックの設定
    BLOCK_ROW = MAP_HEIGHT // BLOCK_HEIGHT
    BLOCK_COLUMN = MAP_WIDTH // BLOCK_WIDTH

    blocks = {}
    for y in range(BLOCK_ROW):
        for x in range(BLOCK_COLUMN):
            block = Block(Point(x, y), [], [], Point(x*BLOCK_WIDTH+BLOCK_WIDTH//2,
                    y*BLOCK_HEIGHT+BLOCK_HEIGHT//2), ([], [], [], []))
            for yy in range(BLOCK_HEIGHT):
                for xx in range(BLOCK_WIDTH):
                    point = Point(x*BLOCK_WIDTH+xx, y*BLOCK_HEIGHT+yy)
                    block.all.append(point)
                    if xx == 0:
                        block.walls[0].append(point)
                    elif xx == BLOCK_WIDTH-1:
                        block.walls[1].append(point)
                    elif yy == 0:
                        block.walls[2].append(point)
                    elif yy == BLOCK_HEIGHT-1:
                        block.walls[3].append(point)
                    else:
                        block.internal.append(point)

            blocks[Point(x, y)] = block

    ROOM_COUNT = round(random.gauss(ROOM_RATIO * BLOCK_ROW * BLOCK_COLUMN, 1))

    # --------------------------------------------------
    done = []

    def extend():
        # 部屋の拡大
        d = random.choice([Point(-1, 0), Point(1, 0), Point(0, -1), Point(0, 1)])
        room = blocks.get(Point(done[-1].point.x+d.x, done[-1].point.y+d.y))
        if not room or room in done:
            return
        terrain.update({Point(p.x+d.x*2, p.y+d.y*2): '.' for p in done[-1].internal})
        terrain.update({p: '.' for p in room.internal})
        assign.update({p: string.ascii_letters[len(done)] for p in room.internal})
        done.append(room)

    def corridor(point0, point1):
        def rect(point0, point1):
            orig = Point(min(point0.x, point1.x), min(point0.y, point1.y))
            dest = Point(max(point0.x, point1.x), max(point0.y, point1.y))
            for y in range(orig.y, dest.y+1):
                for x in range(orig.x, dest.x+1):
                    terrain[Point(x, y)] = '.'

        if random.random() < Fraction('1/2'):
            rect(point0, Point(point0.x, point1.y))
            rect(Point(point0.x, point1.y), point1)
        else:
            rect(point0, Point(point1.x, point0.y))
            rect(Point(point1.x, point0.y), point1)

    ## 最初の部屋
    room = random.choice(list(blocks.values()))
    terrain.update({p: '.' for p in room.internal})
    assign.update({p: string.ascii_letters[len(done)] for p in room.internal})
    assign[room.center] = '@'
    done.append(room)

    while len(done) <= ROOM_COUNT:
        room = random.choice(list(filter(lambda b: b not in done, blocks.values())))

        corridor(done[-1].center, room.center)

        terrain.update({p: '.' for p in room.internal})
        assign.update({p: string.ascii_letters[len(done)] for p in room.internal})
        done.append(room)

        if random.random() < Fraction('1/4'):
            extend()
            if random.random() < Fraction('1'):
                extend()

    # --------------------------------------------------
    for block in blocks.values():
        if any([assign[p] != '_' for p in block.all]):
            for wall in block.walls:
                for i in range(len(wall)-2):
                    if [terrain[p] for p in wall[i:i+2+1]] == ['#', '.', '#']:
                        assign[wall[i+1]] = '+'

    room_xs = [block.point.x for block in done]
    room_ys = [block.point.y for block in done]
    if all((0 in room_xs, BLOCK_COLUMN-1 in room_xs, 0 in room_ys, BLOCK_ROW-1 in room_ys)):
        return terrain, assign
    else:
        return design_stage(MAP_WIDTH, MAP_HEIGHT, BLOCK_WIDTH, BLOCK_HEIGHT, ROOM_RATIO)
