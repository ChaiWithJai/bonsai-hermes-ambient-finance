# Inspect the model and Hermes configuration

![Selected installed Hermes configuration](images/configuration.jpg)

The image shows selected fields from the installed `ambient-finance-managed-launchd-20260927` profile. It is a configuration reference rendered from actual saved settings, not a Hermes application screen. The [source record](../evidence/configuration-view.json) includes the capture time and SHA-256 of the source profile. Credentials, tool environments and local paths are excluded. The profile was captured after the runs, so it does not independently prove the exact configuration of an earlier run.

The source record also includes the applied request settings from the first HTTP exchange of session `20260926_214801_43f342`. Its exchange hash and identifier match the [recorded usage](../evidence/managed-launchd-20260927/usage.json). The sampling configuration is observed evidence, not a claim that the settings are optimal.

Create an isolated profile with the repository setup command, then inspect its model endpoint and MCP tool paths before starting the gateway or scheduler. Setup templates and the installed profile can differ. A service using an existing profile must reload after its configuration changes.

The model alias alone does not establish the GGUF, runtime build or effective sampling values. Use the launch guide and recorded HTTP requests to check those separately. No matched optimization or cost reduction is established by this screenshot.
