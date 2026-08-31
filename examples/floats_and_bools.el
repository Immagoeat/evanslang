class main() {
    var pi: float = 3.14;
    print(pi);
    pi += 1.0;
    print(pi);
    pi *= 2.0;
    print(pi);
    pi /= 4.0;
    print(pi);

    var flag: bool = true;
    print(flag);

    var other: bool = false;
    print(other);

    if (flag == true) {
        print("flag is true");
    }

    if (flag && !other) {
        print("flag is true and other is false");
    }

    if (pi > 1.0) {
        print("pi is greater than 1.0");
    }
}
