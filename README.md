# AutoUUPBuild

AutoUUPBuild downloads the latest retail UUP dump package, applies the conversion settings, and builds either an ISO or WIM artifact through GitHub Actions.

## Local Usage

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Fetch and extract the latest UUP package:

```powershell
python -m autouupbuild fetch --arch amd64 --ring retail --pack zh-cn --edition professional --output .
```

Use Release Preview by passing `rp`:

```powershell
python -m autouupbuild fetch --arch amd64 --ring rp --pack zh-cn --edition professional --output .
```

Configure the extracted UUP conversion files for an ISO:

```powershell
python -m autouupbuild configure --artifact iso --config ConvertConfig.ini --apps-list CustomAppsList.txt
```

Configure for a WIM instead:

```powershell
python -m autouupbuild configure --artifact wim --config ConvertConfig.ini --apps-list CustomAppsList.txt
```

After configuration, run the generated `uup_download_windows.cmd` script on Windows.

## GitHub Actions

The `Build Windows Image` workflow is manually triggered and accepts:

- `artifact`: `iso` or `wim`
- `arch`: default `amd64`
- `ring`: default `rp`; use `retail` for the Retail channel
- `pack`: default `zh-cn`
- `edition`: default `professional`

The workflow installs Python dependencies, fetches the latest UUP package, configures the conversion, runs `uup_download_windows.cmd`, uploads the artifact, and publishes it to a GitHub release tagged with the detected build version, such as `26200.8328`.

Release assets are named with the version and selected inputs, for example:

```text
26200.8328-rp-amd64-zh-cn-professional-iso.iso
26200.8328-rp-amd64-zh-cn-professional-wim.wim
```

When building an ISO, the workflow also copies `sources\install.wim` out of the ISO output and uploads it separately as:

```text
26200.8328.wim
```

Workflow artifacts use `archive: false` so ISO/WIM files are uploaded as plain files instead of being wrapped in an additional archive.

If the release already exists, the workflow reuses it. If the same asset name already exists, the workflow deletes that asset before uploading the new one so reruns of the same version succeed.

GitHub Release assets must be smaller than 2 GiB. Larger ISO/WIM files are still uploaded as Actions artifacts with `archive: false`, but the workflow skips adding them to the Release and records that in the workflow summary and release notes.

## Tests

Run the local regression suite:

```powershell
python -m unittest discover -s tests
python -m compileall -q autouupbuild tests
python -m autouupbuild --help
```
