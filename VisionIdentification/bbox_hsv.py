'''
Altered from bbox example on opencv documentation site 
https://docs.opencv.org/3.4/da/d0c/tutorial_bounding_rects_circles.html 
'''

import numpy as np
import cv2
import argparse 
import random as r 
import image_sizing as imgsz 
from meat import Meat 
import time

r.seed(12345)

DATA_PATH = r"C:\Users\User\Documents\Hylife 2020\Loin Feeder\Data\Output Data 07.05.2020 07-31-40\L"
THRESHOLD = 255

LOWER_MASK = np.array([0, 51, 51])
UPPER_MASK = np.array([15, 204, 255])

def get_bbox(img, threshold=THRESHOLD, draw=False, lower_mask=LOWER_MASK, upper_mask=UPPER_MASK, source="Image"):
    '''
    Returns single bounding polygon for the given middle image
    A larger threshold value will result in larger bbox
    '''
    # img = preprocess(img)
    #Masks meat 
    temp = gen_mask(img, lower_mask=lower_mask, upper_mask=upper_mask)

    #Add border to ensure full hull is created 
    temp = cv2.copyMakeBorder(temp, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    img = cv2.copyMakeBorder(img, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    bound_poly = thresh_callback(threshold, temp)

    drawing = 0

    if draw:
        drawing = draw_results(img, bound_poly, source)
        # cv2.imshow(source, drawing)

    return bound_poly, temp, drawing

def preprocess(img):
    '''
    Crops image
    Scales image
    Filters out red channel (makes contour finding easier for meats for bbox later)
    Grayscales image to reduce computation time
    '''
    ret = img.copy()
    # ret = imgsz.crop(ret)
    ret = imgsz.scale(ret)

    return ret 

def gen_mask(img, lower_mask=LOWER_MASK, upper_mask=UPPER_MASK, bitwise_and=False):
    '''
    Masks input img based off HSV colour ranges provided 
    '''
    iH, iW, _ = img.shape
    ret = img.copy()

    #Masks colour ranges provided
    hsv = cv2.cvtColor(ret, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_mask, upper_mask)
    cv2.bitwise_not(mask)

    # First erode and dilate to remove small pieces and noise
    kernel = np.ones([round(iW*0.03),round(iH*0.03)])
    refined = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    #Then dilate and erode to remove holes 
    kernel = np.ones([round(iW*0.04),round(iH*0.04)])
    refined = cv2.morphologyEx(refined, cv2.MORPH_CLOSE, kernel)
    if bitwise_and:
        return cv2.bitwise_and(ret, ret, mask=refined)
    return refined

def thresh_callback(val, img):
    '''
    Returns single convex hull of all contours of img 

    '''
    threshold = val #Threshold value for contours 
    canny_output = cv2.Canny(img, threshold, threshold * 2)
    
    contours, _ = cv2.findContours(canny_output, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if (len(contours) == 0):
        return 0

    # contours = np.concatenate(contours)
    hulls = [cv2.convexHull(contours[i]) for i in range(0, len(contours)) if cv2.contourArea(cv2.convexHull(contours[i])) > 50000]

    if (len(hulls) == 0):
        return 0

    # Removes hulls that are contained within others. This allows for multiple pieces of meat to be detected
    filt = []
    for i in range(0, len(hulls)):
        flag = True
        for j in range(0, len(hulls)):
            if (cv2.pointPolygonTest(hulls[j], (hulls[i][0][0][0], hulls[i][0][0][1]), measureDist=False) == 1):
                flag = False
            
        filt += [flag]

    ret = [hulls[i] for i in range(0, len(hulls)) if filt[i]==True]

    return ret

def draw_results(img, boundPolys, source, meat=0):
    drawing = img.copy()

    if (boundPolys != 0):
        for i in range(0, len(boundPolys)):
            #Draws convex hull
            cv2.drawContours(drawing, boundPolys, i, (31, 255, 49), 2)

            if meat != 0:
                #Draws identified lines of interest
                line_pts = meat.get_lines()
                #Red - Loin
                cv2.line(drawing, line_pts[0][0], line_pts[0][1], (0, 0, 255), thickness=3)
                #Yellow - Shoulder
                cv2.line(drawing, line_pts[1][0], line_pts[1][1], (0, 255, 255), thickness=3)
                #Blue - Ham
                cv2.line(drawing, line_pts[2][0], line_pts[2][1], (255, 0, 0), thickness=3)
                #Magenta - Shank 
                cv2.line(drawing, line_pts[3][0], line_pts[3][1], (255, 0, 255), thickness=3)

    cv2.imshow(source, drawing)

    return drawing

def n(x):
    pass

def main(input_path=DATA_PATH):
    h = [0, 180]
    s = [0, 255]
    v = [0, 255]
    hlow = 0
    hhigh = 15
    slow = 51
    shigh = 204
    vlow = 51
    vhigh = 255
    flag = False

    for i in range(110, 200):
        temp = input_path + str(i) + ".png"
        try: 
            og = preprocess(cv2.imread(temp))
            og.shape
        except:
            continue
        
        src = 'Source'
        cv2.namedWindow(src)

        # cv2.createTrackbar('H Low', src, hlow, 180, n)
        # cv2.createTrackbar('H High', src, hhigh, 180, n)
        # cv2.createTrackbar('S Low', src, slow, 255, n)
        # cv2.createTrackbar('S High', src, shigh, 255, n)
        # cv2.createTrackbar('V Low', src, vlow, 255, n)
        # cv2.createTrackbar('V High', src, vhigh, 255, n)

        while (1):
            k = cv2.waitKey(1) & 0xFF
            if (k == ord('n')):
                break
            elif (k == ord('q')):
                flag = True
                break
            # hlow = cv2.getTrackbarPos('H Low', src)
            # hhigh = cv2.getTrackbarPos('H High', src)
            # slow = cv2.getTrackbarPos('S Low', src)
            # shigh = cv2.getTrackbarPos('S High', src)
            # vlow = cv2.getTrackbarPos('V Low', src)
            # vhigh = cv2.getTrackbarPos('V High', src)

            LOWER_MASK = np.array([hlow, slow, vlow])
            UPPER_MASK = np.array([hhigh, shigh, vhigh])

            get_bbox(og, draw=True, source=src, lower_mask=LOWER_MASK, upper_mask=UPPER_MASK)

        cv2.destroyAllWindows()

        if (hlow < h[1]):
            h[1] = hlow
        if (slow < s[1]):
            s[1] = slow
        if (vlow < v[1]):
            v[1] = vlow

        if (hhigh > h[0]):
            h[0] = hhigh
        if (shigh > s[0]):
            s[0] = shigh
        if (vhigh > v[0]):
            v[0] = vhigh

        if flag:
            break

    st = ""
    st += "H: (" + str(h[1]) + "," + str(h[0]) + ")\n"
    st += "S: (" + str(s[1]) + "," + str(s[0]) + ")\n"
    st += "V: (" + str(v[1]) + "," + str(v[0]) + ")"
    print(st)

if __name__=="__main__":
    main() 