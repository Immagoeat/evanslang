class main() {
    var bob: str;

    bob = input("Message: ");

    # elseif/else are optional; a trailing ";" after a block is
    # allowed but purely cosmetic - it has no effect either way.
    if (bob == "Hi") {
        print("bob says hi");
    };

    elseif (bob == "Hello"){
        print("bob says hello");
    };

    else {
        print("bob is weird");
    };
}
