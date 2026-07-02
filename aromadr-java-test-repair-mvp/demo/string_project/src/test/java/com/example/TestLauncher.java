package com.example;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Test;

public class TestLauncher {
    public static void main(String[] args) throws Exception {
        Class<?> testClass = Class.forName("com.example.StringSanitizerBehaviorTest");
        Constructor<?> constructor = testClass.getDeclaredConstructor();
        constructor.setAccessible(true);
        Object instance = constructor.newInstance();

        int run = 0;
        int failed = 0;
        for (Method method : testClass.getDeclaredMethods()) {
            if (!method.isAnnotationPresent(Test.class)) {
                continue;
            }
            run++;
            method.setAccessible(true);
            try {
                method.invoke(instance);
            } catch (ReflectiveOperationException exception) {
                failed++;
                Throwable cause = exception.getCause() == null ? exception : exception.getCause();
                System.err.println("FAILED " + method.getName() + ": " + cause.getMessage());
            }
        }

        System.out.println("TESTS_RUN=" + run);
        System.out.println("TESTS_FAILED=" + failed);
        if (failed > 0) {
            System.exit(1);
        }
    }
}
