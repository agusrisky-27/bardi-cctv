# Privacy & Data Protection Guidelines

The **Restaurant CCTV Intelligence System (RCIS)** processes video streams that depict individuals in public and semi-public spaces. Privacy is not a secondary consideration—it is baked into the system architecture from the foundational design.

---

## 1. Core Architectural Privacy Mandates

1. **No Facial Recognition**:
   - The system strictly detects human bodies (`person` class).
   - No face detection, facial landmark extraction, or face embedding algorithms are permitted in the pipeline.
2. **No Demographic or Sensitive Inferences**:
   - The system does not classify gender, age, race, ethnicity, emotion, or physical appearance.
3. **No Permanent Identity Tracking**:
   - Tracking IDs (e.g., `track_id: 14`) are strictly temporary, session-scoped integers assigned by the Kalman filter.
   - When a person exits the field of view and the tracker's buffer expires, the ID is retired. Tracking IDs are never linked to customer names, loyalty accounts, or phone numbers.
4. **Local / On-Premise Processing**:
   - All computer vision inference and database storage occur on the local host machine.
   - Video frames, crops, or raw imagery are never uploaded to third-party cloud services or external APIs.
5. **No Default Video Archiving**:
   - Raw video streams are processed in memory and discarded frame-by-frame.
   - Only structured, anonymous analytics events (e.g., "zone_occupancy: 4 persons at 12:30") are persisted to the database.

---

## 2. Data Minimization & Retention Policy

| Data Category | Processed In Memory | Stored to Disk | Retention Period |
| :--- | :--- | :--- | :--- |
| **Raw Video Frames** | Yes (Transient buffer) | No (Discarded immediately) | 0 seconds (real-time only) |
| **Track Coordinates (x, y)** | Yes (In-flight trajectory) | No | Duration of track + 30s |
| **Zone & Crossing Events** | Yes | Yes (SQLite DB) | 30 days (configurable) |
| **Aggregated Footfall & Dwell** | Yes | Yes (SQLite DB) | 12 months (hourly aggregates) |
| **Camera Access Credentials** | In memory | In `.env` only (never logged) | N/A |

---

## 3. Operational Notice & Regulatory Compliance

- **Notice Requirement**: Venues deploying RCIS should post clear signage at venue entrances informing patrons that CCTV analytics are in use for occupancy management and safety.
- **Access Control**: Local databases and configuration files must reside behind appropriate file system permissions, and administrative interfaces must require authentication.
