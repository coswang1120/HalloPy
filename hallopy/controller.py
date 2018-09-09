"""Multi class incapsulation implementation.  """
import cv2
import logging
import numpy as np
from HalloPy.hallopy.icontroller import Icontroller
from hallopy import utils

# Create loggers.
frame_logger = logging.getLogger('frame_handler')
face_processor_logger = logging.getLogger('face_processor_handler')
back_ground_remover_logger = logging.getLogger('back_ground_remover_handler')
detector_logger = logging.getLogger('detector_handler')
extractor_logger = logging.getLogger('extractor_handler')
ch = logging.StreamHandler()
# create formatter and add it to the handlers.
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to loggers.
frame_logger.addHandler(ch)
face_processor_logger.addHandler(ch)
back_ground_remover_logger.addHandler(ch)
detector_logger.addHandler(ch)
extractor_logger.addHandler(ch)


class FlagsHandler:
    """Simple class for setting flags.  """

    def __init__(self):
        self._key_board_input = None
        self.lifted = False
        self.quit_flag = False
        self.background_capture_required = True
        self.is_bg_captured = False
        self.calibrated = False
        self.hand_control = False
        self.make_threshold_thinner = False
        self.make_threshold_thicker = False

    @property
    def keyboard_input(self):
        return self._key_board_input

    @keyboard_input.setter
    def keyboard_input(self, input_from_key_board):
        """State machine.  """
        if input_from_key_board == 27 and self.lifted is False:
            # press ESC to exit
            print('!!!quiting!!!')  # todo: change to logger
            self.quit_flag = True
        elif input_from_key_board == 27:
            print('!!!cant quit without landing!!!')  # todo: change to logger
        elif input_from_key_board == ord('b'):
            # press 'b' to capture the background
            self.background_capture_required = True
            self.is_bg_captured = True
            print('!!!Background Captured!!!')  # todo: change to logger

        # elif k == ord('r'):  # press 'r' to reset the background
        #     bgModel = None
        #     triggerSwitch = False
        #     isBgCaptured = 0
        #     print('!!!Reset BackGround!!!')
        elif input_from_key_board == ord('t') and self.calibrated is True:
            """Take off"""
            print('!!!Take of!!!')  # todo: change to logger
            if self.lifted is False:
                print('Wait 5 seconds')  # todo: change to logger
                # drone.takeoff()
                # time.sleep(5)
            self.lifted = True
        elif input_from_key_board == ord('l'):
            """Land"""
            # old_frame_captured = False
            self.lifted = False
            print('!!!Landing!!!')  # todo: change to logger
            # if drone is not None:
            #     print('Wait 5 seconds')
            #     drone.land()
            #     time.sleep(5)
        elif input_from_key_board == ord('c'):
            """Control"""
            if self.hand_control is True:
                self.hand_control = False
                # old_frame_captured = False
                print("control switched to keyboard")  # todo: change to logger
            elif self.lifted is True:
                print("control switched to detected hand")  # todo: change to logger
                self.hand_control = True
            else:
                print("Drone not in the air, can't change control to hand")  # todo: change to logger
        elif input_from_key_board == ord('z'):
            """ calibrating Threshold from keyboard """
            self.make_threshold_thinner = True
            print("made threshold thinner")
            # tempThreshold = cv2.getTrackbarPos('trh1', 'trackbar') - 1
            # if tempThreshold >= 0:
            #     cv2.setTrackbarPos('trh1', 'trackbar', tempThreshold)
        elif input_from_key_board == ord('x'):
            """ calibrating Threshold from keyboard """
            print("made threshold thicker")
            self.make_threshold_thicker = True
            # tempThreshold = cv2.getTrackbarPos('trh1', 'trackbar') + 1
            # if tempThreshold <= 100:
            #     cv2.setTrackbarPos('trh1', 'trackbar', tempThreshold)


class FrameHandler:
    """FrameHandler handel input frame from controller,

    and perform some preprocessing.
    """
    _input_frame = ...  # type: np.ndarray

    def __init__(self):
        """Init preprocessing params.  """
        self.logger = logging.getLogger('frame_handler')
        self.logger.setLevel(logging.INFO)
        self._cap_region_x_begin = 0.6
        self._cap_region_y_end = 0.6
        self._input_frame = None

    @property
    def input_frame(self):
        return self._input_frame

    @input_frame.setter
    def input_frame(self, input_frame_from_camera):
        """Setter with preprocessing.  """

        try:
            # make sure input is np.ndarray
            assert type(input_frame_from_camera).__module__ == np.__name__
        except AssertionError as error:
            self.logger.exception(error)
            return

        self._input_frame = cv2.bilateralFilter(input_frame_from_camera, 5, 50, 100)  # smoothing filter
        self._input_frame = cv2.flip(input_frame_from_camera, 1)
        self._draw_roi()

    def _draw_roi(self):
        """Function for drawing the ROI on input frame"""

        cv2.rectangle(self._input_frame, (int(self._cap_region_x_begin * self._input_frame.shape[1]) - 20, 0),
                      (self._input_frame.shape[1], int(self._cap_region_y_end * self._input_frame.shape[0]) + 20),
                      (255, 0, 0), 2)


class FaceProcessor:
    """FaceProcessor detect & cover faces in preprocessed input_frame.  """
    _preprocessed_input_frame = ...  # type: np.ndarray

    def __init__(self):
        self.logger = logging.getLogger('face_processor_handler')
        self.logger.setLevel(logging.INFO)
        self._face_detector = cv2.CascadeClassifier(
            utils.get_full_path('hallopy/config/haarcascade_frontalface_default.xml'))
        self._face_padding_x = 20
        self._face_padding_y = 60
        self._preprocessed_input_frame = None

    @property
    def face_covered_frame(self):
        """Return a face covered frame"""
        return self._preprocessed_input_frame

    @face_covered_frame.setter
    def face_covered_frame(self, input_frame_with_faces):
        """Function to draw black recs over detected faces.

        This function remove eny 'noise' and help detector detecting palm.
        :param input_frame_with_faces (np.ndarray): a frame with faces, that needed to be covered.
        """

        try:
            # make sure input is np.ndarray
            assert type(input_frame_with_faces).__module__ == np.__name__
        except AssertionError as error:
            self.logger.exception(error)
            return

        # Preparation
        self._preprocessed_input_frame = input_frame_with_faces.copy()
        gray = cv2.cvtColor(self._preprocessed_input_frame, cv2.COLOR_BGR2GRAY)

        faces = self._face_detector.detectMultiScale(gray, 1.3, 5)

        # Black rectangle over faces to remove skin noises.
        for (x, y, w, h) in faces:
            self._preprocessed_input_frame[y - self._face_padding_y:y + h + self._face_padding_y,
            x - self._face_padding_x:x + w + self._face_padding_x, :] = 0


class BackGroundRemover:
    """BackGroundRemover removes background from inputted

     (preprocessed and face covered) frame.
     """
    _input_frame_with_hand = ...  # type: np.ndarray

    def __init__(self, flags_handler):
        self.logger = logging.getLogger('back_ground_remover_handler')
        self._cap_region_x_begin = 0.6
        self._cap_region_y_end = 0.6
        # todo: Belong to detector
        # self._threshold = 50
        # self._blur_Value = 41
        self._bg_Sub_Threshold = 50
        self._learning_Rate = 0
        self._bg_model = None
        self._input_frame_with_hand = None
        self.flag_handler = flags_handler

    @property
    def detected_frame(self):
        """Getter for getting the interest frame, with background removed.  """
        return self._input_frame_with_hand

    @detected_frame.setter
    def detected_frame(self, preprocessed_faced_covered_input_frame):
        """Function for removing background from input frame. """
        if self.flag_handler.background_capture_required is True:
            self._bg_model = cv2.createBackgroundSubtractorMOG2(0, self._bg_Sub_Threshold)
            self.flag_handler.background_capture_required = False
        if self._bg_model is not None:
            fgmask = self._bg_model.apply(preprocessed_faced_covered_input_frame, learningRate=self._learning_Rate)
            kernel = np.ones((3, 3), np.uint8)
            fgmask = cv2.erode(fgmask, kernel, iterations=1)
            res = cv2.bitwise_and(preprocessed_faced_covered_input_frame, preprocessed_faced_covered_input_frame,
                                  mask=fgmask)
            self._input_frame_with_hand = res[
                                          0:int(
                                              self._cap_region_y_end * preprocessed_faced_covered_input_frame.shape[0]),
                                          int(self._cap_region_x_begin * preprocessed_faced_covered_input_frame.shape[
                                              1]):
                                          preprocessed_faced_covered_input_frame.shape[
                                              1]]  # clip the ROI


class Detector:
    """Detector class detect hands contour and center of frame.

    Initiated object will receive a preprocessed frame, with detected & covered faces.
    """
    _input_frame_with_background_removed = ...  # type: np.ndarray

    def __init__(self, flags_handler):
        self.logger = logging.getLogger('detector_handler')
        self.flags_handler = flags_handler
        self._input_frame_with_background_removed = None
        self._threshold = 50
        self._blur_Value = 41
        self.horiz_axe_offset = 60
        self.gray = None
        self._detected_out_put = None
        # max_area_contour: the contour of the detected hand.
        self.max_area_contour = None
        # Detected_out_put_center: the center point of the ROI
        self.detected_out_put_center = None

    @property
    def input_frame_for_feature_extraction(self):
        return self._detected_out_put

    @input_frame_for_feature_extraction.setter
    def input_frame_for_feature_extraction(self, input_frame_with_background_removed):
        """Function for finding hand contour. """
        # Preparation
        # Update threshold
        if self.flags_handler.make_threshold_thinner is True and self._threshold >= 0:
            self.flags_handler.make_threshold_thinner = False
            self._threshold = self._threshold - 1
        elif self.flags_handler.make_threshold_thicker is True and self._threshold <= 100:
            self.flags_handler.make_threshold_thicker = False
            self._threshold = self._threshold + 1

        temp_detected_gray = cv2.cvtColor(input_frame_with_background_removed, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(temp_detected_gray, (self._blur_Value, self._blur_Value), 0)
        _, thresh = cv2.threshold(blur, self._threshold, 255, cv2.THRESH_BINARY)

        # Get the contours.
        _, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        # Find the biggest area.
        self.max_area_contour = max(contours, key=cv2.contourArea)
        try:
            self.detected_out_put_center = self._draw_axes(input_frame_with_background_removed)
            self.gray = temp_detected_gray
            # self._detected_out_put = input_frame_with_background_removed
        except AttributeError:
            self.logger.error("something went wrong in self._draw_axes!")

    def _draw_axes(self, detected):
        """Function for drawing axes on detected_out_put.

        Return detected_out_put_center (point): the center coord' of detected_out_put.
        """

        # Preparation
        temp_output = detected.copy()
        # np.array are opposite than cv2 row/cols indexing.
        detected_out_put_center = (
            int(temp_output.shape[1] / 2), int(temp_output.shape[0] / 2) + self.horiz_axe_offset)
        horiz_axe_start = (0, int(temp_output.shape[0] / 2) + self.horiz_axe_offset)
        horiz_axe_end = (
            temp_output.shape[1], int(temp_output.shape[0] / 2) + self.horiz_axe_offset)

        vertic_y_start = (int(temp_output.shape[1] / 2), 0)
        vertic_y_end = (int(temp_output.shape[1] / 2), temp_output.shape[0])

        # draw movement axes.
        cv2.line(temp_output, horiz_axe_start, horiz_axe_end
                 , (0, 0, 255), thickness=3)
        cv2.line(temp_output, vertic_y_start, vertic_y_end
                 , (0, 0, 255), thickness=3)

        self._draw_contours(temp_output)
        self._detected_out_put = temp_output
        return detected_out_put_center

    def _draw_contours(self, input_frame_with_background_removed):
        """Function for drawing contours of detected hand.

        contour color will accordingly to flags.hand_control flag.
        """
        hand_color = None
        if self.flags_handler.hand_control is True:
            hand_color = (0, 255, 0)
        else:
            hand_color = (0, 0, 255)
        assert hand_color is not None, self.logger.error("No flags_handler.hand_control initiated")
        cv2.drawContours(input_frame_with_background_removed, [self.max_area_contour], 0, hand_color, thickness=2)


class Extractor:
    """Extractor receives detected object,

    saves its 'center_of_frame' and 'max_contour'.
    and perform the following calculations:
    1. calculate palm center of mass --> palms center coordination.
    2. find middle finger coordination.
    3. calculate palms rotation.
    """

    def __init__(self, flags_handler):
        self.logger = logging.getLogger('extractor_handler')
        self.flags_handler = flags_handler
        # detector hold: palms contour, frame_center, frame with drawn axes.
        self.detector = None
        self._detected_hand = None
        self.palm_center_point = None
        self.middle_finger_edge = None
        self.lk_params = dict(winSize=(15, 15),
                              maxLevel=2,
                              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

    @property
    def extract(self):
        return self._detected_hand

    @extract.setter
    def extract(self, detector):
        assert isinstance(detector, Detector), self.logger.error("input is not Detector object!")
        self.palm_center_point = self._hand_center_of_mass(detector.max_area_contour)
        self._detected_hand = detector._detected_out_put
        self.middle_finger_edge = self._find_middle_finger_edge(detector.max_area_contour)

    def _hand_center_of_mass(self, hand_contour):
        """Find contours center of mass.  """
        M = cv2.moments(hand_contour)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
        else:
            cX, cY = 0, 0

        return cX, cY

    def _find_middle_finger_edge(self, hand_contour):
        """Function for calculating middle finger edge coordination.
        :type hand_contour: collection.iter
        """
        desiredPoint = None
        temp_y = self._detected_hand.shape[1]
        for point in hand_contour:  # find highest point in contour, and track that point
            if point[0][1] < temp_y:
                temp_y = point[0][1]

        return point[0][0], point[0][1]

    def _calculate_optical_flow(self, old_gray, frame_gray, p0):
        """
            This function tracks the edge of the Middle finger
            :param old_gray: old frame, gray scale
            :param frame_gray: current frame
            :param p0: previous point for tracking
            :return: p0 - updated tracking point,
        """
        # calculate optical flow
        p1, st, err = cv2.calcOpticalFlowPyrLK(old_gray, frame_gray, p0, None, **self.lk_params)
        if p1 is None:
            # conf.old_frame_captured = False
            good_new = p0[st == 1]
        else:
            good_new = p1[st == 1]

        # Now update the previous frame and previous points
        old_gray = frame_gray.copy()
        p0 = good_new.reshape(-1, 1, 2)
        return p0, old_gray


class Controller(Icontroller):
    """Controller class holds all elements relevant for hand features extracting.

    :param icontroller.Icontroller: implemented interface
    """

    def __init__(self):
        """Init a controller object.  """
        self.move_up = 0
        self.move_left = 0
        self.move_right = 0
        self.move_down = 0
        self.move_forward = 0
        self.move_backward = 0
        self.rotate_left = 0
        self.rotate_right = 0

        # Initiate inner objects
        self.flags_handler = FlagsHandler()
        self.frame_handler = FrameHandler()
        self.face_processor = FaceProcessor()
        self.back_ground_remover = BackGroundRemover(self.flags_handler)

    def start(self):
        """Function for starting image pipe processing.  """
        camera = cv2.VideoCapture(0)
        cv2.namedWindow('Controller')
        while self.flags_handler.quit_flag is False:
            ret, frame = camera.read()
            cv2.imshow('Controller', frame)
            self.flags_handler.keyboard_input = cv2.waitKey(1)

        camera.release()
        cv2.destroyWindow('Controller')

    def get_up_param(self):
        """Return up parameter (int between 0..100). """
        if self.move_up <= 0:
            return 0
        return self.move_up if self.move_up <= 100 else 100

    def get_down_param(self):
        """Return down parameter (int between 0..100). """
        if self.move_down < 0:
            return 0
        return self.move_down if self.move_down <= 100 else 100

    def get_left_param(self):
        """Return left parameter (int between 0..100). """
        if self.move_left < 0:
            return 0
        return self.move_left if self.move_left <= 100 else 100

    def get_right_param(self):
        """Return right parameter (int between 0..100). """
        if self.move_right < 0:
            return 0
        return self.move_right if self.move_right <= 100 else 100

    def get_rotate_left_param(self):
        """Return rotate left parameter (int between 0..100). """
        if self.rotate_left < 0:
            return 0
        return self.rotate_left if self.rotate_left <= 100 else 100

    def get_rotate_right_param(self):
        """Return rotate right parameter (int between 0..100). """
        if self.rotate_right < 0:
            return 0
        return self.rotate_right if self.rotate_right <= 100 else 100

    def get_forward_param(self):
        """Return move forward parameter (int between 0..100). """
        if self.move_forward < 0:
            return 0
        return self.move_forward if self.move_forward <= 100 else 100

    def get_backward_param(self):
        """Return move backward parameter (int between 0..100). """
        if self.move_backward < 0:
            return 0
        return self.move_backward if self.move_backward <= 100 else 100


if __name__ == '__main__':
    test = Controller()
    print(test.get_up_param())
