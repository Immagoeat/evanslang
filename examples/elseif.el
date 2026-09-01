class main() {
    var bob: str = "Hello";
    # Only the first matching branch runs; the rest are skipped.
    if (bob == "Hi") {
        print("hi branch");
    }
    elseif (bob == "Hello") {
        print("hello branch");
    }
    else {
        print("else branch");
    }
    print("after");
}
