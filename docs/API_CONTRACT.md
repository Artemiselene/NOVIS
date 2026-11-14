# ASTRA MIND Extension API Contract

Base URL: `http://localhost:8001/api/extension`

All responses are JSON. `astronaut_id` and `mission_id` are identifiers owned by the host ASTRA MIND application; this standalone extension does not create duplicate core tables.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Extension health |
| GET | `/environments` | List mission environments |
| POST | `/environments` | Create an environment |
| GET | `/environments/{id}` | Get environment |
| GET | `/body-systems` | List body system metadata |
| GET | `/body-systems/{key}/status?astronaut_id=1` | Status; grey when telemetry is not connected |
| GET | `/routines` | List routines |
| POST | `/routines` | Create routine |
| POST | `/routines/{id}/complete` | Complete routine |
| GET | `/challenges` | List participation challenges |
| POST | `/challenges/{id}/complete/{astronaut_id}` | Award participation points |
| GET | `/achievements/{astronaut_id}` | List achievements |
| GET | `/education` | List health education entries |

No telemetry values are fabricated by this extension. Body status returns empty measurements until a host telemetry adapter is connected.
