export interface DayZObject {
  name: string;
  pos: [number, number, number];
  ypr: [number, number, number];
  scale?: number;
  enableCEPersistency?: number;
  customString?: string;
}

export interface DayZContainer extends DayZObject {
  items?: string[]; // Potential inventory items
  locked?: boolean;
}

export interface PatchCoordinate {
  x: number;
  z: number;
  radius?: number;
}
