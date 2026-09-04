class main() {
    # goto ln: N; jumps to whichever top-level statement in THIS class
    # starts on source line N. It can be written at the top level of a
    # class body, or directly inside an if/elseif/else - never inside
    # while/for/try/catch, and it can never target a line inside one of
    # those either (only top-level lines are valid targets).
    var i: int = 0;
    print(i);
    i += 1;
    if (i < 3) {
        goto ln: 8;
    }
    print("loop finished");

    # A forward goto skips over statements entirely.
    print("before skip");
    goto ln: 19;
    print("this is never printed");
    print("landed here");
}
