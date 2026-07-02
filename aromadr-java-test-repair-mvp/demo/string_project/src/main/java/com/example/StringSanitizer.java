package com.example;

public class StringSanitizer {
    public String normalize(String input) {
        if (input == null) {
            throw new NullPointerException("input");
        }
        return input.trim().toLowerCase().replaceAll("\\s+", " ");
    }
}
