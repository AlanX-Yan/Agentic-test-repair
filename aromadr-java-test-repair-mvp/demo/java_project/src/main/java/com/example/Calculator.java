package com.example;

public class Calculator {
    public int add(int left, int right) {
        return left + right;
    }

    public int divide(int dividend, int divisor) {
        return dividend / divisor;
    }

    public int clamp(int value, int min, int max) {
        if (min > max) {
            throw new IllegalArgumentException("min must be <= max");
        }
        if (value < min) {
            return min;
        }
        if (value > max) {
            return max;
        }
        return value;
    }
}
