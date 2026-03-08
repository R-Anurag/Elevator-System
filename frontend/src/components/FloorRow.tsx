"use client";
// src/components/FloorRow.tsx
// Renders a single floor row: floor number label, animated sprite people, call buttons.

import React from "react";
import { ElevatorState } from "@/types/elevator";
import { Person } from "@/hooks/usePeopleAnimation";
import SpriteLayer from "./SpriteLayer";

interface Props {
    floor: number;
    elevators: ElevatorState[];
    vipFloors: number[];
    activeRequests: Set<string>; // "floor-UP" | "floor-DOWN"
    onRequest: (floor: number, direction: "UP" | "DOWN") => void;
    people: Person[];
    onWalkComplete: (id: string) => void;
    spriteRightPx: number;
}

export default function FloorRow({
    floor,
    elevators,
    vipFloors,
    activeRequests,
    onRequest,
    people,
    onWalkComplete,
    spriteRightPx,
}: Props) {
    const isVip = vipFloors.includes(floor);
    const upActive = activeRequests.has(`${floor}-UP`);
    const downActive = activeRequests.has(`${floor}-DOWN`);

    // Count waiting passengers on this floor
    const waitingCount = people.filter(p => p.phase === "WAITING").length;

    return (
        <div className={`floor-row ${isVip ? "vip-floor" : ""}`}>
            {/* Floor label */}
            <div className="floor-label">
                {isVip && <span className="vip-badge">★</span>}
                <span className="floor-number">{floor}</span>
            </div>

            {/* Corridor — people sprites live here */}
            <div className="floor-corridor">
                <div className="corridor-hatching" />
                <SpriteLayer people={people} onWalkComplete={onWalkComplete} spriteRightPx={spriteRightPx} />
                {waitingCount > 0 && (
                    <div className="waiting-count">{waitingCount}</div>
                )}
            </div>

            {/* Call buttons */}
            <div className="call-buttons">
                <button
                    className={`call-btn call-up ${upActive ? "active" : ""}`}
                    onClick={() => onRequest(floor, "UP")}
                    aria-label={`Call elevator up from floor ${floor}`}
                    disabled={upActive}
                >
                    ▲
                </button>
                <button
                    className={`call-btn call-down ${downActive ? "active" : ""}`}
                    onClick={() => onRequest(floor, "DOWN")}
                    aria-label={`Call elevator down from floor ${floor}`}
                    disabled={downActive}
                >
                    ▼
                </button>
            </div>
        </div>
    );
}
