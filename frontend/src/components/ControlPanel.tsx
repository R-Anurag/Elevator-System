"use client";
// src/components/ControlPanel.tsx
// Right sidebar: active request log, scheduler info, and maintenance controls.

import React from "react";
import { ElevatorState, SystemStatus } from "@/types/elevator";
import { setMaintenance, restartSimulation } from "@/lib/api";

interface Props {
    status: SystemStatus | null;
    onMaintenanceToggle: () => void;
}

const statusColor: Record<string, string> = {
    IDLE: "#4ade80",
    MOVING: "#f59e0b",
    DOORS_OPEN: "#38bdf8",
    MAINTENANCE: "#f87171",
    EMERGENCY: "#ff0000",
};

export default function ControlPanel({ status, onMaintenanceToggle }: Props) {
    const handleMaintenance = async (elev: ElevatorState) => {
        const making = elev.status !== "MAINTENANCE";
        await setMaintenance(elev.id, making);
        onMaintenanceToggle();
    };

    const handleRestart = async () => {
        await restartSimulation();
    };

    return (
        <aside className="control-panel">
            <h2 className="panel-title">⚙ CONTROL PANEL</h2>

            {/* Elevator status cards */}
            <div className="panel-section">
                <h3 className="section-title">ELEVATORS</h3>
                {status?.elevators.map((elev) => (
                    <div key={elev.id} className="elevator-card">
                        <div className="card-header">
                            <span
                                className="card-dot"
                                style={{ background: elev.color }}
                            />
                            <span className="card-name">{elev.name}</span>
                            <span
                                className="card-status"
                                style={{ color: statusColor[elev.status] ?? "#fff" }}
                            >
                                {elev.status}
                            </span>
                        </div>
                        <div className="card-body">
                            <div className="card-detail">
                                Floor: <b>{elev.current_floor}</b>
                            </div>
                            <div className="card-detail">
                                Dir: <b>{elev.direction}</b>
                            </div>
                            <div className="card-detail">
                                Pax: <b>{elev.passenger_count}/{elev.capacity}</b>
                            </div>
                            <div className="card-detail">
                                Served: <b>{elev.floors_served}</b>
                            </div>
                            {elev.floor_queue.length > 0 && (
                                <div className="card-detail">
                                    Queue: <b>{elev.floor_queue.join(" → ")}</b>
                                </div>
                            )}
                        </div>
                        {/* Maintenance toggle */}
                        <button
                            className={`btn-maintenance ${elev.status === "MAINTENANCE" ? "active" : ""}`}
                            onClick={() => handleMaintenance(elev)}
                        >
                            {elev.status === "MAINTENANCE" ? "🟢 RESTORE" : "🔧 MAINTENANCE"}
                        </button>
                    </div>
                ))}
            </div>

            {/* System info */}
            <div className="panel-section">
                <h3 className="section-title">SYSTEM INFO</h3>
                <div className="info-row">
                    <span>Strategy</span>
                    <span>{status?.scheduler_strategy?.replace("_", " ").toUpperCase() ?? "—"}</span>
                </div>
                <div className="info-row">
                    <span>Tick</span>
                    <span>{status?.tick_interval_ms ?? "—"} ms</span>
                </div>
                <div className="info-row">
                    <span>VIP Floors</span>
                    <span>{status?.vip_floors?.join(", ") || "None"}</span>
                </div>
                <div className="info-row">
                    <span>Emergency Floor</span>
                    <span>{status?.emergency_floor ?? "—"}</span>
                </div>
                <div className="info-row">
                    <span>Elapsed</span>
                    <span>{status?.elapsed_seconds ?? 0}s</span>
                </div>
                <div className="info-row">
                    <span>Pending</span>
                    <span>{status?.pending_requests ?? 0}</span>
                </div>
                <button className="btn-restart" onClick={handleRestart}>
                    🔄 RESTART SIMULATION
                </button>
            </div>
        </aside>
    );
}
