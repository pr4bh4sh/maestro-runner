package dev.devicelab.maestro.agent.test;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.runner.RunWith;

/**
 * Entry point for 'am instrument' to start the Maestro Agent.
 * The actual agent runs via MaestroAgentRunner (Instrumentation subclass).
 * This test class exists as a placeholder required by the test APK.
 */
@RunWith(AndroidJUnit4.class)
public class MaestroAgentTest {
    @Test
    public void agentPlaceholder() {
        // Agent is started by MaestroAgentRunner.onStart()
        // This test is just a placeholder
    }
}
