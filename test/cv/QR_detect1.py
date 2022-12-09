import cv2


def compute_qr_center():
    center_x, center_y = 0, 0
    cap = cv2.VideoCapture('test_vid2.mp4')
    detector = cv2.QRCodeDetector()

    if not cap.isOpened():
        print("Error No Video available")

    bbox_old = []
    while cap.isOpened():
        ret, img = cap.read()
        img = cv2.flip(img, -1)
        top_l = (240 - 10, 375 - 10)
        bot_r = (240 + 10, 375 + 10)
        cx, cy = 240, 375

        # if cap.isEmpty:
        img = cv2.resize(img, (480, 750))
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        data, bbox, _ = detector.detectAndDecode(img_gray)

        if bbox is not None:
            bbox_old = bbox
        if ret:
            detected_img = img_gray.copy()
            if bbox is not None:
                top_left = (int(bbox[0][2][0]) - 10, int(bbox[0][2][1]) - 10)
                bottom_right = (int(bbox[0][0][0]) + 10, int(bbox[0][0][1]) + 10)
                detected_img = cv2.rectangle(detected_img, top_left, bottom_right, (0, 0, 255), 3)
                img = cv2.rectangle(img, top_left, bottom_right, (0, 0, 255), 3)
                center_x = int((bbox[0][2][0] + bbox[0][0][0]) / 2)
                center_y = int((bbox[0][2][1] + bbox[0][0][1]) / 2)
                img = cv2.circle(img, (center_x, center_y), radius=5, color=(0, 255, 0), thickness=5)
                img = cv2.circle(img, (center_x, center_y), radius=2, color=(0, 0, 255), thickness=5)
            # else:
            #
            #     img = cv2.rectangle(img, top_l, bot_r, (0, 0, 255), 3)
            #     # center_x = int((top_left[0] + bottom_right[0]) / 2)
            #     # center_y = int((top_left[1] + bottom_right[1]) / 2)
            #     img = cv2.circle(img, (cx, cy), radius=5, color=(0, 255, 0), thickness=5)
            #     img = cv2.circle(img, (cx, cy), radius=2, color=(0, 0, 255), thickness=5)

            cv2.imshow('Video', img)
            # output_vid.write(img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        else:
            break

    cap.release()
    # output_vid.release()
    return center_x, center_y


compute_qr_center()
