<?php

namespace App\Http\Controllers;

use App\Services\StatsService;
use Carbon\CarbonImmutable;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\Rule;
use Illuminate\View\View;

class DashboardController extends Controller
{
    public function index(): View
    {
        return view('dashboard', ['engineUrl' => config('rcis.engine_url'), 'ranges' => StatsService::RANGES]);
    }

    public function stats(Request $request, StatsService $service): JsonResponse
    {
        $range = $request->validate(['range' => ['nullable', Rule::in(array_keys(StatsService::RANGES))]])['range'] ?? 'today';

        return response()->json($service->stats($range));
    }

    /** Current state written by the Python engine every few seconds. */
    public function live(): JsonResponse
    {
        $row = DB::table('live_status')->where('id', 1)->first();
        $age = $row ? CarbonImmutable::parse($row->updated_at)->diffInSeconds(CarbonImmutable::now(), true) : null;

        return response()->json([
            'available' => $row !== null && $age <= config('rcis.live_stale_seconds'),
            'updated_at' => $row?->updated_at,
            'people_now' => $row?->people_now,
            'laptop_now' => $row?->laptop_now,
            'count_in' => $row?->count_in,
            'count_out' => $row?->count_out,
            'fps' => $row?->fps,
        ]);
    }
}
