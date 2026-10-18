# Browser container seccomp profile

`chromium-seccomp.json` is vendored from Microsoft's Playwright repository at `utils/docker/seccomp_profile.json`, upstream Git blob `fddc05fb520affb145404e6f6f647ca96af8087d` (Apache-2.0). The profile is the default Docker seccomp allowlist with explicit `clone`, `setns`, and `unshare` syscall allowances required for Chromium's namespace sandbox. Source: https://github.com/microsoft/playwright/blob/main/utils/docker/seccomp_profile.json and https://playwright.dev/python/docs/next/docker.

Review and refresh this profile deliberately when updating Playwright or the Docker baseline. Do not replace it with `seccomp=unconfined`, add broad capabilities such as `SYS_ADMIN`, or disable Chromium's sandbox to work around launch failures. CI verifies that the browser can launch with the sandbox enabled inside the built container.
