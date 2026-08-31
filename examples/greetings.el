# A small library file, meant to be @mentions-ed by other programs.
# It has no class main() of its own, so it can never be run directly -
# only imported.

class sdgdsg(ment) {
    print("Hello from another file!");
}

class secret() {
    # Not marked (ment), so this is only callable from within this file -
    # other files that @mentions greetings.el cannot reach it.
    print("You should never see this from outside greetings.el");
}
