# Importing library
import cv2
from pyzbar.pyzbar import decode


# Make one method to decode the barcode
def QRdetector(vid):
    # read the image in numpy array using cv2
    # img = cv2.imread(image)
    ret, img = vid.read()
    # Decode the barcode image

    img = cv2.flip(img, -1)
    img = cv2.resize(img, (480, 750))
    detectedBarcodes = decode(img)

    # If not detected then print the message
    if not detectedBarcodes:
        print("Barcode Not Detected or your barcode is blank/corrupted!")
    else:

        # Traverse through all the detected barcodes in image
        for barcode in detectedBarcodes:
            (x, y, w, h) = barcode.rect

            cv2.rectangle(img, (x - 10, y - 10),
                          (x + w + 10, y + h + 10),
                          (0, 0, 255), 2)

            cv2.circle(img, (int(x + w/2), int(y + h/2)), radius=5, color=(0, 255, 0), thickness=5)
            cv2.circle(img, (int(x + w/2), int(y + h/2)), radius=2, color=(0, 0, 255), thickness=5)

            # if barcode.data != "":
            #     # Print the barcode data
            #     print(barcode.data)
            #     print(barcode.type)

    # Display the image
    cv2.imshow("Image", img)
    cv2.waitKey(1)
    # cv2.destroyAllWindows()


if __name__ == "__main__":
    # Take the image from user
    cap = cv2.VideoCapture('media/test_vid2.mp4')
    while True:
        QRdetector(cap)
