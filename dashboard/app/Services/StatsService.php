<?php

namespace App\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\DB;

/**
 * Dashboard numbers for one time range (port of query_stats in src/rcis/web/__init__.py).
 * Rows are aggregated in PHP so the same code runs on MySQL and on SQLite in tests.
 * Visits = customers only (staff excluded).
 */
class StatsService
{
    public const RANGES = ['today' => 'Hari ini', 'yesterday' => 'Kemarin', '7d' => '7 hari terakhir', '30d' => '30 hari terakhir'];

    /** @return array{0: string, 1: string, 2: string} start, end (exclusive), bucket */
    public function bounds(string $range, ?CarbonImmutable $now = null): array
    {
        $midnight = ($now ?? CarbonImmutable::now())->startOfDay();
        [$start, $end, $bucket] = match ($range) {
            'yesterday' => [$midnight->subDay(), $midnight, 'hour'],
            '7d' => [$midnight->subDays(6), $midnight->addDay(), 'day'],
            '30d' => [$midnight->subDays(29), $midnight->addDay(), 'day'],
            default => [$midnight, $midnight->addDay(), 'hour'],
        };

        return [$start->format('Y-m-d H:i:s'), $end->format('Y-m-d H:i:s'), $bucket];
    }

    public function stats(string $range, ?CarbonImmutable $now = null): array
    {
        [$start, $end, $bucket] = $this->bounds($range, $now);
        $in = fn (string $table, string $col) => DB::table($table)->where($col, '>=', $start)->where($col, '<', $end);

        $visits = $in('visits', 'entered_at')->where('role', 'customer')
            ->get(['entered_at', 'exited_at', 'entry_side', 'gender_est', 'total_seconds']);
        $male = $visits->where('gender_est', 'male')->count();
        $female = $visits->where('gender_est', 'female')->count();

        if ($bucket === 'hour') {
            $labels = array_map(fn ($h) => sprintf('%02d', $h), range(0, 23));
            $key = fn ($v) => substr($v->entered_at, 11, 2);
        } else {
            $first = CarbonImmutable::parse($start);
            $labels = array_map(fn ($d) => $first->addDays($d)->format('Y-m-d'), range(0, $range === '7d' ? 6 : 29));
            $key = fn ($v) => substr($v->entered_at, 0, 10);
        }
        $series = $visits->countBy($key);

        $zones = $in('zone_events', 'enter_at')->get(['zone_name', 'track_id', 'seconds', 'is_sitting'])
            ->groupBy('zone_name')
            ->map(fn (Collection $rows, $zone) => [
                'zone' => $zone,
                'people' => $rows->pluck('track_id')->unique()->count(),
                'total_seconds' => round($rows->sum('seconds'), 1),
                'sitting_seconds' => round($rows->where('is_sitting', true)->sum('seconds'), 1),
            ])->sortByDesc('total_seconds')->values();

        $laptop = $in('activity_events', 'start_at')->where('activity', 'laptop')->get(['track_id', 'start_at', 'seconds']);

        return [
            'range' => $range, 'start' => $start, 'end' => $end, 'bucket' => $bucket,
            'visitors' => $visits->count(),
            'peak_people' => $this->peak($visits),
            'avg_dwell_seconds' => round((float) $visits->avg('total_seconds'), 1),
            'gender' => ['male' => $male, 'female' => $female, 'unknown' => $visits->count() - $male - $female],
            'series' => ['labels' => $labels, 'values' => array_map(fn ($l) => $series->get($l, 0), $labels)],
            'entry_sides' => $visits->countBy(fn ($v) => $v->entry_side ?? '?'),
            'door' => $in('line_crossings', 'crossed_at')->get(['direction'])->countBy('direction'),
            'zones' => $zones,
            'laptop' => [
                'total_seconds' => round($laptop->sum('seconds'), 1),
                'people' => $laptop->pluck('track_id')->unique()->count(),
                'per_person' => $laptop->groupBy('track_id')->map(fn (Collection $rows, $tid) => [
                    'track_id' => $tid,
                    'first_at' => $rows->min('start_at'),
                    'seconds' => round($rows->sum('seconds'), 1),
                    'sessions' => $rows->count(),
                ])->sortByDesc('seconds')->take(20)->values(),
            ],
            'alerts' => $in('alerts', 'created_at')->orderByDesc('created_at')->limit(50)
                ->get(['type', 'zone_name', 'created_at', 'snapshot_path_blurred'])
                ->map(fn ($a) => [
                    'type' => $a->type, 'zone' => $a->zone_name, 'at' => $a->created_at,
                    'snapshot' => $a->snapshot_path_blurred ? basename($a->snapshot_path_blurred) : null,
                ]),
            'avg_food_wait_seconds' => $in('table_sessions', 'seated_at')->avg('wait_seconds'),
        ];
    }

    /** Most people inside at the same moment. A returning person is a new visit, so this approximates headcount. */
    private function peak(Collection $visits): int
    {
        $events = [];
        foreach ($visits as $v) {
            $events[] = [$v->entered_at, 1];
            if ($v->exited_at) {
                $events[] = [$v->exited_at, -1];
            }
        }
        usort($events, fn ($a, $b) => [$a[0], $a[1]] <=> [$b[0], $b[1]]); // same second: leave before enter
        $now = $max = 0;
        foreach ($events as [, $step]) {
            $max = max($max, $now += $step);
        }

        return $max;
    }
}
