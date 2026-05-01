# How To Reset V6 License For Testing

This note is for owner/developer testing only. Do not ship this file inside the customer installer.

## Important

- Close B-Lite Management before deleting license files.
- These commands affect only the current Windows user registry under `HKCU`.
- If the app was tested under another Windows user account, run the registry commands while logged in as that user.
- Do not delete or copy the private admin key to a customer PC.
- Private admin key location on the admin PC:
  `G:\chimmu\Bobys_Salon Billing\License_Admin_Secrets\v6_license_private_key.json`

## Option A: Remove Activation Only

Use this when you want the app to become unactivated but keep the same install identity where possible.

```powershell
Remove-Item "C:\ProgramData\BLiteManagement\license.dat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\Bobys\license.dat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\BobySalon\license.dat" -Force -ErrorAction SilentlyContinue
reg delete "HKCU\Software\BLiteManagement\Licensing" /v license.dat /f
reg delete "HKCU\Software\Bobys\Licensing" /v license.dat /f
```

After this, open the app and use Settings > Licensing > Refresh Status.

## Option B: Full Fresh License Reset

Use this for clean install testing. This removes activation and install identity backups.

Warning: this creates a new Install ID on next app launch. Any old activation token will stop working.

```powershell
Remove-Item "C:\ProgramData\BLiteManagement\license.dat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\BLiteManagement\install.dat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\Bobys\license.dat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\Bobys\install.dat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\BobySalon\license.dat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\BobySalon\install.dat" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\Public\Libraries\syscache.dat" -Force -ErrorAction SilentlyContinue
reg delete "HKCU\Software\BLiteManagement\Licensing" /f
reg delete "HKCU\Software\Bobys\Licensing" /f
```

## After Reset

1. Open B-Lite Management.
2. Go to Settings > Licensing.
3. Copy Device ID and Install ID.
4. On the admin/license PC, run `GENERATE_LICENSE_KEY.bat`.
5. Generate an `activation` key using the copied Device ID and Install ID.
6. Paste the token in the app activation dialog.
7. Refresh Status. It should show `Activated: Yes`.

## What Not To Delete For License Testing

Usually do not delete app business data unless you are testing a completely clean app:

```text
C:\Users\<WindowsUser>\AppData\Roaming\BLiteManagement_Data
```

That folder can contain bills, backups, settings, and app data. License reset does not require deleting it.
