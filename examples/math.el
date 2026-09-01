class main() {
    # Compound assignment: NAME += expr; is shorthand for NAME = NAME + expr;
    var bob: int = 10;
    print(bob);
    bob += 3;
    print(bob);
    bob -= 3;
    print(bob);
    bob *= 3;
    print(bob);
    bob /= 29;
    print(bob);

    # +, -, *, / also work as general infix expressions, with the usual
    # precedence: * and / bind tighter than + and -.
    var order_of_operations: int = 2 + 3 * 4;
    print(order_of_operations);

    # Parentheses override precedence, same as in math.
    var grouped: int = (2 + 3) * 4;
    print(grouped);

    # Unary minus for negative values.
    var negative: int = -5 + 10;
    print(negative);

    # Arithmetic can feed straight into a comparison.
    var is_big: bool = (order_of_operations * 2) > 20;
    print(is_big);
}
