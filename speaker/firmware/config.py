"""Hardware and behavior settings. Secrets (Wi-Fi, server address) live in secrets.py."""

DEVICE_NAME = "esp32s3-speaker"

# ---- Server ----
SERVER_PATH = "/"
RECONNECT_MAX_S = 15

# ---- Audio ----
SAMPLE_RATE = 16000          # Hz, mono, PCM16 both ways
CHUNK = 512                  # samples per packet sent to the server (32 ms)

# INMP441 microphone
MIC_SCK = 2
MIC_WS = 3
MIC_SD = 4
MIC_IBUF = 20000
MIC_SHIFT = 13               # 16 = no gain, smaller = louder

# MAX98357A amplifier
SPK_BCLK = 7
SPK_LRC = 6
SPK_DIN = 8
SPK_IBUF = 16000
VOLUME_Q8 = 256              # 256 = x1.0, 128 = x0.5, 512 = x2.0

BARGE_IN = True              # stream the mic while speaking: the wake word interrupts the answer
PLAY_Q_MAX = 8               # packets in the playback queue (~128 ms each)
SEND_Q_MAX = 12              # packets in the send queue

# ---- Peripherals ----
LED_PIN = 48                 # some boards use 38
LED_BRIGHTNESS = 40          # 0..255
MUTE_BUTTON_PIN = 0          # BOOT: press = mute on/off

# ---- Reliability ----
SPEAKING_TIMEOUT_MS = 15000  # server went silent while answering
WDT_TIMEOUT_MS = 20000       # hardware watchdog; 0 = disabled
CRASH_RESET_DELAY_S = 3      # pause before rebooting after a fatal error

# ---- Debug ----
DEBUG_MIC = False            # print the peak mic level every 2 s
