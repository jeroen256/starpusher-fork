#!/usr/bin/env python3.6
# Build for Android:
# https://github.com/renpy/pygame_sdl2
# https://github.com/renpytom/rapt-pygame-example
# ~/Documents/python/rapt $ python android.py configure ../starpusher-jeroen
# ~/Documents/python/rapt $ python android.py --launch build ../starpusher-jeroen release install
# adb logcat

# Star Pusher (a Sokoban clone)
# By Al Sweigart al@inventwithpython.com
# http://inventwithpython.com/pygame
# Released under a "Simplified BSD" license

try:
    import pygame_sdl2
    pygame_sdl2.import_as_pygame()
except ImportError:
    pass
    
import random, sys, copy, os, pygame
from pygame.locals import *
import queue
import json
import pickle
from enum import Enum

class GameStateItem(Enum):
    SELECTED_STAR_INDEX = 4

class Settings:
    """Saved current level idex, window width and height and if fullscreen"""
    def __init__(self):
        self.current_level_index = 0 # 63
        self.window_width = 0
        self.window_height = 0
        self.fullscreen = True
    def save(self):
        """Saves the settings in a file"""
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.__dict__, f, sort_keys=True, indent=4)
        except Exception as e: print("Error settings.save(): {}".format(str(e)))
    def load(self):
        """Loads the settings from a file"""
        try:
            with open('settings.json', 'r') as f:
                self.__dict__ = json.load(f)
        except Exception as e:
            print("Error settings.load(): {}".format(str(e)))
settings = Settings()
settings.load()

#FPS = 30 # frames per second to update the screen
def set_window_size(size, fullscreen = False):
    global DISPLAYSURF, WINWIDTH, WINHEIGHT, HALF_WINWIDTH, HALF_WINHEIGHT
    x, y = size
    if fullscreen: DISPLAYSURF = pygame.display.set_mode((0,0),HWSURFACE|DOUBLEBUF|FULLSCREEN)
    else: DISPLAYSURF = pygame.display.set_mode(size,HWSURFACE|DOUBLEBUF|RESIZABLE)
    x, y = pygame.display.get_surface().get_size()
    WINWIDTH = x # width of the program's window, in pixels
    WINHEIGHT = y # height in pixels
    HALF_WINWIDTH = int(x / 2)
    HALF_WINHEIGHT = int(y / 2)
    if not fullscreen: # keep original to switch back to this size when leaving fullscreen
        settings.window_width = x
        settings.window_height = y
    settings.fullscreen = fullscreen
# The total width and height of each tile in pixels.
TILEWIDTH = 50
TILEHEIGHT = 85
TILEFLOORHEIGHT = 40

CAM_MOVE_SPEED = 5 # how many pixels per frame the camera moves

# The percentage of outdoor tiles that have additional
# decoration on them, such as a tree or rock.
OUTSIDE_DECORATION_PCT = 20

BRIGHTBLUE = (  0, 170, 255)
WHITE      = (255, 255, 255)
BLACK      = (0,0,0)
BGCOLOR = BLACK
TEXTCOLOR = WHITE

UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'

def main():
    global FPSCLOCK, DISPLAYSURF, IMAGESDICT, TILEMAPPING, OUTSIDEDECOMAPPING, BASICFONT, PLAYERIMAGES, currentImage, savedGameStateObj

    # Pygame initialization and basic set up of the global variables.
    pygame.init()
    FPSCLOCK = pygame.time.Clock()

    # Because the Surface object stored in DISPLAYSURF was returned
    # from the pygame.display.set_mode() function, this is the
    # Surface object that is drawn to the actual computer screen
    # when pygame.display.update() is called.
    set_window_size((settings.window_width, settings.window_height), settings.fullscreen)
    #DISPLAYSURF = pygame.display.set_mode((WINWIDTH, WINHEIGHT),HWSURFACE|DOUBLEBUF|FULLSCREEN)

    pygame.display.set_caption('Star Pusher Fork')
    #BASICFONT = pygame.font.Font('freesansbold.ttf', 18)
    BASICFONT = pygame.font.Font("DejaVuSans.ttf", 18)

    # A global dict value that will contain all the Pygame
    # Surface objects returned by pygame.image.load().
    IMAGESDICT = {'uncovered goal': pygame.image.load('RedSelector.png'),
                  'covered goal': pygame.image.load('Selector.png'),
                  'star': pygame.image.load('Star.png'),
                  'star red': pygame.image.load('star_red.png'),
                  'corner': pygame.image.load('Wall_Block_Tall.png'),
                  'wall': pygame.image.load('Wood_Block_Tall.png'),
                  'inside floor': pygame.image.load('Plain_Block.png'),
                  'outside floor': pygame.image.load('Grass_Block.png'),
                  'title': pygame.image.load('star_title.png'),
                  'solved': pygame.image.load('star_solved.png'),
                  'princess': pygame.image.load('princess.png'),
                  'boy': pygame.image.load('boy.png'),
                  'catgirl': pygame.image.load('catgirl.png'),
                  'horngirl': pygame.image.load('horngirl.png'),
                  'pinkgirl': pygame.image.load('pinkgirl.png'),
                  'rock': pygame.image.load('Rock.png'),
                  'short tree': pygame.image.load('Tree_Short.png'),
                  'tall tree': pygame.image.load('Tree_Tall.png'),
                  'ugly tree': pygame.image.load('Tree_Ugly.png')}

    # These dict values are global, and map the character that appears
    # in the level file to the Surface object it represents.
    TILEMAPPING = {'x': IMAGESDICT['corner'],
                   '#': IMAGESDICT['wall'],
                   'o': IMAGESDICT['inside floor'],
                   ' ': IMAGESDICT['outside floor']}
    OUTSIDEDECOMAPPING = {'1': IMAGESDICT['rock'],
                          '2': IMAGESDICT['short tree'],
                          '3': IMAGESDICT['tall tree'],
                          '4': IMAGESDICT['ugly tree']}

    # PLAYERIMAGES is a list of all possible characters the player can be.
    # currentImage is the index of the player's current player image.
    currentImage = 0
    PLAYERIMAGES = [IMAGESDICT['princess'],
                    IMAGESDICT['boy'],
                    IMAGESDICT['catgirl'],
                    IMAGESDICT['horngirl'],
                    IMAGESDICT['pinkgirl']]

    startScreen() # show the title screen until the user presses a key

    # Read in the levels from the text file. See the readLevelsFile() for
    # details on the format of this file and how to make your own levels.
    levels = readLevelsFile('starPusherLevels.txt')

    savedGameStateObj = None
    try:
        with open('gameStateObj.pkl', 'rb') as f:
            savedGameStateObj = pickle.load(f)
    except Exception as e:
        print("Error loading gameStateObj.pkl: {}".format(str(e)))

    # The main game loop. This loop runs a single level, when the user
    # finishes that level, the next/previous level is loaded.
    while True: # main game loop
        # Run the level to actually start playing the game:
        result = runLevel(levels, settings.current_level_index)
        # try:
        #     result = runLevel(levels, settings.current_level_index)
        # except Exception as ex:
        #     print("Error in runLevel, retrying without savedGameStateObj: {}".format(str(ex)))
        savedGameStateObj = None
        if result in ('solved', 'next'):
            # Go to the next level.
            settings.current_level_index += 1
            if settings.current_level_index >= len(levels):
                # If there are no more levels, go back to the first one.
                settings.current_level_index = 0
        elif result == 'back':
            # Go to the previous level.
            settings.current_level_index -= 1
            if settings.current_level_index < 0:
                # If there are no previous levels, go to the last one.
                settings.current_level_index = len(levels)-1
        elif result == 'reset':
            pass # Do nothing. Loop re-calls runLevel() to reset the level

def runLevel(levels, levelNum):
    global currentImage, gameStateObj
    levelObj = levels[levelNum]
    gameStateObj = copy.deepcopy(levelObj['startState'])
    if savedGameStateObj != None: gameStateObj = savedGameStateObj
    mapObj = decorateMap(levelObj['mapObj'], gameStateObj['player'])
    mapNeedsRedraw = True # set to True to call drawMap()
    mapWidth = len(mapObj) * TILEWIDTH
    mapHeight = (len(mapObj[0]) - 1) * TILEFLOORHEIGHT + TILEHEIGHT
    MAX_CAM_X_PAN = abs(HALF_WINHEIGHT - int(mapHeight / 2)) + TILEWIDTH
    MAX_CAM_Y_PAN = abs(HALF_WINWIDTH - int(mapWidth / 2)) + TILEHEIGHT

    levelIsComplete = False
    # Track how much the camera has moved:
    cameraOffsetX = 0
    cameraOffsetY = 0
    # Track if the keys to move the camera are being held down:
    cameraUp = False
    cameraDown = False
    cameraLeft = False
    cameraRight = False

    playerMoveTo = None
    mousex = 0
    mousey =0
    mouseTileX = 0
    mouseTileY = 0
    TILEHEIGHTREAL = TILEHEIGHT - TILEFLOORHEIGHT
    jump = 0
    gameStateObjHistory = []
    gameStateObjRedoList = []
    while True: # main game loop
        # Reset these variables:
        #playerMoveTo = None
        playerMoveRepeat = 1
        keyPressed = False
        isRedo = False
        isUndo = False

        for event in pygame.event.get(): # event handling loop
            if event.type == QUIT:
                # Player clicked the "X" at the corner of the window.
                terminate()
            elif event.type==VIDEORESIZE:
                mapNeedsRedraw = True
                set_window_size(event.dict['size'])
                MAX_CAM_X_PAN = abs(HALF_WINHEIGHT - int(mapHeight / 2)) + TILEWIDTH
                MAX_CAM_Y_PAN = abs(HALF_WINWIDTH - int(mapWidth / 2)) + TILEHEIGHT
            if event.type == pygame.MOUSEBUTTONUP:
                mapNeedsRedraw = True
                # if y < int(WINHEIGHT / 3): playerMoveTo = UP
                # elif y > int(WINHEIGHT / 3 * 2): playerMoveTo = DOWN
                # else:
                #     if x < int(WINWIDTH / 2): playerMoveTo = LEFT
                #     else: playerMoveTo = RIGHT
                mousex, mousey = pygame.mouse.get_pos()
                cameraOffsetX_tiles = 0 if cameraOffsetX == 0 else cameraOffsetX / TILEWIDTH
                cameraOffsetY_tiles = 0 if cameraOffsetY == 0 else cameraOffsetY / TILEFLOORHEIGHT
                mouseTileX = (0 if mousex - HALF_WINWIDTH == 0 else (mousex - HALF_WINWIDTH) / TILEWIDTH)  + len(mapObj) / 2 - .5 - cameraOffsetX_tiles
                mouseTileY = (mousey - HALF_WINHEIGHT) / (TILEFLOORHEIGHT) + len(mapObj[0]) / 2 - .5 - cameraOffsetY_tiles
                mouseTileX = int(round(mouseTileX, 0))
                mouseTileY = int(round(mouseTileY, 0))
                mouseTile = (mouseTileX, mouseTileY)
                if not isBlocked(mapObj, gameStateObj, mouseTileX, mouseTileY):
                    if gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] != None: # push star
                        selectedStar = gameStateObj['stars'][gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]]
                        distance, player = pushStar(mapObj, gameStateObj, selectedStar, mouseTile) or (None, None)
                        if distance != None and distance > 0:
                            jump = distance
                            gameStateObj['stepCounter'] += distance
                            gameStateObj['player'] = player
                            # Move the star.
                            gameStateObj['stars'][gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]] = mouseTile
                    else: # teleport
                        gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] = None
                        # Create mesh, draw current location of stars:
                        mesh = copy.deepcopy(mapObj)
                        for star_x, star_y in gameStateObj['stars']: mesh[star_x][star_y] = "$"
                        distance = BFS(mesh, gameStateObj['player'], mouseTile)
                        if not distance == None and distance > 0:
                            jump = distance
                            gameStateObj['stepCounter'] += distance
                            gameStateObj['player'] = mouseTile
                        else: jump = 0
                elif mouseTile in gameStateObj['stars']:
                    # select or unselect star
                    mouseTileStarIndex = gameStateObj['stars'].index(mouseTile)
                    if mouseTileStarIndex == gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]:
                        gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] = None
                    else: 
                        # see if player could walk to it
                        mesh = copy.deepcopy(mapObj)
                        for star_x, star_y in gameStateObj['stars']: 
                            if not (star_x == mouseTileX and star_y == mouseTileY): mesh[star_x][star_y] = "$"
                        distance = BFS(mesh, gameStateObj['player'], mouseTile)
                        if not distance == None:
                            gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] = mouseTileStarIndex
                else: # click on wall
                    if gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] != None:
                        gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] = None
            elif event.type == KEYDOWN:
                mapNeedsRedraw = True
                keyPressed = True
                if event.key == K_z:
                    if (pygame.key.get_mods() & KMOD_CTRL) and (pygame.key.get_mods() & KMOD_SHIFT): # redo
                        if len(gameStateObjRedoList) > 0:
                            gameStateObj = gameStateObjRedoList.pop()
                            isRedo = True
                    elif (pygame.key.get_mods() & KMOD_CTRL): # undo
                        if len(gameStateObjHistory) > 1:
                            gameStateObjRedoList.append(gameStateObj)
                            gameStateObjHistory.pop()
                            gameStateObj = gameStateObjHistory.pop()
                            isUndo = True
                elif event.key == K_f:
                    set_window_size((settings.window_width, settings.window_height), not settings.fullscreen)
                    MAX_CAM_X_PAN = abs(HALF_WINHEIGHT - int(mapHeight / 2)) + TILEWIDTH
                    MAX_CAM_Y_PAN = abs(HALF_WINWIDTH - int(mapWidth / 2)) + TILEHEIGHT
                elif event.key == K_a: cameraLeft = True # Set the camera move mode.
                elif event.key == K_d: cameraRight = True
                elif event.key == K_w: cameraUp = True
                elif event.key == K_s: cameraDown = True
                elif event.key == K_n: return 'next'
                elif event.key == K_b: return 'back'
                elif event.key == K_ESCAPE: terminate() # Esc key quits.
                elif event.key == K_BACKSPACE: return 'reset' # Reset the level.
                #elif event.key == K_AC_BACK: return 'reset' # Reset the level.
                elif event.key == K_p:
                    currentImage += 1 # Change the player image to the next one.
                    if currentImage >= len(PLAYERIMAGES): currentImage = 0
                elif event.key == K_LEFT: playerMoveTo = LEFT
                elif event.key == K_RIGHT: playerMoveTo = RIGHT
                elif event.key == K_UP: playerMoveTo = UP
                elif event.key == K_DOWN: playerMoveTo = DOWN
                if playerMoveTo != None:
                    if (pygame.key.get_mods() & KMOD_CTRL): playerMoveRepeat = 5
                    elif (pygame.key.get_mods() & KMOD_SHIFT): playerMoveRepeat = 100

            elif event.type == KEYUP:
                if event.key == K_a: cameraLeft = False # Unset the camera move mode.
                elif event.key == K_d: cameraRight = False
                elif event.key == K_w: cameraUp = False
                elif event.key == K_s: cameraDown = False
                elif event.key == K_UP or event.key == K_DOWN or event.key == K_LEFT or event.key == K_RIGHT:
                    playerMoveTo = None

        if keyPressed == False and (pygame.key.get_mods() & KMOD_ALT) == False: 
            playerMoveTo = None

        if playerMoveTo != None and not levelIsComplete:
            # If the player pushed a key to move, make the move
            # (if possible) and push any stars that are pushable.
            countJump = True if playerMoveRepeat > 1 else False
            if countJump: jump = 0
            while playerMoveRepeat > 0:
                playerMoveRepeat -= 1
                moved = makeMove(mapObj, gameStateObj, playerMoveTo)
                if moved:
                    # increment the step counter.
                    gameStateObj['stepCounter'] += 1
                    mapNeedsRedraw = True
                    if countJump: jump += 1
                else: playerMoveRepeat = 0

        if mapNeedsRedraw:
            if isLevelFinished(levelObj, gameStateObj):
                # level is solved, we should show the "Solved!" image.
                levelIsComplete = True
                keyPressed = False

        if len(gameStateObjHistory) == 0 \
            or gameStateObjHistory[len(gameStateObjHistory)-1]['player'] != gameStateObj['player'] \
            or gameStateObjHistory[len(gameStateObjHistory)-1][GameStateItem.SELECTED_STAR_INDEX.name] != gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]:
            gameStateObjHistory.append(copy.deepcopy(gameStateObj))
            if not isRedo and not isUndo and gameStateObjRedoList != []:
                gameStateObjRedoList = []
        if(len(gameStateObjHistory) > 300): 
            for i in range(len(gameStateObjHistory) - 300):
                gameStateObjHistory.pop(0)

        DISPLAYSURF.fill(BGCOLOR)

        if mapNeedsRedraw:
            mapSurf = drawMap(mapObj, gameStateObj, levelObj['goals'])
            mapNeedsRedraw = False

        if cameraUp and cameraOffsetY < MAX_CAM_X_PAN:
            cameraOffsetY += CAM_MOVE_SPEED
        elif cameraDown and cameraOffsetY > -MAX_CAM_X_PAN:
            cameraOffsetY -= CAM_MOVE_SPEED
        if cameraLeft and cameraOffsetX < MAX_CAM_Y_PAN:
            cameraOffsetX += CAM_MOVE_SPEED
        elif cameraRight and cameraOffsetX > -MAX_CAM_Y_PAN:
            cameraOffsetX -= CAM_MOVE_SPEED

        # Adjust mapSurf's Rect object based on the camera offset.
        mapSurfRect = mapSurf.get_rect()
        mapSurfRect.center = (HALF_WINWIDTH + cameraOffsetX, HALF_WINHEIGHT + cameraOffsetY)

        # Draw mapSurf to the DISPLAYSURF Surface object.
        DISPLAYSURF.blit(mapSurf, mapSurfRect)

        levelSurf = BASICFONT.render('Level %s of %s' % (levelNum + 1, len(levels)), 1, TEXTCOLOR)
        levelRect = levelSurf.get_rect()
        levelRect.bottomleft = (20, WINHEIGHT - 10)
        DISPLAYSURF.blit(levelSurf, levelRect)
        stepSurf = BASICFONT.render('Steps: {}{}'.format(gameStateObj['stepCounter'], "" if jump < 2 else " +"+str(jump)), 1, TEXTCOLOR)
        stepRect = stepSurf.get_rect()
        stepRect.bottomleft = (20, WINHEIGHT - 60)
        DISPLAYSURF.blit(stepSurf, stepRect)
        debugSurf = BASICFONT.render('Player {} {}, Mouse {} {} ({} {}), Map {} {}, Camera: {} {}'.format(gameStateObj['player'][0], gameStateObj['player'][1], mouseTileX, mouseTileY, mousex, mousey, len(mapObj), len(mapObj[0]), cameraOffsetX, cameraOffsetY), 1, TEXTCOLOR)
        debugRect = debugSurf.get_rect()
        debugRect.bottomleft = (20, WINHEIGHT - 35)
        #DISPLAYSURF.blit(debugSurf, debugRect)

        if levelIsComplete:
            # is solved, show the "Solved!" image until the player
            # has pressed a key.
            solvedRect = IMAGESDICT['solved'].get_rect()
            solvedRect.center = (HALF_WINWIDTH, HALF_WINHEIGHT)
            DISPLAYSURF.blit(IMAGESDICT['solved'], solvedRect)

            if keyPressed:
                return 'solved'

        pygame.display.update() # draw DISPLAYSURF to the screen.
        FPSCLOCK.tick()

def pushStar(mapObj, gameStateObj, src, dest):
    """returns tuple (stepCount, player position) if star can be pushed to destination, otherwise returns None"""
    src_x, src_y = src
    mesh = copy.deepcopy(mapObj)
    for star_x, star_y in gameStateObj['stars']:
        if not (star_x == src_x and star_y == src_y): mesh[star_x][star_y] = "$" # draw all stars accept the selected one
    if dest == None: # see already if src adjoining cell can be reached by player
        return None
    dest_x, dest_y = dest
    if mesh[dest_x][dest_y] != 'o': return None # inside floor
    visited = set() # keep track of visited cells
    visited.add(src) # Mark the source cell as visited
    q = queue.Queue() # list to hold for each point: point currently holding the selected star, stepCount, player position
    q.put((src, 0, gameStateObj['player'])) # 0 steps to reach src
    while not q.empty(): # Do a BFS starting from source cell
        (point_x, point_y), distance, (player_x, player_y) = q.get()
        # If we have reached the destination cell, we are done..
        if point_x == dest_x and point_y == dest_y: return (distance, (player_x, player_y))
        # Check current cell and add neighboring cells to the queue
        rowNum = [-1, 0, 0, 1]
        colNum = [0, -1, 1, 0]
        for i in range(4):
            row = point_x + rowNum[i]
            col = point_y + colNum[i]
            opposite_x = point_x - rowNum[i]
            opposite_y = point_y - colNum[i]
            if row >= 0 and row < len(mesh) and col >= 0 and col < len(mesh[0]) and mesh[row][col] == 'o' and not (row, col) in visited:
                # check if player can walk to opposite point to push it here
                mesh2 = copy.deepcopy(mesh)
                mesh2[point_x][point_y] = "$" # draw selected star in it's current position
                playerSteps = BFS(mesh2, (player_x, player_y), (opposite_x, opposite_y))
                if playerSteps != None:
                    # mark cell as visited and enqueue it
                    visited.add((row, col))
                    q.put(((row, col), distance + playerSteps + 1, (point_x, point_y)))
    return None # destination cannot be reached

def BFS(mesh, src, dest):
    """Breadth First Search, function to find the shortest path between a given source cell to a destination cell. https://www.geeksforgeeks.org/shortest-path-in-a-binary-maze/"""
    src_x, src_y = src
    dest_x, dest_y = dest
    if mesh[src_x][src_y] != 'o' or mesh[dest_x][dest_y] != 'o': return None
    visited = set() # keep track of visited cells
    visited.add(src) # Mark the source cell as visited
    q = queue.Queue() # list to hold the calculated distance for each point to dest
    q.put((src, 0)) # 0 steps to reach src
    while not q.empty(): # Do a BFS starting from source cell
        (point_x, point_y), distance = q.get()
        # If we have reached the destination cell, we are done..
        if point_x == dest_x and point_y == dest_y: return distance
        # Check current cell and add neighboring cells to the queue
        rowNum = [-1, 0, 0, 1]
        colNum = [0, -1, 1, 0]
        for i in range(4):
            row = point_x + rowNum[i]
            col = point_y + colNum[i]
            if row >= 0 and row < len(mesh) and col >= 0 and col < len(mesh[0]) and mesh[row][col] == 'o' and not (row, col) in visited:
                # mark cell as visited and enqueue it
                visited.add((row, col))
                q.put(((row, col), distance + 1))
    return None # destination cannot be reached

def isWall(mapObj, x, y):
    """Returns True if the (x, y) position on
    the map is a wall, otherwise return False."""
    if x < 0 or x >= len(mapObj) or y < 0 or y >= len(mapObj[x]):
        return False # x and y aren't actually on the map.
    elif mapObj[x][y] in ('#', 'x'):
        return True # wall is blocking
    return False


def decorateMap(mapObj, startxy):
    """Makes a copy of the given map object and modifies it.
    Here is what is done to it:
        * Walls that are corners are turned into corner pieces.
        * The outside/inside floor tile distinction is made.
        * Tree/rock decorations are randomly added to the outside tiles.

    Returns the decorated map object."""

    startx, starty = startxy # Syntactic sugar

    # Copy the map object so we don't modify the original passed
    mapObjCopy = copy.deepcopy(mapObj)

    # Remove the non-wall characters from the map data
    for x in range(len(mapObjCopy)):
        for y in range(len(mapObjCopy[0])):
            if mapObjCopy[x][y] in ('$', '.', '@', '+', '*'):
                mapObjCopy[x][y] = ' '

    # Flood fill to determine inside/outside floor tiles.
    floodFill(mapObjCopy, startx, starty, ' ', 'o')

    # Convert the adjoined walls into corner tiles.
    for x in range(len(mapObjCopy)):
        for y in range(len(mapObjCopy[0])):

            if mapObjCopy[x][y] == '#':
                if (isWall(mapObjCopy, x, y-1) and isWall(mapObjCopy, x+1, y)) or \
                   (isWall(mapObjCopy, x+1, y) and isWall(mapObjCopy, x, y+1)) or \
                   (isWall(mapObjCopy, x, y+1) and isWall(mapObjCopy, x-1, y)) or \
                   (isWall(mapObjCopy, x-1, y) and isWall(mapObjCopy, x, y-1)):
                    mapObjCopy[x][y] = 'x'

            elif mapObjCopy[x][y] == ' ' and random.randint(0, 99) < OUTSIDE_DECORATION_PCT:
                mapObjCopy[x][y] = random.choice(list(OUTSIDEDECOMAPPING.keys()))

    return mapObjCopy


def isBlocked(mapObj, gameStateObj, x, y):
    """Returns True if the (x, y) position on the map is
    blocked by a wall or star, otherwise return False."""

    if isWall(mapObj, x, y):
        return True

    elif x < 0 or x >= len(mapObj) or y < 0 or y >= len(mapObj[x]):
        return True # x and y aren't actually on the map.

    elif (x, y) in gameStateObj['stars']:
        return True # a star is blocking

    return False


def makeMove(mapObj, gameStateObj, playerMoveTo):
    """Given a map and game state object, see if it is possible for the
    player to make the given move. If it is, then change the player's
    position (and the position of any pushed star). If not, do nothing.

    Returns True if the player moved, otherwise False."""

    # Make sure the player can move in the direction they want.
    playerx, playery = gameStateObj['player']

    # This variable is "syntactic sugar". Typing "stars" is more
    # readable than typing "gameStateObj['stars']" in our code.
    stars = gameStateObj['stars']

    # The code for handling each of the directions is so similar aside
    # from adding or subtracting 1 to the x/y coordinates. We can
    # simplify it by using the xOffset and yOffset variables.
    if playerMoveTo == UP:
        xOffset = 0
        yOffset = -1
    elif playerMoveTo == RIGHT:
        xOffset = 1
        yOffset = 0
    elif playerMoveTo == DOWN:
        xOffset = 0
        yOffset = 1
    elif playerMoveTo == LEFT:
        xOffset = -1
        yOffset = 0

    # See if the player can move in that direction.
    if isWall(mapObj, playerx + xOffset, playery + yOffset):
        return False
    else:
        if (playerx + xOffset, playery + yOffset) in stars:
            # There is a star in the way, see if the player can push it.
            if not isBlocked(mapObj, gameStateObj, playerx + (xOffset*2), playery + (yOffset*2)):
                # Move the star.
                ind = stars.index((playerx + xOffset, playery + yOffset))
                stars[ind] = (stars[ind][0] + xOffset, stars[ind][1] + yOffset)
            else:
                return False
        # Move the player upwards.
        gameStateObj['player'] = (playerx + xOffset, playery + yOffset)
        return True


def startScreen():
    """Display the start screen (which has the title and instructions)
    until the player presses a key. Returns None."""

    # Position the title image.
    titleRect = IMAGESDICT['title'].get_rect()
    topCoord = 50 # topCoord tracks where to position the top of the text
    titleRect.top = topCoord
    titleRect.centerx = HALF_WINWIDTH
    topCoord += titleRect.height

    # Unfortunately, Pygame's font & text system only shows one line at
    # a time, so we can't use strings with \n newline characters in them.
    # So we will use a list with each line in it.
    instructionText = ['Push the stars over the marks.',
                       'Arrow keys to move, WASD for camera control, P to change character.',
                       'Backspace to reset level, Esc to quit.',
                       'N for next level, B to go back a level.', '',
                       'Extra: level is saved, also:',
                       'ALT: walk continuously, CTRL walk 5 steps, SHIFT walk to end of line,',
                       'Mouseclick: teleport, F: toggle fullscreen',
                       'CTRL+Z: undo, CTRL+SHIFT+Z: redo']

    # Start with drawing a blank color to the entire window:
    DISPLAYSURF.fill(BGCOLOR)

    # Draw the title image to the window:
    DISPLAYSURF.blit(IMAGESDICT['title'], titleRect)

    # Position and draw the text.
    for i in range(len(instructionText)):
        instSurf = BASICFONT.render(instructionText[i], 1, TEXTCOLOR)
        instRect = instSurf.get_rect()
        topCoord += 10 # 10 pixels will go in between each line of text.
        instRect.top = topCoord
        instRect.centerx = HALF_WINWIDTH
        topCoord += instRect.height # Adjust for the height of the line.
        DISPLAYSURF.blit(instSurf, instRect)

    while True: # Main loop for the start screen.
        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()
            elif event.type==VIDEORESIZE: 
                set_window_size(event.dict['size'])
                startScreen()
                return
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    terminate()
                elif event.key == K_f:
                    set_window_size((settings.window_width, settings.window_height), not settings.fullscreen)
                    startScreen()
                    return
                #if event.key == pygame.K_AC_BACK:
                #    terminate()

                return # user has pressed a key, so return.
            elif event.type == pygame.MOUSEBUTTONUP:
                return # user has pressed a key, so return.

        # Display the DISPLAYSURF contents to the actual screen.
        pygame.display.update()
        FPSCLOCK.tick()


def readLevelsFile(filename):
    assert os.path.exists(filename), 'Cannot find the level file: %s' % (filename)
    mapFile = open(filename, 'r')
    # Each level must end with a blank line
    content = mapFile.readlines() + ['\r\n']
    mapFile.close()

    levels = [] # Will contain a list of level objects.
    levelNum = 0
    mapTextLines = [] # contains the lines for a single level's map.
    mapObj = [] # the map object made from the data in mapTextLines
    for lineNum in range(len(content)):
        # Process each line that was in the level file.
        line = content[lineNum].rstrip('\r\n')

        if ';' in line:
            # Ignore the ; lines, they're comments in the level file.
            line = line[:line.find(';')]

        if line != '':
            # This line is part of the map.
            mapTextLines.append(line)
        elif line == '' and len(mapTextLines) > 0:
            # A blank line indicates the end of a level's map in the file.
            # Convert the text in mapTextLines into a level object.

            # Find the longest row in the map.
            maxWidth = -1
            for i in range(len(mapTextLines)):
                if len(mapTextLines[i]) > maxWidth:
                    maxWidth = len(mapTextLines[i])
            # Add spaces to the ends of the shorter rows. This
            # ensures the map will be rectangular.
            for i in range(len(mapTextLines)):
                mapTextLines[i] += ' ' * (maxWidth - len(mapTextLines[i]))

            # Convert mapTextLines to a map object.
            for x in range(len(mapTextLines[0])):
                mapObj.append([])
            for y in range(len(mapTextLines)):
                for x in range(maxWidth):
                    mapObj[x].append(mapTextLines[y][x])

            # Loop through the spaces in the map and find the @, ., and $
            # characters for the starting game state.
            startx = None # The x and y for the player's starting position
            starty = None
            goals = [] # list of (x, y) tuples for each goal.
            stars = [] # list of (x, y) for each star's starting position.
            for x in range(maxWidth):
                for y in range(len(mapObj[x])):
                    if mapObj[x][y] in ('@', '+'):
                        # '@' is player, '+' is player & goal
                        startx = x
                        starty = y
                    if mapObj[x][y] in ('.', '+', '*'):
                        # '.' is goal, '*' is star & goal
                        goals.append((x, y))
                    if mapObj[x][y] in ('$', '*'):
                        # '$' is star
                        stars.append((x, y))

            # Basic level design sanity checks:
            assert startx != None and starty != None, 'Level %s (around line %s) in %s is missing a "@" or "+" to mark the start point.' % (levelNum+1, lineNum, filename)
            assert len(goals) > 0, 'Level %s (around line %s) in %s must have at least one goal.' % (levelNum+1, lineNum, filename)
            assert len(stars) >= len(goals), 'Level %s (around line %s) in %s is impossible to solve. It has %s goals but only %s stars.' % (levelNum+1, lineNum, filename, len(goals), len(stars))

            # Create level object and starting game state object.
            gameStateObj = {'player': (startx, starty),
                            'stepCounter': 0,
                            'stars': stars, GameStateItem.SELECTED_STAR_INDEX.name: None}
            levelObj = {'width': maxWidth,
                        'height': len(mapObj),
                        'mapObj': mapObj,
                        'goals': goals,
                        'startState': gameStateObj}

            levels.append(levelObj)

            # Reset the variables for reading the next map.
            mapTextLines = []
            mapObj = []
            gameStateObj = {}
            levelNum += 1
    return levels


def floodFill(mapObj, x, y, oldCharacter, newCharacter):
    """Changes any values matching oldCharacter on the map object to
    newCharacter at the (x, y) position, and does the same for the
    positions to the left, right, down, and up of (x, y), recursively."""

    # In this game, the flood fill algorithm creates the inside/outside
    # floor distinction. This is a "recursive" function.
    # For more info on the Flood Fill algorithm, see:
    #   http://en.wikipedia.org/wiki/Flood_fill
    if mapObj[x][y] == oldCharacter:
        mapObj[x][y] = newCharacter

    if x < len(mapObj) - 1 and mapObj[x+1][y] == oldCharacter:
        floodFill(mapObj, x+1, y, oldCharacter, newCharacter) # call right
    if x > 0 and mapObj[x-1][y] == oldCharacter:
        floodFill(mapObj, x-1, y, oldCharacter, newCharacter) # call left
    if y < len(mapObj[x]) - 1 and mapObj[x][y+1] == oldCharacter:
        floodFill(mapObj, x, y+1, oldCharacter, newCharacter) # call down
    if y > 0 and mapObj[x][y-1] == oldCharacter:
        floodFill(mapObj, x, y-1, oldCharacter, newCharacter) # call up


def drawMap(mapObj, gameStateObj, goals):
    """Draws the map to a Surface object, including the player and
    stars. This function does not call pygame.display.update(), nor
    does it draw the "Level" and "Steps" text in the corner."""

    # mapSurf will be the single Surface object that the tiles are drawn
    # on, so that it is easy to position the entire map on the DISPLAYSURF
    # Surface object. First, the width and height must be calculated.
    mapSurfWidth = len(mapObj) * TILEWIDTH
    mapSurfHeight = (len(mapObj[0]) - 1) * TILEFLOORHEIGHT + TILEHEIGHT
    mapSurf = pygame.Surface((mapSurfWidth, mapSurfHeight))
    mapSurf.fill(BGCOLOR) # start with a blank color on the surface.

    selectedStar = None
    if gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] != None:
        selectedStar = gameStateObj['stars'][gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]]

    # Draw the tile sprites onto this surface.
    for x in range(len(mapObj)):
        for y in range(len(mapObj[x])):
            spaceRect = pygame.Rect((x * TILEWIDTH, y * TILEFLOORHEIGHT, TILEWIDTH, TILEHEIGHT))
            if mapObj[x][y] in TILEMAPPING:
                baseTile = TILEMAPPING[mapObj[x][y]]
            elif mapObj[x][y] in OUTSIDEDECOMAPPING:
                baseTile = TILEMAPPING[' ']

            # First draw the base ground/wall tile.
            mapSurf.blit(baseTile, spaceRect)

            if mapObj[x][y] in OUTSIDEDECOMAPPING:
                # Draw any tree/rock decorations that are on this tile.
                mapSurf.blit(OUTSIDEDECOMAPPING[mapObj[x][y]], spaceRect)
            elif (x, y) in gameStateObj['stars']:
                if (x, y) in goals:
                    # A goal AND star are on this space, draw goal first.
                    mapSurf.blit(IMAGESDICT['covered goal'], spaceRect)
                # Then draw the star sprite.
                if selectedStar != None and (x, y) == selectedStar:
                    mapSurf.blit(IMAGESDICT['star red'], spaceRect)
                else: mapSurf.blit(IMAGESDICT['star'], spaceRect)
            elif (x, y) in goals:
                # Draw a goal without a star on it.
                mapSurf.blit(IMAGESDICT['uncovered goal'], spaceRect)

            # Last draw the player on the board.
            if (x, y) == gameStateObj['player']:
                # Note: The value "currentImage" refers
                # to a key in "PLAYERIMAGES" which has the
                # specific player image we want to show.
                mapSurf.blit(PLAYERIMAGES[currentImage], spaceRect)

    return mapSurf


def isLevelFinished(levelObj, gameStateObj):
    """Returns True if all the goals have stars in them."""
    for goal in levelObj['goals']:
        if goal not in gameStateObj['stars']:
            # Found a space with a goal but no star on it.
            return False
    return True


def terminate():
    settings.save()
    try:
        with open('gameStateObj.pkl', 'wb') as f:
            pickle.dump(gameStateObj, f, pickle.HIGHEST_PROTOCOL)
    except Exception as e: print("Error saving gameStateObj: {}".format(str(e)))
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()