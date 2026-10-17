
import cv2


class FaceEngine:
    def __init__(self):
        self.yunet_model = (
            "models/yunet/face_detection_yunet_2026may.onnx"
        )

        self.sface_model = (
            "models/sface/face_recognition_sface_2021dec.onnx"
        )

        self.detector = cv2.FaceDetectorYN.create(
            self.yunet_model,
            "",
            (320, 320),
            0.9,
            0.3,
            5000,
        )

        self.recognizer = cv2.FaceRecognizerSF.create(
            self.sface_model,
            "",
        )

    def detect_faces(self, frame):
        """
        Detect faces in a camera frame.

        Returns:
            List of detected faces.
        """

        height, width = frame.shape[:2]

        self.detector.setInputSize((width, height))

        _, faces = self.detector.detect(frame)

        if faces is None:
            return []

        return faces

    def extract_feature(self, frame, face):
        """
        Align a detected face and generate
        its SFace feature vector.
        """

        aligned_face = self.recognizer.alignCrop(
            frame,
            face,
        )

        feature = self.recognizer.feature(
            aligned_face,
        )

        return feature

    def compare(self, feature1, feature2):
        """
        Compare two face feature vectors.

        Returns:
            Cosine similarity score.
        """

        return self.recognizer.match(
            feature1,
            feature2,
            cv2.FaceRecognizerSF_FR_COSINE,
        )
