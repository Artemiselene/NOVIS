# Extension database schema

Tables:
- `mission_environments`: mission environment metadata; mission_id references host-owned mission identifiers.
- `body_systems`: explanatory metadata for body systems.
- `health_routines`: scheduled astronaut/mission activities.
- `routine_completions`: completion events.
- `health_challenges`: participation-based challenge definitions.
- `astronaut_achievements`: earned participation achievements; astronaut_id references host-owned astronaut identifiers.
- `health_education`: plain-language measurement explanations.

The standalone extension uses its own SQLite database. For host integration, use the host declarative Base and migration framework.
