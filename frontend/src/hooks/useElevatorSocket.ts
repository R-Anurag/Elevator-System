"use client";
// src/hooks/useElevatorSocket.ts
// Manages the WebSocket connection to the backend simulation service.
// Returns live elevator state and connection status.

import { useEffect, useRef, useState, useCallback } from "react";
import { SystemStatus, FlashMessage } from "@/types/elevator";
import { fetchStatus } from "@/lib/api";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";
const RECONNECT_DELAY_MS = 2000;
const FLASH_TTL_MS = 3000;

export function useElevatorSocket() {
    const [status, setStatus] = useState<SystemStatus | null>(null);
    const [connected, setConnected] = useState(false);
    const [flashes, setFlashes] = useState<FlashMessage[]>([]);
    const wsRef = useRef<WebSocket | null>(null);
    const prevFloorsRef = useRef<Map<number, number>>(new Map());
    const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    const addFlash = useCallback((text: string, type: 'pickup' | 'dropoff' | 'default' = 'default') => {
        const msg: FlashMessage = {
            id: `${Date.now()}-${Math.random()}`,
            text,
            timestamp: Date.now(),
            type,
        };
        setFlashes((f) => [...f.slice(-4), msg]);
        setTimeout(() => {
            setFlashes((f) => f.filter((m) => m.id !== msg.id));
        }, FLASH_TTL_MS);
    }, []);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnected(true);
            addFlash("⚡ CONNECTED TO CONTROL SYSTEM");
        };

        ws.onmessage = (event) => {
            const data: SystemStatus = JSON.parse(event.data);
            setStatus((prev) => {
                // Detect boarding and alighting events
                data.elevators.forEach((elev) => {
                    const prevFloor = prevFloorsRef.current.get(elev.id);
                    if (prevFloor !== undefined && prevFloor !== elev.current_floor) {
                        if (elev.status === "DOORS_OPEN") {
                            // Check passenger groups for boarding/alighting
                            const boardingGroups = data.passenger_groups?.filter(
                                g => g.assigned_elevator_id === elev.id && 
                                     g.state === "RIDING" && 
                                     g.source_floor === elev.current_floor
                            ) || [];
                            
                            const alightingGroups = data.passenger_groups?.filter(
                                g => g.assigned_elevator_id === elev.id && 
                                     g.state === "DELIVERED" && 
                                     g.dest_floor === elev.current_floor
                            ) || [];
                            
                            const boardingCount = boardingGroups.reduce((sum, g) => sum + g.riding_count, 0);
                            const alightingCount = alightingGroups.reduce((sum, g) => sum + g.delivered_count, 0);
                            
                            if (boardingCount > 0) {
                                addFlash(`🟢 ${elev.name} picked up ${boardingCount} passenger${boardingCount > 1 ? 's' : ''} from floor ${elev.current_floor}`, 'pickup');
                            }
                            if (alightingCount > 0) {
                                addFlash(`🔵 ${elev.name} dropped ${alightingCount} passenger${alightingCount > 1 ? 's' : ''} at floor ${elev.current_floor}`, 'dropoff');
                            }
                        }
                    }
                    prevFloorsRef.current.set(elev.id, elev.current_floor);
                });
                return data;
            });
        };

        ws.onclose = () => {
            setConnected(false);
            addFlash("⚠ CONNECTION LOST — RETRYING...");
            reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
        };

        ws.onerror = () => ws.close();
    }, [addFlash]);

    useEffect(() => {
        // Load initial state via REST while WS connects
        fetchStatus()
            .then(setStatus)
            .catch(() => { });

        connect();

        return () => {
            reconnectTimer.current && clearTimeout(reconnectTimer.current);
            wsRef.current?.close();
        };
    }, [connect]);

    return { status, connected, flashes, addFlash };
}
