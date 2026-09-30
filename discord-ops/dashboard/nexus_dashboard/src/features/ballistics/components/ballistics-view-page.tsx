"use client";

import * as React from "react";
import { PageContainer } from "@/components/layout/page-container";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Crosshair, Search, Target, Zap, Gauge, Timer } from "lucide-react";
import { WEAPON_DATABASE, CALIBER_INFO, type WeaponData } from "@/data/weapons";
import { cn } from "@/lib/utils";

export function BallisticsPage() {
  const [search, setSearch] = React.useState("");
  const [selectedCategory, setSelectedCategory] = React.useState<string>("all");

  const categories = ["all", ...Array.from(new Set(WEAPON_DATABASE.map(w => w.category)))];

  const filteredWeapons = WEAPON_DATABASE.filter(weapon => {
    const matchesSearch = weapon.name.toLowerCase().includes(search.toLowerCase()) ||
      weapon.caliber.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = selectedCategory === "all" || weapon.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const getDamageColor = (damage: number) => {
    if (damage >= 100) return "text-red-400";
    if (damage >= 70) return "text-orange-400";
    if (damage >= 50) return "text-yellow-400";
    return "text-green-400";
  };

  return (
    <PageContainer>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-end justify-between border-b border-primary/20 pb-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
                <Crosshair className="w-6 h-6 text-primary" />
              </div>
              <h2 className="text-3xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-primary to-purple-400 uppercase italic">
                Ballistics Laboratory
              </h2>
            </div>
            <p className="text-muted-foreground pl-1 text-sm font-mono tracking-wide max-w-md">
              // WEAPON_PERFORMANCE_ANALYSIS_AND_DAMAGE_CALCULATION
            </p>
          </div>
          <Badge variant="outline" className="text-xs border-emerald-500/20 bg-emerald-500/5 text-emerald-400">
            {filteredWeapons.length} Weapons Indexed
          </Badge>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search weapons or caliber..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 bg-background/50 border-border"
            />
          </div>
        </div>

        {/* Category Tabs */}
        <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
          <TabsList className="bg-black/40 border border-white/5">
            {categories.map(cat => (
              <TabsTrigger key={cat} value={cat} className="data-[state=active]:bg-primary/20">
                {cat === "all" ? "All Weapons" : cat}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {/* Weapons Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredWeapons.map((weapon, idx) => (
            <GlassCard key={idx} className="p-6 hover:border-primary/40 transition-all group">
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-white group-hover:text-primary transition-colors">
                      {weapon.name}
                    </h3>
                    <p className="text-xs text-muted-foreground uppercase tracking-widest">
                      {weapon.category}
                    </p>
                  </div>
                  <Badge variant="outline" className="text-[10px] border-primary/20 bg-primary/5">
                    {weapon.caliber}
                  </Badge>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-3 pt-4 border-t border-white/5">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-red-400" />
                    <div className="flex flex-col">
                      <span className="text-[10px] text-muted-foreground uppercase">Damage</span>
                      <span className={cn("text-sm font-bold font-mono", getDamageColor(weapon.damage))}>
                        {weapon.damage}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-yellow-400" />
                    <div className="flex flex-col">
                      <span className="text-[10px] text-muted-foreground uppercase">Velocity</span>
                      <span className="text-sm font-bold font-mono text-yellow-300">
                        {weapon.velocity}m/s
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Gauge className="w-4 h-4 text-blue-400" />
                    <div className="flex flex-col">
                      <span className="text-[10px] text-muted-foreground uppercase">ROF</span>
                      <span className="text-sm font-bold font-mono text-blue-300">
                        {weapon.rateOfFire}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Timer className="w-4 h-4 text-green-400" />
                    <div className="flex flex-col">
                      <span className="text-[10px] text-muted-foreground uppercase">Reload</span>
                      <span className="text-sm font-bold font-mono text-green-300">
                        {weapon.reloadTime}s
                      </span>
                    </div>
                  </div>
                </div>

                {/* Additional Info */}
                <div className="flex items-center justify-between pt-3 border-t border-white/5 text-xs">
                  <span className="text-muted-foreground">
                    Range: <span className="text-white font-mono">{weapon.range}m</span>
                  </span>
                  <span className="text-muted-foreground">
                    Mag: <span className="text-white font-mono">{weapon.magazineSize}</span>
                  </span>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>

        {filteredWeapons.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <Crosshair className="w-12 h-12 text-muted-foreground/20 mb-4" />
            <p className="text-muted-foreground">No weapons match your search criteria</p>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
export default BallisticsPage;
