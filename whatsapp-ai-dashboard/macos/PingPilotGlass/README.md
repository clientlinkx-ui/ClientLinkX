# PingPilot Glass for macOS

A native SwiftUI client for the existing Flask backend in this repository.

## Run the backend

From the repository root:

```sh
python3 app.py
```

The macOS app defaults to `http://127.0.0.1:5000`.

## Run the macOS app

From this folder:

```sh
swift run PingPilotGlass
```

Use **Settings** in the app to change the backend URL. Use **Sign In** to open the existing Flask Google login/onboarding flow in a WebKit sheet; the app copies the Flask session cookie into the native API client after sign-in.

## Included native surfaces

- Live dashboard using `/api/dashboard/refresh`.
- Conversation queue, thread timeline, replies, AI analysis, resolve, escalate, and continue actions.
- Assistant configuration status and chat through `/api/assistant/config` and `/api/assistant/chat`.
- Liquid glass inspired macOS layout using SwiftUI materials, translucent panels, and compact native controls.
