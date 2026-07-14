package com.example;

import org.junit.jupiter.api.Test;

import static org.junit.Assert.assertEquals;

class CalculatorTest {
    @Test
    void testBasic() {
        Calculator calc = new Calculator();

        assertEquals(5, calc.add(2, 3));
        assertEquals(1, calc.subtract(3, 2));
        assertEquals(6, calc.multiply(2, 3));
    }
}
