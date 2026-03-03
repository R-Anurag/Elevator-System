"use client";
// src/components/ElevatorShaft.tsx
// One elevator shaft column — the dark channel in which the cab slides.

import React from "react";
import { ElevatorState } from "@/types/elevator";
import ElevatorCab from "./ElevatorCab";

interface Props {
    elevator: ElevatorState;
    totalFloors: number;
    floorHeightPx: number;
    vipFloors: number[];
    onFloorSelect: (elevId: number, floor: number) => void;
}

export default function ElevatorShaft({
    elevator,
    totalFloors,
    floorHeightPx,
    vipFloors,
    onFloorSelect,
}: Props) {
    return (
        <div
            className="elevator-shaft"
            style={{ height: totalFloors * floorHeightPx }}
            aria-label={`Elevator shaft for ${elevator.name}`}
        >
            {/* Shaft label at top */}
            <div
                className="shaft-label"
                style={{ color: elevator.color }}
            >
                {elevator.name}
            </div>

            {/* Floor guide lines */}
            {Array.from({ length: totalFloors }).map((_, i) => (
                <div
                    key={i}
                    className="shaft-guide"
                    style={{ bottom: `${i * floorHeightPx}px` }}
                />
            ))}

            {/* The moving cab */}
            <ElevatorCab
                elevator={elevator}
                totalFloors={totalFloors}
                floorHeightPx={floorHeightPx}
                onFloorSelect={onFloorSelect}
                vipFloors={vipFloors}
            />
        </div>
    );
}
