package org.junit.jupiter.api;

public final class Assertions {
    private Assertions() {
    }

    public static void assertEquals(int expected, int actual, String message) {
        if (expected != actual) {
            throw new AssertionError(message + ": expected " + expected + " but got " + actual);
        }
    }

    public static void assertTrue(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    public static <T extends Throwable> T assertThrows(
            Class<T> expectedType,
            ThrowingRunnable runnable,
            String message
    ) {
        try {
            runnable.run();
        } catch (Throwable thrown) {
            if (expectedType.isInstance(thrown)) {
                return expectedType.cast(thrown);
            }
            throw new AssertionError(
                    message + ": expected " + expectedType.getSimpleName()
                            + " but got " + thrown.getClass().getSimpleName()
            );
        }
        throw new AssertionError(message + ": no exception was thrown");
    }

    public interface ThrowingRunnable {
        void run() throws Throwable;
    }
}
