<template>
  <div class="app">
    <h1>Voice Object Detector</h1>

    <div class="health" :class="backendHealth === 'ok' ? 'ok' : (backendHealth === 'fail' ? 'fail' : 'checking')">
      Backend: 
      <span v-if="backendHealth === 'ok'">OK</span>
      <span v-else-if="backendHealth === 'fail'">Offline</span>
      <span v-else>Checking…</span>
    </div>

    <p v-if="status">{{ status }}</p>

    <div class="buttons">
      <button @click="startRecording" :disabled="isRecording">🎙️ Record</button>
      <button @click="stopRecording" :disabled="!isRecording">🛑 Stop</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

// --- Reactive states ---
const isRecording = ref(false)
const status = ref('')
const backendHealth = ref('checking') // 'checking' | 'ok' | 'fail'
let recognition
let targetObject = ''
let videoStream
let videoEl
let captureInterval
let audioContext
let oscillator
let scanning = false
let lastSeen = false
let scanTimeout = null

// Initialize audio context for feedback
function initAudio() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)()
  }
  if (!oscillator) {
    oscillator = audioContext.createOscillator()
    oscillator.type = 'sine'
    oscillator.frequency.setValueAtTime(440, audioContext.currentTime) // 440Hz = A4 note
  }
}

// --- Check backend health on mount ---
onMounted(async () => {
  try {
    const r = await fetch('http://localhost:8000/health')
    const j = await r.json()
    backendHealth.value = j?.ok ? 'ok' : 'fail'
  } catch (e) {
    backendHealth.value = 'fail'
  }
})

function playBeep(freq = 880, duration = 0.3) {
  try {
    if (!audioContext) initAudio()
    const gainNode = audioContext.createGain()
    gainNode.gain.setValueAtTime(0.5, audioContext.currentTime)
    gainNode.connect(audioContext.destination)

    const beep = audioContext.createOscillator()
    beep.type = 'sine'
    beep.frequency.setValueAtTime(freq, audioContext.currentTime)
    beep.connect(gainNode)
    beep.start()
    beep.stop(audioContext.currentTime + duration)
  } catch (e) {
    console.error('Audio feedback error:', e)
  }
}

// Normalize the recognized target to increase matching probability with model labels
function normalizeTarget(s) {
  if (!s) return ''
  s = s.trim().toLowerCase()
  // remove leading filler words
  s = s.replace(/^the\s+|^a\s+|^an\s+/, '')
  // remove punctuation
  s = s.replace(/[.,!?]+$/g, '')
  // simple plural removal: bottles -> bottle
  if (s.endsWith('s') && s.length > 3) {
    s = s.slice(0, -1)
  }
  return s
}

// --- Start voice recording ---
function startRecording() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert('Speech recognition not supported in this browser.')
    return
  }

  // If scanning is active, stop it so we can re-record a new target
  if (scanning) {
    if (captureInterval) {
      clearInterval(captureInterval)
      captureInterval = null
    }
    stopCamera()
    scanning = false
  }

  // Reset seen-state so next detection will trigger feedback
  lastSeen = false

  status.value = 'Listening...'
  isRecording.value = true

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  recognition = new SpeechRecognition()
  recognition.lang = 'en-US'
  recognition.start()

  recognition.onresult = (event) => {
    const raw = event.results[0][0].transcript
    targetObject = normalizeTarget(raw)
    console.log('🎯 Target object (normalized):', targetObject, 'raw:', raw)
    status.value = `Target: "${targetObject}" recorded.`
  }

  recognition.onerror = (e) => {
    console.error('Speech error:', e)
    status.value = 'Error capturing voice input.'
    isRecording.value = false
  }
}

// --- Stop voice recording and start scanning ---
function stopRecording() {
  if (!recognition) return
  recognition.stop()
  isRecording.value = false
  status.value = `Scanning for "${targetObject}"...`
  // Reset lastSeen so the next positive detection triggers feedback
  lastSeen = false
  startScanning()
}

// --- Start scanning with camera ---
async function startScanning() {
  try {
    // Initialize audio context
    initAudio()
    
    videoEl = document.createElement('video')
    videoEl.setAttribute('playsinline', true)
    videoEl.style.display = 'none'
    document.body.appendChild(videoEl)

    // Request camera access with specific settings to match direct camera usage
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { min: 640, ideal: 1280, max: 1920 },
        height: { min: 480, ideal: 720, max: 1080 },
        facingMode: "environment",  // Prefer back camera if available
        frameRate: { ideal: 30 }
      }
    })
    videoEl.srcObject = videoStream
    await videoEl.play()
    if (captureInterval) {
      clearInterval(captureInterval)
      captureInterval = null
    }
    captureInterval = setInterval(captureFrame, 1000) // Scan every second
    scanning = true
  } catch (err) {
    console.error('Camera error:', err)
    status.value = 'Camera access failed.'
  }
}

// --- Capture frame and send to backend ---
async function captureFrame() {
  // if (!videoEl?.videoWidth) return

  // const canvas = document.createElement('canvas')
  // // Maintain aspect ratio but ensure minimum size
  // const width = Math.max(640, videoEl.videoWidth)
  // const height = Math.max(480, videoEl.videoHeight)
  // canvas.width = width
  // canvas.height = height
  // const ctx = canvas.getContext('2d')
  // // Use better quality image rendering
  // ctx.imageSmoothingEnabled = true
  // ctx.imageSmoothingQuality = 'high'
  // ctx.drawImage(videoEl, 0, 0, width, height)

  // // Convert to higher-quality base64 JPEG (reduce compression artifacts)
  // const base64Image = canvas.toDataURL('image/jpeg', 0.92).split(',')[1]
  if (!videoEl?.videoWidth) return

  const canvas = document.createElement('canvas')
  // Use fixed dimensions that match YOLO training
  const width = 640
  const height = 480
  canvas.width = width
  canvas.height = height
  
  const ctx = canvas.getContext('2d')
  ctx.drawImage(videoEl, 0, 0, width, height)

  // Use PNG to avoid compression artifacts
  const base64Image = canvas.toDataURL('image/png').split(',')[1]

  try {
    const res = await fetch('http://localhost:8000/detect', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image_b64: base64Image,
        target: targetObject,
        threshold: 0.25  // Lower threshold for better detection
      })
    })
    const result = await res.json()
    
    if (result.found) {
      // Play beep every time the target is detected
      playBeep(880, 0.3)
      if (navigator.vibrate) {
        navigator.vibrate([200, 100, 200])
      }
      status.value = `Found "${targetObject}"!`
    } else {
      status.value = `Searching for "${targetObject}"...`
    }
  } catch (err) {
    console.error('Detection error:', err)
    status.value = 'Error communicating with detection server.'
  }
}

// --- Stop camera ---
function stopCamera() {
  if (videoStream) {
    videoStream.getTracks().forEach(track => track.stop())
    videoStream = null
  }
  if (videoEl) {
    videoEl.remove()
    videoEl = null
  }
  // mark scanning stopped
  scanning = false
  if (captureInterval) {
    clearInterval(captureInterval)
    captureInterval = null
  }
}
</script>

<style>
.app {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  font-family: system-ui, sans-serif;
  background-color: #f8fafc;
  color: #222;
}

h1 {
  font-size: 1.8rem;
  margin-bottom: 1rem;
}

.health {
  font-size: 0.95rem;
  margin-bottom: 0.5rem;
}
.health.ok { color: #16a34a; }
.health.fail { color: #dc2626; }
.health.checking { color: #64748b; }

.buttons {
  margin-top: 1.5rem;
}

button {
  margin: 0 0.5rem;
  padding: 0.75rem 1.25rem;
  font-size: 1.1rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background-color: #2563eb;
  color: white;
  transition: background 0.2s;
}

button:disabled {
  background-color: #94a3b8;
  cursor: not-allowed;
}

button:not(:disabled):hover {
  background-color: #1d4ed8;
}

p {
  margin: 0.5rem;
  font-size: 1rem;
}
</style>
