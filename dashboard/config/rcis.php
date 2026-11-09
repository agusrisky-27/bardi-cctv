<?php

return [
    // Python engine started with --web (live video, heatmap, blurred alert photos). Empty = hide those parts.
    'engine_url' => rtrim((string) env('RCIS_ENGINE_URL', ''), '/'),
    // live_status older than this = engine is off
    'live_stale_seconds' => 30,
];
