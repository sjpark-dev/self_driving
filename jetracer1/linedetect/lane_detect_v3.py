import cv2
import numpy as np
from utils import camera


class LaneDetection:
    def __init__(self):
        self.right_direction ="Straight"
        self.left_direction = "Straight"
        self.direction = "Straight"
        self.gradient = 0
        self.offcenter = 0

    def test(self, capture):
        while True:
            ret, img = capture.read()

            roi_image, mask, img_width, img_height, resize_img = self.imagepreprocess(img)
            cv2.imshow("a", resize_img)

            bird_to_roi, birdeye, thresh, blur, canny = self.birdeye(roi_image, mask, img_width, img_height)
            # cv2.imshow("2", blur)

            bird_width, bird_height, birdeye = self.linedetect(birdeye, blur)

            cv2.imshow("3", birdeye)

            result = self.addtext(bird_to_roi, birdeye, mask, resize_img, bird_width, bird_height)

            cv2.imshow("result", result)

            if cv2.waitKey(1) == 27:
                break

        capture.release()
        cv2.destroyAllWindows()

    def run(self, img):

        roi_image, mask, img_width, img_height, resize_img = self.imagepreprocess(img)

        bird_to_roi, birdeye, thresh, blur, canny = self.birdeye(roi_image, mask, img_width, img_height)

        bird_width, bird_height, birdeye = self.linedetect(birdeye, blur)

        cv2.imshow("birdeye", birdeye)

        result = self.addtext(bird_to_roi, birdeye, mask, resize_img, bird_width, bird_height)

        return result

    def imagepreprocess(self, img):
        # 이미지 사이즈 조절
        # (이미지 사이즈가 작을 수록 연산속도가 빨라지지 않을까싶음)
        resize_img = cv2.resize(img, dsize=(320, 240))  # x: 320 , y: 240

        # ROI(Region of Interst) 설정, 도로가 있을 부분만 보기위해
        img_height = resize_img.shape[0]
        img_width = resize_img.shape[1]

        roi = np.array([[
            (img_width * 0.25, img_height * 0.4),  # 좌상
            (img_width * 0, img_height * 0.9),  # 좌하
            (img_width * 1, img_height * 0.9),  # 우하
            (img_width * 0.75, img_height * 0.4)  # 우상
        ]], dtype=np.int32)

        # mask 생성, 마스크를 적용하여 ROI를 제외한 나머지 부분을 0(검은색)으로 만들기 위해
        mask = np.zeros_like(resize_img)  # 이미지와 같은 크기의 마스크 생성

        # 마스크 적용
        # 마스크(원본과 같은 사이즈의 크기)에서 roi영역만 255로 채움
        cv2.fillPoly(mask, roi, (255, 255, 255))

        # roi(관심영역)을 표시한 마스크와 resize이미지를 and연산
        # 255 = 1 로 보면 255인 부분만 나타나게 된다
        roi_image = cv2.bitwise_and(resize_img, mask)

        return roi_image, mask, img_width, img_height, resize_img

    def birdeye(self, roi_image, mask, img_width, img_height):

        # Perspective points to be warped
        # 대략적으로 차선이 존재하는 좌표 위치 1280,720
        src = np.float32([[img_width * 0.25, img_height * 0.4],  # 좌상
                          [img_width * 0.75, img_height * 0.4],  # 우상
                          [img_width * 0.0, img_height * 0.9],  # 좌하
                          [img_width * 1, img_height * 0.9]])  # 우하

        # Window to be shown
        # 차선 좌표 위치를 변환해서 출력할 윈도우 크기
        dst = np.float32([[img_width * 0, 0],
                          [img_width * 1, 0],
                          [img_width * 0, img_height * 1],
                          [img_width * 1, img_height * 1]])

        # roi -> bird뷰 변환 행렬 구하기
        roi_to_bird = cv2.getPerspectiveTransform(src, dst)

        # bird뷰 -> roi 변환 행렬 구하기
        bird_to_roi = cv2.getPerspectiveTransform(dst, src)

        # bird뷰로 사진 변환
        birdeye = cv2.warpPerspective(roi_image, roi_to_bird, (img_width, img_height))

        # gray이미지로 변환
        gray_birdeye = cv2.cvtColor(birdeye, cv2.COLOR_RGB2GRAY)

        # 이미지의 값이 threshold 범위 내의 값이 아니면 0 맞으면 255
        ret, thresh = cv2.threshold(gray_birdeye, 160, 255, cv2.THRESH_BINARY)

        # gaussianblur 처리(blurring = 흐릿하게 만들기)
        # 흐릿하게 만듦으로써 차선을 좀더 크게? 만들어서 인식이 잘되게 만들 수 있음
        blur = cv2.GaussianBlur(thresh, (3, 3), 0)

        # canny edge detection
        # 윤곽선 검출의 한 방법, max{ 앞 현재위치 뒤 } = 현재 위치가 아니면 0 맞으면 1(255)
        canny = cv2.Canny(blur, 160, 255)

        return bird_to_roi, birdeye, thresh, blur, canny

    def linedetect(self, birdeye, blur):

        bird_height = birdeye.shape[0]
        bird_width = birdeye.shape[1]

        ploty = np.linspace(0, bird_height - 1, bird_height)
        midpoint = int(bird_width / 2)

        left_blur = blur[0:bird_height, 0:midpoint]
        right_blur = blur[0:bird_height, midpoint:]

        # 왼쪽 차선
        nonzero_left = np.nonzero(left_blur)
        if len(nonzero_left[0]) > 450:
            left_fit = np.polyfit(nonzero_left[0], nonzero_left[1], 2)
            left_fitx = left_fit[0] * ploty ** 2 + left_fit[1] * ploty + left_fit[2]
            lfx = np.trunc(left_fitx)

            lmid = lfx[int(bird_height * 0.7)]

            for y, x in zip(ploty, lfx):
                if x < 0 or x >= left_blur.shape[1]:
                    continue
                birdeye[int(y), int(x)] = [0, 255, 0]

            self.offcenter = midpoint - lmid

        # 오른쪽 차선
        nonzero_right = np.nonzero(right_blur)
        if len(nonzero_right[0]) > 450:
            right_fit = np.polyfit(nonzero_right[0], nonzero_right[1], 2)
            right_fitx = right_fit[0] * ploty ** 2 + right_fit[1] * ploty + right_fit[2]
            rfx = np.trunc(right_fitx)

            rmid = rfx[int(bird_height * 0.7)]

            for y, x in zip(ploty, rfx):
                if x < 0 or x >= right_blur.shape[1]:
                    continue
                birdeye[int(y), midpoint + int(x)] = [0, 255, 0]

            self.offcenter = rmid


        print(midpoint, " : " , self.offcenter)

        return bird_width, bird_height, birdeye


    def addtext(self, bird_to_roi, birdeye, mask, resize_img, bird_width, bird_height):
        # bird뷰 -> 원래 뷰 변환
        roi_image = cv2.warpPerspective(birdeye, bird_to_roi, (bird_width, bird_height))

        # 마스크를 반전 시켜서 원본이미지에서 마스크 부분만 비워내고, 차선을 그린 이미지를 빈자리에 채워넣음
        mask = cv2.bitwise_not(mask)
        resize_img = cv2.bitwise_and(resize_img, mask)
        result = cv2.addWeighted(resize_img, 1, roi_image, 1, 0)

        # 이미지에 커브방향 offcenter 표시
        font = cv2.FONT_HERSHEY_TRIPLEX
        text1 = "Curve Direction :" + self.direction
        text2 = "gradient :" + str(self.gradient)
        text3 = "offcenter :" + str(self.offcenter)

        cv2.putText(result, text1, (10, 20), font, 0.4, (0, 100, 200), 1, cv2.LINE_AA)
        cv2.putText(result, text2, (10, 30), font, 0.4, (0, 100, 200), 1, cv2.LINE_AA)
        cv2.putText(result, text3, (10, 40), font, 0.4, (0, 100, 200), 1, cv2.LINE_AA)

        return result


if __name__ == '__main__':
    lane = LaneDetection()
    camera = camera.Video_Setting()
    capture = camera.video_read()
    while True:
        if capture.isOpened():
            break

    lane.test(capture)