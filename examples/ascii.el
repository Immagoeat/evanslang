# ascii <expression>; loads an image and prints it as ASCII art.
# Requires the 'pillow' package (see requirements.txt).
class main() {
    ascii "examples/assets/sample.png";

    # The path can be any str expression, not just a literal.
    var path: str = "examples/assets/sample.png";
    ascii path;

    print("done");
}
