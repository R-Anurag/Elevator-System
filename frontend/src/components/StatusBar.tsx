"use client";
// src/components/StatusBar.tsx
// Top HUD-style bar showing score counters and system mode — like a game score.

import React from "react";
import { SystemStatus } from "@/types/elevator";

interface Props {
    status: SystemStatus | null;
    connected: boolean;
    onEmergency: () => void;
    onClearEmergency: () => void;
}

export default function StatusBar({ status, connected, onEmergency, onClearEmergency }: Props) {
    const isEmergency = status?.elevators.some((e) => e.status === "EMERGENCY");

    return (
        <div className="status-bar">
            <div className="status-brand">
                <span className="brand-icon">🏢</span>
                <span className="brand-name">ELEVATE!</span>
            </div>

            <div className="status-counters">
                <div className="counter">
                    <span className="counter-label">SIM TIME</span>
                    <span className="counter-value">{status?.elapsed_seconds ?? 0}s</span>
                </div>
                <div className="counter">
                    <span className="counter-label">AVG WAIT</span>
                    <span className="counter-value">
                        {status ? `${Math.round(status.avg_wait_ms / 1000)}s` : "—"}
                    </span>
                </div>
                <div className="counter">
                    <span className="counter-label">ELEVATORS</span>
                    <span className="counter-value">
                        {status?.elevators.filter((e) => e.status !== "MAINTENANCE").length ?? 0}/
                        {status?.elevators.length ?? 0}
                    </span>
                </div>
                <div className="counter">
                    <span className="counter-label">STRATEGY</span>
                    <span className="counter-value strategy">
                        {status?.scheduler_strategy?.replace("_", " ").toUpperCase() ?? "—"}
                    </span>
                </div>
            </div>

            <div className="status-controls">
                <div className={`conn-dot ${connected ? "connected" : "disconnected"}`} />
                <span className="conn-label">{connected ? "ONLINE" : "OFFLINE"}</span>
                {isEmergency ? (
                    <button className="btn-clear-emergency" onClick={onClearEmergency}>
                        ✅ CLEAR ALARM
                    </button>
                ) : (
                    <button className="btn-emergency" onClick={onEmergency}>
                        🚨 EMERGENCY
                    </button>
                )}
            </div>
        </div>
    );
}
