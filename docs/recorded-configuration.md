# Inspect the model and Hermes configuration

![Selected installed Hermes configuration](images/configuration.jpg)

The image is a configuration reference rendered from selected fields in the installed `ambient-finance-managed-launchd-20260927` profile. The [source record](../evidence/configuration-view.json) records the capture time and profile hash. This snapshot was captured after the runs; use the linked HTTP exchanges to inspect settings applied to a recorded request.

The source record also includes the applied request settings from the first HTTP exchange of session `20260926_214801_43f342`. Its exchange hash and identifier match the [recorded usage](../evidence/managed-launchd-20260927/usage.json). Use those values when reproducing that request configuration.

Create an isolated profile with the repository setup command, then inspect its model endpoint and MCP tool paths before starting the gateway or scheduler. Setup templates and the installed profile can differ. A service using an existing profile must reload after its configuration changes.

Use the launch guide to match the GGUF and runtime build, then inspect the recorded HTTP request for the effective sampling values.
