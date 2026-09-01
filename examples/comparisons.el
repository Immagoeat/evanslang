class main() {
    var n: int = 5;
    var m: int = 10;

    # !=, <, >, <=, >= - the full set of comparison operators.
    if (n != m) {
        print("n and m differ");
    }

    if (n < m) {
        print("n is less than m");
    }

    if (m > n) {
        print("m is greater than n");
    }

    if (n <= 5) {
        print("n is at most 5");
    }

    if (m >= 10) {
        print("m is at least 10");
    }

    # && and || do not short-circuit - both sides always run.
    if (n < m && m > 0) {
        print("both conditions true");
    }

    if (n == m || n < m) {
        print("at least one is true");
    }

    # ! (not) applies to the whole comparison that follows it:
    # !n == m means !(n == m), not (!n) == m.
    if (!n == m) {
        print("n is not equal to m");
    }
}
