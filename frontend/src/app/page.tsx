"use client";
// src/app/page.tsx — Main dashboard page using the Elevate! game UI

import React, { useCallback } from "react";
import { useElevatorSocket } from "@/hooks/useElevatorSocket";
import StatusBar from "@/components/StatusBar";
import BuildingView from "@/components/BuildingView";
import ControlPanel from "@/components/ControlPanel";
import { triggerEmergency, clearEmergency } from "@/lib/api";

export default function HomePage() {
  const { status, connected, flashes, addFlash } = useElevatorSocket();

  const handleEmergency = useCallback(async () => {
    await triggerEmergency();
    addFlash("🚨 EMERGENCY ACTIVATED!");
  }, [addFlash]);

  const handleClearEmergency = useCallback(async () => {
    await clearEmergency();
    addFlash("✅ EMERGENCY CLEARED");
  }, [addFlash]);

  return (
    <div className="app-root">
      {/* Top HUD */}
      <StatusBar
        status={status}
        connected={connected}
        onEmergency={handleEmergency}
        onClearEmergency={handleClearEmergency}
      />

      {/* Flash message ticker */}
      <div className="flash-container">
        {flashes.map((f) => (
          <div key={f.id} className={`flash-message flash-${f.type || 'default'}`}>
            {f.text}
          </div>
        ))}
      </div>

      {/* Main game area */}
      <main className="main-area">
        {status ? (
          <BuildingView status={status} onRequestMade={addFlash} />
        ) : (
          <div className="loading-screen">
            <div className="loading-spinner" />
            <p className="loading-text">CONNECTING TO ELEVATOR SYSTEM...</p>
          </div>
        )}

        {/* Right panel */}
        <ControlPanel
          status={status}
          onMaintenanceToggle={() => { }}
        />
      </main>
    </div>
  );
}
