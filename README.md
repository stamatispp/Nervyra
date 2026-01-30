# Nervyra
Private Nervyra Slips App


## Nervyra v1.2 Dashboard & Plugins

- After login, Nervyra opens a dashboard with available tools.
- Tools are discovered from the `plugins/` folder. Each tool lives in its own folder and includes a `manifest.json`.
- To add a tool, copy `plugins/_template_tool`, edit `manifest.json`, and point `entrypoint` to an importable `module:function`.

Logs are written under your AppData Nervyra folder (see Dashboard → Open logs).
