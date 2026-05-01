# How To Activate License - B-Lite V6

Owner/admin note only. Do not include this file, `licensing_admin/`, or any private key file in the customer EXE/installer.

## What Changed From V5.6

V5.6 used a client-side HMAC key model. The same app code that checked a license also contained the signing secret and a `build_key()` generator. That was convenient, but it is not release-quality because extracting the client could allow forged keys.

V6 uses BLV2 signed tokens. The app contains only `licensing/public_key.py`, which can verify a token. The private signing key stays outside the client in admin-only tooling. Old V5.6 keys are intentionally rejected in V6 with `legacy_key_reactivation_required`.

## First-Time Production Key Ceremony

Do this once before building a real V6 release EXE.

1. Choose an admin-only private key location outside the shipping app folder.

   Recommended:

   ```bat
   G:\chimmu\License_Admin_Secrets\v6_license_private_key.json
   ```

2. Generate the private key and install the matching public key into the V6 client:

   ```bat
   python licensing_admin\keygen.py --generate-keypair --install-public-key --private-key "G:\chimmu\License_Admin_Secrets\v6_license_private_key.json" --public-key-module licensing\public_key.py --overwrite
   ```

3. Record the printed public fingerprint in your release notes.

4. Rebuild the V6 EXE after `licensing/public_key.py` is updated.

Important: Never share, ship, upload, or commit the private key JSON. If that private key is leaked, generate a new key pair, replace `licensing/public_key.py`, rebuild the EXE, and reissue licenses.

## Activating A Customer Install With The GUI Tool

1. Open the V6 app on the customer machine.
2. Go to Settings > Licensing.
3. Copy the `device_id` and `install_id`.
4. On the admin machine, double-click the silent launcher:

   ```bat
   GENERATE_LICENSE_KEY_SILENT.vbs
   ```

   If the silent launcher is blocked by Windows policy, use:

   ```bat
   GENERATE_LICENSE_KEY.bat
   ```

   The BAT now tries `pythonw` first, so the console closes immediately after launching the GUI.

5. Choose `Activate` for a full activation, or `Extend Trial` for a trial extension.
6. Paste the Device ID and Install ID into the GUI.
7. Click `Generate Token`.
8. The generated `BLV2...` token is copied automatically. You can also click `Copy Key`.
9. Paste it into the V6 activation dialog.
10. Close and reopen the app, then confirm the licensing screen still shows activated.

The GUI reads the admin private key from the recommended folder automatically:

```bat
G:\chimmu\Bobys_Salon Billing\License_Admin_Secrets\v6_license_private_key.json
```

If the private key is somewhere else, use the GUI `Browse` button.

## Command-Line Fallback

For advanced/admin-only use, the old command-line wrapper is still available:

   ```bat
   GENERATE_LICENSE_KEY_CLI.bat DEVICE_ID_FROM_APP INSTALL_ID_FROM_APP activation
   GENERATE_LICENSE_KEY_CLI.bat DEVICE_ID_FROM_APP INSTALL_ID_FROM_APP trial_extend 10
   ```

## Trial Extension Token

Use `Extend Trial` in the GUI. The days value must match the app's configured trial-extension days.

```bat
python licensing_admin\keygen.py --type trial_extend --device-id "DEVICE_ID_FROM_APP" --install-id "INSTALL_ID_FROM_APP" --extend-days 10 --private-key "G:\chimmu\License_Admin_Secrets\v6_license_private_key.json"
```

## Release Checklist

- `licensing/public_key.py` contains the production public key fingerprint.
- `licensing_admin/` is excluded from `WhiteLabelApp.spec`.
- No private key JSON is inside `licensing/`, `dist/`, `build/`, installer folders, or customer backup folders.
- Activation token works in source mode.
- Activation token works in the built EXE.
- Trial extension token works on a fresh test install.
- Tampered token and wrong-device token are rejected.
