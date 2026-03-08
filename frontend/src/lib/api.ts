// src/lib/api.ts
// REST API client using fetch. Base URL is derived from environment.

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function requestElevator(floor: number, direction: "UP" | "DOWN") {
    const res = await fetch(`${BASE}/api/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ floor, direction }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

export async function selectFloor(elevatorId: number, floor: number) {
    const res = await fetch(`${BASE}/api/elevators/${elevatorId}/select-floor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ floor }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

export async function fetchStatus() {
    const res = await fetch(`${BASE}/api/status`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

export async function fetchConfig() {
    const res = await fetch(`${BASE}/api/config`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

export async function triggerEmergency() {
    const res = await fetch(`${BASE}/api/emergency`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

export async function clearEmergency() {
    const res = await fetch(`${BASE}/api/emergency/clear`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

export async function setMaintenance(elevatorId: number, active: boolean) {
    const res = await fetch(
        `${BASE}/api/elevators/${elevatorId}/maintenance?active=${active}`,
        { method: "POST" }
    );
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

export async function restartSimulation() {
    const res = await fetch(`${BASE}/api/simulation/restart`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}
