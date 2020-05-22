import time

import numpy as np 
import cv2

from sample.VisionIdentification import bbox
from sample.VisionIdentification import image_sizing
from sample.VisionIdentification import meat
from sample.Model.Robot import Robot
from sample.Model.Point import Point
from sample.PathPlanning.Path import PathFinder
from sample import GlobalParameters

DATA_PATH = r"C:\Users\User\Documents\Hylife 2020\Loin Feeder\Data\good.mp4"
model = Robot(Point(280, 600), GlobalParameters.VIDEO_SCALE)
path_finder = PathFinder()

def on_mouse(event, pX, pY, flags, param):
    if event == cv2.EVENT_LBUTTONUP:
        print("Clicked", pX, pY)

def main(data_path=DATA_PATH):
    active = False
    cap = cv2.VideoCapture(data_path)
    # out = cv2.VideoWriter(r'C:\Users\User\Documents\Hylife 2020\Loin Feeder\output11.mp4', 0x7634706d, 30, (850,830))

    win = "Window"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_mouse)

    delay = 0
    times = []
    meats = [0]
    flip_flop = False 
    counter = 0

    while(cap.isOpened()):
        start = time.time()

        ################################################
        ### Video Processing and Meat Identification ###
        ################################################
    
        _, frame = cap.read()
        
        # frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        try:
            frame = bbox.preprocess(frame)
        except:
            print("End of video")
            break

        iH, iW, _ = frame.shape
        box, mask, _ = bbox.get_bbox(frame)

        if (box != 0):
            for i in range(0, len(box)):
                if delay > 50:
                    try:
                        M = cv2.moments(box[i])
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])

                        if iH / 3 - 5 < cY and iH / 3 + 5 > cY:
                            if flip_flop:
                                meats += [meat.Meat(box[i], side="Right", center=[cX, cY])]
                            else:
                                meats += [meat.Meat(box[i], side="Left", center=[cX, cY])]
                            flip_flop = not flip_flop
                            # print("Meat detected")
                            # print(meats[-1])
                            
                            delay = 0
                    except:
                        pass
        delay += 1
        
        ########################################
        ### Path planning and Robot Movement ###
        ########################################

        ep1 = Point(625, 735, angle=90)
        ep2 = Point(250, 735, angle=90)

        if len(meats) > 3:
            if len(meats) % 2 == 0 and delay == 1:
                #First move to meat location
                sp1 = meats[-1].get_center_as_point().copy() + Point(0, GlobalParameters.CONVEYOR_SPEED * 60)
                sp2 = meats[-2].get_center_as_point().copy() + Point(0, GlobalParameters.CONVEYOR_SPEED * 60)

                model.moveMeat(sp1, sp2, ep1, ep2, 60)
                
        if model.phase != 0:
            model.update()

        ###############
        ### Display ###
        ###############        
        
        if (len(meats) != 1):
            for i in range(1, len(meats)):
                meats[i].draw(frame, color=(255, 255, 0))
        model.draw(frame)
        cv2.imshow(win, frame)         

        ################
        ### Controls ###
        ################

        for i in range(1, len(meats)):
            meats[i].step()
        counter += 1

        k = cv2.waitKey(10) & 0xFF
        if k == ord('q'):
            break
        elif k == ord('p'):
            cv2.waitKey(0)

        times += [time.time() - start]
        # out.write(frame)

    print("Average frame processing time:", np.average(times))

    cap.release()
    # out.release()
    cv2.destroyAllWindows()

if __name__=='__main__':
    main()