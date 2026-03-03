// src/types/elevator.ts
// TypeScript interfaces matching the backend domain models

export type Direction = "UP" | "DOWN" | "IDLE";
export type ElevatorStatus = "IDLE" | "MOVING_UP" | "MOVING_DOWN" | "DOORS_OPEN" | "MAINTENANCE" | "EMERGENCY";
export type SchedulerStrategy = "nearest" | "direction_based" | "idle_preference";

export interface ElevatorState {
  id: number;
  name: string;
  current_floor: number;
  status: ElevatorStatus;
  direction: Direction;
  floor_queue: number[];
  passenger_count: number;
  capacity: number;
  color: string;
  floors_served: number;
}

export interface SystemStatus {
  elevators: ElevatorState[];
  floors: number;
  elevator_capacity: number;
  tick_interval_ms: number;
  scheduler_strategy: SchedulerStrategy;
  avg_wait_ms: number;
  vip_floors: number[];
  emergency_floor: number;
  pending_requests: number;
  passenger_groups: PassengerGroup[];
  elapsed_seconds?: number;
  active_requests?: Array<{ floor: number; direction: string }>;
}

export type PassengerGroupState = "WAITING" | "BOARDING" | "RIDING" | "DELIVERED";

export interface PassengerGroup {
  id: string;
  source_floor: number;
  dest_floor: number;
  direction: "UP" | "DOWN";
  total_count: number;
  waiting_count: number;
  riding_count: number;
  delivered_count: number;
  assigned_elevator_id: number | null;
  state: PassengerGroupState;
  spawned: boolean;
}

export interface ElevatorConfig {
  id: number;
  name: string;
  starting_floor: number;
  color: string;
}

export interface BuildingConfig {
  floors: number;
  elevator_capacity: number;
  floor_height_px: number;
}

export interface AppConfig {
  building: BuildingConfig;
  simulation: {
    tick_interval_ms: number;
    scheduler_strategy: string;
  };
  elevators: ElevatorConfig[];
  modes: {
    emergency_floor: number;
    vip_floors: number[];
    maintenance_ids: number[];
  };
}

export interface FlashMessage {
  id: string;
  text: string;
  timestamp: number;
  type?: 'pickup' | 'dropoff' | 'default';
}
