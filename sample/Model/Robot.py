import time

import cv2
import numpy as np

from .Point import Point
from .MainTrack import MainTrack
from .MainArm import MainArm 
from .SecondaryArm import SecondaryArm
from .Carriage import Carriage
from .. import GlobalParameters

class Robot:
    #######################
    ### Basic Functions ###
    #######################

    def __init__(self, robot_base_pt, scale):
        self.scale = scale

        # Initializes robot parts 
        self.basePt = robot_base_pt
        self.main_track = MainTrack(self.basePt, scale)
        self.main_arm = MainArm(self.main_track.otherPt, scale)
        self.secondary_arm = SecondaryArm(self.main_arm.otherPt, scale)
        self.carriage1 = Carriage(self.secondary_arm.otherPt1, scale)
        self.carriage2 = Carriage(self.secondary_arm.otherPt2, scale)

        # Points the robot follows when update() is called 
        self.follow_pt1 = self.get_current_point(1)
        self.follow_pt2 = self.get_current_point(2)

        self.phase = 0
        self.switched = False
        self.delay = 0

        self.counter = 0

    def __repr__(self):
        ret = ""
        ret += "PHASE:" + str(self.phase) + "\n\t" + "Delay:" + str(self.delay) + "\n"
        ret += self.main_track.__repr__()
        ret += self.main_arm.__repr__()
        ret += self.secondary_arm.__repr__()
        ret += self.carriage2.__repr__()
        ret += self.carriage1.__repr__()
        return ret

    ########################
    ### Helper Functions ###
    ########################

    def get_current_point(self, num):
        if num == 1:
            return Point(self.secondary_arm.otherPt1.x, self.secondary_arm.otherPt1.y, angle=self.carriage1.angle)
        elif num == 2:
            return Point(self.secondary_arm.otherPt2.x, self.secondary_arm.otherPt2.y, angle=self.carriage2.angle)

    def draw(self, canvas):
        self.main_track.draw(canvas)
        self.carriage1.draw(canvas, color=(0, 255, 0))
        self.carriage2.draw(canvas, color=(0, 0, 255))
        self.secondary_arm.draw(canvas)
        self.main_arm.draw(canvas)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        y0, dy = 30, 18
        for i, line in enumerate(self.__repr__().split('\n')):
            y = y0 + i*dy
            try:
                if (line[0] == '\t'):
                    cv2.putText(canvas, line[1:], (25, y), font, 0.6, (150, 150, 0))
                else:
                    cv2.putText(canvas, line, (15, y), font, 0.6, (255, 255, 0))
            except:
                cv2.putText(canvas, line, (15, y), font, 0.6, (255, 255, 0))

    ##########################
    ### Movement Functions ###
    ##########################

    '''
    Phase 0: Not moving >> Phase 1 on Function call 
    Phase 1: Moving to predicted meat location >> Phase 2
    Phase 2: Grabbing >> Phase 3
    Phase 3: "Step 0" -> Rotating meat according to pre-set path >> Phase 4
    Phase 4: "Step 2" -> Extending >> Phase 5
    Phase 5: Releasing >> Phase 6
    Phase 6: Moving to "Ready Position" >> Phase 0
    '''

    def moveMeat(self, s1, s2, e1, e2, delay):
        if self.phase != 0:
            print("ERROR: Robot in use")
            return False 
        
        self.s1 = s1
        self.s2 = s2
        self.e1 = e1
        self.e2 = e2
        self.phase = 1
        self.switched = True
        self.delay = delay

    def moveTo(self, pt1, pt2):
        # First moves all the components to the desired points
        self.carriage1.follow(pt1)
        self.carriage2.follow(pt2)
        self.secondary_arm.follow(pt1, pt2)
        self.main_arm.follow(self.secondary_arm.basePt, self.secondary_arm.angle)
        self.main_track.follow(self.main_arm.basePt)

        # Then restricts movements by translating constrained points back 
        self.main_track.moveBase(self.basePt)
        self.main_arm.moveBase(self.main_track.otherPt)
        self.secondary_arm.moveBase(self.main_arm.otherPt, self.main_arm.angle)
        self.carriage1.moveBase(self.secondary_arm.otherPt1, self.secondary_arm.angle)
        self.carriage2.moveBase(self.secondary_arm.otherPt2, self.secondary_arm.angle)

    def followPath(self, path1, path2, execution_time):
        self.follow1_index = 0
        self.follow2_index = 0

        self.path1 = path1
        self.path2 = path2

        self.dt1 = []
        for i in range(0, len(path1)-1):
            self.dt1 += [(path1[i + 1] - path1[i]).mag()]
        self.dt2 = []
        for i in range(0, len(path2)-1):
            self.dt2 += [(path2[i + 1] - path2[i]).mag()]

        dt1_sum = np.sum(self.dt1)
        dt2_sum = np.sum(self.dt2)

        longest = max(dt1_sum, dt2_sum)

        self.dt1 = np.divide(np.multiply(self.dt1, execution_time), longest)
        self.dt2 = np.divide(np.multiply(self.dt2, execution_time), longest)

    def update(self):
        # Phase 0: Not moving, in ready position
        if self.phase == 0:
            return False

        flag1 = self.follow_pt1.update()
        flag2 = self.follow_pt2.update()

        # Phase 1: Moving to predicted meat location
        if self.phase == 1:
            self.delay -= 1 # Delay here tracks time until meat is at start points 
            if self.switched:
                print("Start Phase 1:", self.counter)
                self.counter = 0
                self.switched = False
                self.follow_pt1.moveTo(self.s1, GlobalParameters.PHASE_1_SPEED)
                self.follow_pt2.moveTo(self.s2, GlobalParameters.PHASE_1_SPEED)
            if self.follow_pt1.steps_remaining <= 0 and self.follow_pt2.steps_remaining <= 0 and self.delay < 1: # End of step condition 
                self.switched = True 
                self.phase = 2

        # Phase 2: Grabbing (Follow meat)
        if self.phase == 2:
            self.delay -= 1
            if self.switched:
                print("Start Phase 2:", self.counter)
                self.counter = 0
                self.switched = False
                self.delay = GlobalParameters.PHASE_2_DELAY
                self.follow_pt1.moveTo(self.follow_pt1 + Point(0, self.delay * GlobalParameters.CONVEYOR_SPEED), GlobalParameters.PHASE_2_DELAY)
                self.follow_pt2.moveTo(self.follow_pt2 + Point(0, self.delay * GlobalParameters.CONVEYOR_SPEED), GlobalParameters.PHASE_2_DELAY)
            if self.delay <= 0: # End of step condition 
                self.switched = True 
                self.phase = 3

        # Phase 3: "Step 0" -> Rotating meat according to pre-set path
        if self.phase == 3:
            if self.switched:
                print("Start Phase 3:", self.counter)
                self.counter = 0
                self.switched = False
                self.followPath(GlobalParameters.PHASE_3_PATH1, GlobalParameters.PHASE_3_PATH2, GlobalParameters.PHASE_3_SPEED)
                self.follow_pt1.moveTo(GlobalParameters.PHASE_3_PATH1[0], GlobalParameters.PHASE_3_INITIAL_SPEED)
                self.follow_pt2.moveTo(GlobalParameters.PHASE_3_PATH2[0], GlobalParameters.PHASE_3_INITIAL_SPEED)
                self.follow1_index = 0
                self.follow2_index = 0

            # End condition 
            if self.follow_pt1.steps_remaining <= 0 and self.follow_pt2.steps_remaining <= 0 \
                and self.follow1_index >= len(GlobalParameters.PHASE_3_PATH1)-1 \
                    and self.follow2_index >= len(GlobalParameters.PHASE_3_PATH2)-1: 
                self.switched = True 
                self.phase = 4

                #Stops robot in its tracks
                self.follow_pt1.moveTo(self.follow_pt1, 1)
                self.follow_pt2.moveTo(self.follow_pt2, 1)

            if self.follow_pt1.steps_remaining <= 0 and self.follow1_index < len(GlobalParameters.PHASE_3_PATH1) - 1:
                self.follow1_index += 1
                self.follow_pt1.moveTo(GlobalParameters.PHASE_3_PATH1[self.follow1_index], self.dt1[self.follow1_index - 1])
            if self.follow_pt2.steps_remaining <= 0 and self.follow2_index < len(GlobalParameters.PHASE_3_PATH2) - 1:
                self.follow2_index += 1
                self.follow_pt2.moveTo(GlobalParameters.PHASE_3_PATH2[self.follow2_index], self.dt2[self.follow2_index - 1])

        # Phase 4: "Step 2" -> Extending
        if self.phase == 4:
            if self.switched:
                print("Start Phase 4:", self.counter)
                self.counter = 0
                self.switched = False
                self.follow_pt1.moveTo(self.e1, GlobalParameters.PHASE_4_SPEED)
                self.follow_pt2.moveTo(self.e2, GlobalParameters.PHASE_4_SPEED)
            if self.follow_pt1.steps_remaining <= 0 and self.follow_pt2.steps_remaining <= 0: # End of step condition 
                self.switched = True 
                self.phase = 5

        # Phase 5: Releasing
        if self.phase == 5:
            self.delay -= 1
            if self.switched:
                print("Start Phase 5:", self.counter)
                self.counter = 0
                self.switched = False
                self.delay = GlobalParameters.PHASE_5_DELAY
            if self.delay <= 0: # End of step condition 
                self.switched = True 
                self.phase = 6

        # Phase 6: Moving to "Ready Position"
        if self.phase == 6:
            self.delay -= 1
            if self.switched:
                print("Start Phase 6:", self.counter, "\n")
                self.counter = 0
                self.switched = False
                self.followPath(GlobalParameters.PHASE_6_PATH1, GlobalParameters.PHASE_6_PATH2, GlobalParameters.PHASE_6_SPEED)
                self.follow1_index = 0
                self.follow2_index = 0
                self.delay = round(np.sum(self.dt1))//3

            # End condition 
            if self.follow_pt1.steps_remaining <= 0 and self.follow_pt2.steps_remaining <= 0 \
                and self.follow1_index >= len(GlobalParameters.PHASE_6_PATH1) - 1 \
                    and self.follow2_index >= len(GlobalParameters.PHASE_6_PATH2) - 1: 
                self.switched = True 
                self.phase = 0

                #Stops robot in its tracks
                self.follow_pt1.moveTo(self.follow_pt1, 1)
                self.follow_pt2.moveTo(self.follow_pt2, 1)

            if self.follow_pt1.steps_remaining <= 0 and self.follow1_index < len(GlobalParameters.PHASE_6_PATH1) - 1:
                self.follow1_index += 1
                self.follow_pt1.moveTo(GlobalParameters.PHASE_6_PATH1[self.follow1_index], self.dt1[self.follow1_index - 1])
            if self.follow_pt2.steps_remaining <= 0 and self.follow2_index < len(GlobalParameters.PHASE_6_PATH2) - 1 and self.delay <= 0:
                self.follow2_index += 1
                self.follow_pt2.moveTo(GlobalParameters.PHASE_6_PATH2[self.follow2_index], self.dt2[self.follow2_index - 1])

        self.moveTo(self.follow_pt1, self.follow_pt2)
        self.counter += 1
        return True