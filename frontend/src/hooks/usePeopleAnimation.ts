"use client";
// src/hooks/usePeopleAnimation.ts
// Backend-driven passenger animation system.
// Converts PassengerGroup data from WebSocket into Person sprites.

import { useCallback, useRef, useState } from "react";
import { PassengerGroup } from "@/types/elevator";

export type PersonPhase =
    | "WALKING_IN"
    | "WAITING"
    | "BOARDING"
    | "RIDING"
    | "ALIGHTING";

export interface Person {
    id: string;
    groupId: string;
    floor: number;
    phase: PersonPhase;
    elevatorId: number | null;
    skinTone: number;
    offsetX: number;
}

let _uid = 0;
const uid = () => `person_${++_uid}`;

export function usePeopleAnimation() {
    const [people, setPeople] = useState<Person[]>([]);
    const prevGroupsRef = useRef<Map<string, PassengerGroup>>(new Map());

    const processTick = useCallback((groups: PassengerGroup[]) => {
        const prev = prevGroupsRef.current;
        const current = new Map<string, PassengerGroup>();

        groups.forEach((grp) => {
            current.set(grp.id, grp);
            const prevGrp = prev.get(grp.id);

            // ── New group: create sprites based on whatever state it first appears in ──
            if (!prevGrp && grp.spawned) {
                if (grp.state === "WAITING" && grp.waiting_count > 0) {
                    // Normal case — group broadcast as WAITING before elevator arrived
                    const newPeople: Person[] = [];
                    for (let i = 0; i < grp.waiting_count; i++) {
                        newPeople.push({
                            id: uid(),
                            groupId: grp.id,
                            floor: grp.source_floor,
                            phase: "WAITING",
                            elevatorId: null,
                            skinTone: Math.floor(Math.random() * 5),
                            offsetX: i * 20,
                        });
                    }
                    setPeople((ps) => [...ps, ...newPeople]);

                } else if (grp.state === "BOARDING" && grp.riding_count > 0) {
                    // Race condition fallback — elevator arrived in the same tick as spawn;
                    // group jumped straight to BOARDING before we could show WAITING sprites.
                    // Still show boarding animation so something is visible.
                    const newPeople: Person[] = [];
                    for (let i = 0; i < grp.riding_count; i++) {
                        newPeople.push({
                            id: uid(),
                            groupId: grp.id,
                            floor: grp.source_floor,
                            phase: "BOARDING",
                            elevatorId: grp.assigned_elevator_id,
                            skinTone: Math.floor(Math.random() * 5),
                            offsetX: i * 20,
                        });
                    }
                    setPeople((ps) => [...ps, ...newPeople]);
                    // Transition to RIDING after boarding animation
                    setTimeout(() => {
                        setPeople((ps) =>
                            ps.map((p) =>
                                p.groupId === grp.id && p.phase === "BOARDING"
                                    ? { ...p, phase: "RIDING" }
                                    : p
                            )
                        );
                    }, 600);
                }
                // RIDING: already in elevator, skip (will appear at dest via alighting)
                // DELIVERED: handled by the delivered block below
            }

            // Transition WAITING -> BOARDING when group starts boarding
            if (
                prevGrp?.state === "WAITING" &&
                grp.state === "BOARDING" &&
                grp.riding_count > 0
            ) {
                setPeople((ps) => {
                    const groupSprites = ps.filter(p => p.groupId === grp.id && (p.phase === "WAITING" || p.phase === "WALKING_IN"));
                    const toBoard = groupSprites.slice(0, grp.riding_count);

                    // Remove all sprites from this group, then add back only those boarding
                    const withoutGroup = ps.filter(p => p.groupId !== grp.id);
                    const boarding = toBoard.map(p => ({ ...p, phase: "BOARDING" as PersonPhase, elevatorId: grp.assigned_elevator_id }));
                    return [...withoutGroup, ...boarding];
                });

                // Transition BOARDING -> RIDING after animation
                setTimeout(() => {
                    setPeople((ps) =>
                        ps.map((p) =>
                            p.groupId === grp.id && p.phase === "BOARDING"
                                ? { ...p, phase: "RIDING" }
                                : p
                        )
                    );
                }, 600);
            }

            // Transition BOARDING/RIDING -> ALIGHTING when group reaches destination
            if (
                (prevGrp?.state === "BOARDING" || prevGrp?.state === "RIDING") &&
                grp.state === "DELIVERED" &&
                grp.delivered_count > 0
            ) {
                // Create alighting sprites (they were hidden during RIDING)
                const alightingPeople: Person[] = [];
                for (let i = 0; i < grp.delivered_count; i++) {
                    alightingPeople.push({
                        id: uid(),
                        groupId: grp.id,
                        floor: grp.dest_floor,
                        phase: "ALIGHTING",
                        elevatorId: grp.assigned_elevator_id,
                        skinTone: Math.floor(Math.random() * 5),
                        offsetX: i * 20,
                    });
                }
                setPeople((ps) => [...ps, ...alightingPeople]);

                // Remove sprites after alighting animation
                setTimeout(() => {
                    setPeople((ps) => ps.filter((p) => !(p.groupId === grp.id && p.phase === "ALIGHTING")));
                }, 3500);
            }
        });

        // Remove sprites for groups that no longer exist in backend (except ALIGHTING)
        setPeople((ps) => ps.filter((p) => current.has(p.groupId) || p.phase === "ALIGHTING"));
        prevGroupsRef.current = current;
    }, []);

    const onWalkComplete = useCallback((personId: string) => {
        setPeople((ps) =>
            ps.map((p) =>
                p.id === personId && p.phase === "WALKING_IN"
                    ? { ...p, phase: "WAITING" }
                    : p
            )
        );
    }, []);

    const peopleByFloor = people.reduce<Record<number, Person[]>>((acc, p) => {
        if (p.phase === "RIDING") return acc;
        if (!acc[p.floor]) acc[p.floor] = [];
        acc[p.floor].push(p);
        return acc;
    }, {});

    return { people, peopleByFloor, processTick, onWalkComplete };
}
