package org.junit;

public final class Assert {
    private Assert() {
    }

    public static void assertEquals(String message, int expected, int actual) {
        if (expected != actual) {
            throw new AssertionError(message + ": expected " + expected + " but got " + actual);
        }
    }

    public static void assertEquals(String message, Object expected, Object actual) {
        if (expected == null ? actual != null : !expected.equals(actual)) {
            throw new AssertionError(message + ": expected " + expected + " but got " + actual);
        }
    }

    public static void assertTrue(String message, boolean condition) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    public static void fail(String message) {
        throw new AssertionError(message);
    }
}
