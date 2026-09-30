"""
Plugin: Hand Tracking — controlla il cursore con i gesti della mano via webcam.
Usa MediaPipe e OpenCV per rilevare il dito indice e mapparlo sullo schermo.
Un pizzico (indice + pollice) simula un click.
"""
import math
import threading

PLUGIN = {
    "name": "hand_tracking",
    "description": (
        "Avvia o ferma il controllo del mouse tramite gesti della mano ripresi dalla webcam. "
        "Azione 'start' per avviare, 'stop' per fermare, 'sensitivity' per regolare la sensibilità (float, default 1.5)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Azione da eseguire: 'start', 'stop', o 'sensitivity'."
            },
            "value": {
                "type": "NUMBER",
                "description": "Valore di sensibilità (solo quando action='sensitivity')."
            }
        },
        "required": ["action"]
    }
}

_tracker_lock = threading.Lock()
_tracker_instance = None


def _get_tracker():
    global _tracker_instance
    with _tracker_lock:
        if _tracker_instance is None:
            import cv2
            import mediapipe as mp
            import pyautogui
            import numpy as np

            class HandTracker:
                def __init__(self, sensitivity=1.5):
                    self.mp_hands = mp.solutions.hands
                    self.hands = self.mp_hands.Hands(
                        max_num_hands=1,
                        min_detection_confidence=0.7,
                        min_tracking_confidence=0.7
                    )
                    self.sensitivity = sensitivity
                    self.screen_w, self.screen_h = pyautogui.size()
                    self.running = False
                    self.thread = None

                def _track(self):
                    cap = cv2.VideoCapture(0)
                    while self.running and cap.isOpened():
                        success, img = cap.read()
                        if not success:
                            continue
                        img = cv2.flip(img, 1)
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        results = self.hands.process(img_rgb)
                        if results.multi_hand_landmarks:
                            for hand_landmarks in results.multi_hand_landmarks:
                                index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                                thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                                h, w, _ = img.shape
                                ix, iy = int(index_tip.x * w), int(index_tip.y * h)
                                tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)
                                distance = math.hypot(tx - ix, ty - iy)
                                screen_x = int(np.interp(index_tip.x, [0.1, 0.9], [0, self.screen_w]))
                                screen_y = int(np.interp(index_tip.y, [0.1, 0.9], [0, self.screen_h]))
                                try:
                                    pyautogui.moveTo(screen_x, screen_y)
                                    if distance < 30:
                                        pyautogui.click()
                                except Exception:
                                    pass
                        cv2.waitKey(1)
                    cap.release()

                def start(self):
                    if not self.running:
                        self.running = True
                        self.thread = threading.Thread(target=self._track, daemon=True)
                        self.thread.start()
                        return "Hand tracking avviato."
                    return "Hand tracking è già in esecuzione."

                def stop(self):
                    self.running = False
                    if self.thread:
                        self.thread.join(timeout=2)
                    return "Hand tracking fermato."

            _tracker_instance = HandTracker()
        return _tracker_instance


def run(parameters: dict, **kwargs) -> str:
    action = parameters.get("action", "").lower()
    if action == "start":
        return _get_tracker().start()
    elif action == "stop":
        return _get_tracker().stop()
    elif action == "sensitivity":
        val = float(parameters.get("value", 1.5))
        _get_tracker().sensitivity = val
        return f"Sensibilità hand tracking impostata a {val}."
    return "Azione non valida. Usa 'start', 'stop' o 'sensitivity'."
