from pykinect import nui
from pykinect.nui import JointId, SkeletonTrackingState
import time
import thread
import random
import pygame
from pygame.color import THECOLORS
from pygame.locals import *
from pygame import sprite
import ctypes
import math

KINECTEVENT = pygame.USEREVENT
TIMER_EVENT = pygame.USEREVENT + 1
skeleton_to_depth_image = nui.SkeletonEngine.skeleton_to_depth_image_FLT_EPSILON = 1.192092896e-07

def post_frame(frame):
    """Get skeleton events from the Kinect device and post them into the PyGame event queue"""
    try:
        pygame.event.post(pygame.event.Event(KINECTEVENT, skeletons = frame.SkeletonData))
    except:
        # event queue full
        pass

class Brick(sprite.Sprite):
    def __init__(self, x = 50, y = 50, width = 10, height = 5):
        super (Brick, self).__init__()
        self.size = pygame.Rect(0, 0, width, height)
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.SurfaceType((width, height))
        self.color = 'white'
        pygame.draw.rect(self.image, THECOLORS['white'], self.size)

    def hit_by_ball(self, cur_ball):
        self.kill()
class Bumper(pygame.sprite.DirtySprite):
    def __init__(self, image):
        super(Bumper, self).__init__()
        self.image = image
        self.dirty = 2
        self.rect = self.source_rect = pygame.Rect(0, 0, image.get_width(), 
                                                   image.get_height())
class Ball(sprite.Sprite):
    def __init__(self, game, color = 'red', velocity = 8, size = 24, 
                 direction = math.atan2(1, .5), x = 0, y = 0):
        super(Ball, self).__init__()
        self.game = game
        self.size = size
        self.color = color
        self.image = pygame.SurfaceType((size, size))
        self.velocity = velocity
        self.direction = direction
        self.old_pos = None        
        self.rect = pygame.Rect(x, y, size, size)

    def flipDirection(self, horizontal = True):
        if horizontal:
            x = self.velocity * math.cos(self.direction)
            y = -self.velocity * math.sin(self.direction)
            direction = math.atan2(y, x)
        else:
            x = -self.velocity * math.cos(self.direction)
            y = self.velocity * math.sin(self.direction)
            direction = math.atan2(y, x)

    def update(self, *args):
        r = self.rect
        assert isinstance(r, pygame.Rect)        

        x = r.x + self.velocity * math.cos(self.direction)
        y = r.y + self.velocity * math.sin(self.direction)  

        if x >= (self.game.width - self.size) or x <= 0:
            self.flipDirection(False)
        elif y >= (self.game.height - self.size) or y <= 0:
            self.flipDirection(True)
        self.rect = pygame.Rect(int(x), int(y), self.size, self.size)
        return super(Ball, self).update(*args)

    def bounce_ball(self, hit_rect):
        clip = hit_rect.clip(self.rect)
        assert isinstance(clip, pygame.Rect)
        vel = self.velocity
        x_dist_traveled = clip.width / (math.cos(self.direction) * vel)
        y_dist_traveled = clip.height / (math.sin(self.direction) * vel)
        if abs(x_dist_traveled) < abs(y_dist_traveled):
            time_adj = x_dist_traveled
        else:
            time_adj = y_dist_traveled 
        
        if clip.left == hit_rect.left:
            self.rect.x -= math.cos(self.direction) * self.velocity * time_adj
        else:
            self.rect.x += math.cos(self.direction) * self.velocity * time_adj

        if clip.top == hit_rect.top:
            self.rect.y -= math.sin(self.direction) * self.velocity * time_adj
        else:
            self.rect.y += math.sin(self.direction) * self.velocity * time_adj
    
        self.flipDirection(clip.width < clip.height)
    def __repr__(self):
        return '<Ball %x>' % id(self)

class Player(object):
    def __init__(self, game, color = 'red'):
        self.game = game
        self.active = False
        self.old_rects = [None, None, None, None]        
        self.color = color

        self.bumper = pygame.SurfaceType((15, 40))        
        pygame.draw.rect(self.bumper, THECOLORS[color], pygame.Rect(0, 0, 15, 40))

        if self.color == 'red':
            x = self.game.blocks_across / 2 - 2
        else: 
            x = self.game.blocks_across / 2

        y = self.game.blocks_down / 2 - 1
        width = ((self.game.width / self.game.blocks_across) - 5) * 2
        height = ((self.game.height / self.game.blocks_down) - 5) * 2

        x_loc = (self.game.width / self.game.blocks_across) * x
        y_loc = (self.game.height / self.game.blocks_down) * y
    
clock = pygame.time.Clock() 
if hasattr(ctypes.pythonapi, 'Py_InitModule4'):
   Py_ssize_t = ctypes.c_int
elif hasattr(ctypes.pythonapi, 'Py_InitModule4_64'):
   Py_ssize_t = ctypes.c_int64
else:
   raise TypeError("Cannot determine type of Py_ssize_t")
_PyObject_AsWriteBuffer = ctypes.pythonapi.PyObject_AsWriteBuffer
_PyObject_AsWriteBuffer.restype = ctypes.c_int
_PyObject_AsWriteBuffer.argtypes = [ctypes.py_object,
                                  ctypes.POINTER(ctypes.c_void_p),
                                  ctypes.POINTER(Py_ssize_t)]

def surface_to_array(surface):
   buffer_interface = surface.get_buffer()
   address = ctypes.c_void_p()
   size = Py_ssize_t()
   _PyObject_AsWriteBuffer(buffer_interface,
                          ctypes.byref(address), ctypes.byref(size))
   bytes = (ctypes.c_byte * size.value).from_address(address.value)
   bytes.object = buffer_interface
   return bytes

class Game():
    def __init__(self):
        self.width = 640
        self.height = 480
        pygame.time.set_timer(TIMER_EVENT, 25)
        self.screen_lock = thread.allocate()
        self.last_kinect_event = time.clock()
        self.screen = pygame.display.set_mode((self.width, self.height), 0, 32)
        self.screen.convert()
        self.pieces_group = sprite.Group()
        pygame.display.set_caption('Python Kinect Game')
        self.screen.fill(THECOLORS["black"])
        self.background = pygame.Surface((self.width, self.height), 0, 32)
        self.background.fill(THECOLORS["black"])
        self.background.convert()
        self.video_screen = pygame.SurfaceType((self.width, self.height), 0, 32)
        self.known_players = {}
        self.ball_group = sprite.Group(
            Ball(self, 'white', direction = math.atan2(.5, 1), x = 30, y = 410))
        self.blocks_across = 10
        self.blocks_down = 10
        width = (self.width / self.blocks_across) - 5
        height = (self.height / self.blocks_down) - 5

        for y in xrange(self.blocks_down):
            for x in xrange(self.blocks_across):
                x_loc = (self.width / self.blocks_across) * x
                y_loc = (self.height / self.blocks_down) * y
                bp = Brick(x_loc, y_loc, width, height)
                bp.add(self.pieces_group)
        self.kinect = nui.Runtime()
        self.kinect.skeleton_engine.enabled = True
        self.kinect.skeleton_frame_ready += post_frame
        self.kinect.video_frame_ready += self.video_frame_ready    
        self.kinect.video_stream.open(nui.ImageStreamType.Video, 2, nui.ImageResolution.Resolution640x480, nui.ImageType.Color)
        self.kinect.camera.elevation_angle = 2

    def checkCollisionBrick(self, cur_ball):
        collisions = pygame.sprite.spritecollide(cur_ball, self.pieces_group, False)
        hit = None
        
        for collision in collisions:
            if hit is None:
                hit = collision.rect
            else:
                hit = collision.rect.union(hit)
        
            collision.hit_by_ball(cur_ball)
        if hit is not None:
            cur_ball.bounce_ball(hit)

    def do_update(self):
        if time.clock() - self.last_kinect_event > 1:
            for player in self.known_players.values():
                player.active = False

        pygame.display.set_caption('Python Kinect Game %d fps' % clock.get_fps())
        self.ball_group.update()

        for cur_ball in self.ball_group:
            assert isinstance(cur_ball, Ball)
            
            self.checkCollisionBrick(cur_ball)
        self.draw()

    def draw(self):
        """renders the entire frame"""
        for cur_player in self.known_players.values():
            cur_player.draw(self.screen, self.background)
        
        self.pieces_group.clear(self.screen, self.background)
        self.pieces_group.draw(self.screen)
        
        self.ball_group.clear(self.screen, self.background)
        self.ball_group.draw(self.screen)

    def process_kinect_event(self, e):
        self.last_kinect_event = time.clock()
        for old_player in self.known_players.values():
            old_player.active = False

        for skeleton in e.skeletons:         
            if skeleton.eTrackingState == SkeletonTrackingState.TRACKED:
                player = self.known_players.get(skeleton.dwTrackingID)
                if player is not None:
                    player.active = True
        
        for skeleton in e.skeletons:         
            if skeleton.eTrackingState == SkeletonTrackingState.TRACKED:
                player = self.known_players.get(skeleton.dwTrackingID)
                if player is None:

                    color = 'red'
                    for existing_player in self.known_players.values():
                        if existing_player.active:
                            if existing_player.color == 'red':
                                color = 'blue'
                            break
        
                    player = Player(self, color)
                    self.known_players[skeleton.dwTrackingID] = player
                
                left_hand = skeleton.SkeletonPositions[JointId.HandLeft]
                left_pos = skeleton_to_depth_image(left_hand, self.dispInfo.current_w, self.dispInfo.current_h)
                right_hand = skeleton.SkeletonPositions[JointId.HandRight]
                right_pos = skeleton_to_depth_image(left_hand, self.dispInfo.current_w, self.dispInfo.current_h)
                head = skeleton.SkeletonPositions[JointId.Head]
                head_pos = skeleton_to_color_image(head, self.dispInfo.current_w, self.dispInfo.current_h)
        
                player.update(left_pos, right_pos, head_pos, head.z)

    def play(self):
        while True:
            e = pygame.event.wait()

            if e.type == pygame.QUIT:
                break
            elif e.type == pygame.KEYUP:
                if e.key == K_SPACE and len(self.pieces_group) == 0:
                    # TODO: Start a new game!
                    print 'new game'
                    pass
            elif e.type == KINECTEVENT:
                # process e.skeletons here
                if len(self.pieces_group):
                    self.process_kinect_event(e)
            elif e.type == TIMER_EVENT:
                if not len(self.pieces_group):
                    # game is over
                    self.display_winner()
                else:
                    self.do_update()
                
                pygame.display.flip()
                clock.tick(40)

    def video_frame_ready(self, frame):
        with self.screen_lock:
            address = surface_to_array(self.video_screen)
            frame.image.copy_bits(address)
            del address
     
if __name__ == '__main__':
    # Initialize PyGame
    pygame.init()
    pygame.font.init()

    game = Game()
    game.play()