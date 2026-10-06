import cv2
import mediapipe as mp
import random
import math
import time
import json
import os


# ============================================================
# SETTINGS
# ============================================================

WIDTH = 1280
HEIGHT = 720

MAX_AMMO = 8
GAME_TIME = 60

TARGET_RADIUS = 40

LEADERBOARD_FILE = "leaderboard.json"


# ============================================================
# MEDIAPIPE
# ============================================================

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


# ============================================================
# DISTANCE
# ============================================================

def distance(p1, p2):
    return math.sqrt(
        (p1.x - p2.x) ** 2 +
        (p1.y - p2.y) ** 2
    )


# ============================================================
# LEADERBOARD
# ============================================================

def load_leaderboard():

    if not os.path.exists(LEADERBOARD_FILE):
        return []

    try:

        with open(LEADERBOARD_FILE, "r") as file:
            return json.load(file)

    except:

        return []


def save_score(name, score, accuracy):

    leaderboard = load_leaderboard()

    leaderboard.append({
        "name": name,
        "score": score,
        "accuracy": round(accuracy, 1)
    })

    leaderboard.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    leaderboard = leaderboard[:10]

    try:

        with open(
            LEADERBOARD_FILE,
            "w"
        ) as file:

            json.dump(
                leaderboard,
                file,
                indent=4
            )

    except Exception as e:

        print("Could not save leaderboard:", e)


# ============================================================
# SPAWN TARGET
# ============================================================

def spawn_target():

    x = random.randint(
        TARGET_RADIUS + 30,
        WIDTH - TARGET_RADIUS - 30
    )

    y = random.randint(
        140,
        HEIGHT - TARGET_RADIUS - 50
    )

    return {
        "x": x,
        "y": y
    }


# ============================================================
# RESET GAME
# ============================================================

def reset_game():

    return {
        "score": 0,
        "ammo": MAX_AMMO,
        "shots": 0,
        "hits": 0,
        "combo": 0,
        "best_combo": 0,
        "target": spawn_target(),
        "start_time": time.time(),
        "last_shot": 0,
        "last_reload": 0,
        "game_over": False,
        "score_saved": False
    }


# ============================================================
# HAND GESTURE
# ============================================================

def detect_gesture(hand_landmarks):

    lm = hand_landmarks.landmark

    # --------------------------------------------------------
    # LANDMARKS
    # --------------------------------------------------------

    thumb_tip = lm[4]
    thumb_ip = lm[3]

    index_tip = lm[8]
    index_pip = lm[6]

    middle_tip = lm[12]
    middle_pip = lm[10]

    ring_tip = lm[16]
    ring_pip = lm[14]

    pinky_tip = lm[20]
    pinky_pip = lm[18]


    # --------------------------------------------------------
    # INDEX
    # --------------------------------------------------------

    index_extended = (
        index_tip.y < index_pip.y
    )


    # --------------------------------------------------------
    # MIDDLE
    # --------------------------------------------------------

    middle_extended = (
        middle_tip.y < middle_pip.y
    )


    # --------------------------------------------------------
    # RING
    # --------------------------------------------------------

    ring_folded = (
        ring_tip.y > ring_pip.y
    )


    # --------------------------------------------------------
    # PINKY
    # --------------------------------------------------------

    pinky_folded = (
        pinky_tip.y > pinky_pip.y
    )


    # --------------------------------------------------------
    # AIM
    # --------------------------------------------------------

    aiming = (
        index_extended
        and
        middle_extended
        and
        ring_folded
        and
        pinky_folded
    )


    # --------------------------------------------------------
    # THUMB DISTANCES
    # --------------------------------------------------------

    thumb_index_distance = distance(
        thumb_tip,
        index_tip
    )

    thumb_middle_distance = distance(
        thumb_tip,
        middle_tip
    )


    # --------------------------------------------------------
    # THUMB CLOSE
    # --------------------------------------------------------

    thumb_closed = (
        thumb_index_distance < 0.18
        or
        thumb_middle_distance < 0.18
    )


    # --------------------------------------------------------
    # SHOOT
    # --------------------------------------------------------

    shooting = (
        aiming
        and
        thumb_closed
    )


    # --------------------------------------------------------
    # OPEN PALM
    # --------------------------------------------------------

    thumb_open = abs(
        thumb_tip.x - thumb_ip.x
    ) > 0.04

    ring_open = (
        ring_tip.y < ring_pip.y
    )

    pinky_open = (
        pinky_tip.y < pinky_pip.y
    )

    open_palm = (
        index_extended
        and
        middle_extended
        and
        ring_open
        and
        pinky_open
    )


    return {
        "aiming": aiming,
        "shooting": shooting,
        "thumb_closed": thumb_closed,
        "open_palm": open_palm,
        "thumb_index_distance": thumb_index_distance,
        "thumb_middle_distance": thumb_middle_distance
    }


# ============================================================
# FIND CAMERA
# ============================================================

def find_camera():

    print()
    print("Searching for camera...")
    print()

    for camera_index in [0, 1, 2]:

        print(
            f"Trying camera {camera_index}..."
        )

        camera = cv2.VideoCapture(
            camera_index,
            cv2.CAP_DSHOW
        )

        camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            WIDTH
        )

        camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            HEIGHT
        )

        time.sleep(1)

        if not camera.isOpened():

            camera.release()

            continue

        ret, frame = camera.read()

        if ret and frame is not None:

            print(
                f"Camera {camera_index} connected!"
            )

            return camera

        camera.release()


    return None


# ============================================================
# PLAYER NAME
# ============================================================

player_name = input(
    "Enter your player name: "
).strip()

if player_name == "":
    player_name = "Player"


# ============================================================
# CAMERA
# ============================================================

cap = find_camera()


if cap is None:

    print()
    print("==========================================")
    print("           CAMERA NOT FOUND")
    print("==========================================")
    print()
    print("Please check:")
    print()
    print("1. Camera is connected")
    print("2. Windows camera permission is ON")
    print("3. Close Zoom / Teams / Camera app")
    print("4. Try restarting VS Code")
    print()
    print("Game cannot start without a camera.")
    print()

    input(
        "Press ENTER to close..."
    )

    raise SystemExit


# ============================================================
# MEDIAPIPE HANDS
# ============================================================

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.55,
    min_tracking_confidence=0.55
)


# ============================================================
# GAME
# ============================================================

game = reset_game()


# ============================================================
# STATE
# ============================================================

previous_shooting = False

camera_error_count = 0


# ============================================================
# START MESSAGE
# ============================================================

print()
print("==========================================")
print("       FINGER GUN SPACE SHOOTER")
print("==========================================")
print()
print("PLAYER:", player_name)
print()
print("CONTROLS")
print("------------------------------")
print("Index + Middle = AIM")
print("Thumb close = SHOOT")
print("Open Palm = RELOAD")
print("R = RESTART")
print("Q / ESC = QUIT")
print()
print("Game started!")
print()


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    # --------------------------------------------------------
    # READ CAMERA
    # --------------------------------------------------------

    ret, frame = cap.read()


    # --------------------------------------------------------
    # CAMERA FAILURE
    # --------------------------------------------------------

    if not ret or frame is None:

        camera_error_count += 1

        print(
            "Camera frame unavailable..."
        )

        # Don't immediately close the game.
        time.sleep(0.05)

        # If camera keeps failing for a long time,
        # show an error instead of crashing.

        if camera_error_count > 100:

            print()
            print(
                "Camera stopped responding."
            )

            break

        continue


    # Camera working again

    camera_error_count = 0


    # --------------------------------------------------------
    # MIRROR
    # --------------------------------------------------------

    frame = cv2.flip(
        frame,
        1
    )


    # --------------------------------------------------------
    # RESIZE
    # --------------------------------------------------------

    frame = cv2.resize(
        frame,
        (WIDTH, HEIGHT)
    )


    # --------------------------------------------------------
    # RGB
    # --------------------------------------------------------

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # --------------------------------------------------------
    # HAND DETECTION
    # --------------------------------------------------------

    result = hands.process(
        rgb
    )


    # --------------------------------------------------------
    # DEFAULT VALUES
    # --------------------------------------------------------

    aiming = False

    shooting = False

    thumb_closed = False

    open_palm_gesture = False

    hand_x = WIDTH // 2

    hand_y = HEIGHT // 2


    # ========================================================
    # HAND FOUND
    # ========================================================

    if result.multi_hand_landmarks:

        hand = result.multi_hand_landmarks[0]


        # ----------------------------------------------------
        # DRAW HAND
        # ----------------------------------------------------

        mp_draw.draw_landmarks(
            frame,
            hand,
            mp_hands.HAND_CONNECTIONS
        )


        # ----------------------------------------------------
        # GESTURE
        # ----------------------------------------------------

        gesture = detect_gesture(
            hand
        )

        aiming = gesture["aiming"]

        shooting = gesture["shooting"]

        thumb_closed = gesture["thumb_closed"]

        open_palm_gesture = gesture["open_palm"]


        # ----------------------------------------------------
        # INDEX POSITION
        # ----------------------------------------------------

        index_tip = hand.landmark[8]

        hand_x = int(
            index_tip.x * WIDTH
        )

        hand_y = int(
            index_tip.y * HEIGHT
        )


        # Keep crosshair inside screen

        hand_x = max(
            0,
            min(WIDTH - 1, hand_x)
        )

        hand_y = max(
            0,
            min(HEIGHT - 1, hand_y)
        )


        # ----------------------------------------------------
        # CROSSHAIR
        # ----------------------------------------------------

        cv2.circle(
            frame,
            (hand_x, hand_y),
            18,
            (0, 255, 255),
            2
        )

        cv2.line(
            frame,
            (
                hand_x - 28,
                hand_y
            ),
            (
                hand_x + 28,
                hand_y
            ),
            (0, 255, 255),
            2
        )

        cv2.line(
            frame,
            (
                hand_x,
                hand_y - 28
            ),
            (
                hand_x,
                hand_y + 28
            ),
            (0, 255, 255),
            2
        )


    # ========================================================
    # TIME
    # ========================================================

    elapsed = (
        time.time()
        -
        game["start_time"]
    )

    remaining = max(
        0,
        int(GAME_TIME - elapsed)
    )


    # ========================================================
    # GAME ACTIVE
    # ========================================================

    if not game["game_over"]:

        # ----------------------------------------------------
        # TIME OVER
        # ----------------------------------------------------

        if remaining <= 0:

            game["game_over"] = True


        # ====================================================
        # RELOAD
        # ====================================================

        if open_palm_gesture:

            current_time = time.time()

            if (
                current_time
                -
                game["last_reload"]
                > 1.0
            ):

                if game["ammo"] < MAX_AMMO:

                    game["ammo"] = MAX_AMMO

                game["last_reload"] = current_time


        # ====================================================
        # SHOOT
        # ====================================================

        # Only shoot when thumb changes:
        #
        # OPEN -> CLOSED
        #
        # This prevents automatic continuous shooting.

        new_shot = (
            shooting
            and
            not previous_shooting
        )


        if new_shot:

            current_time = time.time()


            # ------------------------------------------------
            # SHOOT COOLDOWN
            # ------------------------------------------------

            if (
                current_time
                -
                game["last_shot"]
                >= 0.25
            ):

                # --------------------------------------------
                # AMMO
                # --------------------------------------------

                if game["ammo"] > 0:

                    game["ammo"] -= 1

                    game["shots"] += 1

                    game["last_shot"] = (
                        current_time
                    )


                    # ----------------------------------------
                    # TARGET HIT
                    # ----------------------------------------

                    target = game["target"]

                    dx = (
                        hand_x
                        -
                        target["x"]
                    )

                    dy = (
                        hand_y
                        -
                        target["y"]
                    )

                    hit_distance = math.sqrt(
                        dx * dx
                        +
                        dy * dy
                    )


                    # ----------------------------------------
                    # HIT
                    # ----------------------------------------

                    if (
                        hit_distance
                        <=
                        TARGET_RADIUS
                    ):

                        game["hits"] += 1

                        game["combo"] += 1


                        # Best combo

                        if (
                            game["combo"]
                            >
                            game["best_combo"]
                        ):

                            game["best_combo"] = (
                                game["combo"]
                            )


                        # Score

                        points = (
                            10
                            +
                            game["combo"] * 2
                        )

                        game["score"] += points


                        # New target

                        game["target"] = (
                            spawn_target()
                        )


                    # ----------------------------------------
                    # MISS
                    # ----------------------------------------

                    else:

                        game["combo"] = 0


        # ----------------------------------------------------
        # SAVE SHOOT STATE
        # ----------------------------------------------------

        previous_shooting = shooting


    # ========================================================
    # GAME OVER
    # ========================================================

    else:

        # Save only once

        if not game["score_saved"]:

            if game["shots"] > 0:

                accuracy = (
                    game["hits"]
                    /
                    game["shots"]
                ) * 100

            else:

                accuracy = 0


            save_score(
                player_name,
                game["score"],
                accuracy
            )


            game["score_saved"] = True


    # ========================================================
    # DRAW TARGET
    # ========================================================

    if not game["game_over"]:

        target = game["target"]


        # Outer red circle

        cv2.circle(
            frame,
            (
                target["x"],
                target["y"]
            ),
            TARGET_RADIUS,
            (0, 0, 255),
            -1
        )


        # White ring

        cv2.circle(
            frame,
            (
                target["x"],
                target["y"]
            ),
            TARGET_RADIUS - 8,
            (255, 255, 255),
            3
        )


        # Center

        cv2.circle(
            frame,
            (
                target["x"],
                target["y"]
            ),
            8,
            (0, 0, 255),
            -1
        )


    # ========================================================
    # TOP HUD BACKGROUND
    # ========================================================

    cv2.rectangle(
        frame,
        (0, 0),
        (WIDTH, 90),
        (25, 25, 25),
        -1
    )


    # ========================================================
    # PLAYER
    # ========================================================

    cv2.putText(
        frame,
        f"Player: {player_name}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # ========================================================
    # SCORE
    # ========================================================

    cv2.putText(
        frame,
        f"Score: {game['score']}",
        (260, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )


    # ========================================================
    # AMMO
    # ========================================================

    cv2.putText(
        frame,
        f"Ammo: {game['ammo']}/{MAX_AMMO}",
        (460, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # ========================================================
    # TIME
    # ========================================================

    cv2.putText(
        frame,
        f"Time: {remaining}",
        (680, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )


    # ========================================================
    # COMBO
    # ========================================================

    cv2.putText(
        frame,
        f"Combo: {game['combo']}",
        (850, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 100, 255),
        2
    )


    # ========================================================
    # ACCURACY
    # ========================================================

    if game["shots"] > 0:

        accuracy = (
            game["hits"]
            /
            game["shots"]
        ) * 100

    else:

        accuracy = 0


    cv2.putText(
        frame,
        f"Accuracy: {accuracy:.0f}%",
        (1050, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    # ========================================================
    # GESTURE STATUS
    # ========================================================

    if not result.multi_hand_landmarks:

        status_text = "NO HAND DETECTED"

        status_color = (0, 0, 255)


    elif aiming and thumb_closed:

        status_text = "SHOOT!"

        status_color = (0, 255, 0)


    elif aiming:

        status_text = "AIMING - CLOSE THUMB TO SHOOT"

        status_color = (0, 255, 255)


    elif open_palm_gesture:

        status_text = "RELOADING..."

        status_color = (255, 255, 0)


    else:

        status_text = (
            "SHOW INDEX + MIDDLE "
            "FINGERS"
        )

        status_color = (255, 255, 255)


    cv2.putText(
        frame,
        status_text,
        (20, HEIGHT - 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        status_color,
        2
    )


    # ========================================================
    # GAME OVER SCREEN
    # ========================================================

    if game["game_over"]:

        overlay = frame.copy()


        cv2.rectangle(
            overlay,
            (180, 100),
            (1100, 630),
            (0, 0, 0),
            -1
        )


        frame = cv2.addWeighted(
            overlay,
            0.80,
            frame,
            0.20,
            0
        )


        # ----------------------------------------------------
        # GAME OVER
        # ----------------------------------------------------

        cv2.putText(
            frame,
            "GAME OVER!",
            (440, 190),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 255, 255),
            4
        )


        # ----------------------------------------------------
        # PLAYER
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Player: {player_name}",
            (430, 260),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2
        )


        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Score: {game['score']}",
            (460, 325),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            3
        )


        # ----------------------------------------------------
        # ACCURACY
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Accuracy: {accuracy:.1f}%",
            (425, 380),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


        # ----------------------------------------------------
        # HITS
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Hits: {game['hits']}",
            (480, 430),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2
        )


        # ----------------------------------------------------
        # BEST COMBO
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Best Combo: {game['best_combo']}",
            (420, 475),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 100, 255),
            2
        )


        # ----------------------------------------------------
        # RESTART
        # ----------------------------------------------------

        cv2.putText(
            frame,
            "Press R to Restart",
            (425, 535),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )


        # ----------------------------------------------------
        # QUIT
        # ----------------------------------------------------

        cv2.putText(
            frame,
            "Press Q to Quit",
            (455, 580),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


    # ========================================================
    # SHOW WINDOW
    # ========================================================

    cv2.imshow(
        "Finger Gun Space Shooter",
        frame
    )


    # ========================================================
    # KEYBOARD
    # ========================================================

    key = cv2.waitKey(1) & 0xFF


    # --------------------------------------------------------
    # QUIT
    # --------------------------------------------------------

    if key == ord("q") or key == 27:

        break


    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------

    if (
        key == ord("r")
        and
        game["game_over"]
    ):

        game = reset_game()

        previous_shooting = False


# ============================================================
# CLEANUP
# ============================================================

print()
print("Closing game...")


cap.release()

hands.close()

cv2.destroyAllWindows()


print("Game closed.")
print("Thank you for playing!")