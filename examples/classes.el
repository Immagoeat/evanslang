@mentions greetings.el -> test;

class init() {
    # Runs once, automatically, before main - no (ment) needed locally.
    print("Starting up...");
}

class helper() {
    # A same-file class, callable locally without (ment).
    print("helper() called locally");
}

class main() {
    helper;
    test.sdgdsg;
    print("main() finished");
}
