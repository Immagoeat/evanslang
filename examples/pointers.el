class main() {
    var x: int = 10;
    var p: ptr<int> = &x;

    print(*p);
    *p = 99;
    print(x);

    var y: int = 5;
    p = &y;
    *p = *p + 1;
    print(y);
    print(x);
}
