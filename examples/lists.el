class main() {
    list empty;
    empty.append(1);
    empty.append(2);
    print(empty);

    list mixed: [1, "two", true];
    print(mixed);

    list<int> nums: [10, 20, 30];
    print(nums[0]);
    nums[0] = 99;
    print(nums);

    var sum: int = 0;
    for (var i: int = 0; i < nums.length(); i += 1) {
        sum = sum + nums[i];
    }
    print(sum);

    try {
        print(nums[10]);
    }
    catch (e: str) {
        print(e);
    }
}
