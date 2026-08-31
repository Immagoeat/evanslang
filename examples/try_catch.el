class divide_by() {
    var a: int = 10;
    var b: int = 0;
    var result: int = a / b;
    print(result);
}

class main() {
    try {
        print("attempting division");
        divide_by;
        print("this never runs");
    }
    catch (e: str) {
        print("caught an error:");
        print(e);
    }

    try {
        throw "custom failure message";
    }
    catch (e: str) {
        print("caught a throw:");
        print(e);
    }

    print("program continues normally");
}
