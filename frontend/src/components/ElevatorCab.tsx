"use client";
// src/components/ElevatorCab.tsx
// Renders a single elevator cab that slides smoothly between floors.

import React from "react";
import { ElevatorState } from "@/types/elevator";

interface Props {
    elevator: ElevatorState;
    totalFloors: number;
    floorHeightPx: number;
    onFloorSelect: (elevId: number, floor: number) => void;
    vipFloors: number[];
}

const dirArrow: Record<string, string> = {
    UP: "▲",
    DOWN: "▼",
    IDLE: "—",
};

export default function ElevatorCab({
    elevator,
    totalFloors,
    floorHeightPx,
    onFloorSelect,
    vipFloors,
}: Props) {
    // Position: floor 1 is at bottom (0px), each floor adds floorHeightPx
    const bottomPx = (elevator.current_floor - 1) * floorHeightPx;

    const statusClass = elevator.status.toLowerCase();
    const isDoorsOpen = elevator.status === "DOORS_OPEN";
    const isMaintenance = elevator.status === "MAINTENANCE";
    const isEmergency = elevator.status === "EMERGENCY";

    return (
        <div
            className={`elevator-cab ${statusClass}`}
            style={{
                bottom: `${bottomPx}px`,
                borderColor: elevator.color,
                boxShadow: isDoorsOpen
                    ? `0 0 18px 4px ${elevator.color}99`
                    : `0 0 6px 1px ${elevator.color}44`,
            }}
            title={`${elevator.name} — Floor ${elevator.current_floor}`}
        >
            {/* Direction indicator */}
            <div
                className="cab-direction"
                style={{ color: elevator.color }}
            >
                {dirArrow[elevator.direction]}
            </div>

            {/* Floor number */}
            <div className="cab-floor">{elevator.current_floor}</div>

            {/* Doors-open animation overlay */}
            {isDoorsOpen && <div className="cab-doors-open" />}

            {/* Maintenance or emergency badge */}
            {isMaintenance && <div className="cab-badge maintenance">🔧</div>}
            {isEmergency && <div className="cab-badge emergency">🚨</div>}

            {/* Passenger indicator dots */}
            <div className="cab-passengers">
                {Array.from({ length: elevator.capacity }).map((_, i) => (
                    <span
                        key={i}
                        className={`passenger-dot ${i < elevator.passenger_count ? "filled" : ""}`}
                        style={
                            i < elevator.passenger_count
                                ? { background: elevator.color }
                                : {}
                        }
                    />
                ))}
            </div>
        </div>
    );
}
