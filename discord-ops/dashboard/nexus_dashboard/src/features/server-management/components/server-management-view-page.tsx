"use client";

import * as React from "react";
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { PageContainer } from '@/components/layout/page-container';
import { toast } from "sonner";
import { Save, RefreshCw, Zap, Package, Skull, Info, CloudSun, Shield, Activity } from "lucide-react";

type GasZone = {
  AreaName: string;
  enabled: boolean;
  Type: string;
  Data: {
    Pos: number[];
    Radius: number;
  };
};

export function ServerManagementPage() {
  const [loading, setLoading] = React.useState(false);
  const [gasZones, setGasZones] = React.useState<GasZone[]>([]);

  // Real DayZ Config Parameters
  const [zombieMaxCount, setZombieMaxCount] = React.useState(1000);
  const [animalMaxCount, setAnimalMaxCount] = React.useState(200);
  const [lootDamageMin, setLootDamageMin] = React.useState(0.0);
  const [lootDamageMax, setLootDamageMax] = React.useState(0.0);

  // Gameplay Settings
  const [disableBaseDamage, setDisableBaseDamage] = React.useState(false);
  const [staminaMax, setStaminaMax] = React.useState(100.0);

  // Weather Settings
  const [weatherReset, setWeatherReset] = React.useState(false);
  const [weatherEnable, setWeatherEnable] = React.useState(true);

  const fetchConfig = React.useCallback(async () => {
    setLoading(true);
    try {
      // Fetch gas zones
      const gasRes = await fetch('/api/server/config/gas-zones');
      const gasData = await gasRes.json();
      if (gasData.zones) setGasZones(gasData.zones);

      // Fetch globals config
      const globalsRes = await fetch('/api/server/config/globals');
      const globalsData = await globalsRes.json();
      if (globalsData.status === 'success' && globalsData.globals) {
        setZombieMaxCount(globalsData.globals.ZombieMaxCount ?? 1000);
        setAnimalMaxCount(globalsData.globals.AnimalMaxCount ?? 200);
        setLootDamageMin(globalsData.globals.LootDamageMin ?? 0.0);
        setLootDamageMax(globalsData.globals.LootDamageMax ?? 0.0);
      }

      // Fetch Gameplay config
      const gameplayRes = await fetch('/api/server/config/gameplay');
      const gameplayData = await gameplayRes.json();
      if (gameplayData.status === 'success' && gameplayData.gameplay) {
        setDisableBaseDamage(gameplayData.gameplay.disableBaseDamage ?? false);
        setStaminaMax(gameplayData.gameplay.staminaMax ?? 100.0);
      }

      // Fetch Weather config
      const weatherRes = await fetch('/api/server/config/weather');
      const weatherData = await weatherRes.json();
      if (weatherData.status === 'success' && weatherData.weather) {
        setWeatherReset(weatherData.weather.reset ?? false);
        setWeatherEnable(weatherData.weather.enable ?? true);
      }

    } catch (error) {
      toast.error("Failed to fetch server configuration");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const toggleAllGasZones = (enabled: boolean) => {
    setGasZones(zones => zones.map(z => ({ ...z, enabled })));
  };

  const toggleGasZone = (index: number) => {
    setGasZones(zones => zones.map((z, i) =>
      i === index ? { ...z, enabled: !z.enabled } : z
    ));
  };

  const saveGasZones = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/server/config/gas-zones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zones: gasZones })
      });
      const data = await res.json();
      if (data.status === 'success') toast.success("Gas zones configuration saved!");
      else toast.error(data.message || "Failed to save gas zones");
    } catch (error) {
      toast.error("Error saving gas zones");
    } finally {
      setLoading(false);
    }
  };

  const saveGlobalsSettings = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/server/config/globals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ZombieMaxCount: zombieMaxCount,
          AnimalMaxCount: animalMaxCount,
          LootDamageMin: lootDamageMin,
          LootDamageMax: lootDamageMax
        })
      });
      const data = await res.json();
      if (data.status === 'success') toast.success("Globals configuration saved!");
      else toast.error(data.message || "Failed to save globals");
    } catch (error) {
      toast.error("Error saving globals settings");
    } finally {
      setLoading(false);
    }
  };

  const saveGameplaySettings = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/server/config/gameplay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          disableBaseDamage: disableBaseDamage,
          staminaMax: staminaMax
        })
      });
      const data = await res.json();
      if (data.status === 'success') toast.success("Gameplay settings saved!");
      else toast.error(data.message || "Failed to save gameplay settings");
    } catch (error) {
      toast.error("Error saving gameplay settings");
    } finally {
      setLoading(false);
    }
  };

  const saveWeatherSettings = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/server/config/weather', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reset: weatherReset,
          enable: weatherEnable
        })
      });
      const data = await res.json();
      if (data.status === 'success') toast.success("Weather settings saved!");
      else toast.error(data.message || "Failed to save weather settings");
    } catch (error) {
      toast.error("Error saving weather settings");
    } finally {
      setLoading(false);
    }
  };


  // Preset handlers
  const setPristine = () => { setLootDamageMin(0.0); setLootDamageMax(0.0); };
  const setVanillaLoot = () => { setLootDamageMin(0.0); setLootDamageMax(0.82); };
  const setHighDamage = () => {
    setLootDamageMin(0.5);
    setLootDamageMax(1.0);
  };
  const setInfiniteStamina = () => { setStaminaMax(1200.0); }; // Mod default
  const setVanillaStamina = () => { setStaminaMax(100.0); };
  const setClearSkies = () => { setWeatherReset(false); setWeatherEnable(false); }; // Disable dynamic weather
  const setDynamicWeather = () => { setWeatherReset(true); setWeatherEnable(true); }; // Enable weather

  return (
    <PageContainer scrollable>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-primary">Server Management</h2>
            <p className="text-muted-foreground">
              Configure server gameplay settings, gas zones, and economy parameters.
            </p>
          </div>
          <Button onClick={fetchConfig} disabled={loading} variant="outline">
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Config
          </Button>
        </div>

        <Tabs defaultValue="economy" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="economy">Economy & Spawns</TabsTrigger>
            <TabsTrigger value="gameplay">Gameplay</TabsTrigger>
            <TabsTrigger value="weather">Weather</TabsTrigger>
            <TabsTrigger value="gas-zones">Gas Zones</TabsTrigger>
          </TabsList>

          <TabsContent value="economy" className="space-y-4">
            <GlassCard className="p-6">
              <div className="space-y-8">
                {/* Population Settings */}
                <div>
                  <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <Package className="h-5 w-5 text-primary" />
                    Population Limits (globals.xml)
                  </h3>
                  <div className="grid gap-6 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="zombie-count">Max Zombies (Global)</Label>
                      <div className="flex items-center gap-2">
                        <Input
                          id="zombie-count"
                          type="number"
                          min="0"
                          max="5000"
                          value={zombieMaxCount}
                          onChange={(e) => setZombieMaxCount(parseInt(e.target.value) || 0)}
                          className="flex-1"
                        />
                        <span className="text-sm text-muted-foreground w-20">
                          {zombieMaxCount === 1000 ? "1x (Vanilla)" : `${(zombieMaxCount / 1000).toFixed(1)}x`}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">Default: 1000. Higher values affect server FPS.</p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="animal-count">Max Animals (Global)</Label>
                      <div className="flex items-center gap-2">
                        <Input
                          id="animal-count"
                          type="number"
                          min="0"
                          max="1000"
                          value={animalMaxCount}
                          onChange={(e) => setAnimalMaxCount(parseInt(e.target.value) || 0)}
                          className="flex-1"
                        />
                        <span className="text-sm text-muted-foreground w-20">
                          {animalMaxCount === 200 ? "1x (Vanilla)" : `${(animalMaxCount / 200).toFixed(1)}x`}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">Default: 200.</p>
                    </div>
                  </div>
                </div>

                {/* Loot Condition Settings */}
                <div>
                  <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <Zap className="h-5 w-5 text-primary" />
                    Loot Condition
                  </h3>
                  <div className="space-y-6 p-4 rounded-lg border border-border bg-background/50">
                    <div className="flex justify-between items-center mb-4">
                      <p className="text-sm text-muted-foreground">
                        Configure damage range for spawned items. 0.0 = Pristine, 1.0 = Ruined.
                      </p>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={setPristine}>All Pristine</Button>
                        <Button size="sm" variant="outline" onClick={setVanillaLoot}>Vanilla</Button>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="flex justify-between">
                        <Label>Min Damage ({lootDamageMin.toFixed(2)})</Label>
                      </div>
                      <Slider value={[lootDamageMin]} min={0} max={1} step={0.01} onValueChange={(val) => setLootDamageMin(val[0])} />

                      <div className="flex justify-between">
                        <Label>Max Damage ({lootDamageMax.toFixed(2)})</Label>
                      </div>
                      <Slider value={[lootDamageMax]} min={0} max={1} step={0.01} onValueChange={(val) => setLootDamageMax(val[0])} />
                    </div>

                    <div className="flex items-center gap-2 p-2 bg-secondary/20 rounded text-sm text-secondary-foreground">
                      <Info className="w-4 h-4" />
                      <span>
                        {lootDamageMin === 0 && lootDamageMax === 0
                          ? "✨ All items will spawn 100% Pristine."
                          : "⚠️ Items will have random damage within this range."}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-4">
                  <Button onClick={saveGlobalsSettings} disabled={loading} className="w-full">
                    <Save className="mr-2 h-4 w-4" />
                    Save Economy & Spawn Settings
                  </Button>
                </div>
              </div>
            </GlassCard>
          </TabsContent>

          <TabsContent value="gameplay" className="space-y-4">
            <GlassCard className="p-6">
              <div className="space-y-8">
                <div>
                  <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Player & Stats
                  </h3>
                  <div className="space-y-4 p-4 rounded-lg border border-border bg-background/50">
                    <div className="flex justify-between items-center">
                      <div>
                        <Label className="text-base">Max Stamina</Label>
                        <p className="text-sm text-muted-foreground">Set max stamina (100 = Vanilla, 1200 = Modded/Infinite).</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Input
                          type="number"
                          value={staminaMax}
                          onChange={(e) => setStaminaMax(parseFloat(e.target.value))}
                          className="w-24"
                        />
                      </div>
                    </div>
                    <div className="flex gap-2 justify-end">
                      <Button size="sm" variant="outline" onClick={setVanillaStamina}>Reset to Vanilla (100)</Button>
                      <Button size="sm" variant="outline" onClick={setInfiniteStamina}>Reset to Mod (1200)</Button>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <Shield className="h-5 w-5 text-primary" />
                    Raid & Base Damage
                  </h3>
                  <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-background/50">
                    <div>
                      <Label className="text-base">Disable Base Damage</Label>
                      <p className="text-sm text-muted-foreground">If enabled, player bases cannot be damaged (Anti-Raid).</p>
                    </div>
                    <Switch checked={disableBaseDamage} onCheckedChange={setDisableBaseDamage} />
                  </div>
                </div>

                <div className="pt-4">
                  <Button onClick={saveGameplaySettings} disabled={loading} className="w-full">
                    <Save className="mr-2 h-4 w-4" />
                    Save Gameplay Settings
                  </Button>
                </div>
              </div>
            </GlassCard>
          </TabsContent>

          <TabsContent value="weather" className="space-y-4">
            <GlassCard className="p-6">
              <div className="space-y-6">
                <div>
                  <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <CloudSun className="h-5 w-5 text-primary" />
                    Weather Control
                  </h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Configure dynamic weather behavior (cfgweather.xml).
                  </p>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="p-4 rounded-lg border border-border bg-background/50 cursor-pointer hover:bg-muted/50 transition-colors" onClick={setClearSkies}>
                    <h4 className="font-medium mb-2">☀️ Clear Skies (Mod Default)</h4>
                    <p className="text-sm text-muted-foreground">Disables dynamic weather and resets logic. Forces static clear weather.</p>
                    <div className="mt-2 text-xs text-primary font-mono bg-primary/10 inline-block px-2 py-1 rounded">
                      enable="0", reset="0"
                    </div>
                  </div>
                  <div className="p-4 rounded-lg border border-border bg-background/50 cursor-pointer hover:bg-muted/50 transition-colors" onClick={setDynamicWeather}>
                    <h4 className="font-medium mb-2">🌧️ Dynamic Weather (Vanilla)</h4>
                    <p className="text-sm text-muted-foreground">Enables standard DayZ dynamic weather (rain, fog, wind).</p>
                    <div className="mt-2 text-xs text-secondary-foreground font-mono bg-secondary/20 inline-block px-2 py-1 rounded">
                      enable="1", reset="1"
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-background/50">
                    <Label>Enable Weather System</Label>
                    <Switch checked={weatherEnable} onCheckedChange={setWeatherEnable} />
                  </div>
                  <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-background/50">
                    <Label>Reset Weather on Startup</Label>
                    <Switch checked={weatherReset} onCheckedChange={setWeatherReset} />
                  </div>
                </div>

                <Button onClick={saveWeatherSettings} disabled={loading} className="w-full">
                  <Save className="mr-2 h-4 w-4" />
                  Save Weather Settings
                </Button>
              </div>
            </GlassCard>
          </TabsContent>

          <TabsContent value="gas-zones" className="space-y-4">
            <GlassCard className="p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-semibold flex items-center gap-2">
                      <Skull className="h-5 w-5 text-primary" />
                      Contaminated Areas
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Toggle individual gas zones (cfgEffectArea.json).
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={() => toggleAllGasZones(true)} variant="outline" size="sm">
                      Enable All
                    </Button>
                    <Button onClick={() => toggleAllGasZones(false)} variant="outline" size="sm">
                      Disable All
                    </Button>
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  {gasZones.map((zone, index) => (
                    <div key={index} className="flex items-center justify-between p-4 rounded-lg border border-border bg-background/50">
                      <div className="flex-1">
                        <p className="font-medium">{zone.AreaName}</p>
                        <p className="text-xs text-muted-foreground">
                          Radius: {zone.Data.Radius}m | Pos: [{zone.Data.Pos[0]}, {zone.Data.Pos[2]}]
                        </p>
                      </div>
                      <Switch
                        checked={zone.enabled}
                        onCheckedChange={() => toggleGasZone(index)}
                      />
                    </div>
                  ))}
                </div>

                <Button onClick={saveGasZones} disabled={loading} className="w-full">
                  <Save className="mr-2 h-4 w-4" />
                  Save Gas Zones Configuration
                </Button>
              </div>
            </GlassCard>
          </TabsContent>
        </Tabs>
      </div>
    </PageContainer>
  );
}
export default ServerManagementPage;
