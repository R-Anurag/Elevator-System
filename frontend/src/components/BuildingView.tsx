"use client";
// src/components/BuildingView.tsx
// Main game screen — the building cross-section showing all floors and elevator shafts.
// Floors are displayed top-to-bottom (floor N at top, floor 1 at bottom).
// Elevator shafts run as overlay columns on the right side.

import React, { useState, useCallback, useEffect, useRef } from "react";
import { ElevatorState, SystemStatus } from "@/types/elevator";
import FloorRow from "./FloorRow";
import ElevatorShaft from "./ElevatorShaft";
import { requestElevator, selectFloor } from "@/lib/api";
import { usePeopleAnimation } from "@/hooks/usePeopleAnimation";

interface Props {
    status: SystemStatus;
    onRequestMade: (msg: string) => void;
}

export default function BuildingView({ status, onRequestMade }: Props) {
    const [activeRequests, setActiveRequests] = useState<Set<string>>(new Set());
    const { peopleByFloor, processTick, onWalkComplete } = usePeopleAnimation();
    const prevStatusRef = useRef<SystemStatus | null>(null);

    // Feed passenger_groups from WebSocket into the animation engine
    useEffect(() => {
        if (!status || !status.passenger_groups) return;
        processTick(status.passenger_groups);
        prevStatusRef.current = status;
    }, [status, processTick]);

    // Sync active requests from backend
    useEffect(() => {
        if (!status?.active_requests) return;
        const backendActive = new Set(
            status.active_requests.map(r => `${r.floor}-${r.direction}`)
        );
        setActiveRequests(backendActive);
    }, [status?.active_requests]);

    const handleFloorRequest = useCallback(
        async (floor: number, direction: "UP" | "DOWN") => {
            onRequestMade(`REQUEST QUEUED — FLOOR ${floor} ${direction}`);

            try {
                await requestElevator(floor, direction);
            } catch (e) {
                console.error("Request failed:", e);
            }
        },
        [onRequestMade]
    );

    const handleCabFloorSelect = useCallback(
        async (elevId: number, floor: number) => {
            try {
                await selectFloor(elevId, floor);
                onRequestMade(`ELEVATOR ${elevId} → FLOOR ${floor}`);
            } catch (e) {
                console.error("Select floor failed:", e);
            }
        },
        [onRequestMade]
    );

    const { floors, elevators, vip_floors } = status;
    // Driven by building.floor_height_px in config.yaml — no hardcoding
    const FLOOR_HEIGHT = (status as any).floor_height_px ?? 80;

    // Sprite positioning: each shaft is 56px wide, gap 4px, overlay padding 8px each side.
    // To sit just LEFT of the shafts (relative to corridor right edge):
    //   spriteRight = numElevators * 60  + 8
    const numElevators = elevators.length;
    const spriteRightPx = numElevators * 60 + 8; // 8px padding from shafts

    // Floors rendered top-to-bottom (highest floor first)
    const floorNumbers = Array.from(
        { length: floors },
        (_, i) => floors - i
    );

    return (
        <div
            className="building-view"
            style={{
                "--floor-height": `${FLOOR_HEIGHT}px`,
                "--sprite-right": `${spriteRightPx}px`,
                "--num-elevators": numElevators,
            } as React.CSSProperties}
        >
            {/* Floor rows */}
            <div className="floor-rows">
                {floorNumbers.map((floor) => (
                    <FloorRow
                        key={floor}
                        floor={floor}
                        elevators={elevators}
                        vipFloors={vip_floors}
                        activeRequests={activeRequests}
                        onRequest={handleFloorRequest}
                        people={peopleByFloor[floor] ?? []}
                        onWalkComplete={onWalkComplete}
                        spriteRightPx={spriteRightPx}
                    />
                ))}
            </div>

            {/* Elevator shaft columns overlay */}
            <div className="shafts-overlay">
                {elevators.map((elev) => (
                    <ElevatorShaft
                        key={elev.id}
                        elevator={elev}
                        totalFloors={floors}
                        floorHeightPx={FLOOR_HEIGHT}
                        vipFloors={vip_floors}
                        onFloorSelect={handleCabFloorSelect}
                    />
                ))}
            </div>
        </div>
    );
}
