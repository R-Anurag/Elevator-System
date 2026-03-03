"use client";
// src/components/SpriteLayer.tsx
// Renders animated pixel-art people on a single floor corridor.
// Each person is a minimal inline SVG "stick figure" styled with pixel-art CSS.
// Phase class names map directly to keyframe animations in globals.css.

import React, { useEffect, useRef } from "react";
import { Person } from "@/hooks/usePeopleAnimation";

interface Props {
    people: Person[];
    onWalkComplete: (id: string) => void;
    spriteRightPx: number;
}

// 5 skin-tone palette pairs [body, head]
const SKIN_PALETTES: [string, string][] = [
    ["#f59e0b", "#fde68a"], // amber
    ["#3b82f6", "#bfdbfe"], // blue
    ["#10b981", "#a7f3d0"], // green
    ["#e879f9", "#f5d0fe"], // pink
    ["#f87171", "#fecaca"], // red
];

function PixelPerson({
    person,
    onWalkComplete,
}: {
    person: Person;
    onWalkComplete: (id: string) => void;
}) {
    const ref = useRef<HTMLDivElement>(null);
    const [body, head] = SKIN_PALETTES[person.skinTone];

    // Listen for animation end to promote WALKING_IN → WAITING
    useEffect(() => {
        const el = ref.current;
        if (!el || person.phase !== "WALKING_IN") return;
        const handler = (e: AnimationEvent) => {
            if (e.animationName === "person-walk-in") {
                onWalkComplete(person.id);
            }
        };
        el.addEventListener("animationend", handler);
        return () => el.removeEventListener("animationend", handler);
    }, [person.id, person.phase, onWalkComplete]);

    // Minimal stagger - groups walk together
    const delayMs = person.offsetX * 15; // 15ms per 20px

    // Vertical offset for depth
    const bottomOffset = 4 + ((person.offsetX / 20) % 3) * 3;

    return (
        <div
            ref={ref}
            className={`sprite-person sprite-${person.phase.toLowerCase()}`}
            style={{
                animationDelay: `${delayMs}ms`,
                animationDuration:
                    person.phase === "WALKING_IN"
                        ? "2s"
                        : person.phase === "ALIGHTING"
                            ? "2s"
                            : undefined,
                bottom: `${bottomOffset}px`,
            }}
            aria-hidden="true"
        >
            {/* Inline pixel-art SVG person */}
            <svg
                width="14"
                height="26"
                viewBox="0 0 14 26"
                style={{ imageRendering: "pixelated", display: "block" }}
            >
                {/* Head */}
                <rect x="4" y="0" width="6" height="6" fill={head} />
                {/* Body */}
                <rect x="4" y="7" width="6" height="7" fill={body} />
                {/* Left arm */}
                <rect x="1" y="8" width="3" height="3" fill={body} />
                {/* Right arm */}
                <rect x="10" y="8" width="3" height="3" fill={body} />
                {/* Left leg — animated walking bob via parent animation */}
                <rect x="4" y="15" width="2" height="7" fill={body} />
                {/* Right leg */}
                <rect x="8" y="15" width="2" height="7" fill={body} />
                {/* Eyes */}
                <rect x="5" y="2" width="1" height="1" fill="#000" />
                <rect x="8" y="2" width="1" height="1" fill="#000" />
            </svg>
        </div>
    );
}

export default function SpriteLayer({ people, onWalkComplete, spriteRightPx }: Props) {
    const layerRef = useRef<HTMLDivElement>(null);

    // Measure the corridor and set --corridor-walk-distance so the walk-in
    // animation ends exactly at the shaft edge.
    // spriteRightPx = distance from corridor right edge to sprite resting position.
    useEffect(() => {
        const el = layerRef.current;
        if (!el) return;
        const updateDistance = () => {
            const w = el.offsetWidth;
            // sprite rests at `right: spriteRightPx` inside the corridor,
            // so it is at (w - spriteRightPx - 14px sprite width) from left.
            el.style.setProperty(
                "--corridor-walk-distance",
                `${Math.max(0, w - spriteRightPx - 14)}px`
            );
        };
        updateDistance();
        const ro = new ResizeObserver(updateDistance);
        ro.observe(el);
        return () => ro.disconnect();
    }, [spriteRightPx]);

    if (people.length === 0) return null;

    return (
        <div ref={layerRef} className="sprite-layer" aria-hidden="true">
            {people.map((p) => (
                <PixelPerson key={p.id} person={p} onWalkComplete={onWalkComplete} />
            ))}
        </div>
    );
}
