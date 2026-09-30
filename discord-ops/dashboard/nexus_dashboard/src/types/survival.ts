// Survival Analytics Types

export interface SurvivalProfile {
  steam_id: string;
  player_name: string;
  total_playtime: number; // hours
  survival_score: number; // 0-100
  kills: number;
  deaths: number;
  kd_ratio: number;
  longest_survival: number; // hours
  favorite_weapon: string;
  preferred_zone: string;
  activity_pattern: 'aggressive' | 'defensive' | 'explorer' | 'builder';
  threat_level: 'low' | 'medium' | 'high' | 'extreme';
  last_seen: string;
  status: 'online' | 'offline' | 'deceased';
}

export interface NeuralActivity {
  id: string;
  timestamp: string;
  player_name: string;
  steam_id?: string; // Optional Steam ID for player identification
  console_id?: string; // Optional console ID (same as Steam ID in DayZ)
  activity_type: 'combat' | 'building' | 'looting' | 'movement' | 'interaction' | 'death' | 'spawn';
  intensity: number; // 0-100
  location: { x: number; y: number; z: number };
  details: string;
  threat_detected: boolean;
  anomaly_score: number; // 0-1
}

export interface SurvivalMetrics {
  total_survivors: number;
  active_now: number;
  avg_survival_time: number;
  total_deaths_24h: number;
  hotspot_zones: Array<{ zone: string; activity: number }>;
  threat_level: 'calm' | 'moderate' | 'elevated' | 'critical';
}
