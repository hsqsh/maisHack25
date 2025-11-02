<template>
  <div class="app">
    <h1>Voice Object Detector</h1>

    <p v-if="status">{{ status }}</p>

    <div class="buttons">
      <button @click="startRecording" :disabled="isRecording">🎙️ Record</button>
      <button @click="stopRecording" :disabled="!isRecording">🛑 Stop</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// --- Reactive states ---
const isRecording = ref(false)
const status = ref('')
let recognition
let targetObject = ''
let videoStream
let videoEl
let captureInterval
let audioContext
let oscillator

// Initialize audio context for feedback
function initAudio() {
  audioContext = new (window.AudioContext || window.webkitAudioContext)()
  oscillator = audioContext.createOscillator()
  oscillator.type = 'sine'
  oscillator.frequency.setValueAtTime(440, audioContext.currentTime) // 440Hz = A4 note
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

    // Request camera access with higher resolution to improve detection accuracy
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    })
    videoEl.srcObject = videoStream
    await videoEl.play()

    captureInterval = setInterval(captureFrame, 200) // Scan every second
  } catch (err) {
    console.error('Camera error:', err)
    status.value = 'Camera access failed.'
  }
}

// --- Capture frame and send to backend ---
async function captureFrame() {
  if (!videoEl?.videoWidth) return

  const canvas = document.createElement('canvas')
  canvas.width = videoEl.videoWidth
  canvas.height = videoEl.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height)

  // Convert to higher-quality base64 JPEG (reduce compression artifacts)
  const base64Image = canvas.toDataURL('image/jpeg', 0.92).split(',')[1]

  try {
    const res = await fetch('http://localhost:8000/detect', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image_b64: base64Image,
        target: targetObject,
        threshold: 0.4
      })
    })
    const result = await res.json()
    
    if (result.found) {
      console.log(`✅ Found ${targetObject}!`)
      
      // Provide both haptic and audio feedback
      if (navigator.vibrate) {
        navigator.vibrate([200, 100, 200]) // Vibrate pattern: 200ms on, 100ms off, 200ms on
      }
      
      // Play audio tone
      const gainNode = audioContext.createGain()
      gainNode.gain.setValueAtTime(0.5, audioContext.currentTime)
      gainNode.connect(audioContext.destination)
      
      const beep = audioContext.createOscillator()
      beep.frequency.setValueAtTime(880, audioContext.currentTime) // Higher pitch for found object
      beep.connect(gainNode)
      beep.start()
      beep.stop(audioContext.currentTime + 0.3) // Play for 300ms
      
      status.value = `Found "${targetObject}"!`
      clearInterval(captureInterval)
      stopCamera()
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
