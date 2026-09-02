import shutil
import subprocess

from utils.errors import EvansLangError


class Cell:
    # A boxed variable slot, shared by the VM and the interpreter. Every
    # declared variable's storage is a Cell rather than a raw value, so
    # &x (address-of) can push the Cell itself as a first-class pointer
    # value: *p (dereference) reads cell.value, *p = v (deref-assignment)
    # writes cell.value, and both observe/mutate whatever x currently
    # holds even after x's own later assignments replace cell.value.
    def __init__(self, value=None):
        self.value = value

    def __repr__(self):
        return f"Cell({self.value!r})"


class EvList(list):
    # A plain Python list, tagged with the declared element type of a
    # list<type> (None for an untyped `list`). The parser already rejects
    # a type-mismatched *literal* at parse time (list<int> x: [1, "y"];),
    # but .append(expr)/list[i] = expr; can carry an arbitrary runtime
    # value the parser can't see through - element_type is what lets the
    # VM/interpreter catch a mismatch there too, the same way ptr<type>
    # and arithmetic are runtime-checked beyond what's staticly knowable.
    def __init__(self, iterable=(), element_type: str | None = None):
        super().__init__(iterable)
        self.element_type = element_type


ELEMENT_TYPE_CHECK = {
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, float),
    "bool": lambda v: isinstance(v, bool),
    "str": lambda v: isinstance(v, str),
}


def check_element_type(target, value, action: str) -> None:
    element_type = getattr(target, "element_type", None)
    if element_type is None:
        return
    if not ELEMENT_TYPE_CHECK[element_type](value):
        raise EvansLangError(
            f"Cannot {action} a {type(value).__name__} into "
            f"list<{element_type}>"
        )


def display(value):
    if isinstance(value, Cell):
        return f"ptr@{id(value):x}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(_display_element(element) for element in value) + "]"
    return value


def _display_element(value) -> str:
    # Like display(), but always returns a str (rather than passing an
    # int/float straight through) since it's building one comma-joined
    # str for the whole list - and quotes strings so "hi" is
    # distinguishable from an unquoted identifier/number in the output.
    if isinstance(value, str):
        return f'"{value}"'
    displayed = display(value)
    return displayed if isinstance(displayed, str) else str(displayed)


ASCII_WIDTH = 80
# Terminal character cells are roughly twice as tall as they are wide, so
# scaling the height by the same factor as the width would render a
# vertically-stretched image; halving it (times an extra 0.5 for the
# characters-are-taller-than-wide ratio) keeps the printed aspect ratio
# close to the source image's.
ASCII_HEIGHT_RATIO = 0.55
ASCII_RAMP = "@%#*+=-:. "  # darkest to lightest


def _ascii_dimensions(width: int, height: int) -> tuple[int, int]:
    new_width = ASCII_WIDTH
    new_height = max(1, int(height * ASCII_HEIGHT_RATIO * (new_width / width)))
    return new_width, new_height


def _pixels_to_ascii(pixels: bytes, width: int) -> str:
    # pixels is one 0-255 grayscale byte per pixel, row-major (len(pixels)
    # == width * height) - shared by both a still image (render_ascii_art)
    # and each decoded video frame (play_ascii_video), so the two stay
    # visually consistent rather than each having its own ramp-mapping copy.
    ramp_last_index = len(ASCII_RAMP) - 1
    rows = []
    for row_start in range(0, len(pixels), width):
        row_pixels = pixels[row_start : row_start + width]
        row = "".join(
            ASCII_RAMP[ramp_last_index - (pixel * ramp_last_index // 255)]
            for pixel in row_pixels
        )
        rows.append(row)
    return "\n".join(rows)


def render_ascii_art(path: str) -> str:
    try:
        from PIL import Image
    except ImportError:
        raise EvansLangError(
            "The 'ascii' statement requires the 'pillow' package "
            "(pip install pillow)"
        )

    try:
        image = Image.open(path)
    except FileNotFoundError:
        raise EvansLangError(f"Image file not found: {path!r}")
    except Exception as error:
        raise EvansLangError(f"Cannot open image {path!r}: {error}")

    with image:
        width, height = image.size
        new_width, new_height = _ascii_dimensions(width, height)
        grayscale = image.convert("L").resize((new_width, new_height))
        pixels = grayscale.tobytes()

    return _pixels_to_ascii(pixels, new_width)


ANSI_CLEAR_SCREEN = "\033[2J\033[H"


def _start_audio_playback(path: str):
    # Best-effort only: ffplay is a separate system binary (not the
    # opencv-python pip dependency the frame loop uses), so its absence
    # must never break video playback - a program that already worked
    # silently before audio support was added must keep working exactly
    # the same way if ffplay isn't installed. -nodisp suppresses ffplay's
    # own video window (frames are already being rendered as ASCII by the
    # caller); a file with no audio track just makes ffplay exit almost
    # immediately on its own, which is harmless since nothing here waits
    # on it finishing before the frame loop proceeds.
    if shutil.which("ffplay") is None:
        return None
    try:
        return subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None


def play_ascii_video(path: str) -> None:
    import time

    try:
        import cv2
    except ImportError:
        raise EvansLangError(
            "The 'video' statement requires the 'opencv-python' package "
            "(pip install opencv-python)"
        )

    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        capture.release()
        raise EvansLangError(f"Video file not found or unreadable: {path!r}")

    audio_process = _start_audio_playback(path)
    completed = False
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        # Some containers/codecs report 0 (or nonsense) for FPS - fall back
        # to a reasonable default rather than dividing by zero or sleeping
        # for a nonsensical duration between frames.
        frame_delay = 1.0 / fps if fps and fps > 0 else 1.0 / 24.0

        while True:
            ok, frame = capture.read()
            if not ok:
                break
            height, width = frame.shape[:2]
            new_width, new_height = _ascii_dimensions(width, height)
            grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(grayscale, (new_width, new_height))
            print(ANSI_CLEAR_SCREEN + _pixels_to_ascii(resized.tobytes(), new_width))
            time.sleep(frame_delay)
        completed = True
    finally:
        capture.release()
        if audio_process is not None:
            if completed:
                # The frame loop and the audio track may finish at
                # slightly different times (frame conversion has its own
                # CPU cost, so video playback commonly lags slightly
                # behind real audio time) - wait for ffplay to finish its
                # own timeline rather than cutting audio off the instant
                # the last frame is drawn.
                audio_process.wait()
            else:
                # The frame loop raised partway through - don't leave
                # audio playing (or block error propagation waiting for
                # it) for a video that didn't finish.
                audio_process.terminate()


def parse_as(text: str, target_type: str):
    if target_type == "str":
        return text
    if target_type == "int":
        try:
            return int(text)
        except ValueError:
            raise EvansLangError(f"Cannot parse {text!r} as an int")
    if target_type == "float":
        try:
            return float(text)
        except ValueError:
            raise EvansLangError(f"Cannot parse {text!r} as a float")
    if target_type == "bool":
        if text == "true":
            return True
        if text == "false":
            return False
        raise EvansLangError(f"Cannot parse {text!r} as a bool")
    raise EvansLangError(f"Unknown parse target type {target_type!r}")
