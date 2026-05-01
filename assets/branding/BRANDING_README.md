# V5.6 White-Label Branding

Edit only:

- `assets/branding/branding_config.json`

Replace customer assets here:

- `assets/branding/logo/company_logo.png`
- `assets/branding/logo/sidebar_logo.png`
- `assets/branding/logo/invoice_logo.png`
- `assets/branding/logo/loading_logo.gif`
- `assets/branding/icon/app.ico`
- `assets/branding/icon/installer.ico`

If any custom file is missing, V5.6 falls back to the legacy bundled files:

- `logo.png`
- `loading_logo.gif`
- `icon.ico`

Recommended workflow for a new customer build:

1. Edit `branding_config.json`
2. Replace logo/icon files in the branding folders
3. Run `BUILD.bat`
4. Test the EXE and installer output

Optional About tab contact fields in `branding_config.json`:

- `contact_name`
- `contact_phone`
- `contact_whatsapp`
- `contact_email`
- `contact_website`
- `contact_address`
- `contact_note`

Leave these blank to hide the About > Contact section.
