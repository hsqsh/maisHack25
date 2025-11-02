
# Object Detector Frontend

## Quick Start

1. **Install Node.js**
  - Download the latest version from [Node.js official site](https://nodejs.org/).

2. **Install dependencies** /objectDetectorFE
  ```bash
  npm install
  # or
  yarn install
  ```

3. **in the backend**
  - start the backend:
  - in the root
    ```bash
    uvicorn models.infer_server:app --host 0.0.0.0 --port 8000=http://localhost:8000
    ```
  - Make sure the port matches your backend.

4. **Start the development server**
  ```bash
  npm run dev
  # or
  yarn dev
  ```
  - Default access: http://localhost:5173 or the port shown in the console.

5. **Allow browser camera access**
  - On first visit, your browser will prompt for camera permission.
  - Grant access to enable real-time video frame capture and backend detection.

## Typical Workflow
- Frontend captures webcam video, splits it into image frames (JPEG/PNG), and POSTs them to the backend API in real time.
- Backend (FastAPI + YOLOv8) returns detection results, which are displayed instantly on the frontend.

## Common Issues
- If dependency installation fails, check your Node.js version and network.
- If the camera can't be accessed, check browser permission settings.
- If the backend API address is incorrect, update the `.env` file and restart the frontend.

## Tech Stack
- Vite + Vue/React (customize as needed)
- Node.js
- Native browser camera API

---

> Hackathon-ready: lightning deployment, seamless frontend-backend integration, and real-time AI detection!
# objectDetectorFE

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd) 
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```
