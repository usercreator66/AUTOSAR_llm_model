#include <stdint.h>
#include <stdio.h>
#include <math.h>

int main() {
    float a, b, c;
    int is_valid = 0;

    // Input side lengths
    printf("Enter the lengths of the three sides of the triangle: ");
    scanf("%f %f %f", &a, &b, &c);

    // Check if sides are positive
    if (a <= 0 || b <= 0 || c <= 0) {
        printf("Error: All sides must be positive numbers.\n");
        return 1;
    }

    // Check triangle inequality theorem
    if ((a + b > c) && (a + c > b) && (b + c > a)) {
        is_valid = 1;
    } else {
        printf("Error: The given sides cannot form a valid triangle.\n");
        return 1;
    }

    // Determine triangle type
    if (a == b && b == c) {
        printf("\nTriangle Type: EQUILATERAL\n");
        printf("All three sides are equal.\n");
    } else if (a == b || b == c || a == c) {
        printf("\nTriangle Type: ISOSCELES\n");
        printf("Two sides are equal.\n");
    } else if (a * a + b * b == c * c || 
               a * a + c * c == b * b || 
               b * b + c * c == a * a) {
        printf("\nTriangle Type: RIGHT-ANGLED\n");
        printf("One angle is 90 degrees (Pythagorean theorem).\n");
    } else {
        printf("\nTriangle Type: SCALENE\n");
        printf("All three sides are different.\n");
    }

    return 0;
}
