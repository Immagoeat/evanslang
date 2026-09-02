# video <expression>; plays a video as ASCII art in the terminal,
# clearing the screen between frames and pacing playback to the
# source video's own frame rate. Requires the 'opencv-python'
# package (see requirements.txt).
class main() {
    video "examples/assets/sample.mp4";

    # The path can be any str expression, not just a literal.
    var path: str = "examples/assets/sample.mp4";
    video path;

    print("playback finished");
}
