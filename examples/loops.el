class main() {
    # while checks its condition before every iteration, including the
    # first - a false condition means the body never runs.
    var i: int = 0;
    while (i < 3) {
        print(i);
        i += 1;
    };

    # C-style for: init runs once, condition is checked before each
    # iteration, update runs after each iteration's body.
    for (var j: int = 0; j < 3; j += 1) {
        print(j);
    }

    # Loop bodies can contain anything else the language supports.
    for (var k: int = 0; k < 3; k += 1) {
        if (k == 1) {
            print("one!");
        }
        else {
            print(k);
        }
    }
}
