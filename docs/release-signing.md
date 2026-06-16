# Release Signing

GitHub Actions can build unsigned macOS and Windows artifacts without extra setup.
Unsigned macOS artifacts will trigger Gatekeeper warnings such as:

> Apple could not verify "BOTC Script Editor" is free of malware.

To make the macOS download open normally for users, configure Apple Developer ID
signing and notarization secrets in GitHub:

1. Create/export a `Developer ID Application` certificate as a `.p12` file.
2. Base64 encode the `.p12` file and save it as `APPLE_CERTIFICATE`.
3. Save the `.p12` password as `APPLE_CERTIFICATE_PASSWORD`.
4. Save the Apple account email as `APPLE_ID`.
5. Create an app-specific Apple password and save it as `APPLE_PASSWORD`.
6. Save the Apple Developer Team ID as `APPLE_TEAM_ID`.

After these secrets exist, rerun the `Build app binaries` workflow. The macOS
job will automatically sign and notarize the `.app`/`.dmg`. Without those
secrets, the workflow still builds unsigned artifacts for local testing.

Useful command for encoding a certificate:

```sh
base64 -i DeveloperIDApplication.p12 | pbcopy
```

References:

- <https://v2.tauri.app/distribute/sign/macos/>
