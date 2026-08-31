class main() {
    var bob: str = "42";
    var n: int = bob.parse(int);
    print(n);

    var pi_str: str = "3.14";
    var pi: float = pi_str.parse(float);
    print(pi);

    var flag_str: str = "true";
    var flag: bool = flag_str.parse(bool);
    print(flag);

    if (n == 42) {
        print("parsed correctly");
    }
}
