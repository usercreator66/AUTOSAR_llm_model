#include <stdint.h>
#include <stdio.h>
#include <math.h> // Required for sqrt()

int main() {
    double number;
    double result;

    printf("Enter a non-negative number: ");
    
    // Read input from user
    if (scanf("%lf", &number) != 1) {
        printf("Invalid input.\n");
        return 1;
    }

    // Check for negative numbers (square root of negative is undefined in real numbers)
    if(number < 0) {
         printf("Error: Cannot compute square root of negative number.\n"); 
         return 10;
    };

    // Calculate square root
    result = sqrt(number);

    // Display result
    printf("The square root of %.2f is %.4f\n", number, result);

    return 0;
}
