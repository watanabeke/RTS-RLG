#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import tdl
from collections import namedtuple, OrderedDict
from fractions import Fraction
from functools import lru_cache
from copy import deepcopy
import weakref
import json

# 定数

MAP_WIDTH = 54
MAP_HEIGHT = 36

MESSAGE_HEIGHT = 3
STATUS_HEIGHT = 1

SCREEN_WIDTH = MAP_WIDTH
SCREEN_HEIGHT = MAP_HEIGHT + MESSAGE_HEIGHT + STATUS_HEIGHT

TURN_TIME = Fraction('1/5')

## 色

def code_to_rgb(code):
    return (int(code[1:1+2], 16),
            int(code[1+2:1+2*2], 16),
            int(code[1+2*2:1+2*3], 16))

COLOR_BACK = code_to_rgb('#222728')
COLOR_CURRENT = code_to_rgb('#42484a')
COLOR_SELECT = code_to_rgb('#42484a')
COLOR_FORE = code_to_rgb('#c4c7c8')
COLOR_COMMENT = code_to_rgb('#757879')
COLOR_RED = code_to_rgb('#ff72a4')
COLOR_ORANGE = code_to_rgb('#f69113')
COLOR_YELLOW = code_to_rgb('#b9ad00')
COLOR_GREEN = code_to_rgb('#83ba54')
COLOR_AQUA = code_to_rgb('#00c1b0')
COLOR_BLUE = code_to_rgb('#80b2d4')
COLOR_PURPLE = code_to_rgb('#c09cef')

COLOR_ALLIE = COLOR_RED
COLOR_HOME = COLOR_ORANGE
COLOR_ENEMY0 = COLOR_AQUA
COLOR_ENEMY1 = COLOR_BLUE
COLOR_ENEMY2 = COLOR_PURPLE
COLOR_GATE = COLOR_GREEN
COLOR_ITEM = COLOR_YELLOW

# 全般的なもの

Point = namedtuple('Point', ['x', 'y'])
ALL_POINTS = [Point(x, y) for y in range(MAP_HEIGHT) for x in range(MAP_WIDTH)]

def distance(orig, dest):
    import math
    dx = orig.x - dest.x
    dy = orig.y - dest.y
    return math.sqrt(dx ** 2 + dy ** 2)

def _wall_chars():
    patterna = [(0,0,0), (0,1,0), (0,0,0), (0,0,0), (0,0,0), (0,0,0), (0,1,0), (0,0,0)]
    patternb = [(0,1,0), (0,1,0), (0,1,0), (1,1,0), (0,1,1), (1,1,1), (0,1,0), (1,1,0)]
    patternc = [(0,0,0), (0,0,0), (0,1,0), (0,0,0), (0,0,0), (0,0,0), (0,1,0), (0,1,0)]

    pattern1 = [patterna[n]+patternb[n]+patternc[n] for n in range(8)]

    patternd = [(0,1,0), (0,1,0), (0,0,0), (0,1,0), (0,1,0), (0,0,0), (0,1,0), (0,1,0)]
    patterne = [(1,1,0), (0,1,1), (0,1,1), (1,1,0), (1,1,1), (1,1,1), (0,1,1), (1,1,1)]
    patternf = [(0,0,0), (0,0,0), (0,1,0), (0,1,0), (0,0,0), (0,1,0), (0,1,0), (0,1,0)]

    pattern2 = [patternd[n]+patterne[n]+patternf[n] for n in range(8)]

    patterns = pattern1 + pattern2

    chars = [172, 168, 169, 170, 171, 205, 186, 187, 188, 200, 201, 185, 202, 203, 204, 206]

    return {p: chr(c) for p, c in zip(patterns, chars)}

WALL_CHARS = _wall_chars()

gv = lambda: None
gv.seed = None
gv.console = None
gv.stage = None
gv.start_time = None
gv.turn = None
gv.selecteds = set()
gv.home = None
gv.focused = None
gv.pointed = None
gv.ctrl = False
gv.shift = False
gv.init_count = {}
gv.count = {}
gv.messages = []  # (文字列, 色)

gv.animation_datas = []
AnimationData = namedtuple('AnimationData', ['point', 'char', 'fgcolor', 'bgcolor', 'fin_time'])

def animation(point, char=None, fgcolor=None, bgcolor=None, dur_time=Fraction('1/8')):
    import time
    gv.animation_datas.append(AnimationData(point, char, fgcolor, bgcolor, dur_time + time.clock()))

def darken(color, ratio):
    return tuple(map(lambda i: round(i*ratio), color))

try:
    with open('seed.json', 'r') as f:
        gv.seed_json = json.load(f, object_pairs_hook=OrderedDict)
except:
    gv.seed_json = OrderedDict()
    gv.seed_json['seed'] = ''
    gv.seed_json['history'] = []

# 準備

tdl.setFont('font_14x14.png', 32, 2048, False, True)
gv.console = tdl.init(SCREEN_WIDTH, SCREEN_HEIGHT, title='nullRLG', renderer='SDL')
gv.console.clear(COLOR_FORE, COLOR_BACK)
gv.message_console = tdl.Console(SCREEN_WIDTH, MESSAGE_HEIGHT)
gv.message_console.clear(COLOR_FORE, darken(COLOR_CURRENT, 0.5))
gv.status_console = tdl.Console(SCREEN_WIDTH, STATUS_HEIGHT)
gv.status_console.clear(COLOR_FORE, COLOR_CURRENT)

tdl.setFPS(30)

# ステージ

class Stage(object):

    def __init__(self, seed=None):
        self.tiles = {}  # Dict[Point, Tile]
        self.units = []  # List[Unit]
        self.rooms = []  # List[List[Point]]
        self.corridors = []  # List[List[Point]]
        self.build(seed)

    def build(self, seed=None):
        # 定数
        BLOCK_WIDTH = 9
        BLOCK_HEIGHT = 9

        ROOM_RATIO = Fraction('1/3')

        # 乱数種
        import random
        random.seed(seed)

        # デザインの取得
        import design_stage
        terrein, assign = design_stage.design_stage(MAP_WIDTH, MAP_HEIGHT,
                BLOCK_WIDTH, BLOCK_HEIGHT, ROOM_RATIO)

        # タイルの設定
        for p in ALL_POINTS:
            tile = Tile(terrein[p], assign[p])
            tile.stage = weakref.proxy(self)
            tile.point = p
            self.tiles[p] = tile

        # ユニット数の決定
        ALLIE_COUNT = 6

        gv.init_count['allie'] = ALLIE_COUNT
        gv.init_count['enemy'] = {
            0 : round(random.gauss(gv.init_count['allie']*2, gv.init_count['allie'] / 4)),
            1 : round(random.gauss(gv.init_count['allie'], gv.init_count['allie'] / 4)),
            2 : round(random.gauss(gv.init_count['allie']/2, gv.init_count['allie'] / 4)),
        }
        gv.init_count['gate'] = round(random.gauss(gv.init_count['allie'], gv.init_count['allie'] / 4))
        gv.init_count['item'] = max(round(random.gauss(gv.init_count['allie'], gv.init_count['allie'] / 4)), 1)

        # ユニットの配置
        for _ in range(gv.init_count['allie']):
            self.place(Allie(fgcolor=COLOR_ALLIE, hp=1024, cure=32, power=64), 'a')

        import string
        for _ in range(gv.init_count['enemy'][0]):
            self.place(Enemy(fgcolor=COLOR_ENEMY0, hp=1024, cure=16, power=64), string.ascii_letters[1:])

        for _ in range(gv.init_count['enemy'][1]):
            self.place(Enemy(fgcolor=COLOR_ENEMY1, hp=1024, cure=16, power=64), string.ascii_letters[1:])

        for _ in range(gv.init_count['enemy'][2]):
            self.place(Enemy(fgcolor=COLOR_ENEMY2, hp=1024, cure=16, power=64), string.ascii_letters[1:])

        for _ in range(gv.init_count['gate']):
            self.place(Gate(fgcolor=COLOR_GATE, hp=1024), '+')

        for _ in range(gv.init_count['item']):
            self.place(Item(char='*', fgcolor=COLOR_ITEM), string.ascii_letters[1:])

        gv.home = Home(char='@', fgcolor=COLOR_HOME)
        self.place(gv.home, '@')

        gv.init_count['enemy'] = sum(gv.init_count['enemy'].values())
        gv.count = deepcopy(gv.init_count)

    def is_empty(self, point):
        return (point in self.tiles and self.tiles[point].passable
                and not [u for u in self.units if u.point == point])

    def is_passable(self, point):
        return (point in self.tiles and self.tiles[point].passable
                and all([u.passable for u in self.units if u.point == point]))

    def is_transparent(self, point):
        return (point in self.tiles and self.tiles[point].transparent
                and all([u.transparent for u in self.units if u.point == point]))

    def place(self, unit, assigns):
        # assign は1文字または複数文字の文字列
        # 複数文字ならそのすべての文字の地点からランダム配置
        candidates = [p for p in ALL_POINTS if self.tiles[p].assign in assigns
                and self.is_empty(p)]
        if not candidates:
            candidates = [p for p in ALL_POINTS if self.tiles[p].assign in assigns
                    and self.is_passable(p)]
        if not candidates and unit.passable:
            candidates = [p for p in ALL_POINTS if self.tiles[p].assign in assigns
                    and p in self.tiles]
        if not candidates:
            raise
        else:
            import random
            unit.stage = weakref.proxy(self)
            self.units.append(unit)
            success = unit.move(random.choice(candidates))
            if not success:
                raise

    def get_path(self, orig, dest, ignore_units=None):
        # ignore_unitは無視するユニットのクラスまたはそのタプル
        ignore_units = ignore_units if ignore_units else ()
        ignore_units = ignore_units if hasattr(ignore_units, '__iter__') else (ignore_units,)

        def func(x, y):
            p = Point(x, y)
            if p in self.tiles:
                if p == orig or p == dest:
                    return True
                if self.tiles[p].passable:
                    if not [u for u in self.units if u.point == p
                            and not u.passable and not isinstance(u, ignore_units)]:
                        return True
            return False

        aster = tdl.map.AStar(MAP_WIDTH, MAP_HEIGHT, func)

        return [Point(*t) for t in aster.getPath(orig.x, orig.y, dest.x, dest.y)]

class Tile(object):

    def __init__(self, terrein, assign):
        # terrein, assign は1文字の文字列
        self.terrein = terrein
        self.assign = assign

        self.point = None
        self.stage = None

    # 壁文字

    @property
    def wall(self):
        return self.terrein == '#'

    @property
    @lru_cache(None)
    def is_external_wall(self):
        if not self.wall:
            return False

        #周囲の中で壁でないタイルがあるか？
        for p in [Point(self.point.x + s, self.point.y + t)
                for t in (-1, 0, 1) for s in (-1, 0, 1)
                if (s, t) != (0, 0)]:
            if p in self.stage.tiles and not self.stage.tiles[p].wall:
                return True
        else:
            return False

    @lru_cache(None)
    def get_wall_shape(self):
        if not self.wall:
            raise

        around = []
        for p in [Point(self.point.x + s, self.point.y + t)
                for t in (-1, 0, 1) for s in (-1, 0, 1)]:
            if p in self.stage.tiles and self.stage.tiles[p].is_external_wall:
                around.append(1)
            else:
                around.append(0)
        around = [s & t for s, t in zip(around, [0, 1, 0, 1, 1, 1, 0, 1, 0])]

        try:
            return WALL_CHARS[tuple(around)]
        except KeyError:
            return ' '

    # 各種プロパティ

    @property
    def char(self):
        if self.terrein in ('#'):
            return self.get_wall_shape()
        elif self.terrein in ('.'):
            return chr(175)

    @property
    def fgcolor(self):
        if self.terrein in ('#', '.'):
            return COLOR_COMMENT
        else:
            return COLOR_FORE

    @property
    def passable(self):
        if self.terrein in ('#'):
            return False
        elif self.terrein in ('.'):
            return True

    @property
    def transparent(self):
        if self.terrein in ('#'):
            return False
        elif self.terrein in ('.'):
            return True

# ユニット

class Unit(object):

    def __init__(self):
        self.wait = 0
        self.point = None
        self.stage = None

    def take_turn(self):
        return 1

    def move(self, point):
        if point in self.stage.tiles and self.stage.is_passable(point):
            self.point = point
            # if hasattr(self, 'compute_fov'):
            #     self.compute_fov()
            return True
        else:
            return False

    def displace(self, point):
        return self.move(Point(self.point.x + point.x, self.point.y + point.y))

    def remove(self):
        self.stage.units.remove(self)
        if self in gv.selecteds:
            gv.selecteds.remove(self)
        if gv.focused is self:
            gv.focused = None

class Item(Unit):

    def __init__(self, char, fgcolor):
        self.char = char
        self.fgcolor = fgcolor
        self.passable = True
        self.transparent = True
        self.possessor = None
        super().__init__()

    def remove(self):
        gv.count['item'] -= 1
        gv.messages.append(('Item is collected.', self.fgcolor))
        if self.possessor:
            self.possessor.item = None
        super().remove()

class Home(Unit):

    def __init__(self, char, fgcolor):
        self.char = char
        self.fgcolor = fgcolor
        self.passable = True
        self.transparent = True
        super().__init__()

    def take_turn(self):
        super().take_turn()
        for u in [u for u in self.stage.units
                if isinstance(u, Item) and u.point == self.point]:
            u.remove()
        for u in [u for u in self.stage.units
                if isinstance(u, Allie) and u.point == self.point]:
            import random
            u.move(random.choice([p for p in ALL_POINTS if 1 <= distance(u.point, p) <= 1.5]))
            if u.destination == self.point:
                u.destination = None
        return 1

class Fighter(Unit):

    def __init__(self, fgcolor, team, hp, cure, power, reach=1.5):
        self.fgcolor = fgcolor
        self.team = team  # 味方は正の数、敵は負の数、小さいほうが攻撃優先度が高い
        self.max_hp = hp
        self.hp = hp
        self.cure = cure  # 1ターンあたりの回復量
        self.power = power  # 平均攻撃力
        self.reach = reach
        super().__init__()

    def take_turn(self):
        super().take_turn()
        self.take_damage(-self.cure)
        return 1

    @property
    def char(self):
        hp_percent = self.hp / self.max_hp
        if hp_percent <= 0:
            return '0'
        elif hp_percent >= 1:
            return '9'
        else:
            return str(int(hp_percent * 10))

    def approach(self, target):
        points = [Point(self.point.x + s, self.point.y + t)
                for t in (-1, 0, 1) for s in (-1, 0, 1)]
        points = [p for p in points if self.stage.is_passable(p)]
        if points:
            return self.move(min(points, key=lambda p: distance(p, target.point)))
        else:
            return False

    def attack(self, target):
        if target.point in self.fov and distance(self.point, target.point) <= self.reach:
            import random
            damage = round(random.gauss(self.power, self.power / 2))
            target.take_damage(damage)
            animation(target.point, '*')
            return True
        else:
            return False

    def take_damage(self, damage):
        # 負の値で回復
        self.hp -= damage
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        elif self.hp <= 0:
            self.remove()

    def compute_fov(self):
        self.fov = {Point(*t) for t in tdl.map.quickFOV(*self.point,
                callback=lambda x, y: self.stage.is_transparent(Point(x, y)), radius=2.5)}

class Allie(Fighter):

    def __init__(self, fgcolor, hp, cure, power, reach=1.5):
        self.destination = None
        self.passable = False
        self.transparent = True
        self.item = None
        super().__init__(fgcolor, 1, hp, cure, power, reach)

    def remove(self):
        gv.count['allie'] -= 1
        gv.messages.append(('Your unit is destroyed.', self.fgcolor))
        if self.item:
            self.item.possessor = None
        super().remove()

    def get(self, item):
        gv.messages.append(('Your unit picked up item.', COLOR_FORE))
        item.possessor = self
        self.item = item
        if self in gv.selecteds:
            gv.selecteds.remove(self)

    def release(self):
        gv.messages.append(('Your unit released item.', COLOR_FORE))
        self.item.possessor = None
        self.item = None

    def move(self, point):
        if self.item:
            self.item.move(point)
        return super().move(point)

    def take_turn(self):
        super().take_turn()

        def free_will():
            if self.item:
                path = self.stage.get_path(self.point, gv.home.point, (Allie, Enemy))
                if path and self.move(path[0]):
                        return 4
                else:
                    path = self.stage.get_path(self.point, gv.home.point, None)
                    if path and self.move(path[0]):
                            return 4
                return 2

            # アイテムを拾う
            items = [u for u in self.stage.units if isinstance(u, Item)
                    and u.point in self.fov and not u.possessor]
            ## 距離でソート
            items = sorted(items, key=lambda u: distance(self.point, u.point))
            item_target = items[0] if items else None

            # 敵を攻撃
            enemies = [u for u in self.stage.units if hasattr(u, 'team')
                    and ((self.team > 0) != (u.team > 0)) and u.point in self.fov]
            ## まず距離でソート
            enemies = sorted(enemies, key=lambda u: distance(self.point, u.point))
            ## 次に攻撃優先度でソート（安定ソート）
            enemies = sorted(enemies, key=lambda u: u.team)
            enemy_target = enemies[0] if enemies else None

            if item_target and item_target.point == self.point:
                self.get(item_target)
                return 2
            elif enemy_target:
                if distance(self.point, enemy_target.point) > self.reach:
                    self.approach(enemy_target)
                    return 2
                else:
                    self.attack(enemy_target)
                    return 2
            elif item_target:
                self.approach(item_target)
                return 2
            return 2

        if self.destination:
            if self.item:
                self.release()
            if (self.point == self.destination
                    or (not (gv.stage.is_passable(self.destination)
                    or gv.home.point == self.destination)
                    and distance(self.point, self.destination) < 2.5)):
                self.destination = None
            else:
                path = self.stage.get_path(self.point, self.destination, (Allie, Enemy))
                if path and self.move(path[0]):
                        return 2
                else:
                    path = self.stage.get_path(self.point, self.destination, None)
                    if path and self.move(path[0]):
                            return 2

        return free_will()

class Enemy(Fighter):
    def __init__(self, fgcolor, hp, cure, power, reach=1.5):
        self.passable = False
        self.transparent = True
        super().__init__(fgcolor, -2, hp, cure, power, reach)

    def remove(self):
        gv.count['enemy'] -= 1
        gv.messages.append(('Enemy unit is destroyed.', self.fgcolor))
        super().remove()

    def take_turn(self):
        super().take_turn()

        # 敵を攻撃
        enemies = [u for u in self.stage.units if hasattr(u, 'team')
                and ((self.team > 0) != (u.team > 0)) and u.point in self.fov]
        ## まず距離でソート
        enemies = sorted(enemies, key=lambda u: distance(self.point, u.point))
        ## 次に攻撃優先度でソート（安定ソート）
        enemies = sorted(enemies, key=lambda u: u.team)
        if enemies:
            target = enemies[0]
            if distance(self.point, target.point) > self.reach:
                self.approach(target)
                return 3
            else:
                self.attack(target)
                return 2
        else:
            return 2

class Gate(Fighter):
    def __init__(self, fgcolor, hp, cure=0):
        self.passable = False
        self.transparent = False
        super().__init__(fgcolor, -1, hp, cure, None, None)

    def remove(self):
        gv.count['gate'] -= 1
        gv.messages.append(('Gate is destroyed.', self.fgcolor))
        super().remove()

    @property
    def char(self):
        hp_percent = self.hp / self.max_hp
        if hp_percent < 0.25:
            return 'n'
        elif hp_percent < 0.5:
            return 'm'
        elif hp_percent < 0.75:
            return 'N'
        else:
            return 'M'

def render():
    import time
    from collections import defaultdict

    # 描画優先順位
    def priority(unit):
        if isinstance(unit, Fighter):
            return 0
        else:
            return 1

    # ユニット辞書の作成
    unit_dict = defaultdict(list)
    for unit in gv.stage.units:
        unit_dict[unit.point].append(unit)
    for value in unit_dict.values():
        value.sort(key=priority)

    for p in ALL_POINTS:
        gv.console.drawChar(*p, char=gv.stage.tiles[p].char, fgcolor=gv.stage.tiles[p].fgcolor)

        # ユニットの数は？
        unit_count = len(unit_dict[p])
        if unit_count:
            unit = unit_dict[p][(gv.turn // 2) % unit_count]
            gv.console.drawChar(*unit.point, char=unit.char, fgcolor=unit.fgcolor)

    # マウスホバー中
    if gv.focused:
        focused = gv.focused
        if hasattr(focused, 'destination') and focused.destination:
            gv.console.drawChar(*focused.destination, char=None, fgcolor=None,
                    bgcolor=darken(COLOR_GREEN, 0.5))
        if isinstance(focused, (Allie, Enemy)) and hasattr(focused, 'fov'):
            for point in focused.fov:
                gv.console.drawChar(*point, char=None, fgcolor=None,
                        bgcolor=darken(COLOR_COMMENT, 0.25))

    # 選択中
    for selected in gv.selecteds:
        gv.console.drawChar(*selected.point, char=None, fgcolor=None,
                bgcolor=darken(COLOR_RED, 0.5))

    message_console = tdl.Console(SCREEN_WIDTH, MESSAGE_HEIGHT)
    message_console.clear(COLOR_FORE, darken(COLOR_CURRENT, 0.5))
    status_console = tdl.Console(SCREEN_WIDTH, STATUS_HEIGHT)
    status_console.clear(COLOR_FORE, COLOR_CURRENT)

    # メッセージ表示
    try:
        for i, message in enumerate(reversed(gv.messages)):
            message_console.drawStr(0, i, message[0], darken(message[1], 0.75**i), None)
    except:
        pass
    gv.console.blit(message_console, 0, MAP_HEIGHT)

    # ステータス表示
    try:
        status = ' {0} | {1} | {2} | {3} | {4}'.format(
                gv.seed,
                time.strftime('%H:%M:%S', time.gmtime(time.clock() - gv.start_time)),
                '{0}/{1}'.format(gv.count['allie'], gv.init_count['allie']),
                '{0}/{1}'.format(gv.count['enemy'], gv.init_count['enemy']),
                '{0}/{1}'.format(gv.count['item'], gv.init_count['item']),
        )
        status_console.drawStr(0, 0, status, None, None)
    except:
        pass
    gv.console.blit(status_console, 0, MAP_HEIGHT+MESSAGE_HEIGHT)

    gv.animation_datas = [data for data in gv.animation_datas if data.fin_time > time.clock()]
    for data in gv.animation_datas:
        gv.console.drawChar(*data.point, char=data.char, fgcolor=data.fgcolor, bgcolor=data.bgcolor)

    tdl.flush()

def game_over():
    render()
    while not tdl.event.isWindowClosed():
        for event in tdl.event.get():
            pass

def main():
    import random

    def get_seed():
        loaded_seed = gv.seed_json['seed']
        available_chars = '345679ACDEFGHJKLMNPQRSTUWX'

        if isinstance(loaded_seed, str):
            loaded_seed = loaded_seed.upper()
            if (len(loaded_seed) == 4 and
                    all([c in available_chars for c in loaded_seed])):
                return loaded_seed

        new_seed = ''
        for _ in range(4):
            new_seed += random.choice(available_chars)
        return new_seed

    gv.seed = get_seed()

    gv.seed_json['history'].append(gv.seed)
    with open('seed.json', 'w') as f:
        json.dump(gv.seed_json, f, indent=4)

    gv.stage = Stage(gv.seed)

    import time
    gv.start_time = time.clock()
    gv.turn = 0

    while not tdl.event.isWindowClosed():
        now_turn = int((time.clock() - gv.start_time) / TURN_TIME)

        if now_turn > gv.turn:
            gv.turn = now_turn
            for unit in gv.stage.units:
                if hasattr(unit, 'compute_fov'):
                    unit.compute_fov()
                if unit.wait == 0:
                    unit.wait += unit.take_turn()  # take_turnは待機時間を返す
                unit.wait -= 1

        render()

        if gv.count['allie'] <= 0:
            gv.messages.append(('All your units are destroyed. *you lose*', COLOR_FORE))
            game_over()
        elif gv.count['item'] <= 0:
            gv.messages.append(('All items are collected. *you win*', COLOR_FORE))
            game_over()

        for event in tdl.event.get():
            if event.type == 'KEYDOWN':
                if event.key == 'CONTROL':
                    gv.ctrl = True
                elif event.key == 'SHIFT':
                    gv.shift = True
            elif event.type == 'KEYUP':
                if event.key == 'CONTROL':
                    gv.ctrl = False
                elif event.key == 'SHIFT':
                    gv.shift = False

            elif event.type == 'MOUSEDOWN':
                point = Point(*event.cell)
                if event.button == 'LEFT':
                    selecteds = {u for u in gv.stage.units
                            if u.point == point and isinstance(u, Allie)}
                    if selecteds:
                        if gv.ctrl:
                            gv.selecteds.update(selecteds)
                        else:
                            gv.selecteds = selecteds
                    else:
                        gv.selecteds.clear()
                elif event.button == 'RIGHT':
                    for selected in gv.selecteds:
                        selected.destination = point

            elif event.type == 'MOUSEMOTION':
                point = Point(*event.cell)
                # if point in ALL_POINTS:
                #     gv.pointed = point
                focuseds = [u for u in gv.stage.units if u.point == point]
                if focuseds:
                    gv.focused = focuseds[0]
                    if gv.shift and isinstance(gv.focused, Allie):
                        gv.selecteds.add(gv.focused)
                else:
                    gv.focused = None

main()
