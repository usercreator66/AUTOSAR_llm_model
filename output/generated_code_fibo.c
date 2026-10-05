#include <stdint.h>
#include <stdio.h>

// Function to calculate Fibonacci number recursively
int fibonacci_recursive(int n) {
    if (n <= 1)
        return n;
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2);
}

int main() {
    int n;
    printf("Enter a number to calculate Fibonacci: ");
    scanf("%d", &n);

    if (n < 0) {
        printf("Fibonacci is not defined for negative numbers.\n");
    } else {
        printf("Fibonacci(%d) = %d\n", n, fibonacci_recursive(n));
    }

    return 0;
}
