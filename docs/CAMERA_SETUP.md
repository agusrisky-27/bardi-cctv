# Camera Setup & Inspection Guide

Because the existing CCTV camera's specifications (analog vs IP, RTSP, ONVIF, Wi-Fi, Ethernet, or USB) are currently unknown, this guide provides a step-by-step methodology to discover, test, and integrate the physical camera.

---

## 1. Physical Hardware Inspection Protocol

Inspect the physical camera device and record the following attributes:

1. **Brand & Model Number**: Look for labels or embossed serial plates (e.g., Hikvision, Dahua, Uniview, TP-Link Tapo, Ezviz, Xiaomi, or generic Tuya/OEM).
2. **Physical Connectors**:
   - **BNC Connector (Coaxial)** + 12V DC barrel: Indicates an analog CCTV camera (AHD / TVI / CVI / CVBS). Requires a USB video capture card (BNC-to-USB / RCA-to-USB) or a DVR with network streaming capability to ingest into a computer.
   - **RJ-45 Ethernet Jack**: Indicates an IP camera. May support PoE (Power over Ethernet) or separate 12V DC power.
   - **USB Cable**: Indicates a UVC webcam or USB inspection camera. Can be directly accessed via OpenCV index (e.g. `0` or `1`).
   - **Wi-Fi Antenna**: Indicates a consumer IP camera. Requires an initial mobile app setup to connect to the local Wi-Fi network.

---

## 2. IP Camera Network Discovery

If the camera is an Ethernet or Wi-Fi IP camera:

1. Connect the camera to the local router or PoE switch.
2. Find its assigned IP address using the router administration portal, or run an ARP/mDNS scan:
   ```bash
   arp -a
   ```
3. Check for standard RTSP ports (typically port `554` or `8554`):
   ```bash
   nc -zv <CAMERA_IP> 554
   ```
4. Test common vendor RTSP stream URL patterns:
   - **Hikvision**: `rtsp://<username>:<password>@<ip>:554/Streaming/Channels/101` (substream: `102`)
   - **Dahua / Amcrest**: `rtsp://<username>:<password>@<ip>:554/cam/realmonitor?channel=1&subtype=0`
   - **Tapo**: `rtsp://<username>:<password>@<ip>:554/stream1`
   - **ONVIF Generic**: `rtsp://<username>:<password>@<ip>:554/live/ch0`

---

## 3. Using the RCIS Camera Inspection Tool

RCIS includes a hardware discovery script to probe local video devices:

```bash
# Inspect all connected video devices and list frame resolutions / FPS
python scripts/inspect_camera.py --list-webcams

# Test a specific webcam device index
python scripts/inspect_camera.py --test-webcam 0

# Probe an RTSP IP camera connection
python scripts/inspect_camera.py --test-rtsp "rtsp://admin:password@192.168.1.100:554/stream1"
```

---

## 4. BARDI Smart IP Camera (PTZ 360)

Kamera project ini: BARDI indoor PTZ 360 (putih, Wi-Fi, slot microSD). BARDI tidak menerbitkan dokumentasi RTSP resmi.

- Data komunitas (iSpyConnect, model tidak spesifik): RTSP port **8554**, path `/Streaming/Channels/101` (main) dan `/Streaming/Channels/102` (sub). Belum terverifikasi untuk unit ini.
- RTSP/ONVIF biasanya harus diaktifkan dulu di pengaturan kamera pada app (jika firmware mendukung). Tanpa menu itu, stream hanya lewat cloud app dan **tidak bisa** dibaca OpenCV.
- Cek port terbuka: `nc -zv <IP_KAMERA> 8554`
- Pakai sub-stream (`102`) untuk analitik: lebih ringan, cukup untuk input YOLO 640.
- Bersihkan lensa sebelum tes; lensa kotor menurunkan confidence deteksi.
- Matikan auto-tracking / patrol PTZ selama analitik (zona berbasis piksel tetap).

Fallback bila RTSP tidak tersedia: uji coba di ruang meeting memakai webcam Mac (`--webcam 0`) atau rekaman video (`--video`).
