import {
  DayZContainer,
  DayZObject,
  PatchCoordinate
} from '@/types/dayz-structure';

export class PatchManager {
  private static instance: PatchManager;
  private patches: Map<string, any[]> = new Map();

  private constructor() { }

  public static getInstance(): PatchManager {
    if (!PatchManager.instance) {
      PatchManager.instance = new PatchManager();
    }
    return PatchManager.instance;
  }

  public registerPatch(name: string, data: any[]): void {
    if (!data || !Array.isArray(data)) {
      console.warn(`[PatchManager] Invalid data for patch: ${name}`);
      return;
    }
    this.patches.set(name, data);
    console.log(`[PatchManager] Registered patch: ${name} with ${data.length} entries`);
  }

  public getPatch(name: string): any[] | undefined {
    return this.patches.get(name);
  }

  public getAllContainers(): DayZContainer[] {
    const containers: DayZContainer[] = [];
    this.patches.forEach((data, name) => {
      // Use ONLY Generated Mission Spawns for the "Live" count (Official Source)
      if (name.includes('LockedContainers_Spawns')) {
        const patchContainers = data.filter(obj => {
          return obj.name && (obj.name.includes('Container') || obj.name.includes('Barrel') || obj.name.includes('Chest'));
        });
        containers.push(...patchContainers);
      }
    });
    return containers;
  }
}
