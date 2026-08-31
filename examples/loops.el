class main() {
    var i: int = 0;
    while (i < 3) {
        print(i);
        i += 1;
    };

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
