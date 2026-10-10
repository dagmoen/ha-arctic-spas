# Brand assets

Neutral icon for the integration (not the Arctic Spas company logo).

- `icon.png` — 256×256
- `icon@2x.png` — 512×512

## Making the icon show up in Home Assistant

Home Assistant loads integration brand images from the
[home-assistant/brands](https://github.com/home-assistant/brands) repository,
not from this repo. To have this icon appear in the HA UI, submit these files to
brands under:

```
custom_integrations/arctic_spas/icon.png
custom_integrations/arctic_spas/icon@2x.png
```

Steps: fork `home-assistant/brands`, add the two files at the path above, open a
pull request. Once merged, the icon shows for the `arctic_spas` domain.
