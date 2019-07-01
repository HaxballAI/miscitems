import pygame
import pickle
import boardanalysis

# adds antialiasing to game, makes it look SmoothAndSilky(TM)
from pygame import gfxdraw
import numpy as np
import math
import random
from scipy.stats import logistic
import pandas as pd
from pandas import DataFrame
import xlsxwriter

writer = pd.ExcelWriter('HaxballData.xlsx', engine = 'xlsxwriter')

windowwidth = 840
windowheight = 400
pitchwidth = 640
pitchheight = 260
goalsize = 110

pygame.init()
win = pygame.display.set_mode((windowwidth, windowheight))
pygame.display.set_caption("ball")

clock = pygame.time.Clock()
timeelapsed = 0
font = pygame.font.Font(None, 50)

games = []


# defines player numbers
# the first players are controlled manually
# this was added because it will end up being added anyways
# it also allows us to test the robustness of player-player collisions when there are large numbers of players
redteamsize = 1
blueteamsize = 1

# defines terminal game parameters
maxscore = 1

# game parameters for the player
playerradius = 15
playerbouncing = 0.5
playerinvmass = 0.5
playerdamping = 0.96
accel = 0.1
kickaccel = 0.07
kickstrength = 5

# game parameters for the ball
ballradius = 10
balldamping = 0.99
ballinvmass = 1
ballbouncing = 0.5

# parameters for the pitch drawing
redstart = (200, 200)
bluestart = (640, 200)
ballstart = (420, 200)
goalpostradius = 8
goalpostbouncingquotient = 0.5
goalpostborderthickness = 2
goallinethickness = 3
kickingcircleradius = 15
kickingcirclethickness = 2

# defines colors used in drawing the map
redcolour = (229, 110, 86)
bluecolour = (86, 137, 229)
ballcolour = (0, 0, 0)
goallinecolour = (199, 230, 189)
goalpostcolour = (150, 150, 150)
pitchcolour = (127, 162, 112)
bordercolour = (113, 140, 90)
kickingcirclecolour = (255, 255, 255)

# defines centre line properties
centrecircleradius = 70
centrecirclecolour = (199, 230, 189)
centrecirclethickness = 3
centrelinethickness = 3

# defines text properties
textcolour = (0, 0, 0)
textposition = (215, 25)

# defines relevant pitch coordinates for calculation
pitchcornerx = int(np.floor((windowwidth - pitchwidth) / 2))
pitchcornery = int(np.floor((windowheight - pitchheight) / 2))

goalcornery = int(np.floor((windowheight - goalsize) / 2))
y1 = pitchcornerx - 30

z1 = pitchcornerx + pitchwidth
z2 = goalcornery

a1 = y1 + 2 * ballradius
a2 = int(np.floor(goalcornery - goallinethickness / 2))

b1 = z1
b2 = int(np.floor(goalcornery - goallinethickness / 2))

# defines the movespace of a player
movespacex = [playerradius, windowwidth - playerradius]
movespacey = [playerradius, windowheight - playerradius]

# defines the movespace of a ball
ballspacex = [pitchcornerx + ballradius, pitchcornerx + pitchwidth - ballradius]
ballspacey = [pitchcornery + ballradius, pitchcornery + pitchheight - ballradius]

# defines goal width
goaly = [goalcornery, goalcornery + goalsize]

# handles player indexing
curr_idx = -1


def get_idx():
    global curr_idx
    curr_idx += 1
    return curr_idx


class player(object):

    def __init__(self, x, y, colour):

        # sets default positions
        self.defaultx = x
        self.defaulty = y
        self.idx = get_idx()

        # position vectors
        self.pos = np.array([x, y]).astype(float)

        # velocity and speed
        self.velocity = np.array([0, 0])
        self.speed = 0

        # acceleration
        self.acc = np.array([0, 0])
        self.acceleration = accel

        # player properties
        self.colour = colour
        self.kicking = False
        self.newkick = True
        self.bouncingquotient = playerbouncing
        self.radius = playerradius
        self.mass = 1 / playerinvmass

    def draw(self, win):
        x = tuple(self.pos.astype(int))[0]
        y = tuple(self.pos.astype(int))[1]

        if self.kicking == True and self.newkick == True:
            pygame.gfxdraw.filled_circle(win, x, y,
                kickingcircleradius, kickingcirclecolour)
            pygame.gfxdraw.aacircle(win, x, y,
                kickingcircleradius, kickingcirclecolour)

        else:
            pygame.gfxdraw.filled_circle(win, x, y,
                kickingcircleradius, (0,0,0))
            pygame.gfxdraw.aacircle(win, x, y,
                kickingcircleradius, (0,0,0))

        pygame.gfxdraw.filled_circle(win, x, y, playerradius-kickingcirclethickness, self.colour)
        pygame.gfxdraw.aacircle(win, x, y, playerradius-kickingcirclethickness, self.colour)


    def reset(self):

        # position vectors
        self.pos = np.array([pitchcornerx + (np.random.random_sample())*580, pitchcornery + (np.random.random_sample())*200]).astype(float)

        # velocity and speed
        self.velocity = np.array([0, 0])
        self.speed = 0

        # acceleration
        self.acc = np.array([0, 0])
        self.acceleration = accel

        # player properties
        self.kicking = False
        self.newkick = True

    def dist(self, obj):
        return np.linalg.norm(obj.pos - self.pos)

    def kickdirection(self, ball):
        return (ball.pos - self.pos) / self.dist(ball)


class ball(object):

    def __init__(self, x, y):
        # sets default positions
        self.defaultx = x
        self.defaulty = y

        # position vectors
        self.pos = np.array([x, y]).astype(float)

        # velocity and speed
        self.velocity = np.array([0.0, 0.0])
        self.speed = 0

        # acceleration
        self.acc = np.array([0.0, 0.0])
        self.acceleration = accel

        # ball properties
        self.bouncingquotient = ballbouncing
        self.radius = ballradius
        self.mass = 1 / ballinvmass

    def draw(self, win):
        x = tuple(self.pos.astype(int))[0]
        y = tuple(self.pos.astype(int))[1]

        pygame.gfxdraw.filled_circle(win, x, y, ballradius+2, (0, 0, 0))
        pygame.gfxdraw.aacircle(win, x, y, ballradius+2, (0, 0, 0))
        pygame.gfxdraw.filled_circle(win, x, y, ballradius, (255, 255, 255))
        pygame.gfxdraw.aacircle(win, x, y, ballradius, (255, 255, 255))


    def reset(self):
        # position vectors
        self.pos = np.array([pitchcornerx + (np.random.random_sample())*580, pitchcornery + (np.random.random_sample())*200]).astype(float)

        b.pos = np.array([pitchcornerx + (np.random.random_sample())*580, pitchcornery + (np.random.random_sample())*200]).astype(float)

        # velocity and speed
        self.velocity = np.array([0, 0])
        self.speed = 0

        # acceleration
        self.acc = np.array([0, 0])
        self.acceleration = accel


class goalpost(object):

    def __init__(self, x, y):
        self.pos = np.array([x, y])
        self.bouncingquotient = goalpostbouncingquotient
        self.velocity = np.array([0.0, 0.0])
        self.radius = goalpostradius

    def draw(self, win):
        x = tuple(self.pos.astype(int))[0]
        y = tuple(self.pos.astype(int))[1]

        pygame.gfxdraw.filled_circle(win, x, y, goalpostradius, (0, 0, 0))
        pygame.gfxdraw.aacircle(win, x, y, goalpostradius, (0, 0, 0))
        pygame.gfxdraw.filled_circle(win, x, y, goalpostradius-goalpostborderthickness, goalpostcolour)
        pygame.gfxdraw.aacircle(win, x, y, goalpostradius-goalpostborderthickness, goalpostcolour)



# the object for blocking the player not kicking off from entering the centre
class centrecircleblock(object):

    def __init__(self):
        self.pos = np.array([ballstart[0], ballstart[1]])
        self.radius = centrecircleradius
        self.bouncingquotient = 0
        self.velocity = [0, 0]


# converts milliseconds to hh:mm:ss
def timeformat(millis):
    ss = (millis // 1000) % 60
    mm = (millis // 60000) % 60
    hh = (millis // 3600000) % 60
    return hh, mm, ss


def redrawgamewindow():
    win.fill((0, 0, 0))

    # draws border
    pygame.draw.rect(win, bordercolour, (0, 0, windowwidth, windowheight))

    # draws pitch
    pygame.draw.rect(win, pitchcolour, (pitchcornerx, pitchcornery, pitchwidth, pitchheight))
    pygame.draw.rect(win, pitchcolour, (pitchcornerx - 30, goalcornery, 30, goalsize))
    pygame.draw.rect(win, pitchcolour, (windowwidth - pitchcornerx, goalcornery, 30, goalsize))

    # draws goal lines
    pygame.draw.rect(win, goallinecolour, (
    pitchcornerx - goallinethickness // 2, pitchcornery - goallinethickness // 2, goallinethickness,
    pitchheight + goallinethickness))
    pygame.draw.rect(win, goallinecolour, (
    windowwidth - pitchcornerx - goallinethickness // 2, pitchcornery - goallinethickness // 2, goallinethickness,
    pitchheight + goallinethickness))
    pygame.draw.rect(win, goallinecolour, (
    pitchcornerx - goallinethickness // 2, pitchcornery - goallinethickness // 2, pitchwidth + goallinethickness,
    goallinethickness))
    pygame.draw.rect(win, goallinecolour, (
    pitchcornerx - goallinethickness // 2, windowheight - pitchcornery - goallinethickness // 2,
    pitchwidth + goallinethickness, goallinethickness))

    # draws center circle
    pygame.gfxdraw.filled_circle(win, ballstart[0], ballstart[1], centrecircleradius, centrecirclecolour)
    pygame.gfxdraw.aacircle(win, ballstart[0], ballstart[1], centrecircleradius, centrecirclecolour)

    pygame.gfxdraw.filled_circle(win, ballstart[0], ballstart[1],
                            centrecircleradius-centrecirclethickness, pitchcolour)
    pygame.gfxdraw.aacircle(win, ballstart[0], ballstart[1],
                            centrecircleradius-centrecirclethickness, pitchcolour)

    pygame.draw.rect(win, centrecirclecolour,
                     (windowwidth // 2 - centrelinethickness // 2, pitchcornery, centrelinethickness, pitchheight))

    # draws environment objects
    b.draw(win)

    for obj in movingobjects:
        obj.draw(win)

    for goal in goalposts:
        goal.draw(win)


    # draws score
    string = str(redscore) + ":" + str(bluescore)
    text = font.render(string, True, (255, 255, 255))
    win.blit(text, (100, 25))

    # draws time
    timetpl = timeformat(timeelapsed)
    timestr = str(timetpl[0]).zfill(2)  + ":" + str(timetpl[1]).zfill(2)  + ":" + str(timetpl[2]).zfill(2)
    timetext = font.render(timestr, True, (255, 255, 255))
    win.blit(timetext, (600, 25))

    # determine if game is won and handles end game behaviour
#    if redscore >= maxscore:
#        text = font.render("Red Team Won", True, (255, 255, 255))
#        coord = text.get_rect(center = (windowwidth // 2, windowheight // 2))
#        win.blit(text, coord)
#        global run
#        run = False
#    elif bluescore >= maxscore:
#        text = font.render("blue Team Won", True, (255, 255, 255))
#        coord = text.get_rect(center=(windowwidth // 2, windowheight // 2))
#        win.blit(text, coord)
#        global run
#        run = False

    pygame.display.update()


# defines object-object collision
def collision(obj1, obj2):
    direction = (obj1.pos - obj2.pos)
    distance = (np.linalg.norm(direction))
    bouncingq = obj1.bouncingquotient * obj2.bouncingquotient
    centerofmass = (obj1.pos * obj1.mass + obj2.pos * obj2.mass) / (obj1.mass + obj2.mass)

    # calculates normal and tangent vectors
    collisionnormal = direction / distance
    collisiontangent = np.array([direction[1], - direction[0]]) / (np.linalg.norm(direction))

    # updates object components
    obj1normalvelocity = np.dot(np.array(obj1.velocity), collisionnormal)
    obj2normalvelocity = np.dot(np.array(obj2.velocity), collisionnormal)

    # inelastic collision formula
    obj1newnormalvelocity = (bouncingq * obj2.mass * (obj2normalvelocity - obj1normalvelocity) + obj1.mass * obj1normalvelocity + obj2.mass * obj2normalvelocity) / (obj1.mass + obj2.mass)
    obj2newnormalvelocity = (bouncingq * obj1.mass * (obj1normalvelocity - obj2normalvelocity) + obj2.mass * obj2normalvelocity + obj1.mass * obj1normalvelocity) / (obj2.mass + obj1.mass)
    obj1tangentvelocity = np.dot(np.array(obj1.velocity), collisiontangent)
    obj2tangentvelocity = np.dot(np.array(obj2.velocity), collisiontangent)

    obj1.velocity = obj1newnormalvelocity * np.array(collisionnormal) + obj1tangentvelocity * np.array(collisiontangent)
    obj2.velocity = obj2newnormalvelocity * np.array(collisionnormal) + obj2tangentvelocity * np.array(collisiontangent)

    obj1.pos = centerofmass + ((obj1.radius + obj2.radius) + bouncingq * (obj1.radius + obj2.radius - distance)) * collisionnormal * obj2.mass / (obj1.mass + obj2.mass)
    obj2.pos = centerofmass - ((obj1.radius + obj2.radius) + bouncingq * (obj1.radius + obj2.radius - distance)) * collisionnormal * obj1.mass / (obj1.mass + obj2.mass)

# defines object-goalpost collision
def collisiongoalpost(obj1, obj2):
    direction = (obj1.pos - obj2.pos)
    distance = (np.linalg.norm(direction))
    bouncingq = obj1.bouncingquotient * obj2.bouncingquotient

    # calculates normal and tangent vectors
    collisionnormal = direction / distance
    collisiontangent = np.array([direction[1], - direction[0]]) / (np.linalg.norm(direction))

    # updates components
    obj1normalvelocity = np.dot(np.array(obj1.velocity), collisionnormal)
    obj2normalvelocity = np.dot(np.array(obj2.velocity), collisionnormal)
    velocityafter = (obj1normalvelocity + obj2normalvelocity) * bouncingq * 2

    obj1tangentvelocity = np.dot(np.array(obj1.velocity), collisiontangent)
    obj2tangentvelocity = np.dot(np.array(obj2.velocity), collisiontangent)

    obj1.velocity = - velocityafter * np.array(collisionnormal) + obj1tangentvelocity * np.array(collisiontangent)
    obj2.velocity = velocityafter * np.array(collisionnormal) + obj2tangentvelocity * np.array(collisiontangent)

    obj2.pos = obj1.pos - collisionnormal * (obj1.radius + obj2.radius)



# handles kick interaction
def kick(obj1, ball):
    ball.velocity = np.array(ball.velocity) + kickstrength * ballinvmass * obj1.kickdirection(ball)

# resets the map
def resetmap():
    for obj in movingobjects:
        obj.reset()
    kickedoff = False


# handles players and movespace
def keep_player_in_movespace(player):
    # should keep things on board
    if player.pos[0] <= movespacex[0] or player.pos[0] >= movespacex[1]:
        player.velocity[0] = 0
        if player.pos[0] <= movespacex[0]:
            player.pos[0] = movespacex[0]
        if player.pos[0] >= movespacex[1]:
            player.pos[0] = movespacex[1]
    if player.pos[1] <= movespacey[0] or player.pos[1] >= movespacey[1]:
        player.velocity[1] = 0
        if player.pos[1] <= movespacey[0]:
            player.pos[1] = movespacey[0]
        if player.pos[1] >= movespacey[1]:
            player.pos[1] = movespacey[1]


# handles balls and movespace
def keep_ball_in_movespace(ball):
    if ball.pos[0] <= ballspacex[0] or ball.pos[0] >= ballspacex[1]:
        if ball.pos[1] >= goaly[0] and ball.pos[1] <= goaly[1]:
            pass
        else:
            ball.velocity[0] = - 0.5 * ball.velocity[0]
            if ball.pos[0] <= ballspacex[0]:
                ball.pos[0] = ballspacex[0] + (ballspacex[0] - ball.pos[0]) / 2

            if ball.pos[0] >= ballspacex[1]:
                ball.pos[0] = ballspacex[1] + (ballspacex[1] - ball.pos[0]) / 2
    if ball.pos[1] <= ballspacey[0] or b.pos[1] >= ballspacey[1]:
        ball.velocity[1] = - 0.5 * b.velocity[1]
        if ball.pos[1] <= ballspacey[0]:
            ball.pos[1] = ballspacey[0] + (ballspacey[0] - ball.pos[1]) / 2
        if ball.pos[1] >= ballspacey[1]:
            ball.pos[1] = ballspacey[1] + (ballspacey[1] - ball.pos[1]) / 2


# keeps players not kicking off away from the centre at the start of the game
def keepoutofcentre(blocked):
    vector = np.array([centreblock.pos[0] - blocked.pos[0], centreblock.pos[1] - blocked.pos[1]])
    distance = np.linalg.norm(vector)
    if distance <= centreblock.radius + blocked.radius:
        blocked.pos[0] = centreblock.pos[0] - vector[0] / np.linalg.norm(vector)
        blocked.pos[1] = centreblock.pos[1] - vector[1] / np.linalg.norm(vector)
        collisiongoalpost(centreblock, blocked)
        centreblock.pos[0] = int(centreblock.pos[0])
        centreblock.pos[1] = int(centreblock.pos[1])

# initialises players
reds = []
blues = []

# for now, players are distributed evenly along the starting point as a proof of concept
for i in range(redteamsize):
    reds.append(
        player(redstart[0] + 0 * np.random.uniform(-1, 1), redstart[1] + 0 * np.random.uniform(-1, 1), redcolour))

for i in range(blueteamsize):
    blues.append(
        player(bluestart[0] + 0 * np.random.uniform(-1, 1), bluestart[1] + 0 * np.random.uniform(-1, 1), bluecolour))

b = ball(ballstart[0], ballstart[1])

# initialises goalposts
redgoalpost1 = goalpost(pitchcornerx, goalcornery)
redgoalpost2 = goalpost(pitchcornerx, goalcornery + goalsize)
bluegoalpost1 = goalpost(windowwidth - pitchcornerx, goalcornery)
bluegoalpost2 = goalpost(windowwidth - pitchcornerx, goalcornery + goalsize)

# initialises object blocking centre
centreblock = centrecircleblock()

# collects objects into useful groups
players = reds + blues
movingobjects = players + [b]
goalposts = [redgoalpost1, redgoalpost2, bluegoalpost1, bluegoalpost2]

# initialises scores
bluescore = 0
redscore = 0

# for kickoff
kickedoff = True
redlastgoal = False

frames = 0
gamedata = []
movedata = []
redstate = []
bluestate = []

def data(x,y): return games[math.floor(x/50)][0][math.floor(y*len(games[math.floor(x/50)][0]))]

run = True
while run:
    timeelapsed += clock.tick(60)
    frames += 1
    oldredstate = redstate
    oldbluestate = bluestate
    redstate = np.array([(reds[0].pos[0] - 15)*2 / (windowwidth - 30) - 1, (reds[0].pos[1] - 15)*2 / (windowheight - 30) - 1, (blues[0].pos[0] - reds[0].pos[0]) / (windowwidth - 30), (blues[0].pos[1] - reds[0].pos[1]) / (windowheight - 30), (b.pos[0] - reds[0].pos[0]) / (windowwidth - 25), (b.pos[1] - reds[0].pos[1]) / (windowheight - 25)])
    bluestate = np.array([(windowwidth - blues[0].pos[0] - 15)*2 / (windowwidth - 30) - 1, (blues[0].pos[1] - 15)*2 / (windowheight - 30) - 1, (blues[0].pos[0] - reds[0].pos[0]) / (windowwidth - 30), (reds[0].pos[1] - blues[0].pos[1]) / (windowheight - 30), (blues[0].pos[0] - b.pos[0]) / (windowwidth - 25), (b.pos[1] - blues[0].pos[1]) / (windowheight - 25)])

    fps = clock.get_fps()
    #print(frames / timeelapsed)
    #print(redinput)

    redinput = []
    blueinput = []
    if frames > 1:
        redintermediate = [redstate, redstate - oldredstate]
    else:
        redintermediate = [redstate,[0,0,0,0,0,0]]

    if frames > 1:
        blueintermediate = [bluestate, bluestate - oldbluestate]
    else:
        blueintermediate = [bluestate,[0,0,0,0,0,0]]

    for sublist in redintermediate:
        for item in sublist:
            redinput.append(item)

    for sublist in blueintermediate:
        for item in sublist:
            blueinput.append(item)



    gamestate = [reds[0].pos[0], reds[0].pos[1], blues[0].pos[0], blues[0].pos[1], b.pos[0], b.pos[1]]
    gamedata.append(redinput)
    gamedata.append(blueinput)


    # blocks the player that isn't kicking off from entering the circle/ other half
    if kickedoff == False:
        if redlastgoal == True:
            for i in range(len(reds)):

                if reds[i].pos[0] >= windowwidth // 2 - playerradius:
                    reds[i].velocity[0] = 0
                    reds[i].pos[0] = windowwidth // 2 - playerradius

                keepoutofcentre(reds[i])
        else:
            for i in range(len(blues)):

                if blues[i].pos[0] <= windowwidth // 2 + playerradius:
                    blues[i].velocity[0] = 0
                    blues[i].pos[0] = windowwidth // 2 + playerradius

                keepoutofcentre(blues[i])

    # handles the key events
    keys = pygame.key.get_pressed()

    redchoice = [0]
    bluechoice = [0]
    # red movement controls
    if keys[pygame.K_a]:
        if keys[pygame.K_w]:
            reds[0].acc = np.array([-1.0, -1.0]) / (2) ** (1 / 2)
            redchoice[0] = 5
        elif keys[pygame.K_s]:
            reds[0].acc = np.array([-1.0, 1.0]) / (2) ** (1 / 2)
            redchoice[0] = 1
        else:
            reds[0].acc = np.array([-1.0, 0.0])
            redchoice[0] = 3

    elif keys[pygame.K_d]:
        if keys[pygame.K_w]:
            reds[0].acc = np.array([1.0, -1.0]) / (2) ** (1 / 2)
            redchoice[0] = 9
        elif keys[pygame.K_s]:
            reds[0].acc = np.array([1.0, 1.0]) / (2) ** (1 / 2)
            redchoice[0] = 13
        else:
            reds[0].acc = np.array([1.0, 0.0])
            redchoice[0] = 11

    elif keys[pygame.K_w]:
        reds[0].acc = np.array([0.0, -1.0])
        redchoice[0] = 7

    elif keys[pygame.K_s]:
        reds[0].acc = np.array([0.0, 1.0])
        redchoice[0] = 15
    else:
        reds[0].acc = np.array([0.0, 0.0])
        redchoice[0] = 17
    if keys[pygame.K_v]:
        reds[0].kicking = True
        redchoice[0] -= 1
    else:
        reds[0].kicking = False
        reds[0].newkick = True

    # blue movement controls
    if keys[pygame.K_LEFT]:
        if keys[pygame.K_UP]:
            blues[0].acc = np.array([- 1.0, - 1.0]) / (2) ** (1 / 2)
            bluechoice[0] = 9
        elif keys[pygame.K_DOWN]:
            blues[0].acc = np.array([- 1.0, 1.0]) / (2) ** (1 / 2)
            bluechoice[0] = 13
        else:
            blues[0].acc = np.array([- 1.0, 0.0])
            bluechoice[0] = 11

    elif keys[pygame.K_RIGHT]:
        if keys[pygame.K_UP]:
            blues[0].acc = np.array([1.0, - 1.0]) / (2) ** (1 / 2)
            bluechoice[0] = 5
        elif keys[pygame.K_DOWN]:
            blues[0].acc = np.array([1.0, 1.0]) / (2) ** (1 / 2)
            bluechoice[0] = 1
        else:
            blues[0].acc = np.array([1.0, 0.0])
            bluechoice[0] = 3

    elif keys[pygame.K_UP]:
        blues[0].acc = np.array([0.0, -1.0])
        bluechoice[0] = 7

    elif keys[pygame.K_DOWN]:
        blues[0].acc = np.array([0.0, 1.0])
        bluechoice[0] = 15

    else:
        blues[0].acc = np.array([0.0, 0.0])
        bluechoice[0] = 17

    if keys[pygame.K_RCTRL]:
        blues[0].kicking = True
        bluechoice[0] -= 1
    else:
        blues[0].kicking = False
        blues[0].newkick = True
    movedata.append(redchoice[0])
    movedata.append(bluechoice[0])
    # moves the players
    for player in players:
        if player.kicking == True and player.newkick == True:
            player.velocity = np.array(player.velocity) + player.acc * kickaccel
        else:
            player.velocity = np.array(player.velocity) + player.acc * player.acceleration

        player.velocity = player.velocity * playerdamping
        player.pos += player.velocity

    # moves the ball
    b.velocity = np.array(b.velocity) * balldamping
    b.pos += b.velocity

    # should keep things on board
    for player in players:
        keep_player_in_movespace(player)

    keep_ball_in_movespace(b)

    # handles player-ball collisions
    for player in players:
        if player.dist(b) <= playerradius + ballradius:
            collision(b, player)

    # checks for movingobject-goal collisions
    for thing in movingobjects:
        for goalpost in goalposts:
            vector = goalpost.pos - thing.pos
            distance = np.linalg.norm(vector)
            if distance <= goalpostradius + thing.radius:
                thing.pos = goalpost.pos - vector / np.linalg.norm(vector)
                collisiongoalpost(goalpost, thing)

    # checks for player-player collision
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            distance = players[i].dist(players[j])
            if players[i].idx != players[j].idx and distance <= 2 * playerradius:
                collision(players[i], players[j])

    # handles kicks
    for player in players:
        if player.dist(b) <= playerradius + ballradius + 4:

            kickedoff = True

            if player.kicking == True and player.newkick == True:
                kick(player, b)
                player.newkick = False
            elif player.kicking == False:
                player.newkick = True


    # updates score
    if b.pos[0] <= pitchcornerx:
        if len(games) > 99:
            del games[0]
        with open('gamedata.txt', 'wb') as output:
            pickle.dump(np.array(gamedata), output)
        with open('movedata.txt', 'wb') as output:
            pickle.dump(np.array(movedata), output)
        bluescore += 1
        redlastgoal = False
        randomvalues = np.random.rand(len(games) * 50)
        data = []
        errors = []
        frames = 0
        errors = []
        resetmap()
    elif b.pos[0] >= windowwidth - pitchcornerx:
        if len(games) > 99:
            del games[0]
        with open('gamedata.txt', 'wb') as output:
            pickle.dump(np.array(gamedata), output)
        with open('movedata.txt', 'wb') as output:
            pickle.dump(np.array(movedata), output)
        redscore += 1
        redlastgoal = True
        randomvalues = np.random.rand(len(games) * 50)
        data = []
        errors = []
        frames = 0
        resetmap()
    redrawgamewindow()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
